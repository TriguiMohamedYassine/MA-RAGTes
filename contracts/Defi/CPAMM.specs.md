# CPAMM.sol User Stories

## Scope
Constant Product AMM with liquidity shares, swaps, and reserve updates.

## Primary Actors
- Liquidity provider
- Trader
- Protocol integrator

## User Stories
- As a trader, I want to swap one token for the other, so that I can execute market trades against pool liquidity.
- As a liquidity provider, I want to add liquidity and receive LP shares, so that I can earn fees proportional to my contribution.
- As a liquidity provider, I want to remove liquidity by burning shares, so that I can redeem underlying tokens.
- As a protocol integrator, I want reserves updated on each operation, so that pool pricing remains consistent with balances.

## Acceptance Criteria
- Swap output follows constant-product pricing and deducts configured fees.
- Initial and subsequent liquidity mints shares according to pool ratio rules.
- Removing liquidity returns assets proportional to burned shares.
- Reserve state matches token balances after swap/add/remove operations.
