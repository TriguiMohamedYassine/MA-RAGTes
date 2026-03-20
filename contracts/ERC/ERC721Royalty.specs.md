# ERC721Royalty.sol User Stories

## Scope
ERC721 extension integrating ERC2981 royalty information for NFT secondary sales.

## Primary Actors
- Creator/royalty recipient
- NFT marketplace
- Collection owner/admin

## User Stories
- As a creator, I want royalties attached to my NFT collection, so that I can receive ongoing compensation.
- As a marketplace, I want standardized royalty queries from the NFT contract, so that payouts can be automated.
- As a collection admin, I want to configure royalty settings safely, so that fee policies are enforced.

## Acceptance Criteria
- Contract exposes ERC721 functionality with ERC2981 royalty compatibility.
- Royalty query returns correct receiver and amount for a given sale price.
- Interface support checks include royalty and NFT standards as expected.
