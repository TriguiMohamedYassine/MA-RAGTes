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

from src.config import BASE_DIR, CONTRACTS_DIR, OUTPUT_DIR


# ---------------------------------------------------------------------------
# Helpers : fichiers
# ---------------------------------------------------------------------------

def _extract_main_contract_name(contract_code: str) -> str:
    """
    Extrait le nom du contrat principal depuis le code Solidity.

    Stratégie :
      1. Ignore les interfaces (interface Xxx) et les contrats abstraits (abstract contract Xxx).
      2. Parmi les contrats concrets restants, prend le DERNIER — il s'agit généralement
         du contrat principal qui hérite/compose les autres.
      3. Fallback sur le premier match brut si aucun contrat concret n'est trouvé.
    """
    if not contract_code:
        return "GeneratedContract"

    # Retire les commentaires pour éviter les faux positifs
    code = re.sub(r"/\*.*?\*/", "", contract_code, flags=re.DOTALL)
    code = re.sub(r"//.*$", "", code, flags=re.MULTILINE)

    # Contrats concrets uniquement (ni interface, ni abstract)
    concrete = re.findall(
        r"(?<!abstract\s)(?<!interface\s)\bcontract\s+(\w+)",
        code,
    )
    # Filtre plus explicite : exclure les lignes précédées de abstract ou interface
    concrete_filtered = []
    for m in re.finditer(r"\b(abstract\s+contract|interface|contract)\s+(\w+)", code):
        keyword = m.group(1).strip()
        name    = m.group(2)
        if keyword == "contract":          # contrat concret
            concrete_filtered.append(name)

    if concrete_filtered:
        return concrete_filtered[-1]       # dernier contrat concret = contrat principal

    # Fallback : premier match brut
    fallback = re.search(r"\bcontract\s+(\w+)", code)
    return fallback.group(1) if fallback else "GeneratedContract"


def _ensure_contract_file(contract_code: str, source_filename: str | None = None) -> str:
    """
    Écrit le contrat dans CONTRACTS_DIR et retourne son chemin absolu.

    Si ``source_filename`` est fourni (ex: "SimpleSwap.sol"), il est utilisé
    directement comme nom de fichier — ce qui garantit la cohérence entre le
    fichier écrit et le nom attendu par Hardhat.
    Sinon, le nom est extrait du code Solidity via _extract_main_contract_name.
    """
    CONTRACTS_DIR.mkdir(parents=True, exist_ok=True)

    if source_filename:
        # Utilise le nom du fichier source original (sans chemin)
        contract_name = re.sub(r"\.sol$", "", source_filename, flags=re.IGNORECASE)
    else:
        contract_name = _extract_main_contract_name(contract_code)

    contract_path = CONTRACTS_DIR / f"{contract_name}.sol"
    contract_path.write_text(contract_code or "", encoding="utf-8")
    return str(contract_path)


def _read_relative_imports(sol_file_path: str) -> list[str]:
    """Extrait les chemins d'import relatifs d'un fichier Solidity."""
    with open(sol_file_path, "r", encoding="utf-8") as f:
        content = f.read()
    imports = re.findall(r'import\s+\{[^}]+\}\s+from\s+"([^"]+)";', content)
    return [p for p in imports if p.startswith(".")]


def _copy_contract_tree(contract_path: str, contracts_root: str, dest_dir: str) -> None:
    """Copie le contrat et ses imports relatifs en préservant l'arborescence."""
    visited: set[str] = set()

    def _copy(src: str) -> None:
        src = os.path.normpath(src)
        if src in visited:
            return
        visited.add(src)

        rel  = os.path.relpath(src, contracts_root)
        dest = os.path.join(dest_dir, rel)
        os.makedirs(os.path.dirname(dest), exist_ok=True)
        shutil.copyfile(src, dest)

        for imp in _read_relative_imports(src):
            child = os.path.normpath(os.path.join(os.path.dirname(src), imp))
            if os.path.exists(child) and child.endswith(".sol"):
                _copy(child)

    _copy(contract_path)


def _prepare_single_contract_sources(contract_path: str) -> str:
    """
    Crée .coverage_contracts/ avec uniquement le contrat ciblé et ses imports.
    Cela évite que hardhat coverage compile TOUS les contrats du projet.
    """
    temp_dir = str(BASE_DIR / ".coverage_contracts")
    if os.path.isdir(temp_dir):
        shutil.rmtree(temp_dir, ignore_errors=True)
    os.makedirs(temp_dir)

    contracts_root = str(CONTRACTS_DIR.resolve())
    abs_path       = os.path.abspath(contract_path)

    if abs_path.startswith(contracts_root + os.sep):
        _copy_contract_tree(abs_path, contracts_root, temp_dir)
    else:
        shutil.copyfile(contract_path, os.path.join(temp_dir, os.path.basename(contract_path)))

    return temp_dir


def _clean_hardhat_build_artifacts() -> None:
    """Supprime artifacts/ et cache/ pour forcer une recompilation propre."""
    for folder in ("artifacts", "cache"):
        path = BASE_DIR / folder
        if path.is_dir():
            shutil.rmtree(path, ignore_errors=True)


# ---------------------------------------------------------------------------
# Helpers : exécution
# ---------------------------------------------------------------------------

