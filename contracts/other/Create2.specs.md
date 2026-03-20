# Create2.sol User Stories

## Scope
Utility support for deterministic contract deployment and address precomputation using CREATE2.

## Primary Actors
- Smart contract deployer
- Protocol developer
- Infrastructure integrator

## User Stories
- As a deployer, I want deterministic deployment addresses, so that off-chain systems can preconfigure integrations.
- As a developer, I want to compute CREATE2 addresses before deployment, so that I can validate salts and bytecode.
- As an integrator, I want failed deployments to revert clearly, so that automation can handle errors safely.

## Acceptance Criteria
- Address computation follows CREATE2 formula for deployer, salt, and bytecode hash.
- Deployment helper reverts on empty bytecode or failed creation.
- Predicted and actual addresses match when inputs are identical.
