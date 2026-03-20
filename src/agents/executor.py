# executor.py
import subprocess
import json
import os
import re
import shutil


def _ensure_contract_file(contract_code: str) -> str:
    """Write contract code to contracts/<ContractName>.sol so Hardhat can compile it."""
    os.makedirs("contracts", exist_ok=True)

    contract_name = "GeneratedContract"
    if contract_code:
        match = re.search(r"\bcontract\s+(\w+)", contract_code)
        if match:
            contract_name = match.group(1)

    contract_path = os.path.join("contracts", f"{contract_name}.sol")
    with open(contract_path, "w", encoding="utf-8") as f:
        f.write(contract_code or "")

    return contract_path


def _run_cmd(command, env=None):
    merged_env = os.environ.copy()
    if env:
        merged_env.update(env)

    try:
        return subprocess.run(
            command,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            shell=False,
            env=merged_env,
        )
    except FileNotFoundError:
        if os.name == "nt" and command and command[0] == "npx":
            fallback_command = ["npx.cmd", *command[1:]]
            return subprocess.run(
                fallback_command,
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                shell=False,
                env=merged_env,
            )
        raise


def _summarize_hardhat_error(output: str) -> str:
    """Return a short single-line Hardhat error summary from raw output."""
    if not output:
        return "Unknown Hardhat error."

    patterns = [
        r"Error\s+HH\d+:\s+.+",
        r"HardhatError:\s+HH\d+:\s+.+",
        r"HardhatPluginError:\s+.+",
        r"TypeError:\s+.+",
    ]
    for pattern in patterns:
        match = re.search(pattern, output)
        if match:
            return match.group(0).strip()

    first_non_empty = next((line.strip() for line in output.splitlines() if line.strip()), "")
    return first_non_empty or "Unknown Hardhat error."


def _coverage_artifacts_exist() -> bool:
    return os.path.exists(os.path.join("coverage", "coverage-summary.json")) or os.path.exists(
        os.path.join("coverage", "coverage-final.json")
    )


def _read_relative_imports(sol_file_path: str) -> list[str]:
    with open(sol_file_path, "r", encoding="utf-8") as f:
        content = f.read()
    imports = re.findall(r"import\s+\{[^}]+\}\s+from\s+\"([^\"]+)\";", content)
    return [path for path in imports if path.startswith(".")]


def _copy_contract_tree(contract_path: str, contracts_root: str, temp_sources_dir: str) -> None:
    """Copy target contract and relative imports while preserving source structure."""
    visited = set()

    def copy_recursive(src_path: str):
        src_path = os.path.normpath(src_path)
        if src_path in visited:
            return
        visited.add(src_path)

        rel_path = os.path.relpath(src_path, contracts_root)
        dest_path = os.path.join(temp_sources_dir, rel_path)
        os.makedirs(os.path.dirname(dest_path), exist_ok=True)
        shutil.copyfile(src_path, dest_path)

        for import_path in _read_relative_imports(src_path):
            child_src = os.path.normpath(os.path.join(os.path.dirname(src_path), import_path))
            if os.path.exists(child_src) and child_src.endswith(".sol"):
                copy_recursive(child_src)

    copy_recursive(contract_path)


def _prepare_single_contract_sources(contract_path: str) -> str:
    """Create a temporary sources folder with target contract and its relative imports."""
    temp_sources_dir = ".coverage_contracts"
    if os.path.isdir(temp_sources_dir):
        shutil.rmtree(temp_sources_dir, ignore_errors=True)

    os.makedirs(temp_sources_dir, exist_ok=True)
    contracts_root = os.path.abspath("contracts")
    abs_contract_path = os.path.abspath(contract_path)
    if abs_contract_path.startswith(contracts_root + os.sep):
        _copy_contract_tree(abs_contract_path, contracts_root, temp_sources_dir)
    else:
        target_name = os.path.basename(contract_path)
        shutil.copyfile(contract_path, os.path.join(temp_sources_dir, target_name))

    return temp_sources_dir


def _clean_hardhat_build_artifacts():
    """Remove Hardhat build folders so coverage compiles only the targeted sources."""
    for path in ("artifacts", "cache"):
        if os.path.isdir(path):
            shutil.rmtree(path, ignore_errors=True)


def _coverage_from_final_json(coverage_final: dict) -> dict:
    total_lines = covered_lines = 0
    total_functions = covered_functions = 0
    total_branches = covered_branches = 0

    for file_data in coverage_final.values():
        if not isinstance(file_data, dict):
            continue

        # Statement map and s counters let us derive line-like coverage ratio.
        statements = file_data.get("s", {})
        total_lines += len(statements)
        covered_lines += sum(1 for hit in statements.values() if hit and hit > 0)

        functions = file_data.get("f", {})
        total_functions += len(functions)
        covered_functions += sum(1 for hit in functions.values() if hit and hit > 0)

        branches = file_data.get("b", {})
        for branch_hits in branches.values():
            if isinstance(branch_hits, list):
                total_branches += len(branch_hits)
                covered_branches += sum(1 for hit in branch_hits if hit and hit > 0)

    def pct(covered, total):
        return round((covered / total) * 100, 2) if total else 0

    return {
        "lines": pct(covered_lines, total_lines),
        "functions": pct(covered_functions, total_functions),
        "branches": pct(covered_branches, total_branches),
    }

