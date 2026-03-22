"""
generator.py
------------
Agent LangGraph responsable de la génération et de la correction des tests JS.

Deux nœuds :
  - generator_normal_node    : première génération depuis le test_design
  - generator_corrector_node : correction itérative guidée par l'Analyser

Optimisations :
  - Le contexte RAG est mis en cache dans le state (clé 'rag_cache') pour
    éviter de refaire 3-4 appels LLM à chaque itération.
  - Modèle codestral-latest pour la génération de code JS.
"""

import json
import re
import time

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_mistralai import ChatMistralAI

from src.utils.advanced_rag import AdvancedRAG
from src.config import OUTPUT_DIR, MISTRAL_API_KEY


# ---------------------------------------------------------------------------
# LLM code
# ---------------------------------------------------------------------------

def _get_code_llm() -> ChatMistralAI:
    """Codestral : modèle spécialisé code, bien meilleur que mistral-large pour du JS."""
    return ChatMistralAI(
        model="codestral-latest",
        temperature=0,
        mistral_api_key=MISTRAL_API_KEY,
    )


# ---------------------------------------------------------------------------
# RAG avec cache dans le state
# ---------------------------------------------------------------------------

def _get_rag_context(state: dict) -> tuple[str, list[str]]:
    """
    Retourne (contexte_compressé, standards_détectés).

    Si le state contient déjà 'rag_cache', le réutilise sans rappeler le RAG.
    Sinon, exécute le pipeline RAG et stocke le résultat dans 'rag_cache'.

    Cela évite 3-4 appels LLM supplémentaires à chaque itération du pipeline.
    """
    cache = state.get("rag_cache")
    if cache:
        print("[Generator] RAG servi depuis le cache.")
        return cache["context"], cache["detected_ercs"]

    try:
        rag    = AdvancedRAG(collection_name="erc_standards")
        result = rag.retrieve(state.get("contract_code", ""))
        context       = result.get("context", "Aucun contexte trouvé.")
        detected_ercs = result.get("detected_ercs", [])
        print(f"[Generator] RAG OK — standards : {detected_ercs or ['Aucun']}")
        return context, detected_ercs
    except Exception as exc:
        print(f"[Generator] RAG échoué : {exc}")
        return "Aucun contexte RAG disponible.", []


# ---------------------------------------------------------------------------
# Helpers nettoyage JS
# ---------------------------------------------------------------------------

def _clean_js_output(content: str) -> str:
    """Supprime les fences Markdown et garantit les imports de base."""
    pattern = r"```(?:javascript|js)?(.*?)```"
    match   = re.search(pattern, content, re.DOTALL)
    if match:
        content = match.group(1)
    else:
        content = content.replace("```javascript", "").replace("```js", "").replace("```", "")
    content = content.strip()

    if 'require("chai")' not in content and "require('chai')" not in content:
        content = 'const { expect } = require("chai");\n' + content
    if 'require("hardhat")' not in content and "require('hardhat')" not in content:
        content = 'const { ethers } = require("hardhat");\n' + content
    return content


def _normalize_ethers_v6(code: str) -> str:
    if not code:
        return code
    replacements = {
        "ethers.utils.parseEther(":  "ethers.parseEther(",
        "ethers.utils.formatEther(": "ethers.formatEther(",
        "ethers.utils.parseUnits(":  "ethers.parseUnits(",
        "ethers.utils.formatUnits(": "ethers.formatUnits(",
        ".deployed()":               ".waitForDeployment()",
    }
    for old, new in replacements.items():
        code = code.replace(old, new)
    return code


def _extract_contract_name(contract_code: str) -> str:
    match = re.search(r"\bcontract\s+(\w+)", contract_code)
    return match.group(1) if match else "Contract"


def _prune_failing_tests(code: str, failed_titles: list) -> str:
    if not code or not failed_titles:
        return code
    for title in failed_titles:
        pattern = (
            r"it\(\s*['\"]" + re.escape(title)
            + r"['\"]\s*,\s*(?:async\s*)?(?:function\s*\([^)]*\)|\([^)]*\)\s*=>)\s*\{.*?\}\);\s*"
        )
        code = re.sub(pattern, "", code, flags=re.DOTALL)
    return code


