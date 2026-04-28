# Documentation complète du projet MA-RAGTes

Date de référence : 24 avril 2026

## 1. Vue d'ensemble

MA-RAGTes est une plateforme d'automatisation de génération et d'évaluation de tests pour smart contracts Solidity. Le projet combine un backend Python piloté par LangGraph, une couche RAG pour enrichir le contexte des modèles, une API FastAPI pour exposer le pipeline, une interface web React pour le suivi des exécutions, et une extension VS Code pour lancer et consulter les runs directement depuis l'éditeur.

Le projet est organisé autour d'un pipeline multi-agents qui analyse un contrat, conçoit une stratégie de test, génère du code Hardhat, exécute les tests, puis évalue le résultat pour décider s'il faut régénérer ou s'arrêter.

## 2. Objectif fonctionnel

Le but du projet est de réduire le travail manuel nécessaire pour tester un contrat Solidity. À partir d'un contrat source et, si disponible, d'une user story ou d'une spécification, le système produit automatiquement des tests JavaScript/Hardhat, les exécute, mesure la couverture, analyse les échecs et améliore les tests au besoin.

Le projet conserve également l'historique des exécutions, les artefacts générés, les rapports de couverture et les traces d'analyse pour permettre un suivi complet.

## 3. Arborescence générale

### Racine du dépôt

- `hardhat.config.js` : configuration Hardhat, version Solidity et configuration du reporter de couverture.
- `package.json` : dépendances JavaScript/Hardhat et scripts de test.
- `requirements.txt` : dépendances Python du backend.
- `PROJECT_DESCRIPTION.md` : documentation existante du projet refactoré.
- `coverage.json` : artefact de couverture.
- `backend/` : logique métier Python, API et orchestration.
- `contracts/` : contrats Solidity et leurs spécifications.
- `frontend/` : interface web React/Vite.
- `vscode-extension/` : extension VS Code.
- `data/` : persistance SQLite et base vectorielle pour le RAG.
- `outputs/` : artefacts produits par les exécutions du pipeline.
- `coverage/` : rapports Solidity Coverage.
- `mochawesome-report/` : rapports Mochawesome.
- `test/` : fichiers de test générés.

## 4. Stack technique

### Backend et orchestration

- Python 3.x.
- FastAPI pour l'API HTTP.
- LangGraph pour le graphe d'exécution multi-agents.
- LangChain, LangChain-Chroma, ChromaDB et LangChain-Mistralai/LangChain-OpenAI pour le RAG et les modèles.
- Pydantic pour les modèles d'entrée/sortie.
- SQLite pour l'historique des runs et les paramètres applicatifs.

### Blockchain et tests Solidity

- Hardhat 2.22.4.
- Solidity 0.8.24.
- Ethers.js v6.
- Chai et Hardhat Toolbox.
- Solidity Coverage et Mochawesome.

### Frontend

- React 18.
- Vite.
- JavaScript.

### Extension VS Code

- TypeScript.
- API VS Code.
- Axios pour les appels HTTP.

## 5. Backend Python

Le backend est regroupé sous `backend/` avec une séparation claire entre configuration, agents, utilitaires, RAG et orchestration.

### 5.1 Fichiers d'entrée

- `backend/main.py` : point d'entrée CLI du pipeline. Il nettoie les artefacts précédents, charge un contrat Solidity, lit la user story si elle existe, construit le graphe LangGraph et exécute le pipeline.
- `backend/api.py` : serveur FastAPI qui expose les runs, les résultats, l'historique, la santé de l'API et la sauvegarde de la clé LLM.

### 5.2 Configuration

- `backend/config/settings.py` : centralise les chemins du projet, les valeurs par défaut et la gestion de `MISTRAL_API_KEY`.
- `backend/config/prompts.py` : contient les prompts système ou métier utilisés par les agents.

Paramètres importants observés :

- contrat par défaut : `Adoption`.
- nombre maximal de réessais : `7`.
- seuil de couverture des statements : `85`.
- seuil de couverture des branches : `80`.

Chemins principaux gérés par la configuration :

- `contracts/src` pour les contrats Solidity.
- `outputs` pour les résultats du pipeline.
- `data` pour la persistance.
- `data/vector_db` pour la base vectorielle.

