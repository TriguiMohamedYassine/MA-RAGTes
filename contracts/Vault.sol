// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

contract Vault {
    address public owner;
    bool public paused;

    mapping(address => uint256) public balances;

    // Custom errors
    error NotOwner();
    error Paused();
    error InsufficientBalance();

    // Events
    event Deposit(address indexed user, uint256 amount);
    event Withdraw(address indexed user, uint256 amount);
    event PausedStateChanged(bool newState);

    constructor() {
        owner = msg.sender;
    }

    modifier onlyOwner() {
        if (msg.sender != owner) revert NotOwner();
        _;
    }

    modifier notPaused() {
        if (paused) revert Paused();
        _;
    }

    // Deposit ETH into contract
    function deposit() external payable notPaused {
        balances[msg.sender] += msg.value;
        emit Deposit(msg.sender, msg.value);
    }

    // User withdraws their own ETH
    function withdraw(uint256 amount) external notPaused {
        if (balances[msg.sender] < amount) revert InsufficientBalance();
        balances[msg.sender] -= amount;
        payable(msg.sender).transfer(amount);
        emit Withdraw(msg.sender, amount);
    }

    // Owner can withdraw for a user
    function ownerWithdraw(address user, uint256 amount) external onlyOwner {
        if (balances[user] < amount) revert InsufficientBalance();
        balances[user] -= amount;
        payable(owner).transfer(amount);
        emit Withdraw(user, amount);
    }

    // Owner controls pause system
    function setPaused(bool _paused) external onlyOwner {
        paused = _paused;
        emit PausedStateChanged(_paused);
    }
}
