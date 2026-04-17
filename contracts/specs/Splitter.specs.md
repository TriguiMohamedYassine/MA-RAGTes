# Spécifications du Smart Contract : Splitter

## 1. Présentation
**Catégorie** : Logique  
**Nom du Contrat** : Splitter  
**Rôle** : Automatiser la redistribution de fonds reçus vers plusieurs portefeuilles cibles de manière équitable et transparente.

## 2. User Story
> **En tant que** membre d'un collectif de trois développeurs,  
> **je veux** un contrat qui reçoit les paiements de nos clients et les renvoie instantanément sur nos comptes respectifs,  
> **afin d'** éviter les litiges liés à la gestion manuelle de la trésorerie.

## 3. Acteurs
* **Payeur** : Toute adresse envoyant de l'Ether au contrat (client, donateur).
* **Bénéficiaires (3)** : Les adresses fixées au déploiement qui reçoivent chacune 1/3 des fonds.

## 4. Flux (Acceptance Criteria)
### Scénario A : Réception passive
1. **Action** : Un client envoie 3 ETH directement à l'adresse du contrat.
2. **Résultat** : La fonction `receive()` se déclenche. Chaque bénéficiaire reçoit 1 ETH automatiquement.

### Scénario B : Division avec reste
1. **Action** : Le contrat reçoit 10 Wei.
2. **Résultat** : Chaque bénéficiaire reçoit 3 Wei (10 / 3 = 3). 
3. **Condition** : Le 1 Wei restant (le modulo) demeure sur le solde du contrat.

### Scénario C : Sécurité des adresses
1. **Action** : Tentative de déploiement avec une adresse nulle (0x0).
2. **Résultat** : Le `constructor` rejette la transaction.

## 5. Propriétés Techniques
* **Automatisation** : Utilisation de la fonction `receive()` pour traiter les transferts directs sans appel de fonction spécifique.
* **Transparence** : L'événement `PaymentSplit` permet de vérifier que chaque part a bien été envoyée.
* **Gas Efficiency** : Utilisation d'une boucle `for` sur un tableau de taille fixe (3) pour limiter la consommation de gaz.