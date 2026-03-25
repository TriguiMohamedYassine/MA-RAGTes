"""
hardhat_executor.py
-------------------
Execute generated tests with Hardhat and print a concise execution summary.
"""

import json
import re
import subprocess
from pathlib import Path

from src.config import BASE_DIR, OUTPUT_DIR


def _run_command(command: str) -> tuple[int, str]:
    completed = subprocess.run(
        command,
        cwd=str(BASE_DIR),
        shell=True,
        capture_output=True,
        text=True,
        check=False,
    )
    output = (completed.stdout or "") + ("\n" + completed.stderr if completed.stderr else "")
    return completed.returncode, output


def _parse_test_counts(output: str) -> tuple[int, int, int]:
    passing_match = re.search(r"(\\d+)\\s+passing", output)
    failing_match = re.search(r"(\\d+)\\s+failing", output)
    passing = int(passing_match.group(1)) if passing_match else 0
    failing = int(failing_match.group(1)) if failing_match else 0
    total = passing + failing
    return passing, failing, total


def _load_coverage_summary() -> dict:
    summary_path = BASE_DIR / "coverage" / "coverage-summary.json"
    if not summary_path.exists():
        return {"statements": 0.0, "branches": 0.0, "functions": 0.0}

    try:
        data = json.loads(summary_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {"statements": 0.0, "branches": 0.0, "functions": 0.0}

    total = data.get("total", {})
    return {
        "statements": float(total.get("statements", {}).get("pct", 0.0)),
        "branches": float(total.get("branches", {}).get("pct", 0.0)),
        "functions": float(total.get("functions", {}).get("pct", 0.0)),
    }


def _save_json(filename: str, payload: dict) -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    path = OUTPUT_DIR / filename
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")


def hardhat_executor_node(state: dict) -> dict:
    """Run Hardhat test + coverage and expose structured execution results."""
    print("--- HARDHAT EXECUTOR ---")

    test_file = BASE_DIR / "test" / "generated_test.js"
    if not test_file.exists():
        print("[Executor] Aucun test généré trouvé.")
        empty_summary = {
            "total": 0,
            "passed": 0,
            "failed": 0,
            "coverage": {"statements": 0.0, "branches": 0.0, "functions": 0.0},
        }
        return {
            "test_report": {"return_code": 1, "output": "No generated test file."},
            "coverage_report": {"return_code": 1, "output": "Coverage skipped."},
            "execution_summary": empty_summary,
        }

    print("[Executor] Lancement de 'npx hardhat test test/generated_test.js'...")
    test_rc, test_out = _run_command("npx hardhat test test/generated_test.js")

    print("[Executor] Lancement de 'npx hardhat coverage --testfiles test/generated_test.js'...")
    cov_rc, cov_out = _run_command("npx hardhat coverage --testfiles test/generated_test.js")

    passed, failed, total = _parse_test_counts(test_out)
    coverage = _load_coverage_summary()

    summary = {
        "total": total,
        "passed": passed,
        "failed": failed,
        "coverage": coverage,
    }

    print(
        f"[Executor] Tests: {passed} passed, {failed} failed, total {total} | "
        f"Coverage: statements {coverage['statements']:.1f}%, "
        f"branches {coverage['branches']:.1f}%, functions {coverage['functions']:.1f}%"
    )

    print(f"[Executor] Return codes: hardhat test={test_rc}, hardhat coverage={cov_rc}")
    if test_rc != 0:
        excerpt = "\n".join((test_out or "").splitlines()[-20:])
        print("[Executor] hardhat test a echoue. Extrait:")
        print(excerpt)
    if cov_rc != 0:
        excerpt = "\n".join((cov_out or "").splitlines()[-20:])
        print("[Executor] hardhat coverage a echoue. Extrait:")
        print(excerpt)

    test_report = {"return_code": test_rc, "output": test_out}
    coverage_report = {"return_code": cov_rc, "output": cov_out}

    _save_json("test_report.json", test_report)
    _save_json("coverage_report.json", coverage_report)
    _save_json("execution_summary.json", summary)

    return {
        "test_report": test_report,
        "coverage_report": coverage_report,
        "execution_summary": summary,
    }
