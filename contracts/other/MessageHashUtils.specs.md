# MessageHashUtils.sol User Stories

## Scope
Hashing helpers for constructing signed message digests (for example EIP-191 and EIP-712 related flows).

## Primary Actors
- Signer/application developer
- Relayer/integrator
- Security reviewer

## User Stories
- As a developer, I want standardized message hashing helpers, so that signatures are generated and verified consistently.
- As a relayer, I want digest formats that match signer wallet expectations, so that off-chain signatures validate on-chain.
- As a reviewer, I want clear domain/message hash construction, so that signature replay and mismatch risks are reduced.

## Acceptance Criteria
- Hash helper outputs match canonical standards for supported message formats.
- Inputs map deterministically to a single digest value.
- Signature verification workflows using these hashes succeed for valid signatures and fail for invalid ones.
