"""
prompts.py
----------
Définit les prompts LangChain utilisés dans le pipeline actif.

Etat actuel du workflow (orchestrator.py) :
  single_agent_baseline -> executor -> END

Le flux actif utilise uniquement SINGLE_AGENT_BASELINE_PROMPT.

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
- Sois déterministe et structuré
- N'hallucine pas de fonctions absentes du contrat
"""

_COVERAGE_RULES = """
Consignes de couverture :
- Privilégie la couverture de branches (if/else, require)
- Inclus des tests de revert et des valeurs limites (0, max, entrée invalide)
"""

_CODE_RULES = """
RÈGLES CRITIQUES pour le code généré :
- Utilise UNIQUEMENT les contrats présents dans le fichier Solidity fourni
- N'invente PAS de contrats auxiliaires (MaliciousContract, ReentrancyAttacker, Attacker, etc.)
- Si tu veux tester la réentrance, utilise uniquement le contrat principal
- N'utilise PAS ethers.utils.* — utilise ethers.parseEther(), ethers.parseUnits() directement
- N'utilise PAS .deployed() — utilise .waitForDeployment()
- Le fichier de test doit être autonome (pas d'import de tests externes)
- Préfère ethers + chai uniquement; tu peux utiliser loadFixture seulement si disponible
"""

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
- Le fichier doit être exécutable directement par Hardhat/Mocha
- N'utilise que les fonctions réellement présentes dans le contrat
- Couvre les chemins nominaux + reverts + cas limites
- Si le contrat expose un owner/admin, teste les permissions
- Si le contrat gère l'Ether, teste les montants nuls et invalides

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
