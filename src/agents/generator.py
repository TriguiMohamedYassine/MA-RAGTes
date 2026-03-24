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
  - FIX : utilise GENERATOR_NORMAL_PROMPT et GENERATOR_CORRECTOR_PROMPT
    définis dans prompts.py (cohérence avec le reste du pipeline).
"""

import json
import re
import time

from langchain_core.output_parsers import StrOutputParser

from src.utils.prompts import GENERATOR_NORMAL_PROMPT, GENERATOR_CORRECTOR_PROMPT
from src.utils.naive_rag import NaiveRAG
from src.utils.llm import get_code_llm, invoke_with_retry
from src.config import OUTPUT_DIR


# ---------------------------------------------------------------------------
# RAG avec cache dans le state
# ---------------------------------------------------------------------------

def _get_rag_context(state: dict) -> tuple[str, list[str]]:
    """
    Retourne (contexte_compressé, standards_détectés).

    Si le state contient déjà 'rag_cache', le réutilise sans rappeler le RAG.
    Sinon, exécute le pipeline RAG et stocke le résultat dans 'rag_cache'.
    """
    cache = state.get("rag_cache")
    if cache:
        print("[Generator] RAG servi depuis le cache.")
        return cache["context"], cache["detected_ercs"]

    try:
        rag    = NaiveRAG(collection_name="erc_standards")
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

# FIX : noms de contrats hallusinés par Codestral que Hardhat ne peut pas compiler
_FAKE_CONTRACT_PATTERNS = [
    r'.*getContractFactory\s*\(\s*["\']MaliciousContract["\']\s*\).*\n',
    r'.*getContractFactory\s*\(\s*["\']ReentrancyAttacker["\']\s*\).*\n',
    r'.*getContractFactory\s*\(\s*["\']Attacker["\']\s*\).*\n',
    r'.*getContractFactory\s*\(\s*["\']MockContract["\']\s*\).*\n',
    r'.*getContractFactory\s*\(\s*["\']FakeContract["\']\s*\).*\n',
]

# Noms de variables associés aux faux contrats (pour supprimer les lignes qui les utilisent)
_FAKE_VAR_NAMES = [
    "malicious", "attacker", "reentrancy", "reentrancyAttacker",
    "maliciousContract", "attackContract", "fakeContract", "mockContract",
]


def _remove_fake_contracts(code: str) -> str:
    """
    Supprime les blocs de tests qui référencent des contrats inexistants
    hallusinés par Codestral (MaliciousContract, ReentrancyAttacker, etc.).

    Stratégie en 2 passes :
      1. Supprime les lignes getContractFactory vers des contrats connus-faux.
      2. Supprime les blocs it() entiers qui utilisent ces variables.
    """
    if not code:
        return code

    # Passe 1 : supprime les lignes de factory/deploy des faux contrats
    for pattern in _FAKE_CONTRACT_PATTERNS:
        code = re.sub(pattern, "", code, flags=re.IGNORECASE)

    # Passe 2 : supprime les blocs it() qui contiennent des variables de faux contrats
    for var in _FAKE_VAR_NAMES:
        # Supprime les blocs it(...) { ... } qui contiennent la variable
        pattern = (
            r"it\s*\([^)]*\)\s*,\s*(?:async\s*)?(?:function\s*\([^)]*\)|\([^)]*\)\s*=>)\s*\{"
            r"[^}]*" + re.escape(var) + r"[^}]*\}\s*\);\s*"
        )
        code = re.sub(pattern, "", code, flags=re.DOTALL | re.IGNORECASE)

    removed_count = sum(
        1 for v in _FAKE_VAR_NAMES if v.lower() in code.lower()
    )
    if removed_count == 0:
        print("[CleanJS] Aucun contrat hallusiné détecté.")

    return code


def _clean_js_output(content: str) -> str:
    """
    Extrait le code JS brut depuis la réponse du LLM.

    Le LLM peut retourner :
      - Du JSON  {"updated_test_code": "..."}  (format des prompts)
      - Du code JS directement enveloppé dans des fences Markdown
      - Du code JS brut
    """
    if not content:
        return ""

    print(f"[CleanJS] Début contenu (50 premiers chars) : {repr(content[:50])}")

    # Cas 1 : réponse JSON avec clé "updated_test_code"
    stripped = content.strip()
    if stripped.startswith("{"):
        try:
            data = json.loads(stripped)
            if "updated_test_code" in data:
                content = data["updated_test_code"]
                print(f"[CleanJS] JSON extrait : {len(content)} chars")
        except json.JSONDecodeError:
            # Tentative regex si le JSON est mal formé
            m = re.search(
                r'"updated_test_code"\s*:\s*"((?:[^"\\]|\\.)*)"',
                stripped,
                re.DOTALL,
            )
            if m:
                content = m.group(1).encode().decode("unicode_escape")
                print(f"[CleanJS] JSON extrait via regex : {len(content)} chars")

    # Cas 2 : fences Markdown ```javascript / ```js / ```
    pattern = r"```(?:javascript|js)?(.*?)```"
    match   = re.search(pattern, content, re.DOTALL)
    if match:
        content = match.group(1)
        print(f"[CleanJS] Fence Markdown extraite : {len(content)} chars")
    else:
        content = content.replace("```javascript", "").replace("```js", "").replace("```", "")

    content = content.strip()

    # FIX : supprime les contrats hallusinés AVANT d'ajouter les imports
    content = _remove_fake_contracts(content)

    # Garantit les imports de base
    if 'require("chai")' not in content and "require('chai')" not in content:
        content = 'const { expect } = require("chai");\n' + content
    if 'require("hardhat")' not in content and "require('hardhat')" not in content:
        content = 'const { ethers } = require("hardhat");\n' + content

    print(f"[CleanJS] Résultat final : {content.count(chr(10)) + 1} lignes")
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

    FIX : utilise GENERATOR_NORMAL_PROMPT (prompts.py) + get_code_llm() (llm.py)
    au lieu de construire les messages manuellement.
    Réutilise le rag_cache produit par test_designer_node si présent.
    """
    print("--- GENERATOR (NORMAL) ---")

    contract_code: str = state.get("contract_code", "")
    test_design: dict  = state.get("test_design", {})

    # RAG (avec cache — si test_designer_node a déjà rempli rag_cache, pas de 2ème appel)
    erc_context, detected_ercs = _get_rag_context(state)

    relevant_examples = erc_context

    llm   = get_code_llm()
    chain = GENERATOR_NORMAL_PROMPT | llm | StrOutputParser()

    print("[Generator Normal] Appel Codestral via GENERATOR_NORMAL_PROMPT…")
    time.sleep(1)

    try:
        raw: str = invoke_with_retry(chain, {
            "erc_context":       erc_context,
            "relevant_examples": relevant_examples,
            "contract_code":     contract_code,
            "test_design_json":  json.dumps(test_design, indent=2, ensure_ascii=False),
        })
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

    FIX : utilise GENERATOR_CORRECTOR_PROMPT (prompts.py) + get_code_llm() (llm.py)
    au lieu de construire les messages manuellement.
    Réutilise le cache RAG — aucun appel RAG supplémentaire.
    """
    print("--- GENERATOR (CORRECTOR) ---")

    contract_code: str    = state.get("contract_code", "")
    existing_code: str    = state.get("test_code", "")
    analyzer_report: dict = state.get("analyzer_report", {})

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
    _save_artifact("analyzer_report.json",             analyzer_report)
    _save_artifact("failed_tests.json",                {"failed": failed_titles})

    # RAG depuis le cache (pas de nouvel appel LLM)
    erc_context, detected_ercs = _get_rag_context(state)
    relevant_examples = erc_context

    llm   = get_code_llm()
    chain = GENERATOR_CORRECTOR_PROMPT | llm | StrOutputParser()

    print("[Generator Corrector] Appel Codestral via GENERATOR_CORRECTOR_PROMPT…")
    time.sleep(1)

    try:
        raw: str = invoke_with_retry(chain, {
            "erc_context":       erc_context,
            "relevant_examples": relevant_examples,
            "contract_code":     contract_code,
            "test_code":         base_code,
            "failed_tests_json": json.dumps(failed_titles, ensure_ascii=False),
            "analyzer_json":     json.dumps(analyzer_report, ensure_ascii=False),
        })
        print(f"[Generator Corrector] Réponse brute : {len(raw)} caractères.")
    except Exception as exc:
        print(f"[Generator Corrector] ❌ Erreur Codestral : {exc}")
        raw = existing_code

    corrected_code = _normalize_ethers_v6(_clean_js_output(raw))
    _log_code("Generator Corrector", corrected_code)

    return {"test_code": corrected_code}