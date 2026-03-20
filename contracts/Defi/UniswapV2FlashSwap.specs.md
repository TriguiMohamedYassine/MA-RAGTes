# UniswapV2FlashSwap.sol User Stories

## Scope
Uniswap v2 flash swap execution with callback-based repayment logic.

## Primary Actors
- Arbitrageur/strategy executor
- Uniswap pair callback

## User Stories
- As a strategy executor, I want to borrow assets via flash swap, so that I can run capital-efficient arbitrage.
- As the contract, I want to receive callback execution from the pair, so that I can perform custom logic before repayment.
- As a risk-conscious user, I want transaction-level atomicity, so that unprofitable paths revert automatically.

## Acceptance Criteria
- Flash swap initiates by calling pair swap with callback data.
- Callback validates caller and executes strategy logic.
- Borrowed amount plus required fee is repaid within same transaction.
- Transaction reverts if repayment or strategy conditions fail.