def executor_node(state):
    print("--- EXECUTOR ---")
    
    os.makedirs("test", exist_ok=True)
    _clean_hardhat_build_artifacts()

    contract_path = _ensure_contract_file(state.get("contract_code", ""))
    print(f"Contract file prepared: {contract_path}")

    coverage_sources_path = _prepare_single_contract_sources(contract_path)
    print(f"Coverage sources prepared: {coverage_sources_path}")
    
    # Run tests using Hardhat
    print("Running hardhat tests...")
    test_result = _run_cmd(
        ["npx", "hardhat", "test"],
        env={"HARDHAT_SOURCES_PATH": f"./{coverage_sources_path}"},
    )
    if test_result.returncode != 0:
        test_output = f"{test_result.stdout or ''}\n{test_result.stderr or ''}"
        print(f"Hardhat test failed: {_summarize_hardhat_error(test_output)}")

    # Avoid duplicate artifacts (contracts/ vs .coverage_contracts/) in coverage mode.
    _clean_hardhat_build_artifacts()
    
    # Run coverage using Hardhat
    print("Running hardhat coverage...")
    coverage_result = _run_cmd(
        ["npx", "hardhat", "coverage"],
        env={"HARDHAT_SOURCES_PATH": f"./{coverage_sources_path}"},
    )
    coverage_stdout = (coverage_result.stdout or "").strip()
    coverage_stderr = (coverage_result.stderr or "").strip()
    coverage_crash_after_write = (
        coverage_result.returncode != 0
        and _coverage_artifacts_exist()
        and "Assertion failed: !(handle->flags & UV_HANDLE_CLOSING)" in (coverage_stdout + "\n" + coverage_stderr)
    )

    if coverage_result.returncode != 0:
        if coverage_crash_after_write:
            print("Hardhat coverage finished, but process exited with a known Windows assertion after writing reports.")
        else:
            coverage_output = f"{coverage_stdout}\n{coverage_stderr}"
            print(f"Hardhat coverage failed: {_summarize_hardhat_error(coverage_output)}")

    if os.path.isdir(coverage_sources_path):
        shutil.rmtree(coverage_sources_path, ignore_errors=True)
    _clean_hardhat_build_artifacts()
    
    # Parse Mochawesome report
    test_report = {}
    test_report_path = os.path.join("mochawesome-report", "mochawesome.json")
    if os.path.exists(test_report_path):
        with open(test_report_path, "r") as f:
            try:
                test_report = json.load(f)
            except Exception as e:
                print(f"Failed to parse test report: {e}")
            
    # Parse Coverage report
    coverage_report = {}
    coverage_path = os.path.join("coverage", "coverage-summary.json")
    coverage_final_path = os.path.join("coverage", "coverage-final.json")
    if os.path.exists(coverage_path):
        with open(coverage_path, "r") as f:
            try:
                coverage_report = json.load(f)
            except Exception as e:
                print(f"Failed to parse coverage report: {e}")
    elif os.path.exists(coverage_final_path):
        with open(coverage_final_path, "r") as f:
            try:
                coverage_report = json.load(f)
            except Exception as e:
                print(f"Failed to parse coverage final report: {e}")
            
    # Calculate execution summary
    passed = 0
    failed = 0
    total = 0
    if test_report.get("stats"):
        total = test_report["stats"].get("tests", 0)
        passed = test_report["stats"].get("passes", 0)
        failed = test_report["stats"].get("failures", 0)
        
    cov_summary = {"lines": 0, "functions": 0, "branches": 0}
    if "total" in coverage_report:
        cov_summary = {
            "lines": coverage_report["total"].get("lines", {}).get("pct", 0),
            "functions": coverage_report["total"].get("functions", {}).get("pct", 0),
            "branches": coverage_report["total"].get("branches", {}).get("pct", 0),
        }
    elif coverage_report:
        cov_summary = _coverage_from_final_json(coverage_report)
        
    execution_summary = {
        "total": total,
        "passed": passed,
        "failed": failed,
        "coverage": cov_summary,
        "commands": {
            "test_returncode": test_result.returncode,
            "coverage_returncode": 0 if coverage_crash_after_write else coverage_result.returncode
        }
    }
    
    # Save to the new 'outputs' folder requested by the user
    os.makedirs("outputs", exist_ok=True)
    
    if test_report:
        with open("outputs/test_report.json", "w") as f:
            json.dump(test_report, f, indent=2)
            
    if coverage_report:
        with open("outputs/coverage_report.json", "w") as f:
            json.dump(coverage_report, f, indent=2)
            
    if os.path.exists("test/generated_test.js"):
        with open("outputs/generated_test.js", "w") as tf, open("test/generated_test.js", "r") as rf:
            tf.write(rf.read())
    
    print(f"Tests: {passed}/{total} passed, {failed} failed")
    if total == 0:
        print("No tests were executed. Check generated test file and LLM availability.")
    print(f"Coverage Summary: {cov_summary}")

    return {
        "test_report": test_report,
        "coverage_report": coverage_report,
        "execution_summary": execution_summary
    }
