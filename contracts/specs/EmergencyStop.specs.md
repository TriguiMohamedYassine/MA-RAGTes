# Spécifications du Smart Contract : Emergency Stop

## 1. Présentation
**Catégorie** : Sécurité  
**Nom du Contrat** : EmergencyStop (Pausable)  
**Rôle** : Fournir un mécanisme d'arrêt d'urgence pour suspendre les interactions avec le contrat afin de limiter les dégâts lors d'un incident de sécurité.

## 2. User Story
> **En tant qu'** administrateur d'un protocole DeFi,  
> **je veux** pouvoir désactiver instantanément les retraits ou les échanges si une vulnérabilité est détectée,  
> **afin de** protéger les fonds des utilisateurs le temps de corriger le problème.

## 3. Acteurs
* **Administrateur** : La seule entité capable d'actionner le levier de pause.
* **Utilisateur** : Subit l'arrêt des services durant la période de maintenance ou d'urgence.

## 4. Flux (Acceptance Criteria)
### Scénario A : Fonctionnement normal
1. **Action** : Un utilisateur appelle `sensitiveAction()`.
2. **Condition** : La variable `paused` est à `false`.
3. **Résultat** : La fonction s'exécute normalement.

### Scénario B : Activation de l'urgence
1. **Action** : L'administrateur détecte une anomalie et appelle `pause()`.
2. **Résultat** : La variable `paused` passe à `true`. L'événement `Paused` est émis. Toute tentative d'appel à `sensitiveAction()` échoue désormais.

### Scénario C : Rétablissement du service
1. **Action** : Après résolution du problème, l'administrateur appelle `unpause()`.
2. **Résultat** : Le contrat reprend son fonctionnement normal.

## 5. Propriétés Techniques
* **Contrôle d'Accès** : La sécurité du contrat repose entièrement sur la protection de la clé privée de l'administrateur.
* **Flexibilité** : Le modificateur `whenNotPaused` peut être appliqué de manière sélective (ex: bloquer les retraits mais laisser les dépôts ouverts).
* **Transparence** : L'état de pause est public, permettant aux interfaces (UI) d'afficher un message d'alerte aux utilisateurs.