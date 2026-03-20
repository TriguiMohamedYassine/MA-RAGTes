# DiscreteStakingRewards.sol User Stories

## Scope
Discrete reward distribution staking model with indexed rewards per staked token.

## Primary Actors
- Staker
- Reward distributor

## User Stories
- As a staker, I want to stake tokens, so that I can earn a share of future rewards.
- As a staker, I want to unstake my tokens, so that I can exit my position when needed.
- As a reward distributor, I want to inject rewards discretely, so that rewards are allocated based on active stake.
- As a staker, I want to claim accumulated rewards, so that I can realize earned yield.
- As a staker, I want my unclaimed rewards tracked across stake changes, so that accounting stays fair.

## Acceptance Criteria
- Updating reward index increases claimable rewards for current stakers only.
- Stake and unstake operations update user reward state before balance changes.
- Claim transfers only earned reward amount and resets user accrual correctly.
- Contract prevents claims when no rewards are available.
