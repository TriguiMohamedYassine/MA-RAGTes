# generator.py
import json
import os
import re
import subprocess
import tempfile
from langchain_core.output_parsers import JsonOutputParser
from src.utils.prompts import GENERATOR_NORMAL_PROMPT, GENERATOR_CORRECTOR_PROMPT
from src.utils.llm import get_llm, invoke_with_retry


def _validate_js_syntax(code: str) -> tuple[bool, str]:
    """Return whether JS syntax is valid using `node --check`."""
    if not code or not code.strip():
        return False, "Generated test code is empty."

    with tempfile.NamedTemporaryFile("w", suffix=".js", delete=False, encoding="utf-8") as tmp:
        tmp.write(code)
        tmp_path = tmp.name

    try:
        result = subprocess.run(
            ["node", "--check", tmp_path],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            shell=True,
        )
        if result.returncode == 0:
            return True, ""

        details = (result.stderr or result.stdout or "Unknown JS syntax error").strip()
        return False, details
    finally:
        try:
            os.remove(tmp_path)
        except OSError:
            pass


def _extract_test_code(result: dict, preferred_key: str, fallback_code: str = "") -> str:
    code = result.get(preferred_key, "") if isinstance(result, dict) else ""
    if not code and isinstance(result, dict):
        # Defensive fallback if model returns an alternate key
        code = result.get("test_code", "") or result.get("updated_test_code", "")
    return code or fallback_code


def _normalize_ethers_v6_test_code(code: str) -> str:
    """Normalize common ethers v5 patterns to ethers v6-compatible test syntax."""
    if not code:
        return code

    normalized = code
    replacements = {
        ".deployed()": ".waitForDeployment()",
        "ethers.constants.AddressZero": "ethers.ZeroAddress",
        "ethers.constants.MaxUint256": "ethers.MaxUint256",
    }
    for old, new in replacements.items():
        normalized = normalized.replace(old, new)

    return normalized


def _extract_failed_test_titles_from_report(test_report: dict) -> list[str]:
    """Extract failed test titles from a Mochawesome report."""
    failed_titles: list[str] = []

    def walk_suite(suite: dict):
        for test in suite.get("tests", []) or []:
            if test.get("state") == "failed":
                title = test.get("title") or test.get("fullTitle")
                if isinstance(title, str) and title.strip():
                    failed_titles.append(title.strip())

        for child in suite.get("suites", []) or []:
            if isinstance(child, dict):
                walk_suite(child)

    for result in test_report.get("results", []) or []:
        if isinstance(result, dict):
            walk_suite(result)

    return failed_titles


def _extract_failed_test_titles_from_analyzer(analyzer_report: dict) -> list[str]:
    """Extract failed test names from analyzer feedback."""
    titles: list[str] = []
    for failure in analyzer_report.get("failures", []) or []:
        if not isinstance(failure, dict):
            continue
        title = failure.get("test")
        if isinstance(title, str) and title.strip():
            titles.append(title.strip())
    return titles


def _find_test_block_end(code: str, match_end: int) -> int:
    """Find the end index of an `it(...)` block starting after match_end."""
    brace_start = code.find("{", match_end)
    if brace_start == -1:
        return -1

    depth = 0
    in_quote = ""
    escaped = False
    for idx in range(brace_start, len(code)):
        ch = code[idx]

        if in_quote:
            if escaped:
                escaped = False
                continue
            if ch == "\\":
                escaped = True
                continue
            if ch == in_quote:
                in_quote = ""
            continue

        if ch in ("'", '"', "`"):
            in_quote = ch
            continue

        if ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0:
                close_idx = code.find(");", idx)
                return close_idx + 2 if close_idx != -1 else idx + 1

    return -1


