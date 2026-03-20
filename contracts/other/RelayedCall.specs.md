# RelayedCall.sol User Stories

## Scope
Meta-transaction or relayed execution utility enabling third parties to submit calls on behalf of users.

## Primary Actors
- End user/signer
- Relayer
- Protocol contract

## User Stories
- As a user, I want to authorize calls by signature, so that I can interact without directly sending transactions.
- As a relayer, I want verifiable authorization checks, so that I can safely submit user-intended operations.
- As a protocol, I want replay-protected relayed calls, so that duplicate execution is prevented.

## Acceptance Criteria
- Relayed execution validates signer intent and payload integrity.
- Nonce/replay protections reject duplicated authorizations.
- Failed authorization or malformed payloads revert without state changes.
