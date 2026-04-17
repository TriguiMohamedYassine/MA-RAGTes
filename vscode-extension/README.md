# SolidTest VS Code Extension

Plugin VS Code pour générer automatiquement des tests pour smart contracts Solidity en intégration avec le pipeline SolidTest.

## Fonctionnalités

✨ **Soumission directe depuis l'éditeur**
- Clic droit sur un fichier `.sol` pour soumettre au test
- Raccourci clavier : `Ctrl+Alt+T`

📊 **Tableau de bord intégré**
- Voir en temps réel le statut des tests
- Historique complète des exécutions
- Statistiques et tendances

🔍 **Explorateur d'historique**
- Vue en arborescence des runs par statut
- Résultats détaillés directement accessible
- Rafraîchissement automatique

⚙️ **Configuration flexible**
- URL de l'API SolidTest personnalisable
- Paramètres de notification
- Intervalle de rafraîchissement réglable

## Installation

1. **Cloner le dépôt**
```bash
git clone <repo-url>
cd vscode-solidtest
```

2. **Installer les dépendances**
```bash
npm install
```

3. **Compiler TypeScript**
```bash
npm run compile
```

4. **Installer dans VS Code**
```bash
vsce package
# Puis ouvrir le .vsix généré avec VS Code
```

Ou en développement direct :
```bash
code --extensionDevelopmentPath=. ../..
```

## Configuration

Ouvrir les paramètres VS Code et configurer :

```json
{
  "solidtest.apiUrl": "http://localhost:8000",
  "solidtest.autoRefresh": true,
  "solidtest.refreshInterval": 5000,
  "solidtest.showNotifications": true
}
```

## Commandes disponibles

| Commande | Raccourci | Description |
|----------|-----------|-------------|
| `solidtest.submitContract` | `Ctrl+Alt+T` | Soumettre un contrat pour test |
| `solidtest.viewHistory` | `Ctrl+Alt+H` | Ouvrir l'historique |
| `solidtest.openDashboard` | - | Ouvrir le tableau de bord |
| `solidtest.settings` | - | Ouvrir les paramètres SolidTest |
| `solidtest.refresh` | - | Rafraîchir l'historique |

## Architecture

```
vscode-solidtest/
├── src/
│   ├── extension.ts        ← Point d'entrée
│   ├── apiClient.ts        ← Client HTTP pour l'API SolidTest
│   ├── historyProvider.ts  ← Explorateur d'arborescence
│   ├── webviewPanel.ts     ← Panneaux des résultats
│   └── statusBar.ts        ← Barre de statut
├── media/                   ← Icons et assets
├── package.json            ← Manifest d'extension
└── tsconfig.json           ← Config TypeScript
```

## Développement

```bash
# Compiler en mode watch
npm run watch

# Linter
npm run lint

# Exécuter en développement
npm run compile && code --extensionDevelopmentPath=. ../..
```

## Workflow

1. **Soumettre un contrat**
   - Clic droit sur un fichier `.sol`
   - Sélectionner "SolidTest: Soumettre pour test"
   - Choisir l'environnement (testnet, mainnet, simulation)

2. **Suivre le statut**
   - Un webview s'ouvre avec le statut du run
   - Rafraîchissement automatique

3. **Consulter les résultats**
   - Explorer → SolidTest Explorer
   - Cliquer sur un run pour voir les résultats

4. **Dashboard**
   - Command palette → "SolidTest: Ouvrir le tableau de bord"
   - Vue synthétique des performances

## Démarrage du projet complet

```bash
# Terminal 1 - Backend API
cd ..
uvicorn api:app --reload --port 8000

# Terminal 2 - Frontend React (optionnel)
cd solidtest
npm run dev

# Terminal 3 - L'extension VS Code
code --extensionDevelopmentPath=vscode-solidtest .
```

Puis:
1. Ouvrir un fichier `.sol` dans VS Code
2. Clic droit → "SolidTest: Soumettre pour test"
3. Voir le statut en temps réel dans l'extension

## Dépendances

- **@vscode/vscode** - API VS Code
- **axios** - Client HTTP
- **typescript** - Langage

## Licence

MIT

## Support

Pour les issues ou suggestions, ouvrir une issue sur GitHub.
