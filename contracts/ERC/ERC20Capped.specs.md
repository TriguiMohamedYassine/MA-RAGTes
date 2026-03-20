# ERC20Capped.sol User Stories

## Scope
ERC20 extension enforcing an immutable maximum total supply cap.

## Primary Actors
- Token minter/admin
- Token holder
- Auditor/integrator

## User Stories
- As a token minter, I want minting to stop at a fixed cap, so that inflation cannot exceed policy.
- As a token holder, I want a predictable maximum supply, so that dilution risk is bounded.
- As an auditor, I want on-chain enforcement of cap checks, so that minting constraints are verifiable.

## Acceptance Criteria
- Contract stores a cap value that does not change after deployment.
- Minting reverts when new total supply would exceed cap.
- Minting below cap succeeds and updates balances/supply correctly.