### 5.3 Agents du pipeline

Les agents sont placés dans `backend/agents/` :

- `analyzer.py` : analyse les résultats des tests, les échecs et les zones insuffisamment couvertes.
- `evaluator.py` : décide si le pipeline doit s'arrêter ou relancer une génération/correction.
- `executor.py` : lance Hardhat, exécute les tests et récupère les sorties.
- `generator.py` : produit les fichiers de test JavaScript/Hardhat.
- `test_designer.py` : construit la stratégie de test et les cas à couvrir.

### 5.4 Orchestration

- `backend/workflows/orchestrator.py` : définit le graphe LangGraph.

Le flux principal est :

`test_designer -> generator_normal -> executor -> analyzer -> evaluator`

Si l'évaluateur demande une régénération, le graphe passe par un nœud d'incrémentation puis par `corrector` avant de revenir à l'exécuteur.

Le module contient aussi :

- un calcul de score composite basé sur les tests passés et la couverture.
- une heuristique de stagnation pour arrêter les boucles inutiles.
- un diagnostic des échecs susceptibles d'indiquer un vrai problème métier dans le contrat.

### 5.5 Utilitaires

Les utilitaires sont regroupés dans `backend/utils/` :

- `llm.py` : création/gestion des modèles LLM, statistiques et logique de retry.
- `generator_utils.py` : helpers pour la génération de code de test.
- `executor_utils.py` : helpers liés à l'exécution Hardhat.
- `analyzer_utils.py` : parsing des rapports et extraction des défaillances.
- `evaluator_utils.py` : calcul des scores et logique de décision.

### 5.6 RAG

Le sous-dossier `backend/rag/` contient la couche de récupération augmentée :

- `advanced_rag.py` : logique de recherche sémantique, reranking et fusion des résultats.
- `ingest.py` : ingestion des contrats et des tests dans ChromaDB.
- `ingest_erc.py` : ingestion dédiée aux standards ERC dans une collection séparée.

## 6. API FastAPI

L'API est définie dans `backend/api.py`. Elle sert de couche d'intégration pour le frontend web et l'extension VS Code.

### 6.1 Rôle

- lancer un run sur un contrat donné.
- suivre l'état d'un run en temps réel.
- récupérer les résultats détaillés une fois terminés.
- consulter et vider l'historique.
- enregistrer la clé LLM locale.
- vérifier l'état de santé du service.

### 6.2 Endpoints

- `GET /` : retourne les informations de base de l'API et la liste des endpoints.
- `POST /api/run` : lance le pipeline sur un contrat fourni.
- `GET /api/run/{run_id}` : retourne le statut d'un run.
- `GET /api/results/{run_id}` : retourne les résultats détaillés d'un run terminé.
- `GET /api/history` : retourne tous les runs.
- `DELETE /api/history` : vide l'historique en mémoire et en base.
- `POST /api/settings/llm-key` : enregistre la clé API LLM.
- `GET /api/health` : endpoint de santé.

### 6.3 Persistance

L'API persiste les runs dans `data/runs.sqlite3`.

Les données sauvegardées incluent notamment :

- statut du run.
- nom du contrat.
- horodatages de début et de fin.
- nœud courant.
- nombre d'itérations.
- résumé d'exécution.
- rapports de test, de couverture et d'analyse.
- code de test généré.
- statistiques LLM.

### 6.4 Comportement d'exécution

Le pipeline tourne dans une tâche de fond. Le statut est mis à jour au fur et à mesure de l'avancement des nœuds, ce qui permet un affichage quasi temps réel dans le frontend et l'extension.

## 7. Frontend React

Le frontend se trouve dans `frontend/` et sert d'interface web pour le suivi des runs.

### 7.1 Structure observée

- `index.html` : point d'entrée HTML.
- `package.json` : dépendances React/Vite.
- `vite.config.js` : configuration de Vite.
- `src/main.jsx` : bootstrap de l'application.
- `src/App.jsx` : navigation entre les pages.
- `src/index.css` : styles globaux.
- `src/components/Navbar.jsx` : barre de navigation.
- `src/pages/Dashboard.jsx` : tableau de bord principal.
- `src/pages/NewTest.jsx` : formulaire de soumission d'un nouveau contrat.
- `src/pages/History.jsx` : historique des runs.
- `src/pages/Settings.jsx` : paramètres du pipeline.
- `src/services/api.js` : client HTTP vers l'API FastAPI.

