# Spécifications du Smart Contract : Address Book

## 1. Présentation
**Catégorie** : Données  
**Nom du Contrat** : AddressBook  
**Rôle** : Offrir un service de répertoire décentralisé où chaque utilisateur gère une liste de correspondances entre des noms (alias) et des adresses blockchain.

## 2. User Story
> **En tant qu'** utilisateur fréquent de la blockchain,  
> **je veux** enregistrer les adresses de mes collaborateurs sous des noms explicites,  
> **afin de** ne plus avoir à manipuler des adresses hexadécimales complexes lors de mes vérifications.

## 3. Acteurs
* **Propriétaire du répertoire** : L'utilisateur (`msg.sender`) qui crée et gère sa propre liste.
* **Contact** : L'entité (adresse) dont les coordonnées sont sauvegardées.

## 4. Flux (Acceptance Criteria)
### Scénario A : Ajout d'un nouveau contact
1. **Action** : L'utilisateur appelle `addContact("Alice", 0x123...)`.
2. **Condition** : Le nom "Alice" sert de clé unique pour cet utilisateur.
3. **Résultat** : L'adresse est liée au nom. L'événement `ContactAdded` est émis.

### Scénario B : Recherche de contact
1. **Action** : L'utilisateur appelle `getContact("Alice")`.
2. **Condition** : Le contact doit exister dans le répertoire personnel de l'appelant.
3. **Résultat** : Le contrat retourne l'adresse `0x123...`.

### Scénario C : Suppression
1. **Action** : L'utilisateur appelle `removeContact("Alice")`.
2. **Résultat** : Les données liées à "Alice" sont effacées du stockage (libérant un peu de gaz).

## 5. Propriétés Techniques
* **Confidentialité relative** : Bien que les données soient sur la chaîne, le contrat sépare logiquement les répertoires par adresse (`mapping(address => ...)`).
* **Gestion du Stockage** : Utilise un tableau de chaînes (`string[]`) pour permettre à l'interface utilisateur d'afficher la liste complète des noms disponibles.
* **Sécurité** : Un utilisateur ne peut ni lire ni modifier le répertoire d'un autre utilisateur via les fonctions standards.