"""
advanced_rag.py
---------------
Système RAG avancé combinant :
  - Détection des standards ERC par expressions régulières
  - Transformation de requête (HyDE)
  - Génération de sous-requêtes multiples
  - Recherche hybride sur ChromaDB
  - Re-ranking par scoring LLM
  - Compression contextuelle
"""

import json
import re
from typing import Any

from langchain_core.messages import HumanMessage
from langchain_mistralai import ChatMistralAI, MistralAIEmbeddings
from langchain_chroma import Chroma
from langchain_core.documents import Document

from src.config import VECTOR_DB_DIR, require_mistral_api_key


# ---------------------------------------------------------------------------
# Utilitaires
# ---------------------------------------------------------------------------

def _strip_markdown_fences(text: str) -> str:
    """Supprime les balises ```json … ``` éventuellement ajoutées par le LLM."""
    cleaned = text.strip()
    if cleaned.startswith("```json"):
        cleaned = cleaned[7:]
    elif cleaned.startswith("```"):
        cleaned = cleaned[3:]
    if cleaned.endswith("```"):
        cleaned = cleaned[:-3]
    return cleaned.strip()


# ---------------------------------------------------------------------------
# Patterns de détection ERC
# ---------------------------------------------------------------------------

# Patterns de détection : le contrat IMPLÉMENTE le standard (pas seulement l'utilise).
# Règle : on cherche "contract Xxx is ... ERC20/IERC20" ou l'héritage explicite.
# On évite le faux positif "interface IERC20 { ... }" ou "IERC20(token).transfer()"
# qui signifie que le contrat CONSOMME le standard sans l'implémenter.
_ERC_PATTERNS: dict[str, list[str]] = {
    # Le contrat hérite ou déclare explicitement le standard
    "ERC20":   [r"is\s+(?:[\w,\s]*\s)?(?:ERC20|IERC20)\b",
                r"contract\s+\w+[^{]*\bERC20\b"],
    "ERC721":  [r"is\s+(?:[\w,\s]*\s)?(?:ERC721|IERC721)\b",
                r"contract\s+\w+[^{]*\bERC721\b"],
    "ERC1155": [r"is\s+(?:[\w,\s]*\s)?(?:ERC1155|IERC1155)\b",
                r"contract\s+\w+[^{]*\bERC1155\b"],
    "ERC777":  [r"is\s+(?:[\w,\s]*\s)?(?:ERC777|IERC777)\b",
                r"contract\s+\w+[^{]*\bERC777\b"],
    "ERC4626": [r"is\s+(?:[\w,\s]*\s)?(?:ERC4626|IERC4626)\b",
                r"contract\s+\w+[^{]*\bERC4626\b"],
}


# ---------------------------------------------------------------------------
# Classe principale
# ---------------------------------------------------------------------------

