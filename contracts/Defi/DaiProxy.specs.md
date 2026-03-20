# DaiProxy.sol User Stories

## Scope
MakerDAO proxy flow for opening CDP positions, borrowing DAI, repaying debt, and unlocking ETH collateral.

## Primary Actors
- Vault owner/user
- DeFi borrower

## User Stories
- As a borrower, I want to lock ETH collateral, so that I can open a debt position in Maker.
- As a borrower, I want to draw DAI against collateral, so that I can access liquidity without selling ETH.
- As a borrower, I want to repay part of my debt, so that I can reduce risk and interest exposure.
- As a borrower, I want to repay all debt in one action, so that I can close the position efficiently.
- As a borrower, I want to free ETH collateral after repayment, so that I can reclaim my assets.

## Acceptance Criteria
- Contract creates or uses a user proxy for executing Maker actions.
- Borrowing transfers requested DAI amount to the caller when collateral constraints permit.
- Partial and full repayment paths update debt consistently.
- ETH unlock operation reverts if collateralization constraints are violated.
