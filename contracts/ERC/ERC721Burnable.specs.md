# ERC721Burnable.sol User Stories

## Scope
ERC721 extension enabling authorized holders/operators to permanently destroy NFTs.

## Primary Actors
- NFT owner
- Approved operator
- Collection admin/auditor

## User Stories
- As an NFT owner, I want to burn a token I own, so that I can retire it permanently.
- As an approved operator, I want to burn on behalf of owner when authorized, so that platform workflows can execute.
- As an auditor, I want burn operations to clear ownership and approvals, so that records remain consistent.

## Acceptance Criteria
- Burn requires owner or approved authorization.
- Burned token no longer exists and cannot be transferred.
- Approval state for the burned token is cleared.
