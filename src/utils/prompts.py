"""
prompts.py
----------
Définit tous les prompts LangChain utilisés dans le pipeline.

Convention : les accolades littérales dans les templates ChatPromptTemplate
doivent être doublées ({{ }}) pour ne pas être interprétées comme des
variables de substitution.
"""

from langchain_core.prompts import (
    ChatPromptTemplate,
    SystemMessagePromptTemplate,
    HumanMessagePromptTemplate,
)

# ---------------------------------------------------------------------------
# Règles communes injectées dans chaque prompt système
# ---------------------------------------------------------------------------

_GLOBAL_RULES = """
Tu es un expert Solidity, Hardhat, Mocha et test de smart contracts.

Règles absolues :
- Retourne du JSON strict (aucun texte en dehors du JSON)
- Sois déterministe et structuré
- N'hallucine pas de fonctions absentes du contrat
- Le JSON doit être parsable directement par Python json.loads()
"""

_COVERAGE_RULES = """
Consignes de couverture :
- Privilégie la couverture de branches (if/else, require)
- Inclus des tests de revert et des valeurs limites (0, max, entrée invalide)
"""

# ---------------------------------------------------------------------------
# TEST DESIGNER
# ---------------------------------------------------------------------------

TEST_DESIGNER_PROMPT = ChatPromptTemplate.from_messages([
    SystemMessagePromptTemplate.from_template(
        _GLOBAL_RULES + """
OBJECTIF : Concevoir une stratégie de tests complète pour le contrat Solidity fourni.

FORMAT DE SORTIE (JSON uniquement) :
{{
  "contract_name": "<nom>",
  "test_suites": [
    {{
      "suite_name": "<nom de la suite>",
      "test_cases": [
        {{
          "test_title": "<should…>",
          "target_function": "<fonction>",
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
=== CONTEXTE STANDARDS ERC ===
{erc_context}

=== USER STORY / EXIGENCES ===
{user_story}

=== CONTRAT SOLIDITY ===
{contract_code}
"""),
])

# ---------------------------------------------------------------------------
# GENERATOR — première génération
# ---------------------------------------------------------------------------

GENERATOR_NORMAL_PROMPT = ChatPromptTemplate.from_messages([
    SystemMessagePromptTemplate.from_template(
        _GLOBAL_RULES + _COVERAGE_RULES + """
OBJECTIF : Écrire le fichier de tests JavaScript à partir de la stratégie fournie.

Règles techniques :
- Utilise les matchers Chai : expect(await …).to.be.revertedWith(…)
- Utilise loadFixture et les standards Hardhat Ethers v6
- Retourne le code JS complet dans la clé "updated_test_code"

FORMAT DE SORTIE :
{{ "updated_test_code": "const {{ expect }} = require('chai');\\n…" }}
"""
    ),
    HumanMessagePromptTemplate.from_template("""
=== 1. STANDARDS ERC ===
{erc_context}

=== 2. EXEMPLES DE RÉFÉRENCE ===
{relevant_examples}

=== 3. CONTRAT SOLIDITY ===
{contract_code}

=== 4. STRATÉGIE DE TESTS (JSON) ===
{test_design_json}
"""),
])

# ---------------------------------------------------------------------------
# GENERATOR — correcteur / itération
# ---------------------------------------------------------------------------

GENERATOR_CORRECTOR_PROMPT = ChatPromptTemplate.from_messages([
    SystemMessagePromptTemplate.from_template(
        _GLOBAL_RULES + _COVERAGE_RULES + """
OBJECTIF : Corriger les tests JS existants pour les faire passer et améliorer
la couverture d'après le rapport de l'Analyser.

Retourne le code JS complet et corrigé dans la clé "updated_test_code".

FORMAT DE SORTIE :
{{ "updated_test_code": "const {{ expect }} = require('chai');\\n…" }}
"""
    ),
    HumanMessagePromptTemplate.from_template("""
=== 1. STANDARDS ERC ===
{erc_context}

=== 2. EXEMPLES DE RÉFÉRENCE ===
{relevant_examples}

=== 3. CONTRAT SOLIDITY ===
{contract_code}

=== 4. CODE DE TESTS ACTUEL ===
{test_code}

=== 5. TESTS EN ÉCHEC ===
{failed_tests_json}

=== 6. RAPPORT DE L'ANALYSER ===
{analyzer_json}
"""),
])

# ---------------------------------------------------------------------------
# ANALYZER
# ---------------------------------------------------------------------------

ANALYZER_PROMPT = ChatPromptTemplate.from_messages([
    SystemMessagePromptTemplate.from_template(
        _GLOBAL_RULES + _COVERAGE_RULES + """
OBJECTIF : Analyser les tests et identifier les échecs, les fonctions/branches
non couvertes et les cas limites manquants.

FORMAT DE SORTIE :
{{
  "failures": [
    {{"test": "<nom>", "reason": "<pourquoi>", "fix": "<comment corriger>"}}
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
Contrat      : {contract_code}
Code de test : {test_code}
Rapport test : {mochawesome_json}
Couverture   : {coverage_json}
"""),
])

# ---------------------------------------------------------------------------
# EVALUATOR
# ---------------------------------------------------------------------------

EVALUATOR_PROMPT = ChatPromptTemplate.from_messages([
    SystemMessagePromptTemplate.from_template(
        _GLOBAL_RULES + """
CRITÈRES pour relancer la génération :
  - Nombre de tests en échec > 0
  - Couverture de branches < 80 %
  - Couverture des instructions < 85 %

FORMAT DE SORTIE :
{{ "decision": "stop|regenerate", "reason": "<explication claire>" }}
"""
    ),
    HumanMessagePromptTemplate.from_template("""
Résumé d'exécution : {execution_summary}
Rapport Analyser  : {analyzer_json}
"""),
])