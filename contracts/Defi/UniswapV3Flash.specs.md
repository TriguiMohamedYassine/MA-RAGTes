# UniswapV3Flash.sol User Stories

## Scope
Uniswap v3 flash loan helper with callback repayment flow.

## Primary Actors
- Arbitrage trader
- Flash strategy developer

## User Stories
- As an arbitrage trader, I want to borrow token0/token1 via v3 flash, so that I can execute price discrepancy strategies.
- As a strategy developer, I want callback control after loan receipt, so that custom trade logic can run before repayment.
- As a protocol user, I want strict repayment enforcement, so that failed strategies revert atomically.

## Acceptance Criteria
- Flash function requests loan from configured v3 pool.
- Callback verifies pool origin and decodes context data.
- Borrowed amounts and owed fees are repaid within callback.
- Entire transaction reverts if repayment cannot be completed.
