# GovernorCountingSimple.sol User Stories

## Scope
Simple vote counting module for governance proposals using for/against/abstain categories.

## Primary Actors
- Governance voter
- Governance proposal analyzer
- Governance admin

## User Stories
- As a voter, I want to choose for, against, or abstain, so that my position is represented clearly.
- As a governance system, I want consistent counting logic, so that proposal outcomes are deterministic.
- As an analyzer, I want access to per-category vote totals, so that reporting is transparent.

## Acceptance Criteria
- Vote options are limited to supported categories.
- Counts for each category update correctly on valid vote casts.
- Outcome determination uses the configured counting rules and quorum policy.