def _save_artifact(filename: str, content) -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    path = OUTPUT_DIR / filename
    try:
        with open(path, "w", encoding="utf-8") as f:
            if isinstance(content, dict):
                json.dump(content, f, indent=2, ensure_ascii=False)
            else:
                f.write(content)
    except OSError as exc:
        print(f"[Generator] Impossible de sauvegarder {filename} : {exc}")


def _log_code(label: str, code: str) -> None:
    if not code or not code.strip():
        print(f"[{label}] ⚠️  Code vide.")
    else:
        print(f"[{label}] ✅ {code.count(chr(10)) + 1} lignes générées.")


# ---------------------------------------------------------------------------
# Nœud 1 : Génération initiale
# ---------------------------------------------------------------------------

def generator_normal_node(state: dict) -> dict:
    """
    Nœud LangGraph : GENERATOR (première passe).
    Utilise Codestral + RAG (avec cache) pour générer les tests Hardhat.
    """
    print("--- GENERATOR (NORMAL) ---")

    contract_code: str = state.get("contract_code", "")
    test_design: dict  = state.get("test_design", {})
    contract_name      = _extract_contract_name(contract_code)

    # RAG (avec cache)
    erc_context, detected_ercs = _get_rag_context(state)
    standards_label = ", ".join(detected_ercs) if detected_ercs else "Contrat générique"

    system_prompt = f"""Tu es un expert Blockchain QA Engineer spécialisé en Hardhat + Ethers v6.

CONTRAT : {contract_name}
STANDARDS DÉTECTÉS : {standards_label}

CONTEXTE ERC (RAG) :
{erc_context}

MISSION : Générer un fichier de tests Hardhat COMPLET et fonctionnel.

RÈGLES ABSOLUES :
1. Hardhat + Ethers v6 + Chai uniquement
2. loadFixture de @nomicfoundation/hardhat-toolbox/network-helpers
3. ethers.parseEther() / ethers.parseUnits() — jamais ethers.utils.*
4. .waitForDeployment() — jamais .deployed()
5. Reverts : expect(tx).to.be.revertedWith(...) ou revertedWithCustomError(...)
6. Couvre : happy paths, edge cases (0, max), reverts, events
7. Chaque describe() regroupe les tests par fonction
8. RETOURNE UNIQUEMENT du code JavaScript pur — aucun markdown, aucune explication
"""

    user_prompt = f"""=== STRATÉGIE DE TESTS ===
{json.dumps(test_design, indent=2, ensure_ascii=False)}

=== CODE SOLIDITY ===
{contract_code}
"""

    print("[Generator Normal] Appel Codestral…")
    time.sleep(1)

    try:
        response = _get_code_llm().invoke([
            SystemMessage(content=system_prompt),
            HumanMessage(content=user_prompt),
        ])
        raw = response.content
        print(f"[Generator Normal] Réponse brute : {len(raw)} caractères.")
    except Exception as exc:
        print(f"[Generator Normal] ❌ Erreur Codestral : {exc}")
        raw = ""

    test_code = _normalize_ethers_v6(_clean_js_output(raw))
    _log_code("Generator Normal", test_code)
    _save_artifact("test_code.json", {"test_code": test_code})

    # Stocke le cache RAG dans le state pour éviter de le recalculer
    rag_cache = {"context": erc_context, "detected_ercs": detected_ercs}
    return {"test_code": test_code, "rag_cache": rag_cache}


# ---------------------------------------------------------------------------
# Nœud 2 : Correction itérative
# ---------------------------------------------------------------------------

