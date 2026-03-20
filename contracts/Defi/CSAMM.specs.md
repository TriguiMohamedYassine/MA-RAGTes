# CSAMM.sol User Stories

## Scope
Constant Sum AMM with token swaps and LP share accounting.

## Primary Actors
- Trader
- Liquidity provider

## User Stories
- As a trader, I want to swap token A for token B with predictable arithmetic, so that I can use a low-slippage pool near parity.
- As a liquidity provider, I want to add balanced liquidity and receive shares, so that I can participate in pool fees.
- As a liquidity provider, I want to burn shares to withdraw my proportional assets, so that I can exit the pool at any time.

## Acceptance Criteria
- Swap function accepts one supported token and transfers the other token out.
- Share minting and burning preserve proportional ownership among providers.
- Pool reserves update after each swap and liquidity operation.
- Invalid token inputs and insufficient balances revert safely.
