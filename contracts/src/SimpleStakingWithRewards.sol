// SPDX-License-Identifier: MIT
pragma solidity ^0.8.26;

contract SimpleStakingWithRewards {
    string public name = "Reward Staking Pool";

    address public owner;
    uint256 public totalStaked;
    uint256 public rewardRate = 10;           // 10% APY (simplified)
    uint256 public lastUpdateTime;
    uint256 public rewardPerTokenStored;

    mapping(address => uint256) public balances;
    mapping(address => uint256) public userRewardPerTokenPaid;
    mapping(address => uint256) public rewards;

    event Staked(address indexed user, uint256 amount);
    event Withdrawn(address indexed user, uint256 amount);
    event RewardPaid(address indexed user, uint256 reward);
    event RewardRateUpdated(uint256 newRate);

    modifier onlyOwner() {
        require(msg.sender == owner, "Only owner can call this");
        _;
    }

    modifier updateReward(address account) {
        rewardPerTokenStored = rewardPerToken();
        lastUpdateTime = block.timestamp;
        
        if (account != address(0)) {
            rewards[account] = earned(account);
            userRewardPerTokenPaid[account] = rewardPerTokenStored;
        }
        _;
    }

    constructor() {
        owner = msg.sender;
        lastUpdateTime = block.timestamp;
    }

    // ==================== VIEW FUNCTIONS ====================

    function rewardPerToken() public view returns (uint256) {
        if (totalStaked == 0) {
            return rewardPerTokenStored;
        }
        return rewardPerTokenStored + 
               ((block.timestamp - lastUpdateTime) * rewardRate * 1e18) / totalStaked;
    }

    function earned(address account) public view returns (uint256) {
        return 
            ((balances[account] * (rewardPerToken() - userRewardPerTokenPaid[account])) / 1e18) 
            + rewards[account];
    }

    function getStakedBalance(address account) public view returns (uint256) {
        return balances[account];
    }

    // ==================== MAIN FUNCTIONS ====================

    function stake(uint256 amount) external updateReward(msg.sender) {
        require(amount > 0, "Cannot stake 0");
        require(msg.sender != address(0), "Invalid address");

        // In real test, we simulate token by just increasing balance
        // (for testing we don't need real token transfer)
        balances[msg.sender] += amount;
        totalStaked += amount;

        emit Staked(msg.sender, amount);
    }

    function withdraw(uint256 amount) external updateReward(msg.sender) {
        require(amount > 0, "Cannot withdraw 0");
        require(balances[msg.sender] >= amount, "Insufficient staked balance");

        balances[msg.sender] -= amount;
        totalStaked -= amount;

        emit Withdrawn(msg.sender, amount);
    }

    function claimReward() external updateReward(msg.sender) {
        uint256 reward = rewards[msg.sender];
        require(reward > 0, "No rewards to claim");

        rewards[msg.sender] = 0;
        // In real version we would transfer reward tokens here
        // For testing we just emit event

        emit RewardPaid(msg.sender, reward);
    }

    function compound() external updateReward(msg.sender) {
        uint256 reward = rewards[msg.sender];
        require(reward > 0, "No rewards to compound");

        rewards[msg.sender] = 0;
        
        // Add reward to staked balance
        balances[msg.sender] += reward;
        totalStaked += reward;

        emit Staked(msg.sender, reward);
        emit RewardPaid(msg.sender, reward);
    }

    // ==================== OWNER FUNCTIONS ====================

    function setRewardRate(uint256 newRate) external onlyOwner {
        require(newRate <= 100, "Reward rate too high");
        // Update reward before changing rate
        rewardPerTokenStored = rewardPerToken();
        lastUpdateTime = block.timestamp;
        
        rewardRate = newRate;
        emit RewardRateUpdated(newRate);
    }

    function emergencyWithdraw() external onlyOwner {
        // For testing - reset everything (use with caution)
        totalStaked = 0;
        lastUpdateTime = block.timestamp;
        rewardPerTokenStored = 0;
    }

    // Fallback to receive ETH if needed for testing
    receive() external payable {}
}