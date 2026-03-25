"""
prompts.py
----------
Définit tous les prompts LangChain utilisés dans le pipeline.

Convention : les accolades littérales dans les templates ChatPromptTemplate
doivent être doublées ({{ }}) pour ne pas être interprétées comme des
variables de substitution.

FIX : GENERATOR_NORMAL_PROMPT et GENERATOR_CORRECTOR_PROMPT demandent
désormais du JS brut (plus de JSON wrapper) pour éviter les problèmes
de parsing chez Codestral.
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
- Sois déterministe et structuré
- N'hallucine pas de fonctions absentes du contrat
"""

_JSON_RULES = """
FORMAT JSON OBLIGATOIRE :
- Retourne du JSON strict (aucun texte en dehors du JSON)
- Le JSON doit être parsable directement par Python json.loads()
"""

_COVERAGE_RULES = """
Consignes de couverture :
- Privilégie la couverture de branches (if/else, require)
- Inclus des tests de revert et des valeurs limites (0, max, entrée invalide)
"""

# FIX : règles spécifiques aux prompts de génération de code JS
_CODE_RULES = """
RÈGLES CRITIQUES pour le code généré :
- Utilise UNIQUEMENT les contrats présents dans le fichier Solidity fourni
- N'invente PAS de contrats auxiliaires (MaliciousContract, ReentrancyAttacker, Attacker, etc.)
- Si tu veux tester la réentrance, utilise uniquement le contrat principal
- N'utilise PAS ethers.utils.* — utilise ethers.parseEther(), ethers.parseUnits() directement
- N'utilise PAS .deployed() — utilise .waitForDeployment()
- Utilise loadFixture depuis @nomicfoundation/hardhat-toolbox/network-helpers
"""

# ---------------------------------------------------------------------------
# TEST DESIGNER
# ---------------------------------------------------------------------------

TEST_DESIGNER_PROMPT = ChatPromptTemplate.from_messages([
    SystemMessagePromptTemplate.from_template(
  _GLOBAL_RULES + _JSON_RULES + """
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
  === CONTEXTE CONTRAT ===
{erc_context}

=== USER STORY / EXIGENCES ===
{user_story}

=== CONTRAT SOLIDITY ===
{contract_code}
"""),
])

# ---------------------------------------------------------------------------
# GENERATOR — première génération
# FIX : demande du JS brut directement, plus de JSON wrapper
# ---------------------------------------------------------------------------

GENERATOR_NORMAL_PROMPT = ChatPromptTemplate.from_messages([
    SystemMessagePromptTemplate.from_template(
        _GLOBAL_RULES + _COVERAGE_RULES + _CODE_RULES + """
OBJECTIF : Écrire le fichier de tests JavaScript complet à partir de la stratégie fournie.

FORMAT DE SORTIE :
Retourne UNIQUEMENT le code JavaScript brut, sans aucun texte avant ou après,
sans balises Markdown, sans JSON wrapper.
Commence directement par la première ligne de code :
const {{ expect }} = require("chai");
"""
    ),
    HumanMessagePromptTemplate.from_template("""
  === 1. CONTEXTE CONTRAT ===
{erc_context}

=== 2. EXEMPLES ET BONNES PRATIQUES ===
{relevant_examples}

=== 3. CONTRAT SOLIDITY ===
{contract_code}

=== 4. STRATÉGIE DE TESTS (JSON) ===
{test_design_json}
"""),
])

# ---------------------------------------------------------------------------
# GENERATOR — correcteur / itération
# FIX : demande du JS brut directement, plus de JSON wrapper
# ---------------------------------------------------------------------------

GENERATOR_CORRECTOR_PROMPT = ChatPromptTemplate.from_messages([
    SystemMessagePromptTemplate.from_template(
        _GLOBAL_RULES + _COVERAGE_RULES + _CODE_RULES + """
OBJECTIF : Corriger les tests JS existants pour les faire passer et améliorer
la couverture d'après le rapport de l'Analyser.

Règles supplémentaires :
- Garde tous les tests existants qui passent
- Corrige uniquement les tests en échec listés dans le rapport
- Ajoute les tests manquants signalés dans le rapport
- Ne génère PAS de nouveaux contrats Solidity auxiliaires dans les tests

FORMAT DE SORTIE :
Retourne UNIQUEMENT le code JavaScript brut corrigé et complet,
sans aucun texte avant ou après, sans balises Markdown, sans JSON wrapper.
Commence directement par :
const {{ expect }} = require("chai");
"""
    ),
    HumanMessagePromptTemplate.from_template("""
  === 1. CONTEXTE CONTRAT ===
{erc_context}

=== 2. EXEMPLES ET BONNES PRATIQUES ===
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
# SINGLE-AGENT BASELINE — one-shot generation (LLM-only)
# ---------------------------------------------------------------------------

SINGLE_AGENT_BASELINE_PROMPT = ChatPromptTemplate.from_messages([
  SystemMessagePromptTemplate.from_template(
    _GLOBAL_RULES + _COVERAGE_RULES + _CODE_RULES + """
OBJECTIF : Générer en une seule passe le fichier de tests JavaScript complet
pour le contrat Solidity fourni.

Contraintes baseline :
- Une seule génération
- Aucun retrieval externe
- Aucune boucle de correction

FORMAT DE SORTIE :
Retourne UNIQUEMENT le code JavaScript brut, sans texte avant/après,
sans balises Markdown, sans JSON wrapper.
Commence directement par :
const {{ expect }} = require("chai");
"""
  ),
  HumanMessagePromptTemplate.from_template("""
=== USER STORY / EXIGENCES ===
{user_story}

=== CONTRAT SOLIDITY ===
{contract_code}
"""),
])

# ---------------------------------------------------------------------------
# ANALYZER
# ---------------------------------------------------------------------------

ANALYZER_PROMPT = ChatPromptTemplate.from_messages([
    SystemMessagePromptTemplate.from_template(
  _GLOBAL_RULES + _JSON_RULES + _COVERAGE_RULES + """
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
  _GLOBAL_RULES + _JSON_RULES + """
CRITÈRES pour relancer la génération (decision = "regenerate") :
  - Nombre de tests en échec > 0  ET  la cause est corrigeable (pas un contrat manquant)
  - Couverture de branches < 80 %
  - Couverture des instructions < 85 %

CRITÈRES pour arrêter (decision = "stop") :
  - Tous les tests passent (failures = 0)
  - OU couverture statements >= 85% ET branches >= 80% ET failures <= 0
  - OU les échecs restants sont dus à des contrats inexistants non corrigeables

FORMAT DE SORTIE :
{{ "decision": "stop|regenerate", "reason": "<explication claire>" }}
"""
    ),
    HumanMessagePromptTemplate.from_template("""
Résumé d'exécution : {execution_summary}
Rapport Analyser  : {analyzer_json}
"""),
])