import json
import re

from langchain_core.output_parsers import StrOutputParser

from backend.config.prompts import GENERATOR_NORMAL_PROMPT, GENERATOR_CORRECTOR_PROMPT
from backend.rag.advanced_rag import AdvancedRAG
from backend.utils.llm import get_code_llm, invoke_with_retry
from backend.config.settings import OUTPUT_DIR
from backend.utils.generator_utils import (
    _build_minimal_deploy_test,
    _clean_js_output,
    _count_callable_api,
    _deterministic_auto_fix_pass,
    _extract_contract_name,
    _get_rag_context,
    _log_code,
    _save_artifact,
)


GENERATOR_RAG_COLLECTION = "langchain"




def generator_normal_node(state: dict) -> dict:
    print("--- GENERATOR (NORMAL) ---")

    contract_code: str = state.get("contract_code", "")
    test_design: dict = state.get("test_design", {})
    contract_name = _extract_contract_name(contract_code)

    if _count_callable_api(contract_code) == 0:
        print("[Generator Normal] ℹ️  Aucune fonction callable détectée — génération d'un test minimal de déploiement.")
        test_code = _build_minimal_deploy_test(contract_name, contract_code)
        _log_code("Generator Normal", test_code)
        _save_artifact("test_code.json", {"test_code": test_code})
        return {"test_code": test_code}

    erc_context, detected_ercs = _get_rag_context(state)
    relevant_examples: str = ""

    llm = get_code_llm()
    chain = GENERATOR_NORMAL_PROMPT | llm | StrOutputParser()

    print("[Generator Normal] Appel Codestral via GENERATOR_NORMAL_PROMPT…")

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
        raw = _build_minimal_deploy_test(contract_name, contract_code)
        print("[Generator Normal] ℹ️  Fallback local activé (test minimal de déploiement).")

    test_code = _deterministic_auto_fix_pass(
        _clean_js_output(raw),
        contract_code=contract_code,
        analyzer_report=None,
    )
    _log_code("Generator Normal", test_code)
    _save_artifact("test_code.json", {"test_code": test_code})

    return {"test_code": test_code}


def generator_corrector_node(state: dict) -> dict:
    print("--- GENERATOR (CORRECTOR) ---")

    contract_code: str = state.get("contract_code", "")
    existing_code: str = state.get("test_code", "")
    analyzer_report: dict = state.get("analyzer_report", {})
    contract_name = _extract_contract_name(contract_code)

    if _count_callable_api(contract_code) == 0:
        print("[Generator Corrector] ℹ️  Contrat sans API callable — retour au test minimal de déploiement.")
        return {"test_code": _build_minimal_deploy_test(contract_name, contract_code)}

    if not existing_code or not existing_code.strip():
        print("[Generator Corrector] ⚠️  test_code vide dans le state.")
        # Evite un appel LLM inutile (et coûteux) quand il n'y a rien à corriger.
        fallback = _build_minimal_deploy_test(contract_name, contract_code)
        _log_code("Generator Corrector", fallback)
        return {"test_code": fallback}
    else:
        print(f"[Generator Corrector] Code existant : {existing_code.count(chr(10)) + 1} lignes.")

    if not analyzer_report:
        print("[Generator Corrector] ⚠️  analyzer_report vide.")

    failures = analyzer_report.get("failures", [])
    failed_titles = list({f["test"] for f in failures if isinstance(f, dict) and f.get("test")})
    # Conserver les tests en échec pour correction ciblée (approche générique multi-contrats).
    base_code = _deterministic_auto_fix_pass(
        existing_code,
        contract_code=contract_code,
        analyzer_report=analyzer_report,
    )
    print(f"[Generator Corrector] {len(failed_titles)} test(s) en échec à corriger.")

    if not base_code or not base_code.strip():
        print("[Generator Corrector] ℹ️  Code pruné vide — fallback local sans appel LLM.")
        fallback = _build_minimal_deploy_test(contract_name, contract_code)
        _log_code("Generator Corrector", fallback)
        return {"test_code": fallback}

    _save_artifact("base_code_before_correction.json", {"test_code": base_code})
    _save_artifact("analyzer_report.json",             analyzer_report)
    _save_artifact("failed_tests.json",                {"failed": failed_titles, "details": failures})

    erc_context, detected_ercs = _get_rag_context(state)
    relevant_examples: str = ""

    llm = get_code_llm()
    chain = GENERATOR_CORRECTOR_PROMPT | llm | StrOutputParser()

    print("[Generator Corrector] Appel Codestral via GENERATOR_CORRECTOR_PROMPT…")

    try:
        raw: str = invoke_with_retry(chain, {
            "erc_context":       erc_context,
            "relevant_examples": relevant_examples,
            "contract_code":     contract_code,
            "test_code":         base_code,
            "failed_tests_json": json.dumps(failures, ensure_ascii=False),
            "analyzer_json":     json.dumps(analyzer_report, ensure_ascii=False),
        })
        print(f"[Generator Corrector] Réponse brute : {len(raw)} caractères.")
    except Exception as exc:
        print(f"[Generator Corrector] ❌ Erreur Codestral : {exc}")
        raw = existing_code

    corrected_code = _deterministic_auto_fix_pass(
        _clean_js_output(raw),
        contract_code=contract_code,
        analyzer_report=analyzer_report,
    )
    _log_code("Generator Corrector", corrected_code)

    return {"test_code": corrected_code}

