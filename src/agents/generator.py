import json
import re

from langchain_core.output_parsers import StrOutputParser

from src.utils.prompts import GENERATOR_NORMAL_PROMPT, GENERATOR_CORRECTOR_PROMPT
from src.utils.advanced_rag import AdvancedRAG
from src.utils.llm import get_code_llm, invoke_with_retry
from src.config import OUTPUT_DIR


def _get_rag_context(state: dict) -> tuple[str, list[str]]:
    try:
        # Collection "langchain" = base data_rag (exemples de contrats & tests reels)
        rag = AdvancedRAG(collection_name="langchain")
        result = rag.retrieve(state.get("contract_code", ""))
        context = result.get("context", "Aucun contexte trouve.")
        detected_ercs = result.get("detected_ercs", [])
        print(f"[Generator] RAG data_rag OK")
        return context, detected_ercs
    except Exception as exc:
        print(f"[Generator] RAG echoue : {exc}")
        return "Aucun contexte RAG disponible.", []

def _extract_block(code: str, open_brace_pos: int) -> tuple[int, int] | None:
    depth = 0
    for i in range(open_brace_pos, len(code)):
        if code[i] == "{":
            depth += 1
        elif code[i] == "}":
            depth -= 1
            if depth == 0:
                return open_brace_pos, i
    return None


def _find_it_blocks(code: str) -> list[tuple[int, int]]:
    blocks: list[tuple[int, int]] = []
    it_header = re.compile(
        r"\bit\s*\([^,)]*(?:,[^)]*)??\)\s*,\s*(?:async\s*)?(?:function\s*\([^)]*\)|\([^)]*\)\s*=>)\s*\{",
        re.DOTALL,
    )
    for m in it_header.finditer(code):
        open_brace = m.end() - 1
        result = _extract_block(code, open_brace)
        if result is None:
            continue
        _, end_brace = result
        tail = re.match(r"\s*\)\s*;?\s*", code[end_brace + 1:])
        end_pos = end_brace + (len(tail.group(0)) if tail else 0)
        blocks.append((m.start(), end_pos))
    return blocks


def _remove_it_blocks_matching(code: str, predicate) -> str:
    blocks = _find_it_blocks(code)
    for start, end in reversed(blocks):
        block_text = code[start:end + 1]
        if predicate(block_text):
            code = code[:start] + code[end + 1:]
    return code


_FAKE_CONTRACT_PATTERNS = [
    r'.*getContractFactory\s*\(\s*["\']MaliciousContract["\']\s*\).*\n',
    r'.*getContractFactory\s*\(\s*["\']ReentrancyAttacker["\']\s*\).*\n',
    r'.*getContractFactory\s*\(\s*["\']Attacker["\']\s*\).*\n',
    r'.*getContractFactory\s*\(\s*["\']MockContract["\']\s*\).*\n',
    r'.*getContractFactory\s*\(\s*["\']FakeContract["\']\s*\).*\n',
]

_FAKE_VAR_NAMES = [
    "malicious", "attacker", "reentrancy", "reentrancyAttacker",
    "maliciousContract", "attackContract", "fakeContract", "mockContract",
]


def _remove_fake_contracts(code: str) -> str:
    if not code:
        return code

    for pattern in _FAKE_CONTRACT_PATTERNS:
        code = re.sub(pattern, "", code, flags=re.IGNORECASE)

    for var in _FAKE_VAR_NAMES:
        var_lower = var.lower()
        code = _remove_it_blocks_matching(
            code,
            lambda block, v=var_lower: v in block.lower(),
        )

    still_present = sum(1 for v in _FAKE_VAR_NAMES if v.lower() in code.lower())
    if still_present == 0:
        print("[CleanJS] Aucun contrat halluciné détecté.")
    else:
        print(f"[CleanJS] ⚠️  {still_present} référence(s) de faux contrat encore présente(s).")

    return code


