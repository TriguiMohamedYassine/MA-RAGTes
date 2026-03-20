# Smart Contract Test Automation - Project & Agent Guide

## 1) Project Purpose

This project automates Solidity test generation and refinement using a LangGraph multi-agent pipeline.

Input:
- Solidity contract source (from `contracts/<ContractName>.sol`)
- User story/specification (preferred extension: `.specs.md`)

Output:
- Generated test file: `test/generated_test.js`
- Execution artifacts in `outputs/`:
  - `generated_test_iter_<n>.js`
  - `test_report_iter_<n>.json`
  - `coverage_report_iter_<n>.json`

Main objective:
- Generate tests from requirements + contract code
- Execute tests and coverage
- Analyze failures/coverage gaps
- Iteratively improve tests up to a max of 5 iterations

---

## 2) High-Level Workflow

Entry point: `src/utils/main.py`

Runtime flow:
1. Clean previous artifacts (`outputs`, `coverage`, `mochawesome-report`, etc.)
2. Load contract code from `contracts/`
3. Load user story with the following priority:
   - `contracts/<ContractName>.specs.md`
   - `contracts/user_story.specs.md`
   - `contracts/<ContractName>.txt`
   - `contracts/user_story.txt`
4. Build LangGraph pipeline from `src/utils/orchestrator.py`
5. Stream node execution until stop condition

Pipeline graph:
- `test_designer` -> `generator_normal` -> `executor` -> `analyzer` -> `evaluator`
- If evaluator decision is `fix` or `improve`:
  - `generator_corrector` -> `executor` -> `analyzer` -> `evaluator`
- Stop when decision is `stop` or iteration count reaches 5

---

## 3) Agent-by-Agent Exact Responsibilities

### A) Test Designer Agent

File: `src/agents/test_designer.py`

Function:
- `test_designer_node(state)`

What it does exactly:
- Builds chain: `TEST_DESIGNER_PROMPT | LLM | JsonOutputParser()`
- Invokes with:
  - `contract_code`
  - `user_story`
- Produces structured test strategy JSON and stores it in `state["test_design"]`

Input state keys used:
- `contract_code`
- `user_story`

Output state keys:
- `test_design`

Notes:
- Uses retry-safe invocation (`invoke_with_retry`) to tolerate transient LLM issues.
- Prompt is requirement-first and does not use RAG.

---

### B) Generator Agent (Normal)

File: `src/agents/generator.py`

Function:
- `generator_normal_node(state)`

What it does exactly:
- Builds chain: `GENERATOR_NORMAL_PROMPT | LLM | JsonOutputParser()`
- Invokes with:
  - `contract_code`
  - `test_design_json` (JSON string of `test_design`)
- Extracts `test_code` from model output
- Writes `test/generated_test.js`
- Increments iteration counter by 1

Input state keys used:
- `contract_code`
- `test_design`
- `iterations`

Output state keys:
- `test_code`
- `iterations` (incremented)

Notes:
- This is first-pass test code generation from strategy.

---

### C) Generator Agent (Corrector)

File: `src/agents/generator.py`

Function:
- `generator_corrector_node(state)`

What it does exactly:
- Builds chain: `GENERATOR_CORRECTOR_PROMPT | LLM | JsonOutputParser()`
- Invokes with:
  - `contract_code`
  - `test_code` (current failing/incomplete tests)
  - `analyzer_json` (analysis report as JSON string)
- Extracts `updated_test_code`
- Overwrites `test/generated_test.js`
- Increments iteration counter by 1

Input state keys used:
- `contract_code`
- `test_code`
- `analyzer_report`
- `iterations`

Output state keys:
- `test_code` (updated)
- `iterations` (incremented)

Notes:
- Used only when evaluator returns `fix` or `improve`.

---

### D) Executor Agent

File: `src/agents/executor.py`

Function:
- `executor_node(state)`

What it does exactly:
- Ensures contract file exists by writing current `contract_code` to `contracts/<DetectedContractName>.sol`
- Runs Hardhat commands:
  - `npx hardhat test`
  - `npx hardhat coverage`
- Parses reports:
  - Test report: `mochawesome-report/mochawesome.json`
  - Coverage report: `coverage/coverage-summary.json` or fallback `coverage/coverage-final.json`
- Computes coverage percentages if needed from final coverage structure
- Handles known Windows assertion edge case after coverage output is already written:
  - If coverage artifacts exist and known UV assertion is detected, treats coverage command as effectively successful in summary
- Saves per-iteration artifacts in `outputs/`
- Returns execution summary and raw reports

Input state keys used:
- `contract_code`
- `iterations`

Output state keys:
- `test_report`
- `coverage_report`
- `execution_summary`

Notes:
- `execution_summary.commands.coverage_returncode` may be normalized to 0 for the known Windows post-write crash case.

---

### E) Analyzer Agent

File: `src/agents/analyzer.py`

Function:
- `analyzer_node(state)`

What it does exactly:
- Builds chain: `ANALYZER_PROMPT | LLM | JsonOutputParser()`
- Invokes with:
  - `contract_code`
  - `test_code`
  - `mochawesome_json` (serialized)
  - `coverage_json` (serialized)
- Produces structured analysis containing failures, missing coverage, and suggestions
- On LLM failure, returns fallback report to keep graph alive

Input state keys used:
- `contract_code`
- `test_code`
- `test_report`
- `coverage_report`

Output state keys:
- `analyzer_report`

Notes:
- Uses retry-safe invocation and has graceful fallback behavior.

---

### F) Evaluator Agent

File: `src/agents/evaluator.py`

Function:
- `evaluator_node(state)`

What it does exactly:
- Builds chain: `EVALUATOR_PROMPT | LLM | JsonOutputParser()`
- Invokes with:
  - `execution_summary` (serialized)
  - `analyzer_json` (serialized)
- Produces decision:
  - `fix`
  - `improve`
  - `stop`
- Returns decision + reason
- On LLM failure, defaults to `stop`

Input state keys used:
- `execution_summary`
- `analyzer_report`

Output state keys:
- `evaluation_decision`
- `evaluation_reason`

---

## 4) Orchestration Logic

File: `src/utils/orchestrator.py`

State schema (`GraphState`) includes:
- `contract_code`, `user_story`, `test_design`, `test_code`
- `test_report`, `coverage_report`, `execution_summary`
- `analyzer_report`
- `evaluation_decision`, `evaluation_reason`
- `iterations`

Decision logic:
- If `iterations >= 5` -> stop
- Else if evaluator decision in `{fix, improve}` -> go to `generator_corrector`
- Else -> stop

---

## 5) Prompt System and LLM

Prompt file:
- `src/utils/prompts.py`

LLM adapter:
- `src/utils/llm.py`

Current behavior:
- Uses Ollama model `codestral`
- JSON output enforced (`format="json"`)
- Temperature is deterministic (`0.0`)

---

## 6) Typical Run Command

From project root:

```bash
python src/utils/main.py
```

The script will print each completed node and produce generated artifacts automatically.
