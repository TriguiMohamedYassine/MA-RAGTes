# ERC20FlashMint.sol User Stories

## Scope
ERC20 extension supporting flash-minted tokens that must be repaid in the same transaction.

## Primary Actors
- Flash borrower
- Protocol integrator
- Token issuer

## User Stories
- As a flash borrower, I want temporary access to tokens with no upfront collateral, so that I can execute arbitrage or refinancing logic.
- As a token issuer, I want flash loans to require repayment plus fee in the same transaction, so that protocol solvency is preserved.
- As an integrator, I want standardized callback flow, so that flash loan integrations are reliable.

## Acceptance Criteria
- Borrowed amount is minted for borrower during flash operation.
- Transaction reverts if principal and fee are not returned by completion.
- Successful flash flow restores final supply consistency and collects configured fees.
