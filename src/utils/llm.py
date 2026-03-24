"""
llm.py
------
Fournit les factories LLM et les utilitaires de retry/stats.

Deux modèles distincts :
  - mistral-large-latest : raisonnement, analyse, JSON structuré  (Analyser, Evaluator, RAG)
  - codestral-latest     : génération de code JS/Solidity         (Generator)
"""

import os
import time
from typing import Any

from langchain_mistralai import ChatMistralAI
from dotenv import load_dotenv

load_dotenv()

# ---------------------------------------------------------------------------
# Statistiques d'utilisation
# ---------------------------------------------------------------------------

_LLM_STATS: dict[str, Any] = {
    "calls": 0,
    "total_time_seconds": 0.0,
}


def reset_llm_stats() -> None:
    _LLM_STATS["calls"] = 0
    _LLM_STATS["total_time_seconds"] = 0.0


def get_llm_stats() -> dict[str, Any]:
    return dict(_LLM_STATS)


# ---------------------------------------------------------------------------
# Factories
# ---------------------------------------------------------------------------

def get_llm() -> ChatMistralAI:
    """
    LLM généraliste pour le raisonnement, l'analyse et les sorties JSON.
    Modèle : mistral-large-latest (par défaut) ou LLM_MODEL dans .env
    """
    api_key = os.getenv("MISTRAL_API_KEY", "")
    if not api_key:
        raise EnvironmentError("MISTRAL_API_KEY manquante.")

    return ChatMistralAI(
        model=os.getenv("LLM_MODEL", "mistral-large-latest"),
        temperature=float(os.getenv("LLM_TEMPERATURE", "0.0")),
        mistral_api_key=api_key,
    )


def get_code_llm() -> ChatMistralAI:
    """
    LLM spécialisé code pour la génération de tests JavaScript.
    Modèle : codestral-latest — entraîné spécifiquement sur du code.
    Préférer ce modèle pour tout ce qui produit du JS/Solidity.
    """
    api_key = os.getenv("MISTRAL_API_KEY", "")
    if not api_key:
        raise EnvironmentError("MISTRAL_API_KEY manquante.")

    return ChatMistralAI(
        model="codestral-latest",
        temperature=0,
        mistral_api_key=api_key,
    )


# ---------------------------------------------------------------------------
# Invocation avec retry
# ---------------------------------------------------------------------------

def invoke_with_retry(
    chain: Any,
    payload: dict,
    retries: int = 3,
    delay: float = 15.0,   # FIX : 2.0 → 15.0 pour absorber les rate limits Mistral (429)
) -> Any:
    """
    Invoque ``chain`` avec ``payload``, en réessayant jusqu'à ``retries`` fois.

    Args:
        chain:   Objet LangChain invocable (prompt | llm | parser).
        payload: Dictionnaire d'entrée.
        retries: Nombre maximum de tentatives.
        delay:   Délai en secondes entre tentatives.
                 FIX : augmenté à 15s pour respecter les quotas Mistral.

    Returns:
        Résultat de l'invocation.

    Raises:
        Exception: La dernière exception si toutes les tentatives échouent.
    """
    last_error: Exception | None = None

    for attempt in range(1, retries + 1):
        try:
            start   = time.perf_counter()
            result  = chain.invoke(payload)
            elapsed = time.perf_counter() - start

            _LLM_STATS["calls"] += 1
            _LLM_STATS["total_time_seconds"] += elapsed

            return result

        except Exception as exc:
            last_error = exc
            if attempt < retries:
                # FIX : délai exponentiel en cas de 429 pour mieux absorber le rate limit
                wait = delay * attempt if "429" in str(exc) else delay
                print(f"[LLM] Tentative {attempt}/{retries} échouée : {exc}. Retry dans {wait:.0f}s…")
                time.sleep(wait)

    raise last_error  # type: ignore[misc]