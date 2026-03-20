# OracleReader.sol User Stories

## Scope
Read Chronicle oracle values and age, with optional self-authorization flow.

## Primary Actors
- Protocol contract
- Oracle maintainer

## User Stories
- As a protocol contract, I want to read oracle value and age in one call, so that I can enforce freshness checks.
- As an integrator, I want a simple reader wrapper, so that upstream oracle interfaces are easier to consume.
- As an oracle maintainer, I want self-kiss authorization where required, so that reader access follows oracle permission rules.

## Acceptance Criteria
- Reader returns both value and age when available from source oracle.
- Calls are read-only and do not mutate state.
- Integration can reject stale values using returned age.
