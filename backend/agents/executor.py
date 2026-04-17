"""
executor.py
-----------
Agent LangGraph responsable de l'exécution des tests Hardhat.

Version robuste inspirée d'une implémentation éprouvée, adaptée à notre
arborescence (BASE_DIR, CONTRACTS_DIR, OUTPUT_DIR depuis src/config.py).

Fonctionnalités :
  - Isolation du contrat dans .coverage_contracts/ pour hardhat coverage
  - Nettoyage des artefacts Hardhat entre test et coverage
  - Gestion du crash Windows UV_HANDLE_CLOSING (connu dans Hardhat coverage)
  - Fallback sur coverage-final.json si coverage-summary.json absent
  - Fallback sur parsing stdout si mochawesome.json absent
"""

import json
import os
import re
import shutil
import subprocess

from backend.config.settings import BASE_DIR, CONTRACTS_DIR, OUTPUT_DIR
from backend.utils.executor_utils import (
    _build_cov_summary,
    _clean_hardhat_build_artifacts,
    _coverage_artifacts_exist,
    _ensure_contract_file,
    _load_json,
    _parse_stdout_stats,
    _prepare_single_contract_sources,
    _run_cmd,
    _summarize_hardhat_error,
)

_HARDHAT_TEST_TIMEOUT_SECONDS = float(os.getenv("HARDHAT_TEST_TIMEOUT_SECONDS", "180"))
_HARDHAT_COVERAGE_TIMEOUT_SECONDS = float(os.getenv("HARDHAT_COVERAGE_TIMEOUT_SECONDS", "300"))


# ---------------------------------------------------------------------------
# Helpers : fichiers
# ---------------------------------------------------------------------------



# ---------------------------------------------------------------------------
# Nœud LangGraph
# ---------------------------------------------------------------------------

