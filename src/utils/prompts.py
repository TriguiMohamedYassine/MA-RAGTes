"""
prompts.py
----------
Defines all LangChain prompts used in the pipeline.

Convention: literal braces in ChatPromptTemplate templates
must be doubled ({{ }}) so they are not interpreted as
substitution variables.

FIX: GENERATOR_NORMAL_PROMPT and GENERATOR_CORRECTOR_PROMPT now request
raw JS (no JSON wrapper) to avoid parsing issues with Codestral.
"""

from langchain_core.prompts import (
    ChatPromptTemplate,
    SystemMessagePromptTemplate,
    HumanMessagePromptTemplate,
)

# ---------------------------------------------------------------------------
# Shared rules injected into each system prompt
# ---------------------------------------------------------------------------

_GLOBAL_RULES = """
You are an expert in Solidity, Hardhat, Mocha, and smart contract testing.

Absolute rules:
- Be deterministic and structured
- Do not hallucinate functions that are not present in the contract
"""

_JSON_RULES = """
MANDATORY JSON FORMAT:
- Return strict JSON (no text outside JSON)
- JSON must be directly parseable by Python json.loads()
"""

_COVERAGE_RULES = """
Coverage guidance:
- Prioritize branch coverage (if/else, require)
- Include revert tests and boundary values (0, max, invalid input)
"""

# FIX: specific rules for JS code-generation prompts
_CODE_RULES = """
CRITICAL RULES for generated code:
- Use ONLY the contracts present in the provided Solidity file
- Do NOT invent helper contracts (MaliciousContract, ReentrancyAttacker, Attacker, etc.)
- If you want to test reentrancy, use only the main contract
- Do NOT use ethers.utils.* - use ethers.parseEther(), ethers.parseUnits() directly
- Do NOT use .deployed() - use .waitForDeployment()
- Use loadFixture from @nomicfoundation/hardhat-toolbox/network-helpers
"""

# ---------------------------------------------------------------------------
# TEST DESIGNER
# ---------------------------------------------------------------------------

TEST_DESIGNER_PROMPT = ChatPromptTemplate.from_messages([
    SystemMessagePromptTemplate.from_template(
  _GLOBAL_RULES + _JSON_RULES + """
GOAL: Design a complete testing strategy for the provided Solidity contract.

OUTPUT FORMAT (JSON only):
{{
  "contract_name": "<name>",
  "test_suites": [
    {{
      "suite_name": "<suite name>",
      "test_cases": [
        {{
          "test_title": "<should…>",
          "target_function": "<function>",
          "inputs": {{}},
          "expected_behavior": "…"
        }}
      ]
    }}
  ]
}}
"""
    ),
    HumanMessagePromptTemplate.from_template("""
  === CONTRACT CONTEXT ===
{erc_context}

=== USER STORY / REQUIREMENTS ===
{user_story}

=== SOLIDITY CONTRACT ===
{contract_code}
"""),
])

# ---------------------------------------------------------------------------
# GENERATOR - first generation
# FIX: request raw JS directly, no JSON wrapper
# ---------------------------------------------------------------------------

GENERATOR_NORMAL_PROMPT = ChatPromptTemplate.from_messages([
    SystemMessagePromptTemplate.from_template(
        _GLOBAL_RULES + _COVERAGE_RULES + _CODE_RULES + """
GOAL: Write the complete JavaScript test file from the provided strategy.

OUTPUT FORMAT:
Return ONLY raw JavaScript code, with no text before or after,
no Markdown fences, and no JSON wrapper.
Start directly with the first line of code:
const {{ expect }} = require("chai");
"""
    ),
    HumanMessagePromptTemplate.from_template("""
  === 1. CONTRACT CONTEXT ===
{erc_context}

=== 2. EXAMPLES AND BEST PRACTICES ===
{relevant_examples}

=== 3. SOLIDITY CONTRACT ===
{contract_code}

=== 4. TEST STRATEGY (JSON) ===
{test_design_json}
"""),
])

# ---------------------------------------------------------------------------
# GENERATOR - corrector / iteration
# FIX: request raw JS directly, no JSON wrapper
# ---------------------------------------------------------------------------

GENERATOR_CORRECTOR_PROMPT = ChatPromptTemplate.from_messages([
    SystemMessagePromptTemplate.from_template(
        _GLOBAL_RULES + _COVERAGE_RULES + _CODE_RULES + """
GOAL: Fix existing JS tests so they pass and improve
coverage based on the Analyzer report.

Additional rules:
- Keep all existing tests that pass
- Fix only the failing tests listed in the report
- Add the missing tests reported
- Do NOT generate new helper Solidity contracts in tests

OUTPUT FORMAT:
Return ONLY the corrected and complete raw JavaScript code,
with no text before or after, no Markdown fences, and no JSON wrapper.
Start directly with:
const {{ expect }} = require("chai");
"""
    ),
    HumanMessagePromptTemplate.from_template("""
  === 1. CONTRACT CONTEXT ===
{erc_context}

=== 2. EXAMPLES AND BEST PRACTICES ===
{relevant_examples}

=== 3. SOLIDITY CONTRACT ===
{contract_code}

=== 4. CURRENT TEST CODE ===
{test_code}

=== 5. FAILING TESTS ===
{failed_tests_json}

=== 6. ANALYZER REPORT ===
{analyzer_json}
"""),
])

# ---------------------------------------------------------------------------
# ANALYZER
# ---------------------------------------------------------------------------

ANALYZER_PROMPT = ChatPromptTemplate.from_messages([
    SystemMessagePromptTemplate.from_template(
  _GLOBAL_RULES + _JSON_RULES + _COVERAGE_RULES + """
GOAL: Analyze tests and identify failures, uncovered
functions/branches, and missing edge cases.

OUTPUT FORMAT:
{{
  "failures": [
    {{"test": "<name>", "reason": "<why>", "fix": "<how to fix>"}}
  ],
  "missing_coverage": {{
    "functions": [],
    "branches": [],
    "edge_cases": []
  }},
  "suggestions": []
}}
"""
    ),
    HumanMessagePromptTemplate.from_template("""
Contract    : {contract_code}
Test code   : {test_code}
Test report : {mochawesome_json}
Coverage    : {coverage_json}
"""),
])

# ---------------------------------------------------------------------------
# EVALUATOR
# ---------------------------------------------------------------------------

EVALUATOR_PROMPT = ChatPromptTemplate.from_messages([
    SystemMessagePromptTemplate.from_template(
  _GLOBAL_RULES + _JSON_RULES + """
CRITERIA to regenerate (decision = "regenerate"):
  - Number of failing tests > 0 AND the cause is fixable (not a missing contract)
  - Branch coverage < 80%
  - Statement coverage < 85%

CRITERIA to stop (decision = "stop"):
  - All tests pass (failures = 0)
  - OR statement coverage >= 85% AND branches >= 80% AND failures <= 0
  - OR remaining failures are caused by non-existent contracts that cannot be fixed

OUTPUT FORMAT:
{{ "decision": "stop|regenerate", "reason": "<clear explanation>" }}
"""
    ),
    HumanMessagePromptTemplate.from_template("""
Execution summary : {execution_summary}
Analyzer report   : {analyzer_json}
"""),
])