# TrieProof.sol User Stories

## Scope
Utilities for verifying Merkle Patricia trie proofs and related encoded state membership checks.

## Primary Actors
- Cross-chain/light-client developer
- Protocol integrator
- Security auditor

## User Stories
- As a developer, I want to verify trie proofs on-chain, so that external state claims can be trusted.
- As an integrator, I want deterministic proof verification results, so that bridging/state-sync logic can rely on them.
- As an auditor, I want strict decoding and hashing rules, so that malformed proofs are rejected.

## Acceptance Criteria
- Valid proofs return successful membership/non-membership outcome per function design.
- Invalid nodes, malformed encodings, or hash mismatches are rejected.
- Verification logic follows canonical trie path and node hashing semantics.
