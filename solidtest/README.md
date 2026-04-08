# SolidTest UI

Interface graphique React pour le pipeline SolidTest de génération automatique de tests Solidity.

## Structure des fichiers

```
solidtest/
├── index.html
├── package.json
├── vite.config.js
└── src/
    ├── main.jsx          ← point d'entrée React
    ├── App.jsx           ← routage entre les pages
    ├── index.css         ← styles globaux (DM Sans + Space Mono)
    ├── components/
    │   └── Navbar.jsx    ← barre de navigation
    └── pages/
        ├── Dashboard.jsx ← stats, graphiques, exécutions récentes
        ├── NewTest.jsx   ← formulaire de soumission de contrat
        ├── History.jsx   ← historique filtrable des runs
        └── Settings.jsx  ← configuration du pipeline (4 onglets)
```

## Installation et démarrage

```bash
# Installer les dépendances
npm install

# Démarrer le serveur de développement
npm run dev
# → http://localhost:3000

# Build de production
npm run build
```

## Dépendances

- **React 18** — framework UI
- **Vite** — bundler
- **Chart.js 4** — graphiques (chargé via CDN, aucune installation nécessaire)
- **DM Sans + Space Mono** — polices (Google Fonts)

## Pages

| Page | Route | Description |
|------|-------|-------------|
| Dashboard | `/` | KPIs, tendances, exécutions récentes |
| New Test | `newtest` | Upload/paste de contrat + génération |
| History | `history` | Tableau filtrable de tous les runs |
| Settings | `settings` | Sliders et toggles pour configurer le pipeline |

## Connexion au backend Python

Les boutons "Generate Tests" et les actions de la table History sont prêts à être
connectés à votre API FastAPI/Flask. Remplacez les données statiques par des appels
`fetch()` ou `axios` selon votre backend.

Exemple pour lancer le pipeline depuis `NewTest.jsx` :

```js
const handleGenerate = async () => {
  const res = await fetch("/api/run", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ contract_code: code, contract_name: name }),
  });
  const data = await res.json();
  // rediriger vers la page pipeline...
};
```