def _run_cmd(command: list[str], env_extra: dict | None = None) -> subprocess.CompletedProcess:
    """Lance une commande dans BASE_DIR avec fusion d'environnement optionnelle."""
    merged_env = os.environ.copy()
    if env_extra:
        merged_env.update(env_extra)

    try:
        return subprocess.run(
            command,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            shell=False,
            cwd=str(BASE_DIR),
            env=merged_env,
        )
    except FileNotFoundError:
        if os.name == "nt" and command and command[0] == "npx":
            return subprocess.run(
                ["npx.cmd", *command[1:]],
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                shell=False,
                cwd=str(BASE_DIR),
                env=merged_env,
            )
        raise


def _summarize_hardhat_error(output: str) -> str:
    """Extrait le message d'erreur Hardhat le plus pertinent depuis la sortie brute."""
    if not output:
        return "Erreur Hardhat inconnue."
    for pattern in [
        r"Error\s+HH\d+:\s+.+",
        r"HardhatError:\s+HH\d+:\s+.+",
        r"HardhatPluginError:\s+.+",
        r"TypeError:\s+.+",
    ]:
        m = re.search(pattern, output)
        if m:
            return m.group(0).strip()
    first = next((l.strip() for l in output.splitlines() if l.strip()), "")
    return first or "Erreur Hardhat inconnue."


def _coverage_artifacts_exist() -> bool:
    return (
        (BASE_DIR / "coverage" / "coverage-summary.json").exists()
        or (BASE_DIR / "coverage" / "coverage-final.json").exists()
    )


def _parse_stdout_stats(stdout: str) -> dict:
    """Fallback : extrait les stats depuis la sortie texte de Hardhat."""
    passes   = 0
    failures = 0
    m = re.search(r"(\d+)\s+passing", stdout or "")
    if m:
        passes = int(m.group(1))
    m = re.search(r"(\d+)\s+failing", stdout or "")
    if m:
        failures = int(m.group(1))
    if passes > 0 or failures > 0:
        print(f"[Executor] Fallback stdout → {passes} ✅  {failures} ❌")
        return {"stats": {"passes": passes, "failures": failures, "tests": passes + failures}}
    return {}


# ---------------------------------------------------------------------------
# Helpers : lecture des rapports
# ---------------------------------------------------------------------------

def _load_json(path) -> dict:
    try:
        p = BASE_DIR / path if isinstance(path, str) else path
        if p.exists():
            with open(p, "r", encoding="utf-8") as f:
                return json.load(f)
    except Exception as exc:
        print(f"[Executor] Lecture {path} échouée : {exc}")
    return {}


def _coverage_from_final_json(coverage_final: dict) -> dict:
    """
    Calcule les métriques de couverture depuis coverage-final.json
    quand coverage-summary.json est absent.
    """
    total_stmts = covered_stmts = 0
    total_funcs = covered_funcs = 0
    total_branches = covered_branches = 0

    for file_data in coverage_final.values():
        if not isinstance(file_data, dict):
            continue
        stmts = file_data.get("s", {})
        total_stmts   += len(stmts)
        covered_stmts += sum(1 for h in stmts.values() if h and h > 0)

        funcs = file_data.get("f", {})
        total_funcs   += len(funcs)
        covered_funcs += sum(1 for h in funcs.values() if h and h > 0)

        for hits in file_data.get("b", {}).values():
            if isinstance(hits, list):
                total_branches   += len(hits)
                covered_branches += sum(1 for h in hits if h and h > 0)

    def pct(cov, tot):
        return round((cov / tot) * 100, 2) if tot else 0

    # FIX : clé "statements" (cohérente avec orchestrator._print_execution_summary)
    return {
        "statements": pct(covered_stmts,   total_stmts),
        "functions":  pct(covered_funcs,   total_funcs),
        "branches":   pct(covered_branches, total_branches),
    }


def _build_cov_summary(coverage_report: dict) -> dict:
    if "total" in coverage_report:
        t = coverage_report["total"]
        return {
            # FIX : clé "statements" au lieu de "lines"
            "statements": t.get("statements", t.get("lines", {})).get("pct", 0),
            "functions":  t.get("functions", {}).get("pct", 0),
            "branches":   t.get("branches",  {}).get("pct", 0),
        }
    elif coverage_report:
        return _coverage_from_final_json(coverage_report)
    return {"statements": 0, "functions": 0, "branches": 0}


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
    print("[Executor] Lancement de 'npx hardhat test'…")
    test_result = _run_cmd(
        ["npx", "hardhat", "test"],
        env_extra={"HARDHAT_SOURCES_PATH": f"./{os.path.basename(coverage_sources_dir)}"},
    )
    if test_result.returncode != 0:
        combined = f"{test_result.stdout or ''}\n{test_result.stderr or ''}"
        print(f"[Executor] ⚠️  hardhat test → {_summarize_hardhat_error(combined)}")

    # ---- Étape 2 : hardhat coverage ----
    _clean_hardhat_build_artifacts()
    print("[Executor] Lancement de 'npx hardhat coverage'…")
    cov_result = _run_cmd(
        ["npx", "hardhat", "coverage"],
        env_extra={"HARDHAT_SOURCES_PATH": f"./{os.path.basename(coverage_sources_dir)}"},
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