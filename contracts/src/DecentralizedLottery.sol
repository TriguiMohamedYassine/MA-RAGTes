// SPDX-License-Identifier: MIT
pragma solidity ^0.8.26;

contract DecentralizedLottery {
    address payable public manager;
    address payable[] public players;
    
    uint256 public constant ENTRY_FEE = 0.01 ether;  // Fixed entry fee
    uint256 public lotteryId;
    
    event PlayerEntered(address player, uint256 lotteryId);
    event WinnerPicked(address winner, uint256 amount, uint256 lotteryId);
    event LotteryReset(uint256 newLotteryId);

    modifier onlyManager() {
        require(msg.sender == manager, "Only manager can call this");
        _;
    }

    constructor() {
        manager = payable(msg.sender);
        lotteryId = 1;
    }

    // Players enter by sending exactly ENTRY_FEE ETH
    receive() external payable {
        enterLottery();
    }

    function enterLottery() public payable {
        require(msg.value == ENTRY_FEE, "Must send exactly 0.01 ETH");
        require(msg.sender != manager, "Manager cannot play");
        require(!isPlayer(msg.sender), "You already entered this round");

        players.push(payable(msg.sender));
        emit PlayerEntered(msg.sender, lotteryId);
    }

    function isPlayer(address _player) internal view returns (bool) {
        for (uint256 i = 0; i < players.length; i++) {
            if (players[i] == _player) {
                return true;
            }
        }
        return false;
    }

    // Pick winner - only manager can call
    function pickWinner() public onlyManager {
        require(players.length >= 3, "At least 3 players required");

        // Pseudo-random winner selection (for testing/demo - not production secure)
        uint256 randomIndex = random() % players.length;
        address payable winner = players[randomIndex];

        uint256 prizeAmount = address(this).balance;

        // Transfer prize to winner
        (bool success, ) = winner.call{value: prizeAmount}("");
        require(success, "Transfer to winner failed");

        emit WinnerPicked(winner, prizeAmount, lotteryId);

        // Reset for next round
        resetLottery();
    }

    // Simple pseudo-random function (uses block properties + players count)
    function random() private view returns (uint256) {
        return uint256(
            keccak256(
                abi.encodePacked(
                    block.prevrandao,
                    block.timestamp,
                    block.number,
                    players.length,
                    lotteryId
                )
            )
        );
    }

    function resetLottery() internal {
        delete players;                    // Clear the array
        lotteryId++;
        emit LotteryReset(lotteryId);
    }

    // View functions
    function getPlayersCount() public view returns (uint256) {
        return players.length;
    }

    function getAllPlayers() public view returns (address payable[] memory) {
        return players;
    }

    function getContractBalance() public view returns (uint256) {
        return address(this).balance;
    }

    // Emergency functions (only manager)
    function emergencyWithdraw() public onlyManager {
        require(address(this).balance > 0, "No funds to withdraw");
        (bool success, ) = manager.call{value: address(this).balance}("");
        require(success, "Emergency withdraw failed");
    }

    function forceReset() public onlyManager {
        resetLottery();
    }
}