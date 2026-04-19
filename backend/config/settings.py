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

BASE_DIR: Path = Path(__file__).parent.parent.parent.resolve()  # Navigate up from backend/config/

CONTRACTS_DIR: Path = BASE_DIR / "contracts" / "src"
OUTPUT_DIR:    Path = BASE_DIR / "outputs"
DATA_DIR:      Path = BASE_DIR / "data"
VECTOR_DB_DIR: Path = DATA_DIR / "vector_db"

# ---------------------------------------------------------------------------
# Paramètres de l'application
# ---------------------------------------------------------------------------

DEFAULT_CONTRACT_NAME: str = "Adoption"
DEFAULT_MAX_RETRIES: int = 7
DEFAULT_STATEMENT_COVERAGE_THRESHOLD: int = 85
DEFAULT_BRANCH_COVERAGE_THRESHOLD: int = 80

# ---------------------------------------------------------------------------
# Clés API
# ---------------------------------------------------------------------------

_MISTRAL_API_KEY: str = os.getenv("MISTRAL_API_KEY", "")


def get_mistral_api_key() -> str:
    """Retourne la clé Mistral en mémoire ou depuis l'environnement."""
    return _MISTRAL_API_KEY or os.getenv("MISTRAL_API_KEY", "")


def has_mistral_api_key() -> bool:
    """Indique si une clé API Mistral est configurée."""
    return bool(get_mistral_api_key().strip())


def set_mistral_api_key(value: str) -> None:
    """Met à jour la clé Mistral en mémoire et dans l'environnement du process."""
    global _MISTRAL_API_KEY
    clean = (value or "").strip()
    _MISTRAL_API_KEY = clean
    os.environ["MISTRAL_API_KEY"] = clean


def require_mistral_api_key() -> str:
    """Retourne la clé Mistral ou lève une erreur explicite si absente."""
    api_key = get_mistral_api_key()
    if not api_key:
        raise EnvironmentError(
            "La variable d'environnement MISTRAL_API_KEY est manquante. "
            "Ajoutez-la dans votre fichier .env ou dans l'environnement système."
        )
    return api_key
