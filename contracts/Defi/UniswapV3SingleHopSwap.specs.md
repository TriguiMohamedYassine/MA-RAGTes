# UniswapV3SingleHopSwap.sol User Stories

## Scope
Single-hop Uniswap v3 swaps for exact-input and exact-output execution.

## Primary Actors
- Trader
- Integrator

## User Stories
- As a trader, I want to execute exact-input single-hop swaps, so that I can control spend and enforce minimum output.
- As a trader, I want to execute exact-output single-hop swaps, so that I can receive a target output while capping maximum input.
- As an integrator, I want clean router parameter examples, so that I can integrate v3 swap flows correctly.

## Acceptance Criteria
- Exact-input path enforces `amountOutMinimum`.
- Exact-output path enforces `amountInMaximum` and refunds unused input where applicable.
- Token approvals are set before router calls.
- Swap results are returned to caller and observable.
