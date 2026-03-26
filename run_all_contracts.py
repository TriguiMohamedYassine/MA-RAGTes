"""
run_all_contracts.py
--------------------
Run the LangGraph pipeline sequentially for all Solidity contracts in contracts/,
using their matching .specs.md user stories when available.

Outputs:
- Console table with coverage, pass/fail, API time/tokens
- outputs/batch_reports/batch_results.json
- outputs/batch_reports/batch_results.csv
- outputs/batch_reports/chart_tests_pass_fail.png
- outputs/batch_reports/chart_coverage.png
- outputs/batch_reports/chart_api_time_tokens.png
"""

from __future__ import annotations

import csv
import json
import shutil
import sys
import time
from pathlib import Path

import matplotlib.pyplot as plt

# Allow running directly with: python run_all_contracts.py
_ROOT = Path(__file__).parent.resolve()
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from src.config import BASE_DIR, CONTRACTS_DIR, OUTPUT_DIR
from src.utils.llm import get_llm_stats, reset_llm_stats
from src.workflows.orchestrator import build_graph


# Runtime artifacts cleaned between contract runs
_RUNTIME_DIRS_TO_CLEAN: list[Path] = [
    BASE_DIR / "coverage",
    BASE_DIR / "mochawesome-report",
    BASE_DIR / "artifacts",
    BASE_DIR / "cache",
    BASE_DIR / ".coverage_contracts",
    BASE_DIR / ".nyc_output",
]
_RUNTIME_FILES_TO_CLEAN: list[Path] = [
    BASE_DIR / "test" / "generated_test.js",
]


def clean_runtime_artifacts() -> None:
    """Clean build/test artifacts while preserving outputs/batch_reports."""
    for folder in _RUNTIME_DIRS_TO_CLEAN:
        if folder.exists():
            shutil.rmtree(folder, ignore_errors=True)

    for file_path in _RUNTIME_FILES_TO_CLEAN:
        if file_path.exists():
            try:
                file_path.unlink()
            except OSError:
                pass


def list_contract_files() -> list[Path]:
    return sorted(CONTRACTS_DIR.glob("*.sol"), key=lambda p: p.name.lower())


def load_user_story(contract_name: str) -> str:
    story_path = CONTRACTS_DIR / f"{contract_name}.specs.md"
    if story_path.exists():
        return story_path.read_text(encoding="utf-8")
    return ""


def extract_execution_metrics(final_state: dict) -> dict:
    summary = final_state.get("execution_summary", {}) if isinstance(final_state, dict) else {}
    coverage = summary.get("coverage", {}) if isinstance(summary, dict) else {}

    passed = int(summary.get("passed", 0) or 0)
    failed = int(summary.get("failed", 0) or 0)
    total = int(summary.get("total", passed + failed) or (passed + failed))

    return {
        "tests_total": total,
        "tests_passed": passed,
        "tests_failed": failed,
        "coverage_statements": float(coverage.get("statements", 0.0) or 0.0),
        "coverage_branches": float(coverage.get("branches", 0.0) or 0.0),
        "coverage_functions": float(coverage.get("functions", 0.0) or 0.0),
        "iterations": int(final_state.get("iterations", 0) or 0),
        "evaluation_decision": str(final_state.get("evaluation_decision", "")),
        "evaluation_reason": str(final_state.get("evaluation_reason", "")),
    }


def format_float(value: float) -> str:
    return f"{value:.2f}"


def print_results_table(results: list[dict]) -> None:
    if not results:
        print("No result to display.")
        return

    columns = [
        ("contract", "Contract"),
        ("iterations", "Iter"),
        ("coverage_statements", "Stmt%"),
        ("coverage_branches", "Br%"),
        ("coverage_functions", "Fn%"),
        ("tests_passed", "Pass"),
        ("tests_failed", "Fail"),
        ("api_time_seconds", "API_s"),
        ("api_total_tokens", "Tokens"),
    ]

    rows: list[list[str]] = []
    for item in results:
        rows.append(
            [
                str(item.get("contract", "")),
                str(int(item.get("iterations", 0) or 0)),
                format_float(float(item.get("coverage_statements", 0.0) or 0.0)),
                format_float(float(item.get("coverage_branches", 0.0) or 0.0)),
                format_float(float(item.get("coverage_functions", 0.0) or 0.0)),
                str(int(item.get("tests_passed", 0) or 0)),
                str(int(item.get("tests_failed", 0) or 0)),
                format_float(float(item.get("api_time_seconds", 0.0) or 0.0)),
                str(int(item.get("api_total_tokens", 0) or 0)),
            ]
        )

    widths = []
    for idx, (_, header) in enumerate(columns):
        max_width = len(header)
        for row in rows:
            max_width = max(max_width, len(row[idx]))
        widths.append(max_width)

    def line(parts: list[str]) -> str:
        return " | ".join(part.ljust(widths[idx]) for idx, part in enumerate(parts))

    headers = [header for _, header in columns]
    divider = "-+-".join("-" * width for width in widths)

    print("\nFINAL TABLE")
    print(line(headers))
    print(divider)
    for row in rows:
        print(line(row))


