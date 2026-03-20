# ERC20Pausable.sol User Stories

## Scope
ERC20 extension allowing authorized accounts to pause and unpause token transfers.

## Primary Actors
- Pause admin
- Token holder
- Exchange/integrator

## User Stories
- As a pause admin, I want to pause transfers during incidents, so that potential damage can be contained.
- As a pause admin, I want to unpause once risk is mitigated, so that normal market activity resumes.
- As a token holder, I want pause state to be explicit and consistent, so that I understand temporary restrictions.

## Acceptance Criteria
- While paused, transfer and transferFrom actions revert.
- Mint/burn behavior follows contract policy for pause enforcement.
- Pause and unpause actions are permissioned and emit state-change events.
