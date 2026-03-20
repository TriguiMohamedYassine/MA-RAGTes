# StakingRewards.sol User Stories

## Scope
Time-based staking rewards with configurable reward duration and owner-funded emissions.

## Primary Actors
- Staker
- Contract owner/reward manager

## User Stories
- As a staker, I want to stake tokens and accrue rewards over time, so that I can earn yield.
- As a staker, I want to withdraw part or all of my stake, so that I can manage liquidity needs.
- As a staker, I want to claim earned rewards independently of unstaking, so that I can realize gains without exiting.
- As an owner, I want to notify new reward amounts and durations, so that distribution can be managed in epochs.

## Acceptance Criteria
- Reward accrual is proportional to stake and active reward rate.
- Stake/withdraw/claim operations update user reward state correctly.
- Owner-only functions enforce access control.
- New reward notifications handle overlapping reward periods safely.
