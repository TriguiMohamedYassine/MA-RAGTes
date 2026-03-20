# IERC1155Receiver.sol User Stories

## Scope
Interface for contracts that can safely receive ERC1155 single and batch token transfers.

## Primary Actors
- Receiver contract developer
- ERC1155 token contract
- Integrator/auditor

## User Stories
- As a receiver developer, I want callback hooks for single and batch receives, so that my contract can accept or reject incoming tokens.
- As an ERC1155 token contract, I want deterministic acceptance responses, so that transfers only succeed to compatible receivers.
- As an auditor, I want standard selectors defined, so that receiver correctness can be verified.

## Acceptance Criteria
- Interface declares `onERC1155Received` and `onERC1155BatchReceived` with expected signatures.
- Receiver implementations must return exact acceptance magic values for successful transfers.
- Non-compliant responses cause safe transfer flows to revert.
