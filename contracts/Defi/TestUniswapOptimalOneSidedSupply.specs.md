# TestUniswapOptimalOneSidedSupply.sol User Stories

## Scope
One-sided liquidity provisioning helper that computes optimal swap amount before adding Uniswap v2 liquidity.

## Primary Actors
- Liquidity provider with single-token balance
- Strategy developer

## User Stories
- As a liquidity provider, I want to provide liquidity using only one token, so that I do not need to source both sides manually.
- As a strategy developer, I want an optimal swap amount formula, so that leftover balances are minimized.
- As a user, I want zap flow to swap and then add liquidity in one process, so that execution is simpler.

## Acceptance Criteria
- Contract computes swap amount from reserves and input amount.
- Zap performs token swap and liquidity add in correct sequence.
- Flow reverts on invalid pair/router assumptions or failed transfers.
- Residual token dust is minimized versus naive half-split approach.
