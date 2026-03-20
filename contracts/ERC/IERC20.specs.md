# IERC20.sol User Stories

## Scope
Interface contract defining ERC20 core behavior for fungible tokens.

## Primary Actors
- Token implementer
- Wallet/exchange integrator
- Auditor

## User Stories
- As a token implementer, I want a standard ERC20 interface, so that my token works across wallets and protocols.
- As an integrator, I want stable method signatures for transfer and allowance logic, so that I can integrate once and reuse.
- As an auditor, I want clear event and function expectations, so that compliance validation is consistent.

## Acceptance Criteria
- Interface declares balance, transfer, allowance, approve, and transferFrom methods.
- Transfer and approval events are declared with expected indexed fields.
- Implementations can be checked for ERC20 compatibility against this contract.
