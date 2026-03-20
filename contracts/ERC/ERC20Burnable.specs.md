# ERC20Burnable.sol User Stories

## Scope
ERC20 extension allowing token destruction by holder or approved spender.

## Primary Actors
- Token holder
- Approved spender
- Treasury/accounting team

## User Stories
- As a token holder, I want to burn my tokens, so that I can permanently reduce circulating supply.
- As an approved spender, I want to burn tokens from a holder within allowance, so that compliance or product flows can consume tokens.
- As a treasury manager, I want total supply to decrease after burns, so that supply metrics remain truthful.

## Acceptance Criteria
- `burn` reduces caller balance and total supply.
- `burnFrom` requires sufficient allowance and updates allowance after burn.
- Burn operations emit transfer-to-zero-address semantics per ERC20 behavior.
