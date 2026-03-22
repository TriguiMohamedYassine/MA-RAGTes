"""
main.py
-------
Point d'entrée du pipeline de génération automatique de tests pour smart contracts.

Usage :
    python main.py
"""

import glob
import shutil
import sys
from pathlib import Path

# Permet l'exécution directe (python main.py) sans installation du package
_ROOT = Path(__file__).parent.resolve()
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from src.workflows.orchestrator import build_graph
from src.utils.llm import get_llm_stats, reset_llm_stats
from src.config import CONTRACTS_DIR, OUTPUT_DIR, DEFAULT_CONTRACT_NAME


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def load_contract(contract_name: str | None = None) -> tuple[str, Path]:
    """
    Charge le code source Solidity du contrat.

    Cherche d'abord ``<contract_name>.sol`` dans CONTRACTS_DIR,
    puis prend le premier fichier .sol disponible si aucun nom n'est précisé.

    Returns:
        Tuple (code_source, chemin_du_fichier)

    Raises:
        FileNotFoundError: Si aucun contrat n'est trouvé.
    """
    if contract_name:
        path = CONTRACTS_DIR / f"{contract_name}.sol"
        if not path.exists():
            raise FileNotFoundError(
                f"Contrat introuvable : '{path}'\n"
                f"Placez votre fichier .sol dans '{CONTRACTS_DIR}'."
            )
    else:
        candidates = sorted(CONTRACTS_DIR.glob("*.sol"))
        if not candidates:
            raise FileNotFoundError(
                f"Aucun fichier .sol trouvé dans '{CONTRACTS_DIR}'."
            )
        path = candidates[0]

    return path.read_text(encoding="utf-8"), path


def load_user_story(contract_name: str) -> str:
    """
    Charge les spécifications utilisateur depuis ``<contract_name>.specs.md``
    si le fichier existe, sinon retourne une chaîne vide.
    """
    story_path = CONTRACTS_DIR / f"{contract_name}.specs.md"
    if story_path.exists():
        return story_path.read_text(encoding="utf-8")
    return ""


def clean_previous_outputs() -> None:
    """Supprime et recrée OUTPUT_DIR pour repartir d'un état propre."""
    if OUTPUT_DIR.exists():
        shutil.rmtree(OUTPUT_DIR, ignore_errors=True)
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    print("[Main] Artefacts précédents supprimés.")


# ---------------------------------------------------------------------------
# Point d'entrée
# ---------------------------------------------------------------------------

def main() -> None:
    reset_llm_stats()
    clean_previous_outputs()

    CONTRACTS_DIR.mkdir(parents=True, exist_ok=True)

    # --- Chargement du contrat ---
    try:
        contract_code, contract_path = load_contract(DEFAULT_CONTRACT_NAME)
        user_story = load_user_story(DEFAULT_CONTRACT_NAME)
        print(f"[Main] Contrat chargé : {contract_path}")
        if user_story:
            print(f"[Main] User story chargée ({len(user_story)} caractères).")
    except FileNotFoundError as exc:
        print(f"[Main] ❌ {exc}")
        sys.exit(1)

    # --- Construction du graphe LangGraph ---
    print("[Main] Construction du graphe LangGraph…")
    app = build_graph()

    # --- Exécution du pipeline ---
    initial_state = {
        "contract_code": contract_code,
        "user_story":    user_story,
        "iterations":    0,
    }

    print("[Main] Démarrage du pipeline…\n")
    for chunk in app.stream(initial_state):
        for node_name in chunk:
            print(f"[Main] ✅ Nœud terminé : {node_name}")

    # --- Résumé ---
    stats = get_llm_stats()
    print(
        f"\n[Main] Résumé LLM — appels : {stats['calls']}, "
        f"durée totale : {stats['total_time_seconds']:.2f}s"
    )


if __name__ == "__main__":
    main()