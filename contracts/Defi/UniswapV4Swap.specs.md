# UniswapV4Swap.sol User Stories

## Scope
Uniswap v4 exact-input swap flow implemented through unlock callback and PoolManager interactions.

## Primary Actors
- Trader
- Protocol integrator

## User Stories
- As a trader, I want to perform exact-input swaps on v4 pools, so that I can trade through the new PoolManager architecture.
- As a developer, I want swap execution wrapped in unlock callback flow, so that settlement and token transfers follow v4 rules.
- As a user, I want slippage protection on swaps, so that unfavorable execution is rejected.

## Acceptance Criteria
- Swap request encodes pool key, params, and hook data for callback execution.
- Callback performs transfer, approval, settle, and take operations in required order.
- Resulting output amount is validated against user minimum.
- Unsupported currencies or failed transfers revert safely.
