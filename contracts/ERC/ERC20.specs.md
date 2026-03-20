# ERC20.sol User Stories

## Scope
Fungible token standard for balances, transfers, allowances, and delegated spending.

## Primary Actors
- Token holder
- Spender approved by holder
- Wallet/exchange integrator

## User Stories
- As a token holder, I want to transfer tokens to another address, so that I can pay or move value.
- As a token holder, I want to approve a spender with an allowance, so that third-party apps can spend on my behalf.
- As an approved spender, I want to transfer tokens from the owner within allowance limits, so that protocol interactions can execute.
- As an integrator, I want to read balances and allowances, so that UI and risk checks are accurate.

## Acceptance Criteria
- Transfers fail when sender balance is insufficient.
- `approve` sets allowance and emits approval events.
- `transferFrom` decreases allowance correctly unless unlimited semantics are intentionally implemented.
- Transfer and approval events reflect state changes accurately.
