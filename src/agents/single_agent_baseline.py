"""
single_agent_baseline.py
------------------------
Single-Agent Baseline (LLM-only):
- Une seule invocation LLM
- Génération complète en une passe
- Pas de retrieval, pas de boucle de feedback
"""

import json
import re
from pathlib import Path

from langchain_core.output_parsers import StrOutputParser

from src.utils.prompts import SINGLE_AGENT_BASELINE_PROMPT
from src.utils.llm import get_code_llm, invoke_with_retry
from src.config import BASE_DIR, OUTPUT_DIR


def _clean_js_output(content: str) -> str:
    """Extrait du JS brut depuis une réponse potentiellement encadrée."""
    if not content:
        return ""

    stripped = content.strip()
    if stripped.startswith("{"):
        try:
            data = json.loads(stripped)
            content = data.get("updated_test_code", content)
        except json.JSONDecodeError:
            pass

    match = re.search(r"```(?:javascript|js)?(.*?)```", content, re.DOTALL)
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
        "ethers.utils.parseEther(": "ethers.parseEther(",
        "ethers.utils.formatEther(": "ethers.formatEther(",
        "ethers.utils.parseUnits(": "ethers.parseUnits(",
        "ethers.utils.formatUnits(": "ethers.formatUnits(",
        ".deployed()": ".waitForDeployment()",
    }

    for old, new in replacements.items():
        code = code.replace(old, new)

    return code


def _save_artifact(filename: str, content) -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    path = OUTPUT_DIR / filename
    with open(path, "w", encoding="utf-8") as f:
        if isinstance(content, dict):
            json.dump(content, f, indent=2, ensure_ascii=False)
        else:
            f.write(content)


def _write_test_file(test_code: str) -> Path:
    """Write generated tests to Hardhat test directory."""
    test_dir = BASE_DIR / "test"
    test_dir.mkdir(parents=True, exist_ok=True)
    test_path = test_dir / "generated_test.js"
    test_path.write_text(test_code, encoding="utf-8")
    return test_path


def single_agent_baseline_node(state: dict) -> dict:
    """LangGraph baseline node: one-shot generation of the full test suite."""
    print("--- SINGLE AGENT BASELINE ---")

    llm = get_code_llm()
    chain = SINGLE_AGENT_BASELINE_PROMPT | llm | StrOutputParser()

    try:
        raw: str = invoke_with_retry(chain, {
            "contract_code": state.get("contract_code", ""),
            "user_story": state.get("user_story", ""),
        })
    except Exception as exc:
        print(f"[Baseline] LLM error: {exc}")
        raw = ""

    test_code = _normalize_ethers_v6(_clean_js_output(raw))
    print(f"[Baseline] Test suite générée : {test_code.count(chr(10)) + 1 if test_code else 0} lignes")

    _save_artifact("test_code.json", {"test_code": test_code})
    if test_code.strip():
        path = _write_test_file(test_code)
        print(f"[Baseline] Test écrit : {path}")
    return {"test_code": test_code}
