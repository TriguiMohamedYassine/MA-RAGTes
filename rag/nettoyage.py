import os
import shutil
import re

# ================= CONFIGURATION =================
# Le dossier cible
TARGET_DIR = "./reference_tests"

# La liste EXACTE des fichiers à garder (WhiteList)
KEEP_FILES = {
    "ERC20.test.js",
    "ERC20Burnable.test.js",
    "ERC20Pausable.test.js",
    "ERC20Capped.test.js",
    "ERC721.test.js",
    "Ownable.test.js",
    "AccessControl.test.js"
}

# ================= LOGIQUE DE NETTOYAGE =================

def clean_file_content(file_path):
    """
    Ouvre un fichier, nettoie le code spécifique à OpenZeppelin
    et réécrit le fichier propre.
    """
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()

    # 1. Supprimer les imports OpenZeppelin Test Helpers
    content = re.sub(r"const .* = require\('@openzeppelin/test-helpers'\);", "", content)
    content = re.sub(r"import .* from '@openzeppelin/test-helpers';", "", content)

    # 2. Supprimer les imports de fichiers locaux "behavior" (qu'on a supprimés)
    content = re.sub(r"require\('\..*behavior.*'\);", "", content)

    # 3. Standardiser les BigInt (Supprimer BN.js si présent)
    content = re.sub(r"const .* = require\('bn.js'\);", "", content)

    # 4. Ajouter les imports Hardhat essentiels s'ils manquent
    header = ""
    if 'require("hardhat")' not in content:
        header += 'const { ethers } = require("hardhat");\n'
    if 'require("chai")' not in content:
        header += 'const { expect } = require("chai");\n'
    
    if header:
        content = header + "\n" + content

    # 5. Remplacer 'expectRevert' (OZ) par un commentaire pour guider le RAG
    # (On ne peut pas remplacer parfaitement la logique, mais on enlève la dépendance)
    content = content.replace("await expectRevert(", "// await expectRevert( -> USE try/catch INSTEAD \n await expectRevert(")

    # Sauvegarde
    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(content)
    print(f"✨ Nettoyé et Standardisé : {os.path.basename(file_path)}")

def process_directory():
    if not os.path.exists(TARGET_DIR):
        print(f"❌ Le dossier {TARGET_DIR} n'existe pas.")
        return

    print(f"🚀 Démarrage du nettoyage dans {TARGET_DIR}...")
    
    kept_files_paths = []

    # ÉTAPE 1 : Identifier et déplacer les bons fichiers
    for root, dirs, files in os.walk(TARGET_DIR):
        for file in files:
            if file in KEEP_FILES:
                source_path = os.path.join(root, file)
                dest_path = os.path.join(TARGET_DIR, file)
                
                # Si le fichier est dans un sous-dossier, on le déplace à la racine
                if source_path != dest_path:
                    shutil.move(source_path, dest_path)
                    print(f"📦 Déplacé à la racine : {file}")
                
                kept_files_paths.append(os.path.join(TARGET_DIR, file))

    # ÉTAPE 2 : Supprimer tout ce qui n'est pas dans la liste des gardés
    # On refait un tour du dossier racine
    for root, dirs, files in os.walk(TARGET_DIR, topdown=False):
        for file in files:
            full_path = os.path.join(root, file)
            # Si ce n'est pas un fichier qu'on vient de lister comme "à garder"
            if full_path not in kept_files_paths:
                os.remove(full_path)
                # print(f"🗑️ Supprimé : {file}") # Décommente pour voir les suppressions

        for dir in dirs:
            dir_path = os.path.join(root, dir)
            # Tenter de supprimer le dossier (ne marchera que s'il est vide)
            try:
                os.rmdir(dir_path)
                print(f"📂 Dossier vide supprimé : {dir}")
            except OSError:
                pass # Le dossier n'est pas vide (ne devrait pas arriver ici)

    # ÉTAPE 3 : Nettoyer le contenu des fichiers gardés
    print("\n🧼 Nettoyage du code interne...")
    for file_path in kept_files_paths:
        clean_file_content(file_path)

    print("\n✅ Terminé ! Votre base de connaissances est propre.")
    print(f"   Fichiers restants : {len(kept_files_paths)}")

if __name__ == "__main__":
    process_directory()