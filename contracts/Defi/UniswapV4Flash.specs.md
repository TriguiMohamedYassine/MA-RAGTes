# UniswapV4Flash.sol User Stories

## Scope
Uniswap v4 flash operation via PoolManager unlock callback with currency settlement/take mechanics.

## Primary Actors
- Flash strategy executor
- PoolManager callback system

## User Stories
- As a strategy executor, I want to request flash liquidity in a chosen currency, so that I can run atomic opportunities.
- As a contract developer, I want unlock callback handling, so that borrow-use-repay lifecycle runs in one controlled flow.
- As an integrator, I want native and ERC20 currency support, so that flash logic works across asset types.

## Acceptance Criteria
- Flash call triggers PoolManager unlock with encoded context.
- Callback executes strategy logic and repays borrowed amount plus any required fee.
- Currency settlement and take operations match PoolManager accounting expectations.
- Invalid callback origins or repayment shortfalls revert transaction.
