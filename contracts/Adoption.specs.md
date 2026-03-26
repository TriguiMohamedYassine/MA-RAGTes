# Adoption - Specifications fonctionnelles

## Portee
Le fichier `Adoption.sol` contient le contrat `Vault`.
Cette specification decrit le comportement effectif de `Vault`.

## User stories principales

### US1 - Initialisation du proprietaire
En tant que deployeeur,
je veux etre enregistre comme owner au deploiement,
afin de pouvoir administrer le coffre.

Critere d'acceptation:
- Au constructeur, `owner == msg.sender`.
- `paused` est `false` par defaut.

### US2 - Depot ETH
En tant qu'utilisateur,
je veux deposer de l'ETH dans le vault,
afin d'augmenter mon solde interne.

Critere d'acceptation:
- `deposit()` est payable.
- Si le contrat est en pause, revert avec l'erreur `Paused()`.
- `balances[msg.sender]` augmente de `msg.value`.
- L'evenement `Deposit(user, amount)` est emis.

### US3 - Retrait personnel
En tant qu'utilisateur,
je veux retirer une partie de mon solde,
afin de recuperer mon ETH.

Critere d'acceptation:
- `withdraw(amount)` est refuse si `paused == true` avec `Paused()`.
- Revert avec `InsufficientBalance()` si le solde est insuffisant.
- Le solde interne diminue de `amount`.
- L'ETH est transfere a l'appelant.
- L'evenement `Withdraw(user, amount)` est emis.

### US4 - Retrait owner pour un utilisateur
En tant que owner,
je veux pouvoir debiter le solde d'un utilisateur,
afin de recuperer des fonds vers l'adresse owner.

Critere d'acceptation:
- `ownerWithdraw(user, amount)` est reserve au owner, sinon `NotOwner()`.
- Revert avec `InsufficientBalance()` si `balances[user] < amount`.
- `balances[user]` diminue de `amount`.
- L'ETH est transfere a `owner`.
- L'evenement `Withdraw(user, amount)` est emis.

### US5 - Pause/Unpause
En tant que owner,
je veux activer ou desactiver la pause,
afin de bloquer certaines operations en cas de risque.

Critere d'acceptation:
- `setPaused(bool)` est reserve au owner, sinon `NotOwner()`.
- La valeur de `paused` est mise a jour.
- L'evenement `PausedStateChanged(newState)` est emis.

## Cas de tests minimaux recommandes
- Verification du owner au deploiement.
- `deposit` reussi hors pause et revert en pause.
- `withdraw` reussi avec solde suffisant; revert sinon.
- `ownerWithdraw` accessible uniquement au owner.
- `setPaused` accessible uniquement au owner et emission d'evenement.
