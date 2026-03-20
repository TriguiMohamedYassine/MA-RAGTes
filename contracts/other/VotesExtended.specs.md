# VotesExtended.sol User Stories

## Scope
Voting power extension utilities for delegation, checkpoints, and richer vote-related queries.

## Primary Actors
- Token holder/voter
- Delegate
- Governance integrator

## User Stories
- As a holder, I want to delegate voting power, so that governance participation can be managed flexibly.
- As an integrator, I want historical vote checkpoints and extended queries, so that governance calculations are accurate.
- As a delegate, I want vote power updates when balances or delegations change, so that my represented power is current.

## Acceptance Criteria
- Delegation updates checkpointed vote balances consistently.
- Historical vote queries return block-specific values.
- Extended vote query functions remain coherent with core delegation and transfer events.
