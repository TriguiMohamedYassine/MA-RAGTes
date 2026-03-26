# Spécifications du Smart Contract : Whitelist

## 1. Présentation
**Catégorie** : Accès  
**Nom du Contrat** : Whitelist  
**Rôle** : Créer un périmètre de sécurité en limitant l'exécution de certaines fonctions à un groupe d'adresses préalablement validées par un administrateur.

## 2. User Story
> **En tant qu'** organisateur d'un événement exclusif sur la blockchain,  
> **je veux** définir une liste d'adresses "VIP" ou vérifiées (KYC),  
> **afin de** m'assurer que seuls les participants légitimes puissent interagir avec mes services critiques.

## 3. Acteurs
* **Administrateur (Owner)** : Gère les entrées et sorties de la liste blanche.
* **Utilisateur Autorisé** : Adresse figurant dans la liste, bénéficiant d'un accès complet aux fonctions protégées.
* **Utilisateur Non-Autorisé** : Adresse externe dont les tentatives d'appel seront rejetées.

## 4. Flux (Acceptance Criteria)
### Scénario A : Ajout d'un membre
1. **Action** : L'administrateur appelle `addToWhitelist(0xABC...)`.
2. **Résultat** : L'adresse est enregistrée. L'événement `AddressAdded` est émis.

### Scénario B : Accès refusé
1. **Action** : Une adresse non listée tente d'appeler `restrictedAction()`.
2. **Résultat** : La transaction est annulée avec le message "Whitelist: l'adresse n'est pas autorisee".

### Scénario C : Révocation d'accès
1. **Action** : L'administrateur appelle `removeFromWhitelist(0xABC...)`.
2. **Résultat** : L'adresse perd immédiatement son droit d'accès aux fonctions protégées.

## 5. Propriétés Techniques
* **Stockage** : Utilisation d'un `mapping(address => bool)` pour une vérification instantanée et peu coûteuse en gaz.
* **Sécurité** : Le modificateur `onlyOwner` protège la gestion de la liste elle-même.
* **Flexibilité** : Peut être combiné avec d'autres contrats (comme une vente de tokens) pour créer des étapes de vente privée.