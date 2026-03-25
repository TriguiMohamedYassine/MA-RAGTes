# MetaCoin - Specifications fonctionnelles

## Portee
Ce document decrit le comportement attendu du contrat `MetaCoin` dans `MetaCoin.sol`.

## User stories principales

### US1 - Allocation initiale
En tant que deployeeur,
je veux recevoir un solde initial de `10000` tokens a la creation,
afin de disposer d'une reserve initiale.

Critere d'acceptation:
- Au deploiement, `balances[msg.sender] == 10000`.

### US2 - Transfert de tokens
En tant qu'utilisateur detenant des tokens,
je veux envoyer des tokens a une autre adresse,
afin de transferer de la valeur.

Critere d'acceptation:
- `sendCoin(receiver, amount)` diminue le solde de l'expediteur de `amount`.
- `sendCoin(receiver, amount)` augmente le solde du receveur de `amount`.
- L'evenement `Transfer(from, to, value)` est emis.
- La fonction retourne `true` quand le transfert reussit.

### US3 - Protection contre solde insuffisant
En tant que systeme,
je veux refuser les transferts superieurs au solde disponible,
afin de proteger l'integrite des soldes.

Critere d'acceptation:
- Si `balances[msg.sender] < amount`, `sendCoin` revert avec `"Solde insuffisant"`.

### US4 - Consultation des soldes
En tant qu'utilisateur ou application tierce,
je veux lire le solde d'une adresse,
afin de verifier les fonds disponibles.

Critere d'acceptation:
- `getBalance(addr)` retourne `balances[addr]`.
- `getBalanceInEth(addr)` retourne la meme valeur que `getBalance(addr)`.

## Notes importantes
- Le contrat n'implemente pas ERC20 complet; il s'agit d'une logique simple basee sur un mapping interne.
- `getBalanceInEth` est un alias de compatibilite qui ne fait aucune conversion.

## Cas de tests minimaux recommandes
- Verification de l'allocation initiale au deployeur.
- Transfert valide et verification de l'evenement `Transfer`.
- Revert sur transfert au-dela du solde.
- Verification que `getBalanceInEth(addr) == getBalance(addr)`.