def _clean_js_output(content: str) -> str:
    if not content:
        return ""

    print(f"[CleanJS] Début contenu (50 premiers chars) : {repr(content[:50])}")

    stripped = content.strip()
    if stripped.startswith("{"):
        try:
            data = json.loads(stripped)
            if "updated_test_code" in data:
                content = data["updated_test_code"]
                print(f"[CleanJS] JSON extrait : {len(content)} chars")
        except json.JSONDecodeError:
            m = re.search(
                r'"updated_test_code"\s*:\s*"((?:[^"\\]|\\.)*)"',
                stripped,
                re.DOTALL,
            )
            if m:
                content = m.group(1).encode().decode("unicode_escape")
                print(f"[CleanJS] JSON extrait via regex : {len(content)} chars")

    pattern = r"```(?:javascript|js)?(.*?)```"
    match = re.search(pattern, content, re.DOTALL)
    if match:
        content = match.group(1)
        print(f"[CleanJS] Fence Markdown extraite : {len(content)} chars")
    else:
        content = content.replace("```javascript", "").replace("```js", "").replace("```", "")

    content = content.strip()
    content = _remove_fake_contracts(content)

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


def _sanitize_tx_wait_usage(code: str) -> str:
    if not code:
        return code

    code = re.sub(
        r"^\s*await\s+tx\s*\.\s*wait\s*\([^\)]*\)\s*;\s*$",
        "",
        code,
        flags=re.MULTILINE,
    )

    code = re.sub(
        r"\b(const|let|var)\s+receipt\s*=\s*tx\s*;",
        r"\1 receipt = await tx.wait();",
        code,
    )

    read_call_assigned_tx = re.search(
        r"\b(?:const|let|var)\s+tx\s*=\s*await\s+\w+\.\s*(?:get\w*|retrieve|read|name|symbol|decimals|balanceOf|totalSupply)\s*\(",
        code,
        flags=re.IGNORECASE,
    )
    if read_call_assigned_tx:
        code = re.sub(
            r"^\s*await\s+tx\s*\.\s*wait\s*\([^\)]*\)\s*;\s*$",
            "",
            code,
            flags=re.MULTILINE,
        )
        code = re.sub(
            r"\b(const|let|var)\s+(\w+)\s*=\s*await\s+tx\s*\.\s*wait\s*\([^\)]*\)\s*;",
            r"\1 \2 = tx;",
            code,
        )

    return code


def _extract_contract_name(contract_code: str) -> str:
    match = re.search(r"\bcontract\s+(\w+)", contract_code)
    return match.group(1) if match else "Contract"


def _count_callable_api(contract_code: str) -> int:
    if not contract_code:
        return 0
    code = re.sub(r"/\*.*?\*/", "", contract_code, flags=re.DOTALL)
    code = re.sub(r"//.*$", "", code, flags=re.MULTILINE)
    pattern = r"\bfunction\s+\w+\s*\([^\)]*\)\s*(?:public|external)\b"
    return len(re.findall(pattern, code))


def _build_minimal_deploy_test(contract_name: str) -> str:
    return (
        'const { expect } = require("chai");\n'
        'const { ethers } = require("hardhat");\n\n'
        f'describe("{contract_name}", function () {{\n'
        '  it("should deploy successfully", async function () {\n'
        f'    const Factory = await ethers.getContractFactory("{contract_name}");\n'
        '    const instance = await Factory.deploy();\n'
        '    await instance.waitForDeployment();\n'
        '    expect(await instance.getAddress()).to.not.equal(ethers.ZeroAddress);\n'
        '  });\n'
        '});\n'
    )


def _sanitize_invalid_numeric_literals(code: str) -> str:
    if not code:
        return code

    result_lines: list[str] = []
    for line in code.splitlines():
        stripped = line.lstrip()
        if stripped.startswith("//") or stripped.startswith("*"):
            result_lines.append(line)
        else:
            line = re.sub(r"([\(,]\s*)-\d+(\s*[,\)])", r"\g<1>0\2", line)
            result_lines.append(line)
    return "\n".join(result_lines)


def _functions_with_explicit_revert(contract_code: str) -> set[str]:
    result: set[str] = set()
    if not contract_code:
        return result

    code = re.sub(r"/\*.*?\*/", "", contract_code, flags=re.DOTALL)
    code = re.sub(r"//.*$", "", code, flags=re.MULTILINE)

    fn_pattern = re.compile(
        r"function\s+(\w+)\s*\([^\)]*\)[^{;]*\{",
        flags=re.IGNORECASE,
    )

    for m in fn_pattern.finditer(code):
        fn_name = m.group(1)
        open_brace = m.end() - 1
        bounds = _extract_block(code, open_brace)
        if bounds is None:
            continue
        start, end = bounds
        body = code[start:end + 1]
        if re.search(r"\b(require|revert|assert)\b", body):
            result.add(fn_name)

    return result


