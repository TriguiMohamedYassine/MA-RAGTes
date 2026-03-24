"""
naive_rag.py
------------
RAG minimal et robuste:
  - detection simple des standards ERC via regex
  - recherche vectorielle basique si Chroma + embeddings sont disponibles
  - fallback lecture locale des fichiers *.specs.md

Objectif: fournir un contexte utile sans pipeline multi-etapes ni appels LLM
supplementaires.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from src.config import BASE_DIR, VECTOR_DB_DIR, MISTRAL_API_KEY


_ERC_PATTERNS: dict[str, list[str]] = {
    "ERC20": [r"function\s+transfer\s*\(", r"ERC20", r"IERC20"],
    "ERC721": [r"function\s+ownerOf\s*\(", r"ERC721", r"IERC721"],
    "ERC1155": [r"function\s+balanceOfBatch\s*\(", r"ERC1155", r"IERC1155"],
    "ERC777": [r"function\s+send\s*\(", r"ERC777", r"IERC777"],
    "ERC4626": [r"function\s+deposit\s*\(", r"ERC4626", r"IERC4626"],
}


def _detect_erc_standards(contract_code: str) -> list[str]:
    detected: list[str] = []
    for standard, patterns in _ERC_PATTERNS.items():
        if any(re.search(pattern, contract_code, re.IGNORECASE) for pattern in patterns):
            detected.append(standard)
    label = ", ".join(detected) if detected else "Aucun - Contrat generique"
    print(f"[Naive RAG] Standards ERC detectes : {label}")
    return detected


class NaiveRAG:
    """Recuperation naive du contexte ERC."""

    def __init__(self, collection_name: str = "erc_standards") -> None:
        self.collection_name = collection_name

    def _retrieve_from_vector_db(self, query: str, k: int = 5) -> list[str]:
        """Recherche simple par similarite; renvoie [] si indisponible."""
        try:
            if not MISTRAL_API_KEY or not VECTOR_DB_DIR.exists():
                return []

            from langchain_mistralai import MistralAIEmbeddings
            from langchain_chroma import Chroma

            embeddings = MistralAIEmbeddings(mistral_api_key=MISTRAL_API_KEY)
            vector_db = Chroma(
                persist_directory=str(VECTOR_DB_DIR),
                embedding_function=embeddings,
                collection_name=self.collection_name,
            )
            docs = vector_db.similarity_search(query, k=k)
            return [doc.page_content for doc in docs if getattr(doc, "page_content", "")]
        except Exception as exc:
            print(f"[Naive RAG] Vector DB indisponible, fallback local: {exc}")
            return []

    def _retrieve_from_local_specs(self, detected_ercs: list[str], k: int = 5) -> list[str]:
        """Fallback local: lit les fichiers .specs.md les plus pertinents."""
        specs = sorted(Path(BASE_DIR / "contracts").rglob("*.specs.md"))
        if not specs:
            return []

        selected: list[Path] = []
        lowered_targets = [erc.lower() for erc in detected_ercs]

        for path in specs:
            name = path.name.lower()
            if any(target in name for target in lowered_targets):
                selected.append(path)

        if not selected:
            selected = specs[:k]

        contexts: list[str] = []
        for path in selected[:k]:
            try:
                text = path.read_text(encoding="utf-8", errors="ignore")
                contexts.append(f"--- SOURCE: {path.name} ---\n{text[:2500]}")
            except OSError:
                continue
        return contexts

    def retrieve(self, contract_code: str) -> dict[str, Any]:
        detected_ercs = _detect_erc_standards(contract_code)

        query = " ".join(detected_ercs) if detected_ercs else contract_code[:1200]
        snippets = self._retrieve_from_vector_db(query=query, k=5)
        if not snippets:
            snippets = self._retrieve_from_local_specs(detected_ercs=detected_ercs, k=5)

        if snippets:
            context = "\n\n".join(snippets)
        else:
            context = "Aucun standard pertinent trouve dans la base de connaissances."

        print(f"[Naive RAG] {len(snippets)} document(s) recuperes.")
        return {
            "context": context,
            "detected_ercs": detected_ercs,
        }
