# IERC20Metadata.sol User Stories

## Scope
Optional ERC20 metadata interface for token name, symbol, and decimals.

## Primary Actors
- Token implementer
- Wallet/UI integrator
- End user

## User Stories
- As a token implementer, I want to expose human-readable metadata, so that users can identify my token.
- As a wallet integrator, I want metadata methods with predictable signatures, so that token display is consistent.
- As an end user, I want to see correct symbol and decimals, so that balances are interpreted properly.

## Acceptance Criteria
- Interface declares `name`, `symbol`, and `decimals` view functions.
- Methods are optional extensions and do not alter ERC20 transfer semantics.
- Integrators can gracefully rely on these methods when implemented.
