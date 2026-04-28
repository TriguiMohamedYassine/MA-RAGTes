// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

interface IStrategy {
    function invest(uint256 amount) external payable;
    function divest(uint256 amount) external returns (uint256);
    function totalAssets() external view returns (uint256);
    function harvest() external returns (uint256 profit);
}

contract YieldVault {
    string public name = "YieldVault";
    string public symbol = "yvTOKEN";
    uint8 public decimals = 18;

    uint256 public totalShares;
    uint256 public totalAssets;
    uint256 public performanceFee = 1000; // 10% in BPS
    uint256 public managementFee = 200;   // 2% annual in BPS
    uint256 public constant MAX_FEE = 3000;
    uint256 public constant BPS = 10000;
    uint256 public lastHarvestTime;

    address public governance;
    address public feeRecipient;
    bool public paused;
    bool private _locked;

    struct Strategy {
        bool active;
        uint256 allocation; // BPS of total assets
        uint256 totalInvested;
        uint256 totalHarvested;
    }

    mapping(address => uint256) public shares;
    mapping(address => mapping(address => uint256)) public allowance;
    mapping(address => Strategy) public strategies;
    address[] public strategyList;

    event Deposit(address indexed user, uint256 assets, uint256 shares);
    event Withdraw(address indexed user, uint256 assets, uint256 shares);
    event Harvested(address indexed strategy, uint256 profit, uint256 fee);
    event StrategyAdded(address indexed strategy, uint256 allocation);
    event StrategyRemoved(address indexed strategy);
    event EmergencyWithdraw(address indexed strategy, uint256 amount);
    event FeesUpdated(uint256 performanceFee, uint256 managementFee);

    modifier onlyGovernance() { require(msg.sender == governance, "Not governance"); _; }
    modifier notPaused() { require(!paused, "Paused"); _; }
    modifier noReentrant() { require(!_locked, "Reentrant"); _locked = true; _; _locked = false; }

    constructor(address _feeRecipient) {
        governance = msg.sender;
        feeRecipient = _feeRecipient;
        lastHarvestTime = block.timestamp;
    }

    receive() external payable {}

    function deposit() external payable noReentrant notPaused {
        require(msg.value > 0, "Zero deposit");
        uint256 sharesToMint;
        if (totalShares == 0 || totalAssets == 0) {
            sharesToMint = msg.value;
        } else {
            sharesToMint = (msg.value * totalShares) / totalAssets;
        }
        require(sharesToMint > 0, "Zero shares");
        _collectManagementFee();
        totalAssets += msg.value;
        totalShares += sharesToMint;
        shares[msg.sender] += sharesToMint;
        _allocateToStrategies(msg.value);
        emit Deposit(msg.sender, msg.value, sharesToMint);
    }

    function withdraw(uint256 shareAmount) external noReentrant {
        require(shares[msg.sender] >= shareAmount, "Insufficient shares");
        require(shareAmount > 0, "Zero shares");
        uint256 assets = (shareAmount * totalAssets) / totalShares;
        shares[msg.sender] -= shareAmount;
        totalShares -= shareAmount;
        totalAssets -= assets;
        uint256 available = address(this).balance;
        if (available < assets) {
            uint256 needed = assets - available;
            _withdrawFromStrategies(needed);
        }
        (bool ok,) = msg.sender.call{value: assets}("");
        require(ok, "Transfer failed");
        emit Withdraw(msg.sender, assets, shareAmount);
    }

    function harvest() external noReentrant notPaused {
        for (uint i = 0; i < strategyList.length; i++) {
            address addr = strategyList[i];
            if (!strategies[addr].active) continue;
            try IStrategy(addr).harvest() returns (uint256 profit) {
                if (profit > 0) {
                    uint256 fee = (profit * performanceFee) / BPS;
                    uint256 net = profit - fee;
                    totalAssets += net;
                    strategies[addr].totalHarvested += net;
                    if (fee > 0) {
                        (bool ok,) = feeRecipient.call{value: fee}("");
                        if (!ok) totalAssets += fee;
                    }
                    emit Harvested(addr, profit, fee);
                }
            } catch {}
        }
        lastHarvestTime = block.timestamp;
    }

    function _collectManagementFee() internal {
        uint256 elapsed = block.timestamp - lastHarvestTime;
        if (elapsed == 0 || totalAssets == 0) return;
        uint256 fee = (totalAssets * managementFee * elapsed) / (BPS * 365 days);
        if (fee > 0 && fee < totalAssets) {
            totalAssets -= fee;
            (bool ok,) = feeRecipient.call{value: fee}("");
            if (!ok) totalAssets += fee;
        }
    }

    function _allocateToStrategies(uint256 amount) internal {
        for (uint i = 0; i < strategyList.length; i++) {
            address addr = strategyList[i];
            Strategy storage s = strategies[addr];
            if (!s.active || s.allocation == 0) continue;
            uint256 toInvest = (amount * s.allocation) / BPS;
            if (toInvest > 0 && toInvest <= address(this).balance) {
                try IStrategy(addr).invest{value: toInvest}(toInvest) {
                    s.totalInvested += toInvest;
                } catch {}
            }
        }
    }

    function _withdrawFromStrategies(uint256 needed) internal {
        for (uint i = 0; i < strategyList.length && needed > 0; i++) {
            address addr = strategyList[i];
            if (!strategies[addr].active) continue;
            uint256 available = IStrategy(addr).totalAssets();
            uint256 toWithdraw = available < needed ? available : needed;
            if (toWithdraw > 0) {
                try IStrategy(addr).divest(toWithdraw) returns (uint256 got) {
                    needed = got >= needed ? 0 : needed - got;
                } catch {}
            }
        }
    }

    function addStrategy(address strategy, uint256 allocation) external onlyGovernance {
        require(!strategies[strategy].active, "Already active");
        require(_totalAllocation() + allocation <= BPS, "Over 100%");
        strategies[strategy] = Strategy(true, allocation, 0, 0);
        strategyList.push(strategy);
        emit StrategyAdded(strategy, allocation);
    }

    function removeStrategy(address strategy) external onlyGovernance noReentrant {
        require(strategies[strategy].active, "Not active");
        uint256 assets = IStrategy(strategy).totalAssets();
        if (assets > 0) {
            try IStrategy(strategy).divest(assets) {} catch {}
        }
        strategies[strategy].active = false;
        strategies[strategy].allocation = 0;
        emit StrategyRemoved(strategy);
    }

    function emergencyPause() external onlyGovernance { paused = true; }
    function unpause() external onlyGovernance { paused = false; }

    function setFees(uint256 _perf, uint256 _mgmt) external onlyGovernance {
        require(_perf + _mgmt <= MAX_FEE, "Fee too high");
        performanceFee = _perf;
        managementFee = _mgmt;
        emit FeesUpdated(_perf, _mgmt);
    }

    function _totalAllocation() internal view returns (uint256 total) {
        for (uint i = 0; i < strategyList.length; i++)
            if (strategies[strategyList[i]].active)
                total += strategies[strategyList[i]].allocation;
    }

    function pricePerShare() external view returns (uint256) {
        if (totalShares == 0) return 1e18;
        return (totalAssets * 1e18) / totalShares;
    }

    function getStrategyCount() external view returns (uint256) { return strategyList.length; }
}