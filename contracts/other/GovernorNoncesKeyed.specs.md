# GovernorNoncesKeyed.sol User Stories

## Scope
Governance nonce module with keyed nonce domains for secure signature-based interactions.

## Primary Actors
- Governance voter/signature owner
- Relayer
- Security reviewer

## User Stories
- As a signer, I want keyed nonces for governance signatures, so that replay protection is scoped and reliable.
- As a relayer, I want deterministic nonce validation, so that off-chain submitted votes/operations are accepted once.
- As a reviewer, I want nonce usage segregated by key/context, so that cross-feature replay risk is minimized.

## Acceptance Criteria
- Nonces increment or consume exactly once per valid keyed action.
- Replayed signatures with used nonce/key pairs are rejected.
- Nonce retrieval functions expose current state for clients.
