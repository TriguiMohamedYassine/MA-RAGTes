# Documentation Complète - MA-RAGTes Project (REFACTORED)

## Vue d'ensemble du Projet

**MA-RAGTes** est une plateforme d'automatisation des tests de contrats intelligents utilisant une approche multi-agents avec récupération augmentée par génération (RAG). Le projet intègre Python, Hardhat, JavaScript, Solidity et React pour créer une pipeline complète de génération, exécution et analyse de tests.

### 📋 Refactoring (Avril 2026)
La structure du projet a été réorganisée pour une meilleure modularité et séparation des préoccupations:
- Tous les fichiers Python ont été déplacés dans `backend/` avec une hiérarchie claire
- Les contrats Solidity ont été séparés (`contracts/src/` pour .sol, `contracts/specs/` pour documentation)
- Frontend et extension VS Code sont clairement isolés

---

## Structure Refactorisée

### 📁 Répertoires à la Racine

| Dossier | Contenu | Rôle |
|---------|---------|------|
| **backend/** | API, agents, workflows, config, RAG | Pipeline Python complète |
| **contracts/** | `src/` (contrats), `specs/` (spécifications) | Smart contracts et docs |
| **frontend/** | React application (anciennement solidtest/) | Interface utilisateur web |
| **vscode-extension/** | Extension VS Code (anciennement vscode-solidtest/) | Intégration dans l'éditeur |
| **tests/** | Tests générés | Résultats des exécutions |
| **data/** | `runs.sqlite3`, `vector_db/` | Persistance et RAG |
| **outputs/** | Artefacts générés | Résultats pipeline |
| **.env** | Variables d'environnement | Config sensible |
| **hardhat.config.js** | Configuration Hardhat | Build et test Solidity |
| **package.json** | Dépendances npm | Tools blockchain |
| **requirements.txt** | Dépendances Python | Libraries backend |

---

### 📂 Dossier `/backend` - Architecture Modularisée

#### **backend/config** - Configuration Centralisée
| Fichier | Ancien | Description |
|---------|--------|-------------|
| **settings.py** | `src/config.py` | Variables globales, chemins, clés API |
| **prompts.py** | `src/utils/prompts.py` | Prompts système pour LLM |
| **__init__.py** | N/A | Package initialization |

#### **backend/agents** - Agents LangGraph
| Fichier | Description |
|---------|-------------|
| **analyzer.py** | Analyse les résultats de tests (déterministe, sans LLM) |
| **evaluator.py** | Évalue qualité/couverture et décide de continuer ou arrêter |
| **executor.py** | Exécute les tests via Hardhat, capture résultats |
| **generator.py** | Génère code JavaScript/Hardhat pour tests |
| **test_designer.py** | Conçoit stratégie de test, définit cas de test |
| **__init__.py** | Package initialization |

#### **backend/workflows** - Orchestration
| Fichier | Ancien | Description |
|---------|--------|-------------|
| **orchestrator.py** | `src/workflows/orchestrator.py` | Graphe LangGraph, routage agents, gestion state |
| **__init__.py** | N/A | Package initialization |

#### **backend/rag** - Récupération Augmentée par Génération
| Fichier | Ancien | Description |
|---------|--------|-------------|
| **advanced_rag.py** | `src/utils/advanced_rag.py` | Recherche sémantique, reranking, fusion résultats |
| **ingest.py** | `rag/ingest_rag.py` | Indexe contrats/tests dans ChromaDB |
| **ingest_erc.py** | `rag/ingest_rag_erc.py` | Indexe standards ERC dans collection séparée |
| **__init__.py** | N/A | Package initialization |

#### **backend/utils** - Fonctions Utilitaires
| Fichier | Ancien | Description |
|---------|--------|-------------|
| **llm.py** | `src/utils/llm.py` | Factories LLM (MistralAI), retry, statistiques |
| **analyzer_utils.py** | `src/utils/analyzer_utils.py` | Helpers parser test_report, failures extraction |
| **generator_utils.py** | `src/utils/generator_utils.py` | Helpers génération code JS |
| **executor_utils.py** | `src/utils/executor_utils.py` | Helpers exécution Hardhat |
| **evaluator_utils.py** | `src/utils/evaluator_utils.py` | Helpers calcul scores, décisions |
| **__init__.py** | N/A | Package initialization |

#### **backend/ - Fichiers Racine**
| Fichier | Ancien | Description |
|---------|--------|-------------|
| **api.py** | `api.py` | API REST FastAPI (port 8000) |
| **main.py** | `main.py` | Point d'entrée CLI |
| **__init__.py** | N/A | Package initialization |

---

### 📂 Dossier `/contracts` - Contrats Organisés

#### **contracts/src** - Code Solidity
Contient tous les fichiers `.sol` (anciennement dans `contracts/` root):
- Adoption.sol, AttendanceRecord.sol, CandidateElection.sol, crowdfunding.sol, etc.

#### **contracts/specs** - Documentation/Spécifications
Contient tous les fichiers `.specs.md` (anciennement dans `contracts/` root):
- Adoption.specs.md, AttendanceRecord.specs.md, etc.

---

### 📂 Dossier `/frontend` - Application React
Ancien: `solidtest/`

| Fichier/Dossier | Description |
|---|---|
| **package.json** | Dépendances React + Vite |
| **vite.config.js** | Config bundler Vite |
| **index.html** | Point d'entrée HTML |
| **src/main.jsx** | Bootstrap React |
| **src/App.jsx** | Composant racine |
| **src/components/Navbar.jsx** | Navigation |
| **src/pages/Dashboard.jsx** | Tableau de bord principal |
| **src/pages/History.jsx** | Historique des tests |
| **src/pages/NewTest.jsx** | Création nouveaux tests |
| **src/pages/Settings.jsx** | Paramètres |
| **src/services/api.js** | Client HTTP backend |

---

### 📂 Dossier `/vscode-extension` - Extension VS Code
Ancien: `vscode-solidtest/`

| Fichier | Description |
|---|---|
| **package.json** | Manifest extension |
| **tsconfig.json** | Config TypeScript |
| **src/extension.ts** | Point d'entrée activation |
| **src/apiClient.ts** | Client API backend |
| **src/statusBar.ts** | Barre de statut VS Code |
| **src/webviewPanel.ts** | Gestion vues web |
| **src/historyProvider.ts** | Fournisseur historique |
| **webview/** | Contenu web affichage |

---

### 📂 Dossier `/tests` - Artefacts de Test
Ancien: `test/`

| Fichier | Description |
|---------|-------------|
| **generated_test.js** | Code test généré par pipeline |

---

## Vue d'ensemble de la Pipeline

```
BACKEND PIPELINE (LangGraph)
═══════════════════════════════════

1. ANALYZER      → backend/agents/analyzer.py
                    ├─ Extraction fonctions
                    ├─ Identification risques

2. TEST_DESIGNER → backend/agents/test_designer.py
                    ├─ Définition cas de test
                    ├─ Scénarios couverture

3. GENERATOR     → backend/agents/generator.py
                    ├─ Code JavaScript Hardhat
                    ├─ Assertions Chai

4. EXECUTOR      → backend/agents/executor.py
                    ├─ Compilation contrats
                    ├─ Exécution tests

5. EVALUATOR     → backend/agents/evaluator.py
                    ├─ Analyse couverture
                    ├─ Feedback amélioration

Configuration: backend/config/settings.py
Orchestration: backend/workflows/orchestrator.py
RAG: backend/rag/ (advanced_rag.py)
```

---

## Utilisation Post-Refactoring

### Démarrer l'API
```bash
cd backend
python -m uvicorn api:app --reload --port 8000
```

### Exécuter la pipeline CLI
```bash
cd backend
python main.py
```

### Ingérer les contrats en RAG
```bash
cd backend/rag
python ingest.py
python ingest_erc.py  # Pour standards ERC
```

### Frontend
```bash
cd frontend
npm install && npm run dev
```

### Extension VS Code
```bash
cd vscode-extension
npm install
npm run compile
code --install-extension .
```

---

## Changements d'Import Critiques

| Ancien | Nouveau |
|--------|---------|
| `from src.config import` | `from backend.config.settings import` |
| `from src.utils.prompts import` | `from backend.config.prompts import` |
| `from src.agents.X import` | `from backend.agents.X import` |
| `from src.workflows.orchestrator import` | `from backend.workflows.orchestrator import` |
| `from src.utils.advanced_rag import` | `from backend.rag.advanced_rag import` |
| `from src.utils.llm import` | `from backend.utils.llm import` |
| `from rag.ingest_rag import` | `from backend.rag.ingest import` |
| `from rag.ingest_rag_erc import` | `from backend.rag.ingest_erc import` |

---

## Chemins Solidity Importants

- **Contrats source**: `contracts/src/` (utilisé par hardhat.config.js)
- **Spécifications**: `contracts/specs/` (documentation)
- **RAG ingestion**: Lire depuis `contracts/src/` et `contracts/specs/`

---

## Technologies Clés

- **Backend**: Python 3.10+, LangChain, LangGraph, ChromaDB, MistralAI/OpenAI, FastAPI
- **Blockchain**: Hardhat 2.22.4, Solidity 0.8.24, Ethers.js v6, Chai
- **Frontend**: React 18, Vite, JavaScript
- **Extension**: VS Code API, TypeScript
- **Database**: SQLite (historique), ChromaDB (embeddings RAG)

---

**Date de Refactoring**: Avril 2026  
**Version**: 2.0.0 (Post-Refactoring)  
**Structure Validation**: ✅ Complète