### 7.2 Navigation de l'application

Le composant racine `App.jsx` gère quatre vues :

- `dashboard`.
- `newtest`.
- `history`.
- `settings`.

Le service `src/services/api.js` appelle les endpoints du backend pour :

- démarrer un run.
- récupérer le statut.
- charger l'historique.
- récupérer les résultats détaillés.
- vider l'historique.
- vérifier la santé.
- enregistrer la clé LLM.

## 8. Extension VS Code

L'extension est dans `vscode-extension/` et permet d'interagir avec MA-RAGTes depuis VS Code.

### 8.1 Fichiers principaux

- `src/extension.ts` : point d'entrée et enregistrement des commandes.
- `src/apiClient.ts` : client HTTP vers l'API backend.
- `src/webviewPanel.ts` : gestion des webviews.
- `src/historyProvider.ts` : fournisseur de données pour l'explorateur d'historique.
- `src/statusBar.ts` : gestion de la barre de statut.

### 8.2 Commandes et actions exposées

Le manifeste de l'extension déclare notamment :

- `maragtes.submitContract`.
- `maragtes.submitCurrentContract`.
- `maragtes.viewHistory`.
- `maragtes.openDashboard`.
- `maragtes.openLatestResult`.
- `maragtes.settings`.
- `maragtes.runTestNow`.
- `maragtes.viewResults`.

Raccourcis associés observés :

- `Ctrl+Alt+T` pour soumettre un contrat.
- `Ctrl+Alt+Shift+T` pour soumettre le contrat courant.
- `Ctrl+Alt+H` pour ouvrir l'historique.
- `Ctrl+Alt+L` pour ouvrir le dernier résultat.

### 8.3 Configuration VS Code

Paramètres disponibles :

- URL de l'API backend.
- URL du frontend.
- environnement par défaut.
- activation ou non du rafraîchissement automatique.
- intervalle de rafraîchissement.
- notifications.

## 9. Contrats Solidity

Les contrats sources sont stockés dans `contracts/src/`. Le dépôt contient un ensemble varié de contrats de démonstration, de protocoles simples, de cas orientés DeFi, de gouvernance et de sécurité.

### 9.1 Inventaire des contrats

Fichiers présents dans `contracts/src/` :

- `01-PureERC20.sol`
- `02-PureERC721.sol`
- `AddressBook.sol`
- `Adoption.sol`
- `AttendanceRecord.sol`
- `CandidateElection.sol`
- `CrowdFund.sol`
- `crowdfunding.sol`
- `DaiProxy.sol`
- `DAOGovernor.sol`
- `DAOVoting.sol`
- `DecentralizedLottery.sol`
- `DutchAuction.sol`
- `EmergencyStop.sol`
- `ERC6909.sol`
- `EthGame.sol`
- `FlashLoanPool.sol`
- `IStrategy.sol`
- `lottery_game.sol`
- `LotteryGame_2.sol`
- `MetaCoin.sol`
- `MultisigWallet.sol`
- `MyERC20Token.sol`
- `MyNFT.sol`
- `MyToken.sol`
- `NFTMarketplace.sol`
- `PollCreator.sol`
- `SimpleStakingWithRewards.sol`
- `SimpleStorage.sol`
- `SimpleStorage_2.sol`
- `SimpleVoting.sol`
- `Splitter.sol`
- `StakingRewards.sol`
- `StakingToken.sol`
- `StableSwap.sol`
- `SupplyChain.sol`
- `TaxedToken.sol`
- `TimelockControllerEnumerable.sol`
- `USDCShieldDelegate.sol`
- `VerifyProtocol.sol`
- `WasteManagement.sol`
- `Whitelist.sol`

### 9.2 Type de contenu couvert par ces contrats

Les contrats couvrent plusieurs familles d'exemples :

