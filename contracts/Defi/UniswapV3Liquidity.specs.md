# UniswapV3Liquidity.sol User Stories

## Scope
Manage Uniswap v3 NFT liquidity positions: mint, increase, decrease, and collect fees.

## Primary Actors
- Liquidity provider
- Position manager integrator

## User Stories
- As a liquidity provider, I want to mint a new concentrated liquidity position, so that I can target a custom price range.
- As a liquidity provider, I want to increase liquidity in an existing position, so that I can scale exposure when conditions are favorable.
- As a liquidity provider, I want to decrease liquidity and collect tokens, so that I can rebalance or exit.
- As a liquidity provider, I want to collect accrued fees, so that I can realize trading revenue.
- As a receiver contract, I want to handle ERC721 position receipts safely, so that position NFTs are not lost.

## Acceptance Criteria
- New position mint returns tokenId, liquidity, and actual token usage.
- Increase/decrease operations call position manager with proper params.
- Fee collection transfers owed tokens to designated recipient.
- Contract supports ERC721 receipt callback for position NFTs.
