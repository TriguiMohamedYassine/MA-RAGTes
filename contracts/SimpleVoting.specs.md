# Spécifications du Smart Contract : Voting System

## 1. Présentation
**Catégorie** : Événement  
**Nom du Contrat** : SimpleVoting  
**Rôle** : Organiser une consultation binaire (Oui/Non) sécurisée où chaque adresse possède un droit de vote unique.

## 2. User Story
> **En tant que** membre d'une organisation décentralisée (DAO),  
> **je veux** pouvoir exprimer mon opinion sur une proposition spécifique de manière vérifiable,  
> **afin de** participer à la gouvernance du projet sans risque de fraude ou de double vote.

## 3. Acteurs
* **Administrateur** : Initialise la proposition et possède le droit de clore le vote.
* **Votant** : Toute adresse détenant le droit de participer au scrutin.

## 4. Flux (Acceptance Criteria)
### Scénario A : Émission d'un vote
1. **Action** : Un utilisateur appelle `vote(true)` (Oui).
2. **Condition** : L'utilisateur ne doit pas avoir déjà voté et le scrutin doit être ouvert.
3. **Résultat** : Le compteur `voteCountYes` augmente de 1. L'événement `VoteCast` est émis.

### Scénario B : Tentative de double vote
1. **Action** : Un utilisateur ayant déjà voté tente d'appeler `vote(false)`.
2. **Résultat** : La transaction échoue avec le message "Voting: Vous avez deja vote".

### Scénario C : Clôture du scrutin
1. **Action** : L'administrateur appelle `closeVoting()`.
2. **Résultat** : Plus aucun vote n'est accepté. Les résultats finaux sont figés et consultables via `getResults()`.

## 5. Propriétés Techniques
* **Unicité** : Garantie par le mapping `hasVoted` lié à l'adresse de l'appelant (`msg.sender`).
* **Immuabilité** : Une fois la proposition créée, sa description ne peut plus être modifiée.
* **Intégrité** : Le comptage est effectué automatiquement par le code du contrat, éliminant tout besoin d'un tiers de confiance pour le dépouillement.