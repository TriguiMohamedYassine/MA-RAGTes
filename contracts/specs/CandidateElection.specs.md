# Spécifications du Smart Contract : Candidate Election

## 1. Présentation
**Catégorie** : Événement  
**Nom du Contrat** : CandidateElection  
**Rôle** : Gérer un scrutin à choix multiples où les électeurs votent pour un candidat parmi une liste fermée établie lors du déploiement.

## 2. User Story
> **En tant qu'** organisateur d'une élection de délégués ou de représentants,  
> **je veux** que les participants puissent choisir un candidat unique dans une liste officielle,  
> **afin de** garantir un comptage automatisé, transparent et infalsifiable des voix.

## 3. Acteurs
* **Administrateur** : Définit la liste des candidats au moment de la création du contrat.
* **Électeur** : Toute adresse souhaitant soutenir un candidat (limité à un vote par adresse).

## 4. Flux (Acceptance Criteria)
### Scénario A : Consultation des candidats
1. **Action** : L'utilisateur appelle `getCandidatesCount()` puis `getCandidate(id)`.
2. **Résultat** : Le contrat retourne le nom du candidat et son score actuel.

### Scénario B : Émission d'un vote valide
1. **Action** : L'électeur appelle `vote(1)`.
2. **Condition** : L'ID `1` doit exister et l'adresse ne doit pas avoir déjà voté.
3. **Résultat** : Le `voteCount` du candidat cible augmente de 1. L'événement `VoteCast` est émis.

### Scénario C : Tentative de vote pour un candidat inexistant
1. **Action** : L'électeur appelle `vote(99)` alors qu'il n'y a que 3 candidats.
2. **Résultat** : La transaction échoue (revert) avec le message "Election: Candidat invalide".

## 5. Propriétés Techniques
* **Indexation** : Les candidats sont identifiés par leur index dans le tableau `candidates` (0, 1, 2...).
* **Immuabilité de la liste** : La liste des candidats est fixée au déploiement pour éviter tout ajout frauduleux en cours de scrutin.
* **Transparence** : N'importe qui peut vérifier le score de n'importe quel candidat en temps réel sans intermédiaire.