# Spécifications du Smart Contract : Digital Agreement

## 1. Présentation
**Catégorie** : Commerce / Légal  
**Nom du Contrat** : DigitalAgreement  
**Rôle** : Fournir une preuve cryptographique d'acceptation mutuelle d'un document (contrat, CGU, accord de confidentialité) entre deux entités.

## 2. User Story
> **En tant que** freelance ou prestataire de services,  
> **je veux** que mon client et moi-même signions un hachage de notre contrat de travail sur la blockchain,  
> **afin de** disposer d'une preuve de consentement irréfutable et horodatée en cas de litige sur les termes initiaux.

## 3. Acteurs
* **Partie A (Initiateur)** : Déploie le contrat et définit la Partie B ainsi que le document de référence.
* **Partie B (Contrepartie)** : Doit valider l'accord par une transaction de signature.

## 4. Flux (Acceptance Criteria)
### Scénario A : Processus de signature complet
1. **Action** : La Partie A déploie le contrat avec le hachage du PDF.
2. **Action** : La Partie A appelle `sign()`.
3. **Action** : La Partie B appelle `sign()`.
4. **Résultat** : L'état `isEffectivelySigned` devient vrai. L'événement `AgreementFullyExecuted` est émis.

### Scénario B : Tentative de modification
1. **Action** : Une partie tente de modifier le `documentHash` après déploiement.
2. **Résultat** : Impossible. Le hachage est stocké de manière immuable, garantissant l'intégrité du document original.

### Scénario C : Signature par un tiers
1. **Action** : Une adresse externe (ni A, ni B) tente d'appeler `sign()`.
2. **Résultat** : La transaction échoue via le modificateur `onlyParties`.

## 5. Propriétés Techniques
* **Preuve par Hachage** : On ne stocke pas le texte intégral (trop coûteux), mais son empreinte numérique (SHA-256 ou IPFS CID).
* **Horodatage (Timestamping)** : Utilise `block.timestamp` pour certifier le moment exact du consensus.
* **Immuabilité** : Une fois les deux signatures recueillies, l'accord est gravé dans l'historique de la blockchain.