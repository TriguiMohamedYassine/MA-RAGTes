import os
import sys

# ==============================================================================
# 🚨 FIX PATH : Pour trouver config.py dans le dossier parent (src)
# ==============================================================================
current_dir = os.path.dirname(os.path.abspath(__file__)) # .../src/rag
src_dir = os.path.dirname(current_dir)                 # .../src

if src_dir not in sys.path:
    sys.path.insert(0, src_dir)
# ==============================================================================

from langchain_chroma import Chroma
from langchain_mistralai import MistralAIEmbeddings
# Maintenant, l'import fonctionne
from ..config import MISTRAL_API_KEY, VECTOR_DB_DIR

def verifier_collection():
    print("🕵️‍♂️  Vérification de la base de données...")
    print(f"📂 Dossier cible : {VECTOR_DB_DIR}")

    # 1. On prépare les embeddings
    embeddings = MistralAIEmbeddings(mistral_api_key=MISTRAL_API_KEY)

    # 2. On se connecte SPÉCIFIQUEMENT à la collection "erc_standards"
    try:
        vector_db = Chroma(
            persist_directory=str(VECTOR_DB_DIR),
            embedding_function=embeddings,
            collection_name="erc_standards"  # <--- C'est ça qu'on veut vérifier
        )
        
        # 3. On compte les documents
        # Note: Chroma stocke des "chunks", donc 1 fichier ERC = plusieurs documents
        count = vector_db._collection.count()
        
        if count == 0:
            print("❌ La collection 'erc_standards' est VIDE.")
            print("   -> Avez-vous bien lancé ingest_rag_erc.py ?")
        else:
            print(f"✅ SUCCÈS ! Il y a {count} fragments de texte (chunks) dans la collection 'erc_standards'.")
            
            # 4. On fait un test de lecture
            print("\n--- 🧪 Test de récupération (Recherche 'ERC-20') ---")
            results = vector_db.similarity_search("ERC-20 token standard", k=1)
            
            if results:
                doc = results[0]
                filename = doc.metadata.get('filename', 'Inconnu')
                print(f"📄 Document trouvé : {filename}")
                print(f"📝 Extrait : {doc.page_content[:150]}...")
            else:
                print("⚠️ Bizarre : Des données existent mais la recherche ne donne rien.")

    except Exception as e:
        print(f"❌ Erreur lors de la connexion : {e}")

if __name__ == "__main__":
    verifier_collection()