def _count_callable_names(contract_code: str) -> list[str]:
    if not contract_code:
        return []
    code = re.sub(r"/\*.*?\*/", "", contract_code, flags=re.DOTALL)
    code = re.sub(r"//.*$", "", code, flags=re.MULTILINE)
    matches = re.findall(
        r"\bfunction\s+(\w+)\s*\([^\)]*\)\s*(?:public|external)\b",
        code,
        flags=re.IGNORECASE,
    )
    return list(dict.fromkeys(matches))


def _sanitize_impossible_revert_expectations(code: str, contract_code: str) -> str:
    if not code:
        return code

    reverting = _functions_with_explicit_revert(contract_code)

    if not reverting:
        code = _remove_it_blocks_matching(
            code,
            lambda block: ".to.be.reverted" in block,
        )
        return code

    non_reverting = [
        fn for fn in _count_callable_names(contract_code)
        if fn not in reverting
    ]
    for fn in non_reverting:
        fn_call = fn + "("
        code = _remove_it_blocks_matching(
            code,
            lambda block, f=fn_call: f in block and ".to.be.reverted" in block,
        )

    return code


def _prune_failing_tests(code: str, failed_titles: list) -> str:
    if not code or not failed_titles:
        return code

    titles_set = set(failed_titles)

    def _title_matches(block: str) -> bool:
        m = re.match(r'\bit\s*\(\s*[\'"](.+?)[\'"]\s*,', block)
        return bool(m and m.group(1) in titles_set)

    return _remove_it_blocks_matching(code, _title_matches)


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


def generator_normal_node(state: dict) -> dict:
    print("--- GENERATOR (NORMAL) ---")

    contract_code: str = state.get("contract_code", "")
    test_design: dict = state.get("test_design", {})
    contract_name = _extract_contract_name(contract_code)

    if _count_callable_api(contract_code) == 0:
        print("[Generator Normal] ℹ️  Aucune fonction callable détectée — génération d'un test minimal de déploiement.")
        test_code = _build_minimal_deploy_test(contract_name)
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
        raw = ""

    test_code = _sanitize_impossible_revert_expectations(
        _sanitize_invalid_numeric_literals(
            _sanitize_tx_wait_usage(_normalize_ethers_v6(_clean_js_output(raw)))
        ),
        contract_code,
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
        return {"test_code": _build_minimal_deploy_test(contract_name)}

    if not existing_code or not existing_code.strip():
        print("[Generator Corrector] ⚠️  test_code vide dans le state.")
    else:
        print(f"[Generator Corrector] Code existant : {existing_code.count(chr(10)) + 1} lignes.")

    if not analyzer_report:
        print("[Generator Corrector] ⚠️  analyzer_report vide.")

    failures = analyzer_report.get("failures", [])
    failed_titles = list({f["test"] for f in failures if isinstance(f, dict) and f.get("test")})
    base_code = _prune_failing_tests(existing_code, failed_titles)
    print(f"[Generator Corrector] {len(failed_titles)} test(s) supprimé(s) avant correction.")

    _save_artifact("base_code_before_correction.json", {"test_code": base_code})
    _save_artifact("analyzer_report.json",             analyzer_report)
    _save_artifact("failed_tests.json",                {"failed": failed_titles})

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
            "failed_tests_json": json.dumps(failed_titles, ensure_ascii=False),
            "analyzer_json":     json.dumps(analyzer_report, ensure_ascii=False),
        })
        print(f"[Generator Corrector] Réponse brute : {len(raw)} caractères.")
    except Exception as exc:
        print(f"[Generator Corrector] ❌ Erreur Codestral : {exc}")
        raw = existing_code

    corrected_code = _sanitize_impossible_revert_expectations(
        _sanitize_invalid_numeric_literals(
            _sanitize_tx_wait_usage(_normalize_ethers_v6(_clean_js_output(raw)))
        ),
        contract_code,
    )
    _log_code("Generator Corrector", corrected_code)

    return {"test_code": corrected_code}