def generator_corrector_node(state: dict) -> dict:
    """
    Nœud LangGraph : GENERATOR (correcteur).
    Corrige les tests existants en s'appuyant sur le rapport de l'Analyser.
    Réutilise le cache RAG — aucun appel RAG supplémentaire.
    """
    print("--- GENERATOR (CORRECTOR) ---")

    contract_code: str    = state.get("contract_code", "")
    existing_code: str    = state.get("test_code", "")
    analyzer_report: dict = state.get("analyzer_report", {})
    contract_name         = _extract_contract_name(contract_code)

    # Diagnostics
    if not existing_code or not existing_code.strip():
        print("[Generator Corrector] ⚠️  test_code vide dans le state.")
    else:
        print(f"[Generator Corrector] Code existant : {existing_code.count(chr(10)) + 1} lignes.")

    if not analyzer_report:
        print("[Generator Corrector] ⚠️  analyzer_report vide.")

    # Supprime les tests cassés
    failures      = analyzer_report.get("failures", [])
    failed_titles = list({f["test"] for f in failures if isinstance(f, dict) and f.get("test")})
    base_code     = _prune_failing_tests(existing_code, failed_titles)
    print(f"[Generator Corrector] {len(failed_titles)} test(s) supprimé(s) avant correction.")

    # Artefacts de débogage
    _save_artifact("base_code_before_correction.json", {"test_code": base_code})
    _save_artifact("analyzer_report.json",  analyzer_report)
    _save_artifact("failed_tests.json",     {"failed": failed_titles})

    # RAG depuis le cache (pas de nouvel appel LLM)
    erc_context, detected_ercs = _get_rag_context(state)
    standards_label = ", ".join(detected_ercs) if detected_ercs else "Contrat générique"

    # Résumé des problèmes
    missing     = analyzer_report.get("missing_coverage", {})
    suggestions = analyzer_report.get("suggestions", [])
    problems    = []
    if failed_titles:
        problems.append(f"Tests en échec :\n" + "\n".join(f"  - {t}" for t in failed_titles))
    if missing.get("functions"):
        problems.append("Fonctions non couvertes :\n" + "\n".join(f"  - {f}" for f in missing["functions"]))
    if missing.get("branches"):
        problems.append("Branches non couvertes :\n" + "\n".join(f"  - {b}" for b in missing["branches"]))
    if missing.get("edge_cases"):
        problems.append("Cas limites manquants :\n" + "\n".join(f"  - {e}" for e in missing["edge_cases"]))
    if suggestions:
        problems.append("Suggestions :\n" + "\n".join(f"  - {s}" for s in suggestions))
    problems_text = "\n\n".join(problems) if problems else "Améliorer la couverture de branches (objectif ≥ 80%)."

    system_prompt = f"""Tu es un Senior Web3 QA Engineer spécialisé en Hardhat + Ethers v6.

CONTRAT : {contract_name}
STANDARDS : {standards_label}

CONTEXTE ERC :
{erc_context}

MISSION : Corriger et améliorer les tests Hardhat fournis.

PROBLÈMES À CORRIGER :
{problems_text}

RÈGLES :
1. Hardhat + Ethers v6 + Chai uniquement
2. loadFixture de @nomicfoundation/hardhat-toolbox/network-helpers
3. ethers.parseEther() / ethers.parseUnits() — jamais ethers.utils.*
4. .waitForDeployment() — jamais .deployed()
5. Garde tous les tests existants qui passent
6. Ajoute les tests manquants signalés ci-dessus
7. RETOURNE UNIQUEMENT du JavaScript pur — aucun markdown
"""

    user_prompt = f"""=== CODE DE TESTS ACTUEL ===
{base_code}

=== CODE SOLIDITY ===
{contract_code}
"""

    print("[Generator Corrector] Appel Codestral…")
    time.sleep(1)

    try:
        response = _get_code_llm().invoke([
            SystemMessage(content=system_prompt),
            HumanMessage(content=user_prompt),
        ])
        raw = response.content
        print(f"[Generator Corrector] Réponse brute : {len(raw)} caractères.")
    except Exception as exc:
        print(f"[Generator Corrector] ❌ Erreur Codestral : {exc}")
        raw = existing_code

    corrected_code = _normalize_ethers_v6(_clean_js_output(raw))
    _log_code("Generator Corrector", corrected_code)

    return {"test_code": corrected_code}