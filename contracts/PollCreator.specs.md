# Spécifications du Smart Contract : Poll Creator

## 1. Présentation
**Catégorie** : Événement  
**Nom du Contrat** : PollCreator  
**Rôle** : Plateforme de création de sondages multiples où chaque sondage peut avoir un nombre variable d'options de réponse.

## 2. User Story
> **En tant qu'** administrateur de communauté,  
> **je veux** pouvoir lancer plusieurs consultations sur différents sujets au fil du temps,  
> **afin de** recueillir l'avis des membres sur des points précis avec des choix multiples.

## 3. Acteurs
* **Admin** : Créateur des sondages et modérateur (peut clore les votes).
* **Participant** : Adresse autorisée à voter une seule fois par sondage créé.

## 4. Flux (Acceptance Criteria)
### Scénario A : Création d'un sondage dynamique
1. **Action** : L'admin appelle `createPoll("Couleur préférée ?", ["Bleu", "Rouge", "Vert"])`.
2. **Résultat** : Un nouvel ID de sondage est généré. Le contrat initialise un tableau de compteurs de taille 3.

### Scénario B : Vote sur un sondage spécifique
1. **Action** : Un utilisateur vote pour l'option "Rouge" (index 1) du sondage ID 0.
2. **Condition** : L'utilisateur n'a pas encore voté pour l'ID 0.
3. **Résultat** : Le compteur d'index 1 du sondage 0 augmente. L'événement `VoteRegistered` est émis.

### Scénario C : Consultation des résultats
1. **Action** : Un utilisateur appelle `getPollResults(0)`.
2. **Résultat** : Le contrat retourne la question, la liste textuelle des options et le tableau des scores correspondants.

## 5. Propriétés Techniques
* **Flexibilité** : Utilisation de tableaux dynamiques (`string[]`, `uint256[]`) pour s'adapter à n'importe quel nombre d'options.
* **Isolation** : Le mapping `hasVoted` est imbriqué dans la structure `Poll`, garantissant que voter dans le Sondage A n'empêche pas de voter dans le Sondage B.
* **Économie de Gaz** : Les données de vote sont stockées de manière indexée pour optimiser les écritures sur la blockchain.