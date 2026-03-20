# UniswapV2AddLiquidity.sol User Stories

## Scope
Utility contract for adding and removing Uniswap v2 liquidity with safe token handling.

## Primary Actors
- Liquidity provider
- Protocol integrator

## User Stories
- As a liquidity provider, I want to add token pair liquidity through a helper contract, so that I reduce repetitive approval and router logic.
- As a liquidity provider, I want to remove liquidity and receive both tokens back, so that I can exit positions cleanly.
- As an integrator, I want safe transfer and safe approve wrappers, so that ERC20 interaction failures are handled consistently.

## Acceptance Criteria
- Add liquidity transfers user tokens in and mints LP position via router.
- Remove liquidity burns LP tokens and returns underlying assets.
- Safe wrappers revert on failed token calls.
- Contract does not retain user funds unexpectedly after operation.
