# IERC721Receiver.sol User Stories

## Scope
Interface for contracts that can safely receive ERC721 tokens.

## Primary Actors
- Receiver contract developer
- ERC721 token contract
- Integrator/auditor

## User Stories
- As a receiver developer, I want an ERC721 receive callback, so that my contract can accept NFT safe transfers.
- As an ERC721 contract, I want explicit acceptance signaling from receiver contracts, so that NFTs are not sent to incompatible addresses.
- As an auditor, I want a standard return selector definition, so that safe transfer behavior can be verified.

## Acceptance Criteria
- Interface declares `onERC721Received` with required parameters and return value.
- Safe transfers to contracts succeed only when correct selector is returned.
- Invalid or missing selector responses cause transfer reversion.