def save_results_files(results: list[dict], out_dir: Path) -> tuple[Path, Path]:
    out_dir.mkdir(parents=True, exist_ok=True)
    json_path = out_dir / "batch_results.json"
    csv_path = out_dir / "batch_results.csv"

    with open(json_path, "w", encoding="utf-8") as f_json:
        json.dump(results, f_json, indent=2, ensure_ascii=False)

    fieldnames = [
        "contract",
        "status",
        "tests_total",
        "tests_passed",
        "tests_failed",
        "coverage_statements",
        "coverage_branches",
        "coverage_functions",
        "elapsed_seconds",
        "api_calls",
        "api_time_seconds",
        "api_prompt_tokens",
        "api_completion_tokens",
        "api_total_tokens",
        "iterations",
        "evaluation_decision",
        "evaluation_reason",
        "error",
    ]

    with open(csv_path, "w", newline="", encoding="utf-8") as f_csv:
        writer = csv.DictWriter(f_csv, fieldnames=fieldnames)
        writer.writeheader()
        for item in results:
            writer.writerow({name: item.get(name, "") for name in fieldnames})

    return json_path, csv_path


def generate_graphs(results: list[dict], out_dir: Path) -> list[Path]:
    if not results:
        return []

    out_dir.mkdir(parents=True, exist_ok=True)

    contracts = [str(item.get("contract", "")) for item in results]
    passes = [int(item.get("tests_passed", 0) or 0) for item in results]
    fails = [int(item.get("tests_failed", 0) or 0) for item in results]
    stmt = [float(item.get("coverage_statements", 0.0) or 0.0) for item in results]
    branches = [float(item.get("coverage_branches", 0.0) or 0.0) for item in results]
    functions = [float(item.get("coverage_functions", 0.0) or 0.0) for item in results]
    api_time = [float(item.get("api_time_seconds", 0.0) or 0.0) for item in results]
    api_tokens = [int(item.get("api_total_tokens", 0) or 0) for item in results]

    saved_paths: list[Path] = []

    # Tests pass/fail chart
    fig1, ax1 = plt.subplots(figsize=(12, 6))
    ax1.bar(contracts, passes, label="Passed", color="#2E8B57")
    ax1.bar(contracts, fails, bottom=passes, label="Failed", color="#C0392B")
    ax1.set_title("Tests Passed vs Failed by Contract")
    ax1.set_ylabel("Tests")
    ax1.set_xlabel("Contracts")
    ax1.tick_params(axis="x", rotation=45)
    ax1.legend()
    fig1.tight_layout()
    chart1 = out_dir / "chart_tests_pass_fail.png"
    fig1.savefig(chart1, dpi=150)
    plt.close(fig1)
    saved_paths.append(chart1)

    # Coverage chart
    fig2, ax2 = plt.subplots(figsize=(12, 6))
    ax2.plot(contracts, stmt, marker="o", label="Statements %", color="#1F77B4")
    ax2.plot(contracts, branches, marker="o", label="Branches %", color="#FF7F0E")
    ax2.plot(contracts, functions, marker="o", label="Functions %", color="#2CA02C")
    ax2.axhline(85, linestyle="--", color="#1F77B4", alpha=0.4)
    ax2.axhline(80, linestyle="--", color="#FF7F0E", alpha=0.4)
    ax2.set_title("Coverage by Contract")
    ax2.set_ylabel("Coverage (%)")
    ax2.set_xlabel("Contracts")
    ax2.tick_params(axis="x", rotation=45)
    ax2.set_ylim(0, 100)
    ax2.legend()
    fig2.tight_layout()
    chart2 = out_dir / "chart_coverage.png"
    fig2.savefig(chart2, dpi=150)
    plt.close(fig2)
    saved_paths.append(chart2)

    # API cost chart
    fig3, ax3 = plt.subplots(figsize=(12, 6))
    ax3.bar(contracts, api_time, color="#8E44AD", alpha=0.7)
    ax3.set_ylabel("API Time (s)")
    ax3.set_xlabel("Contracts")
    ax3.tick_params(axis="x", rotation=45)

    ax4 = ax3.twinx()
    ax4.plot(contracts, api_tokens, marker="D", color="#16A085", linewidth=2)
    ax4.set_ylabel("API Total Tokens")

    ax3.set_title("API Time and Token Usage by Contract")
    fig3.tight_layout()
    chart3 = out_dir / "chart_api_time_tokens.png"
    fig3.savefig(chart3, dpi=150)
    plt.close(fig3)
    saved_paths.append(chart3)

    return saved_paths