- ERC20, ERC721 et variantes personnalisées.
- gouvernance et vote.
- crowdfunding et financement.
- loterie et jeux on-chain.
- sécurité, timelock, pause et contrôles d'accès.
- staking, rewards et tokens taxés.
- NFT marketplace.
- supply chain et gestion de ressources.
- contrats simples d'exemple pour l'analyse et la génération de tests.

## 10. Spécifications associées

Les spécifications utilisateur se trouvent dans `contracts/specs/`.

### 10.1 Inventaire des fichiers de spécification

- `Adoption.specs.md`
- `AttendanceRecord.specs.md`
- `CandidateElection.specs.md`
- `crowdfunding.specs.md`
- `DAOVoting.specs.md`
- `EmergencyStop.specs.md`
- `lottery_game.specs.md`
- `LotteryGame_2.specs.md`
- `MetaCoin.specs.md`
- `SimpleStorage.specs.md`
- `SimpleStorage_2.specs.md`
- `Splitter.specs.md`
- `WasteManagement.specs.md`
- `Whitelist.specs.md`

Ces fichiers servent d'entrée contextuelle pour le pipeline RAG et pour l'étape de conception des tests.

## 11. Données et artefacts

### 11.1 `data/`

- `runs.sqlite3` : historique persistant des exécutions.
- `vector_db/` : base vectorielle utilisée pour le RAG.

### 11.2 `outputs/`

Le dossier contient les artefacts générés par les runs, par exemple :

- `analyzer_report.json`
- `base_code_before_correction.json`
- `coverage_report.json`
- `failed_tests.json`
- `generated_test.js`
- `test_code.json`
- `test_design.json`
- `test_report.json`
- `batch_reports/`

### 11.3 Rapports locaux

- `coverage/` : rapports générés par solidity-coverage.
- `mochawesome-report/` : rapports de tests au format Mochawesome.
- `test/generated_test.js` : fichier de test généré observé dans le workspace.

## 12. Configuration Hardhat

Le fichier `hardhat.config.js` indique :

- le chargement de `@nomicfoundation/hardhat-toolbox`.
- le chargement de `solidity-coverage`.
- la version Solidity `0.8.24`.
- le chemin des sources `./contracts/src` par défaut.
- un reporter Mochawesome pour les tests.

Les scripts NPM racine utiles sont :

- `npm test` : exécute `hardhat test`.
- `npm run coverage` : exécute `hardhat coverage`.

## 13. Dépendances Python

Le fichier `requirements.txt` contient :

- `langchain`
- `langchain-chroma`
- `langchain-mistralai`
- `langchain-openai`
- `langgraph`
- `chromadb`
- `pydantic`
- `python-dotenv`
- `matplotlib`

## 14. Flux d'exécution global

### 14.1 Depuis le CLI

1. Nettoyage des artefacts précédents.
2. Chargement du contrat Solidity et de la user story.
3. Construction du graphe LangGraph.
4. Exécution séquentielle des agents.
5. Mesure des résultats et des statistiques LLM.

### 14.2 Depuis l'API

1. Le client envoie un contrat via `POST /api/run`.
2. L'API crée un `run_id` et lance le pipeline en arrière-plan.
3. Le frontend ou l'extension pollent `GET /api/run/{run_id}`.
4. Une fois terminé, les résultats détaillés sont récupérés via `GET /api/results/{run_id}`.

### 14.3 Depuis l'extension VS Code

1. L'utilisateur clique droit sur un fichier `.sol` ou utilise un raccourci.
2. L'extension lit le contrat courant.
3. Elle soumet le contrat à l'API backend.
4. L'interface affiche le statut, l'historique et les résultats.

## 15. Points saillants du projet

- Architecture modulaire et refactorisée.
- Séparation claire entre contrats, spécifications, backend, frontend et extension.
- Pipeline de génération de tests piloté par graphe d'agents.
- RAG dédié aux contrats et aux standards ERC.
- Persistance des runs dans SQLite.
- Plusieurs points d'entrée pour différents usages : CLI, API, UI web, VS Code.

## 16. Résumé court

MA-RAGTes est un environnement complet pour tester automatiquement des smart contracts Solidity. Il combine génération de tests, exécution Hardhat, analyse des échecs, mesure de couverture, RAG, suivi web et intégration VS Code.
