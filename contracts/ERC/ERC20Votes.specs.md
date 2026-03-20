# ERC20Votes.sol User Stories

## Scope
ERC20 governance extension with delegated voting power and checkpointed vote history.

## Primary Actors
- Token holder/governance voter
- Delegate
- Governance contract/integrator

## User Stories
- As a token holder, I want to delegate voting power to myself or another address, so that governance participation is flexible.
- As a governance contract, I want historical vote snapshots at specific blocks, so that proposals use deterministic quorum and voting power.
- As a voter, I want voting power updates when balances change, so that governance reflects token ownership.

## Acceptance Criteria
- Delegation updates delegate checkpoints and emits delegate-change events.
- Vote queries for past blocks return checkpointed values, not current mutable balances.
- Transfers and mint/burn operations correctly update delegated voting power.