def _prune_failing_tests(test_code: str, failing_titles: list[str]) -> str:
    """Remove failing `it('...')` blocks so the corrector rewrites them instead of appending."""
    if not test_code or not failing_titles:
        return test_code

    spans: list[tuple[int, int]] = []
    for raw_title in failing_titles:
        title = raw_title.strip()
        if not title:
            continue

        # Try exact title first.
        candidates = [title]
        # Analyzer may provide long path-like names; keep a short fallback.
        if "  " in title:
            candidates.append(title.split("  ")[-1].strip())
        if "::" in title:
            candidates.append(title.split("::")[-1].strip())

        for candidate in candidates:
            pattern = re.compile(r"\bit\s*\(\s*([\"'])" + re.escape(candidate) + r"\1\s*,")
            for match in pattern.finditer(test_code):
                end_idx = _find_test_block_end(test_code, match.end())
                if end_idx != -1:
                    spans.append((match.start(), end_idx))

    if not spans:
        return test_code

    # Merge overlaps and remove from end to start.
    spans.sort()
    merged: list[tuple[int, int]] = []
    for start, end in spans:
        if not merged or start > merged[-1][1]:
            merged.append((start, end))
        else:
            merged[-1] = (merged[-1][0], max(merged[-1][1], end))

    pruned = test_code
    for start, end in reversed(merged):
        pruned = pruned[:start] + pruned[end:]

    return pruned

def generator_normal_node(state):
    print("--- GENERATOR (NORMAL) ---")
    llm = get_llm()
    chain = GENERATOR_NORMAL_PROMPT | llm
    parser = JsonOutputParser()
    
    message = invoke_with_retry(chain, {
        "contract_code": state.get("contract_code", ""),
        "test_design_json": json.dumps(state.get("test_design", {}))
    })
    result = parser.invoke(message)
    
    os.makedirs("test", exist_ok=True)
    test_code = _normalize_ethers_v6_test_code(_extract_test_code(result, "test_code"))
    is_valid, details = _validate_js_syntax(test_code)
    if not is_valid:
        raise ValueError(f"Generator produced invalid JavaScript test code: {details}")

    with open("test/generated_test.js", "w") as f:
        f.write(test_code)
        
    return {"test_code": test_code, "iterations": state.get("iterations", 0) + 1}

def generator_corrector_node(state):
    print("--- GENERATOR (CORRECTOR) ---")
    llm = get_llm()
    chain = GENERATOR_CORRECTOR_PROMPT | llm
    parser = JsonOutputParser()
    
    report_failed_titles = _extract_failed_test_titles_from_report(state.get("test_report", {}))
    analyzer_failed_titles = _extract_failed_test_titles_from_analyzer(state.get("analyzer_report", {}))

    # Prefer concrete Mochawesome failures and use analyzer as fallback/supplement.
    failed_titles = list(report_failed_titles)
    if not failed_titles:
        failed_titles.extend(analyzer_failed_titles)
    else:
        failed_titles.extend(title for title in analyzer_failed_titles if title not in failed_titles)

    # Preserve order, remove duplicates.
    seen = set()
    deduped_failed_titles = []
    for title in failed_titles:
        if title not in seen:
            seen.add(title)
            deduped_failed_titles.append(title)

    existing_test_code = state.get("test_code", "")
    replacement_base_code = _prune_failing_tests(existing_test_code, deduped_failed_titles)
    analyzer_json = json.dumps(state.get("analyzer_report", {}), indent=2)
    failed_tests_json = json.dumps(deduped_failed_titles, indent=2)

    os.makedirs("outputs", exist_ok=True)
    with open("outputs/test_code.json", "w", encoding="utf-8") as f:
        json.dump({"test_code": replacement_base_code}, f, indent=2)
    with open("outputs/analyzer_json.json", "w", encoding="utf-8") as f:
        f.write(analyzer_json)
    with open("outputs/failed_tests_json.json", "w", encoding="utf-8") as f:
        f.write(failed_tests_json)

    message = invoke_with_retry(chain, {
        "contract_code": state.get("contract_code", ""),
        "test_code": replacement_base_code,
        "analyzer_json": analyzer_json,
        "failed_tests_json": failed_tests_json,
    })
    result = parser.invoke(message)
    
    updated_code = _extract_test_code(
        result,
        "updated_test_code",
        fallback_code=existing_test_code,
    )
    updated_code = _normalize_ethers_v6_test_code(updated_code)
    is_valid, details = _validate_js_syntax(updated_code)
    if not is_valid:
        raise ValueError(f"Corrector produced invalid JavaScript test code: {details}")

    with open("test/generated_test.js", "w") as f:
        f.write(updated_code)
        
    return {"test_code": updated_code, "iterations": state.get("iterations", 0) + 1}
