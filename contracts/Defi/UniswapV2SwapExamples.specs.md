# UniswapV2SwapExamples.sol User Stories

## Scope
Reference examples for Uniswap v2 single-hop and multi-hop swaps with exact-input and exact-output variants.

## Primary Actors
- Trader
- Integrator learning swap patterns

## User Stories
- As a trader, I want a single-hop exact-input swap example, so that I can trade with known input and minimum output protection.
- As a trader, I want a multi-hop exact-input example, so that I can route through intermediate assets.
- As a trader, I want exact-output examples, so that I can cap max input while targeting a specific output amount.
- As an integrator, I want reusable patterns for approvals and router calls, so that implementation errors are reduced.

## Acceptance Criteria
- Each swap path calls the matching router function.
- Exact-input methods respect `amountOutMin` slippage constraints.
- Exact-output methods respect `amountInMax` spend constraints.
- Token approvals and transfers are handled before router execution.
