# Vault.sol User Stories

## Scope
Token vault issuing shares on deposit and redeeming underlying assets on withdraw.

## Primary Actors
- Depositor
- Shareholder withdrawing funds

## User Stories
- As a depositor, I want to deposit an underlying token and receive vault shares, so that my position is represented proportionally.
- As a depositor, I want fair share pricing between early and later deposits, so that ownership remains equitable.
- As a shareholder, I want to burn shares to withdraw underlying tokens, so that I can redeem my share of vault assets.
- As a protocol integrator, I want deterministic mint/burn math, so that accounting and UI projections are reliable.

## Acceptance Criteria
- Deposit transfers underlying tokens from user and mints correct share amount.
- First deposit and subsequent deposits use appropriate share pricing formulas.
- Withdraw burns shares and sends proportional underlying amount to user.
- Contract reverts when deposits or withdrawals violate balance/share constraints.
