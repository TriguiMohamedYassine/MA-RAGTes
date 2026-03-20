# GovernorVotesQuorumFraction.sol User Stories

## Scope
Governance quorum module deriving quorum as a fraction of token total supply at snapshot.

## Primary Actors
- Governance admin
- Governance voter
- Governance auditor

## User Stories
- As an admin, I want quorum configured as a supply fraction, so that governance scales with token distribution.
- As a voter, I want quorum calculated at the proposal snapshot, so that vote thresholds are deterministic.
- As an auditor, I want quorum math transparent and bounded, so that governance legitimacy is verifiable.

## Acceptance Criteria
- Quorum calculation uses snapshot supply and configured numerator/denominator rules.
- Quorum parameter updates are permissioned and reflected in subsequent proposals per design.
- Proposal success checks include quorum satisfaction.