def executor_node(state: dict) -> dict:
    """
    Nœud LangGraph : EXECUTOR.

    Entrées : contract_code, test_code
    Sorties  : test_report, coverage_report, execution_summary
    """
    print("--- EXECUTOR ---")

    contract_code: str     = state.get("contract_code", "")
    test_code: str         = state.get("test_code", "")
    source_filename: str   = state.get("source_filename", "")  # nom du fichier .sol original

    # Écriture des fichiers sources
    (BASE_DIR / "test").mkdir(parents=True, exist_ok=True)
    test_path = BASE_DIR / "test" / "generated_test.js"
    test_path.write_text(test_code or "", encoding="utf-8")
    lines = (test_code or "").count("\n") + 1
    print(f"[Executor] Test écrit : {test_path} ({lines} lignes)")

    _clean_hardhat_build_artifacts()
    contract_path        = _ensure_contract_file(contract_code, source_filename or None)
    coverage_sources_dir = _prepare_single_contract_sources(contract_path)
    print(f"[Executor] Contrat : {contract_path}")
    print(f"[Executor] Sources coverage : {coverage_sources_dir}")

    # ---- Étape 1 : hardhat test ----
    print("[Executor] Lancement de 'npx --no-install hardhat test'…")
    test_result = _run_cmd(
        ["npx", "--no-install", "hardhat", "test"],
        env_extra={"HARDHAT_SOURCES_PATH": f"./{os.path.basename(coverage_sources_dir)}"},
        timeout_seconds=_HARDHAT_TEST_TIMEOUT_SECONDS,
    )
    if test_result.returncode != 0:
        combined = f"{test_result.stdout or ''}\n{test_result.stderr or ''}"
        print(f"[Executor] ⚠️  hardhat test → {_summarize_hardhat_error(combined)}")

    if test_result.returncode == 124:
        print("[Executor] ⛔ hardhat test bloque trop longtemps (timeout).")
        execution_summary = {
            "total": 0,
            "passed": 0,
            "failed": 1,
            "coverage": {"statements": 0, "branches": 0, "functions": 0},
            "commands": {
                "test_returncode": test_result.returncode,
                "coverage_returncode": None,
            },
        }
        return {
            "test_report": {
                "stats": {"passes": 0, "failures": 1, "tests": 1},
                "results": [],
                "error": "hardhat test timeout",
                "stderr": test_result.stderr or "",
            },
            "coverage_report": {},
            "execution_summary": execution_summary,
        }

    # ---- Étape 2 : hardhat coverage ----
    _clean_hardhat_build_artifacts()
    print("[Executor] Lancement de 'npx --no-install hardhat coverage'…")
    cov_result = _run_cmd(
        ["npx", "--no-install", "hardhat", "coverage"],
        env_extra={"HARDHAT_SOURCES_PATH": f"./{os.path.basename(coverage_sources_dir)}"},
        timeout_seconds=_HARDHAT_COVERAGE_TIMEOUT_SECONDS,
    )
    cov_stdout = (cov_result.stdout or "").strip()
    cov_stderr = (cov_result.stderr or "").strip()

    # Détection du crash Windows connu (UV_HANDLE_CLOSING) après écriture des rapports
    windows_crash = (
        cov_result.returncode != 0
        and _coverage_artifacts_exist()
        and "UV_HANDLE_CLOSING" in f"{cov_stdout}\n{cov_stderr}"
    )
    if cov_result.returncode != 0:
        if windows_crash:
            print("[Executor] ℹ️  Coverage terminé (crash Windows UV_HANDLE_CLOSING connu — rapports OK).")
        else:
            print(f"[Executor] ⚠️  hardhat coverage → {_summarize_hardhat_error(f'{cov_stdout}{cov_stderr}')}")

    # Nettoyage des sources temporaires
    if os.path.isdir(coverage_sources_dir):
        shutil.rmtree(coverage_sources_dir, ignore_errors=True)
    _clean_hardhat_build_artifacts()

    # ---- Lecture des rapports ----
    test_report: dict = _load_json(BASE_DIR / "mochawesome-report" / "mochawesome.json")
    if not test_report:
        print("[Executor] ⚠️  mochawesome.json absent — tentative parsing stdout…")
        test_report = _parse_stdout_stats(test_result.stdout)

    coverage_report: dict = _load_json(BASE_DIR / "coverage" / "coverage-summary.json")
    if not coverage_report:
        coverage_report = _load_json(BASE_DIR / "coverage" / "coverage-final.json")

    # ---- Stats ----
    passed      = test_report.get("stats", {}).get("passes",   0)
    failed      = test_report.get("stats", {}).get("failures", 0)
    total       = test_report.get("stats", {}).get("tests",    passed + failed)
    cov_summary = _build_cov_summary(coverage_report)

    print(f"[Executor] Tests  : {passed} ✅  {failed} ❌  (total {total})")
    print(f"[Executor] Coverage : statements {cov_summary.get('statements', 0):.1f}%  "
          f"branches {cov_summary.get('branches', 0):.1f}%  "
          f"functions {cov_summary.get('functions', 0):.1f}%")
    if total == 0:
        print("[Executor] ⚠️  Aucun test exécuté. Vérifiez le fichier de test généré.")

    # ---- Persistance OUTPUT_DIR ----
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    if test_report:
        with open(OUTPUT_DIR / "test_report.json", "w") as f:
            json.dump(test_report, f, indent=2)
    if coverage_report:
        with open(OUTPUT_DIR / "coverage_report.json", "w") as f:
            json.dump(coverage_report, f, indent=2)
    with open(OUTPUT_DIR / "generated_test.js", "w", encoding="utf-8") as f:
        f.write(test_code)

    execution_summary = {
        "total":    total,
        "passed":   passed,
        "failed":   failed,
        "coverage": cov_summary,
        "commands": {
            "test_returncode":     test_result.returncode,
            "coverage_returncode": 0 if windows_crash else cov_result.returncode,
        },
    }

    return {
        "test_report":       test_report,
        "coverage_report":   coverage_report,
        "execution_summary": execution_summary,
    }