def main() -> None:
    CONTRACTS_DIR.mkdir(parents=True, exist_ok=True)
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    contracts = list_contract_files()
    if not contracts:
        print(f"No .sol contract found in {CONTRACTS_DIR}")
        sys.exit(1)

    print(f"Detected {len(contracts)} contract(s). Building graph once...")
    app = build_graph()

    run_results: list[dict] = []

    for index, contract_path in enumerate(contracts, start=1):
        contract_name = contract_path.stem
        print(f"\n===== Contract {index}/{len(contracts)}: {contract_name} =====")

        clean_runtime_artifacts()

        contract_code = contract_path.read_text(encoding="utf-8")
        user_story = load_user_story(contract_name)
        print(
            f"User story: {'loaded' if user_story else 'missing'}"
            f" ({len(user_story)} chars)"
        )

        initial_state = {
            "contract_code": contract_code,
            "user_story": user_story,
            "iterations": 0,
        }

        result_row = {
            "contract": contract_name,
            "status": "success",
            "tests_total": 0,
            "tests_passed": 0,
            "tests_failed": 0,
            "coverage_statements": 0.0,
            "coverage_branches": 0.0,
            "coverage_functions": 0.0,
            "elapsed_seconds": 0.0,
            "api_calls": 0,
            "api_time_seconds": 0.0,
            "api_prompt_tokens": 0,
            "api_completion_tokens": 0,
            "api_total_tokens": 0,
            "iterations": 0,
            "evaluation_decision": "",
            "evaluation_reason": "",
            "error": "",
        }

        reset_llm_stats()
        run_start = time.perf_counter()

        try:
            final_state = app.invoke(initial_state)
            if isinstance(final_state, dict):
                result_row.update(extract_execution_metrics(final_state))
        except Exception as exc:
            result_row["status"] = "error"
            result_row["error"] = str(exc)
            print(f"Pipeline error: {exc}")

        elapsed = time.perf_counter() - run_start
        stats = get_llm_stats()

        result_row["elapsed_seconds"] = round(elapsed, 3)
        result_row["api_calls"] = int(stats.get("calls", 0) or 0)
        result_row["api_time_seconds"] = round(float(stats.get("total_time_seconds", 0.0) or 0.0), 3)
        result_row["api_prompt_tokens"] = int(stats.get("prompt_tokens", 0) or 0)
        result_row["api_completion_tokens"] = int(stats.get("completion_tokens", 0) or 0)
        result_row["api_total_tokens"] = int(stats.get("total_tokens", 0) or 0)

        run_results.append(result_row)

        print(
            f"Result {contract_name}: pass={result_row['tests_passed']}, "
            f"fail={result_row['tests_failed']}, "
            f"stmt={result_row['coverage_statements']:.1f}%, "
            f"api_time={result_row['api_time_seconds']:.2f}s, "
            f"tokens={result_row['api_total_tokens']}"
        )

    print_results_table(run_results)

    report_dir = OUTPUT_DIR / "batch_reports"
    json_path, csv_path = save_results_files(run_results, report_dir)
    chart_paths = generate_graphs(run_results, report_dir)

    total_api_calls = sum(int(item.get("api_calls", 0) or 0) for item in run_results)
    total_api_time = sum(float(item.get("api_time_seconds", 0.0) or 0.0) for item in run_results)
    total_tokens = sum(int(item.get("api_total_tokens", 0) or 0) for item in run_results)

    print("\nGenerated files:")
    print(f"- {json_path}")
    print(f"- {csv_path}")
    for chart in chart_paths:
        print(f"- {chart}")

    print(
        f"\nGlobal API summary: calls={total_api_calls}, "
        f"time={total_api_time:.2f}s, tokens={total_tokens}"
    )


if __name__ == "__main__":
    main()
