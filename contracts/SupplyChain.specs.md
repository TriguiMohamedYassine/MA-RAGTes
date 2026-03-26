# Spécifications du Smart Contract : Supply Chain Step

## 1. Présentation
**Catégorie** : Commerce / Logistique  
**Nom du Contrat** : SupplyChain  
**Rôle** : Créer un registre décentralisé pour le suivi des marchandises, permettant de vérifier l'état et la localisation d'un produit à chaque étape de la chaîne d'approvisionnement.

## 2. User Story
> **En tant que** gestionnaire logistique ou client final,  
> **je veux** consulter l'historique de déplacement de mon colis,  
> **afin de** vérifier qu'il a respecté le trajet prévu et identifier précisément quel transporteur était responsable à quel moment.

## 3. Acteurs
* **Admin (Owner)** : Gère la liste des transporteurs de confiance.
* **Transporteur (Carrier)** : Met à jour la localisation et le statut du colis lors de sa prise en charge ou livraison.
* **Auditeur/Client** : Consulte l'historique immuable du colis.

## 4. Flux (Acceptance Criteria)
### Scénario A : Suivi d'un colis
1. **Action** : Le fabricant crée le colis "Composants Électroniques" à "Usine A".
2. **Action** : Le transporteur 1 met à jour le statut à `IN_TRANSIT` à "Port de Marseille".
3. **Action** : Le transporteur 2 met à jour le statut à `ARRIVED` à "Entrepôt Paris".
4. **Résultat** : Le client peut appeler `getPackageHistory()` et voir les 3 étapes horodatées et signées.

### Scénario B : Sécurité des mises à jour
1. **Action** : Une adresse non autorisée tente d'appeler `updateStep()`.
2. **Résultat** : La transaction échoue via le modificateur `onlyAuthorized`.

### Scénario C : Intégrité temporelle
1. **Action** : Un transporteur tente de marquer un colis comme `CREATED` alors qu'il est déjà `IN_TRANSIT`.
2. **Résultat** : Échec de la transaction. La logique empêche tout retour en arrière dans les étapes logistiques.

## 5. Propriétés Techniques
* **Traçabilité Granulaire** : Chaque modification d'état enregistre l'adresse du responsable, le lieu et l'heure (`block.timestamp`).
* **Modèle d'Autorisation** : Système de Whitelist pour garantir que seules les entités logistiques vérifiées peuvent modifier les données.
* **Immuabilité** : L'historique est stocké dans un tableau dynamique (`TrackingStep[]`) qui ne peut être ni supprimé ni modifié rétroactivement.