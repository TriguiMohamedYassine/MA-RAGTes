# StableSwap.sol User Stories

## Scope
Curve-style stable AMM for low-slippage swaps between similarly priced assets with LP shares.

## Primary Actors
- Stablecoin trader
- Liquidity provider

## User Stories
- As a stablecoin trader, I want to swap between pegged assets with low slippage, so that I preserve value during conversion.
- As a liquidity provider, I want to deposit multiple assets and mint pool shares, so that I can earn protocol trading fees.
- As a liquidity provider, I want to withdraw proportionally or in a single token, so that I can optimize my exit strategy.
- As an integrator, I want virtual price visibility, so that I can measure LP token value over time.

## Acceptance Criteria
- Swap output uses stable-swap invariant and respects minimum output constraints.
- Liquidity add/remove operations mint and burn shares consistently.
- Single-token withdrawal uses invariant math and slippage checks.
- Virtual price reflects current pool state and total shares.
