# LimitOrderHook.sol User Stories

## Scope
Uniswap v4 hook for placing, executing, and canceling on-chain limit orders around swap events.

## Primary Actors
- Trader placing limit orders
- Pool manager/hook system
- Order owner canceling orders

## User Stories
- As a trader, I want to place a limit order at a target tick/price, so that my trade executes only when market conditions are favorable.
- As a trader, I want the hook to evaluate orders after swaps, so that executable orders are filled automatically.
- As an order owner, I want to cancel my pending order, so that I can manage risk if market conditions change.
- As a protocol integrator, I want explicit hook permissions, so that hook behavior is transparent and deterministic.

## Acceptance Criteria
- Order placement stores owner, side, amount, and trigger conditions.
- After swap callback executes only qualifying orders and updates order state.
- Cancel operation is restricted to order owner or authorized logic.
- Hook permission configuration matches implemented callbacks.
