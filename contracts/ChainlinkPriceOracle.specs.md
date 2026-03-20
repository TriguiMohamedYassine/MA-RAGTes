# ChainlinkPriceOracle.sol User Stories

## Scope
Read latest price data from a Chainlink aggregator feed.

## Primary Actors
- On-chain consumer contract
- Off-chain integration developer

## User Stories
- As a consumer contract, I want to read the latest price from Chainlink, so that I can price assets using an external oracle.
- As an integration developer, I want the oracle contract to expose a simple getter, so that I can reduce integration complexity.
- As a protocol engineer, I want to read round metadata from the aggregator, so that I can validate freshness and reliability.

## Acceptance Criteria
- Contract returns the latest oracle price in feed-native decimals.
- Reads are view-only and do not mutate state.
- Integration can detect stale or invalid round responses using aggregator fields.
