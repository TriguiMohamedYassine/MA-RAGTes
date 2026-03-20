# Auth.sol User Stories

## Scope
Authorization and token lock management with time-based unlock controls.

## Primary Actors
- Contract owner/admin
- Authorized operator
- Treasury manager

## User Stories
- As a contract owner, I want to allow an address, so that trusted operators can execute protected actions.
- As a contract owner, I want to deny an address, so that I can revoke compromised or obsolete permissions quickly.
- As an authorized operator, I want to configure lock duration per token, so that vesting and release policies are enforceable.
- As an authorized operator, I want to lock token amounts into the contract, so that funds remain unavailable until unlock conditions are met.
- As an authorized operator, I want to unlock only the claimable amount, so that token releases are consistent with elapsed time.
- As an authorized operator, I want to sync lock state with actual balances, so that accounting remains correct after external token transfers.

## Acceptance Criteria
- Unauthorized callers cannot invoke admin or lock-management functions.
- Allowed and denied states change immediately and are queryable.
- Claimable amount increases over time according to configured lock duration.
- Unlock cannot transfer more than currently claimable amount.
- Sync updates lock tracking without granting extra claimable funds.
