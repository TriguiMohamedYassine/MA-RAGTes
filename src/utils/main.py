import os
import glob
import shutil
import sys

# Allow direct execution (python src/utils/main.py) by adding project root to PYTHONPATH.
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.abspath(os.path.join(CURRENT_DIR, "..", ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from src.utils.orchestrator import build_graph
from src.utils.llm import get_llm_stats, reset_llm_stats

DEFAULT_CONTRACT_NAME = "MetaCoin"  # Default contract name to look for if not specified by the user.


def load_contract_code(contract_name=None, contracts_dir="contracts"):
    if contract_name:
        contract_path = os.path.join(contracts_dir, f"{contract_name}.sol")
        if not os.path.exists(contract_path):
            raise FileNotFoundError(
                f"Contract file not found at '{contract_path}'."
            )
    else:
        contract_files = sorted(glob.glob(os.path.join(contracts_dir, "*.sol")))
        if not contract_files:
            raise FileNotFoundError(f"No Solidity contract found in '{contracts_dir}'.")
        contract_path = contract_files[0]

    with open(contract_path, "r", encoding="utf-8") as f:
        return f.read(), contract_path


def load_user_story(contract_name, contracts_dir="contracts"):
    # Prefer the new markdown spec format, but keep .txt for backward compatibility.
    candidate_paths = [
        os.path.join(contracts_dir, f"{contract_name}.specs.md"),
        os.path.join(contracts_dir, "user_story.specs.md"),
        os.path.join(contracts_dir, f"{contract_name}.txt"),
        os.path.join(contracts_dir, "user_story.txt"),
    ]

    story_path = None
    for path in candidate_paths:
        if os.path.exists(path):
            story_path = path
            break

    if story_path is None:
        expected_files = ", ".join(f"'{path}'" for path in candidate_paths)
        raise FileNotFoundError(
            f"User story file not found. Expected one of: {expected_files}."
        )

    if story_path != candidate_paths[0]:
        print(
            f"Warning: '{candidate_paths[0]}' not found, using '{story_path}'."
        )

    with open(story_path, "r", encoding="utf-8") as f:
        return f.read().strip(), story_path


def clean_runtime_artifacts():
    """Remove generated files/folders so each run starts from a clean state."""
    dirs_to_remove = [
        "outputs",
        "coverage",
        "mochawesome-report",
        "artifacts",
        "cache",
    ]
    files_to_remove = [
        "coverage.json",
        os.path.join("test", "generated_test.js"),
    ]

    for dir_path in dirs_to_remove:
        if os.path.isdir(dir_path):
            shutil.rmtree(dir_path, ignore_errors=True)

    for file_path in files_to_remove:
        if os.path.exists(file_path):
            os.remove(file_path)


def main():
    reset_llm_stats()
    clean_runtime_artifacts()
    print("Cleaned previous run artifacts.")

    contract_name = DEFAULT_CONTRACT_NAME

    contract_code, contract_path = load_contract_code(contract_name, "contracts")
    user_story, story_path = load_user_story(contract_name, "contracts")
    print(f"Loaded contract: {contract_path}")
    print(f"Loaded user story: {story_path}")

    print("Building LangGraph application...")
    app = build_graph()

    initial_state = {
        "contract_code": contract_code,
        "user_story": user_story,
        "iterations": 0
    }

    print("Starting pipeline...")
    for output in app.stream(initial_state):
        # We can print the currently active node
        for node_name, state_update in output.items():
            print(f"--- FINISHED NODE: {node_name} ---")

    llm_stats = get_llm_stats()
    print(
        "LLM usage summary: "
        f"calls={llm_stats['calls']}, "
        f"time={llm_stats['total_time_seconds']:.3f}s, "
        f"prompt_tokens={llm_stats['prompt_tokens']}, "
        f"completion_tokens={llm_stats['completion_tokens']}, "
        f"total_tokens={llm_stats['total_tokens']}"
    )

    print("Pipeline finished.")

if __name__ == "__main__":
    main()
