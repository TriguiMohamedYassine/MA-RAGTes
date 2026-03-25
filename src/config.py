"""
config.py
---------
Centralise toutes les constantes et variables d'environnement du projet.
"""

import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

# ---------------------------------------------------------------------------
# Chemins principaux
# ---------------------------------------------------------------------------

BASE_DIR: Path = Path(__file__).parent.parent.resolve()

CONTRACTS_DIR: Path = BASE_DIR / "contracts"
OUTPUT_DIR:    Path = BASE_DIR / "outputs"

# ---------------------------------------------------------------------------
# Paramètres de l'application
# ---------------------------------------------------------------------------

DEFAULT_CONTRACT_NAME: str = "CrowdFunding"
MAX_RETRIES: int = 7

# ---------------------------------------------------------------------------
# Clés API
# ---------------------------------------------------------------------------

MISTRAL_API_KEY: str = os.getenv("MISTRAL_API_KEY", "")

if not MISTRAL_API_KEY:
    raise EnvironmentError(
        "La variable d'environnement MISTRAL_API_KEY est manquante. "
        "Ajoutez-la dans votre fichier .env ou dans l'environnement système."
    )