class AdvancedRAG:
    """
    Pipeline RAG avancé pour récupérer le contexte ERC pertinent
    avant la génération de tests.
    """

    def __init__(self, collection_name: str = "erc_standards") -> None:
        self._collection_name = collection_name
        api_key = require_mistral_api_key()
        self._embeddings = MistralAIEmbeddings(mistral_api_key=api_key)
        self._vector_db = Chroma(
            persist_directory=str(VECTOR_DB_DIR),
            embedding_function=self._embeddings,
            collection_name=collection_name,
        )
        self._llm = ChatMistralAI(
            model="mistral-large-latest",
            temperature=0,
            mistral_api_key=api_key,
        )

    # ------------------------------------------------------------------
    # Étape 1 : Détection des standards ERC
    # ------------------------------------------------------------------

    def _detect_erc_standards(self, contract_code: str) -> list[str]:
        """Détecte les standards ERC implémentés dans le contrat."""
        detected: list[str] = []
        for standard, patterns in _ERC_PATTERNS.items():
            for pattern in patterns:
                if re.search(pattern, contract_code, re.IGNORECASE):
                    detected.append(standard)
                    break  # un seul match suffit par standard

        label = ", ".join(detected) if detected else "Aucun — Contrat générique"
        print(f"[RAG] Standards ERC détectés : {label}")
        return detected

    # ------------------------------------------------------------------
    # Étape 2 : Génération d'un document hypothétique (HyDE)
    # ------------------------------------------------------------------

    def _generate_hypothetical_document(
        self, contract_code: str, detected_ercs: list[str]
    ) -> str:
        """
        Génère une documentation ERC hypothétique afin d'améliorer
        la similarité sémantique lors de la recherche vectorielle.
        """
        standards_label = ", ".join(detected_ercs) if detected_ercs else "Contrat Solidity générique"

        prompt = (
            f"Standards détectés : {standards_label}\n\n"
            f"Code du contrat (extrait) :\n{contract_code[:2000]}\n\n"
            "Génère une spécification technique hypothétique (200-300 mots) couvrant :\n"
            "1. Fonctions requises et comportement attendu\n"
            "2. Événements requis\n"
            "3. Conditions de revert\n"
            "Réponds uniquement avec le texte de la spécification."
        )

        response = self._llm.invoke([HumanMessage(content=prompt)])
        print("[HyDE] Document hypothétique généré.")
        return response.content

    # ------------------------------------------------------------------
    # Étape 3 : Génération de sous-requêtes
    # ------------------------------------------------------------------

    def _generate_sub_queries(
        self, contract_code: str, detected_ercs: list[str]
    ) -> list[str]:
        """Produit plusieurs requêtes ciblées pour maximiser le rappel."""
        queries: list[str] = [contract_code[:1500]]

        for erc in detected_ercs:
            queries.append(f"{erc} standard specification required functions")
            queries.append(f"{erc} required events and emit conditions")
            queries.append(f"{erc} security requirements and revert conditions")

        # Ajoute une requête par fonction publique détectée (jusqu'à 5)
        function_names = re.findall(r"function\s+(\w+)\s*\(", contract_code)
        for func in function_names[:5]:
            queries.append(f"Solidity {func} function security best practices")

        print(f"[Multi-Query] {len(queries)} sous-requêtes générées.")
        return queries

    # ------------------------------------------------------------------
    # Étape 4 : Recherche hybride
    # ------------------------------------------------------------------

    def _hybrid_search(
        self, queries: list[str], k_per_query: int = 3
    ) -> list[Document]:
        """Effectue une recherche par similarité pour chaque requête et déduplique."""
        results: list[Document] = []
        seen_hashes: set[int] = set()

        for query in queries:
            try:
                docs = self._vector_db.similarity_search(query, k=k_per_query)
                for doc in docs:
                    content_hash = hash(doc.page_content[:200])
                    if content_hash not in seen_hashes:
                        seen_hashes.add(content_hash)
                        results.append(doc)
            except Exception as exc:
                print(f"[Hybrid Search] Requête ignorée : {exc}")

        print(f"[Hybrid Search] {len(results)} documents uniques récupérés.")
        return results

    # ------------------------------------------------------------------
    # Étape 5 : Re-ranking par scoring LLM
    # ------------------------------------------------------------------

    def _rerank_documents(
        self,
        documents: list[Document],
        detected_ercs: list[str],
        top_k: int = 5,
    ) -> list[Document]:
        """Trie les documents par pertinence via un scoring LLM."""
        if len(documents) <= top_k:
            return documents

        # On limite à 15 docs pour maîtriser le coût API
        candidates = documents[:15]
        summaries = "\n".join(
            f"[DOC {i}] Source: {doc.metadata.get('filename', 'Inconnu')}\n"
            f"Contenu: {doc.page_content[:300].replace(chr(10), ' ')}…"
            for i, doc in enumerate(candidates)
        )

        standards_label = ", ".join(detected_ercs) if detected_ercs else "Contrat générique"
        rerank_prompt = (
            f"Le contrat implémente : {standards_label}\n\n"
            f"Critères de scoring (0-10) :\n"
            f"  10 — Spécifie directement le comportement requis du standard\n"
            f"   8 — Contient des conditions de sécurité ou de test\n"
            f"   6 — Bonnes pratiques de test\n"
            f"   4 — Lien indirect\n"
            f"   0 — Non pertinent\n\n"
            f"Documents :\n{summaries}\n\n"
            f'Réponds UNIQUEMENT en JSON : {{"scores": [<score_0>, <score_1>, …]}}'
        )

        try:
            response = self._llm.invoke([HumanMessage(content=rerank_prompt)])
            cleaned = _strip_markdown_fences(response.content)
            scores: list[float] = json.loads(cleaned).get("scores", [])

            # Complète les scores manquants avec 0
            padded_scores = scores + [0.0] * (len(candidates) - len(scores))
            ranked = sorted(zip(candidates, padded_scores), key=lambda x: x[1], reverse=True)

            print(f"[Re-ranking] Top {top_k} documents sélectionnés.")
            return [doc for doc, _ in ranked[:top_k]]

        except Exception as exc:
            print(f"[Re-ranking] Échec, ordre original conservé : {exc}")
            return candidates[:top_k]

    # ------------------------------------------------------------------
    # Étape 6 : Compression contextuelle
    # ------------------------------------------------------------------

    def _compress_context(
        self, documents: list[Document], detected_ercs: list[str]
    ) -> str:
        """Extrait uniquement les informations utiles pour la génération de tests."""
        if not documents:
            return "Aucun standard pertinent trouvé dans la base de connaissances."

        raw_context = "\n\n".join(
            f"--- SOURCE ---\n{doc.page_content}" for doc in documents
        )
        standards_label = ", ".join(detected_ercs) if detected_ercs else "Contrat générique"

        prompt = (
            f"Standards détectés : {standards_label}\n\n"
            f"Contexte brut :\n{raw_context[:6000]}\n\n"
            "Extrais et organise UNIQUEMENT les informations utiles pour les tests :\n"
            "1. FONCTIONS REQUISES\n"
            "2. ÉVÉNEMENTS REQUIS\n"
            "3. CONDITIONS DE REVERT\n"
            "4. EXIGENCES DE SÉCURITÉ"
        )

        try:
            response = self._llm.invoke([HumanMessage(content=prompt)])
            print("[Compression] Contexte réduit.")
            return response.content
        except Exception as exc:
            print(f"[Compression] Échec : {exc}")
            return raw_context[:4000]

    # ------------------------------------------------------------------
    # Pipeline principal
    # ------------------------------------------------------------------

    def retrieve(self, contract_code: str) -> dict[str, Any]:
        """
        Exécute le pipeline RAG complet et retourne un dictionnaire contenant :
          - ``context``       : contexte compressé prêt à injecter dans un prompt
          - ``detected_ercs`` : liste des standards ERC détectés
          - ``metadata``      : statistiques de récupération
        """
        print("\n" + "=" * 60)
        print(f"[ADVANCED RAG] Démarrage du pipeline… (collection: {self._collection_name})")
        print("=" * 60)

        detected_ercs = self._detect_erc_standards(contract_code)
        hyde_doc      = self._generate_hypothetical_document(contract_code, detected_ercs)
        queries       = self._generate_sub_queries(contract_code, detected_ercs) + [hyde_doc]
        raw_docs      = self._hybrid_search(queries, k_per_query=3)
        ranked_docs   = self._rerank_documents(raw_docs, detected_ercs, top_k=5)
        context       = self._compress_context(ranked_docs, detected_ercs)

        print(f"[ADVANCED RAG] Pipeline terminé ✅ (collection: {self._collection_name})")
        print("=" * 60 + "\n")

        return {
            "context": context,
            "detected_ercs": detected_ercs,
            "metadata": {
                "total_docs_retrieved": len(raw_docs),
                "docs_after_rerank":    len(ranked_docs),
            },
        }