# IERC721Enumerable.sol User Stories

## Scope
Optional ERC721 extension interface for global and per-owner token enumeration.

## Primary Actors
- NFT implementer
- Marketplace/indexer integrator
- End user

## User Stories
- As an implementer, I want to expose enumerable token views, so that external apps can iterate collection holdings.
- As a marketplace, I want total supply and indexed token queries, so that listing and discovery are easier.
- As a user, I want wallet apps to enumerate my NFT IDs without custom indexing.

## Acceptance Criteria
- Interface declares `totalSupply`, `tokenByIndex`, and `tokenOfOwnerByIndex`.
- Enumeration methods are view-only and do not alter token ownership state.
- Implementations provide deterministic ordering per contract policy.
