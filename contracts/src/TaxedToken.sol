// SPDX-License-Identifier: MIT
pragma solidity ^0.8.26;

contract TaxedToken {
    string public name = "Test Complex Token";
    string public symbol = "TCT";
    uint8 public decimals = 18;
    uint256 public totalSupply;

    address public owner;

    uint256 public taxRate = 5; // 5% tax on transfers
    uint256 public maxTxAmount = 10000 * 10 ** 18; // Max 10,000 tokens per tx

    mapping(address => uint256) public balanceOf;
    mapping(address => mapping(address => uint256)) public allowance;
    mapping(address => bool) public isBlacklisted;

    event Transfer(address indexed from, address indexed to, uint256 value);
    event Approval(address indexed owner, address indexed spender, uint256 value);
    event TaxCollected(address from, uint256 taxAmount);
    event Blacklisted(address account);
    event Unblacklisted(address account);

    modifier onlyOwner() {
        require(msg.sender == owner, "Only owner can call this");
        _;
    }

    constructor() {
        owner = msg.sender;
        uint256 initialSupply = 1000000 * 10 ** 18; // 1 million tokens
        balanceOf[msg.sender] = initialSupply;
        totalSupply = initialSupply;
        emit Transfer(address(0), msg.sender, initialSupply);
    }

    function transfer(address to, uint256 amount) public returns (bool) {
        require(to != address(0), "Transfer to zero address");
        require(!isBlacklisted[msg.sender], "Sender is blacklisted");
        require(!isBlacklisted[to], "Recipient is blacklisted");
        require(amount <= maxTxAmount, "Exceeds max transaction amount");

        uint256 taxAmount = (amount * taxRate) / 100;
        uint256 sendAmount = amount - taxAmount;

        require(balanceOf[msg.sender] >= amount, "Insufficient balance");

        balanceOf[msg.sender] -= amount;
        balanceOf[to] += sendAmount;

        if (taxAmount > 0) {
            // Tax stays in contract (you can change this to burn or send to marketing)
            balanceOf[address(this)] += taxAmount;
            emit TaxCollected(msg.sender, taxAmount);
        }

        emit Transfer(msg.sender, to, sendAmount);
        return true;
    }

    function approve(address spender, uint256 amount) public returns (bool) {
        require(spender != address(0), "Approve to zero address");
        allowance[msg.sender][spender] = amount;
        emit Approval(msg.sender, spender, amount);
        return true;
    }

    function transferFrom(address from, address to, uint256 amount) public returns (bool) {
        require(to != address(0), "Transfer to zero address");
        require(!isBlacklisted[from], "From is blacklisted");
        require(!isBlacklisted[to], "To is blacklisted");
        require(amount <= maxTxAmount, "Exceeds max tx amount");

        require(allowance[from][msg.sender] >= amount, "Insufficient allowance");
        require(balanceOf[from] >= amount, "Insufficient balance");

        uint256 taxAmount = (amount * taxRate) / 100;
        uint256 sendAmount = amount - taxAmount;

        balanceOf[from] -= amount;
        balanceOf[to] += sendAmount;
        allowance[from][msg.sender] -= amount;

        if (taxAmount > 0) {
            balanceOf[address(this)] += taxAmount;
            emit TaxCollected(from, taxAmount);
        }

        emit Transfer(from, to, sendAmount);
        return true;
    }

    function mint(address to, uint256 amount) public onlyOwner {
        require(to != address(0), "Mint to zero address");
        require(!isBlacklisted[to], "Recipient is blacklisted");

        balanceOf[to] += amount;
        totalSupply += amount;
        emit Transfer(address(0), to, amount);
    }

    function burn(uint256 amount) public {
        require(balanceOf[msg.sender] >= amount, "Insufficient balance");

        balanceOf[msg.sender] -= amount;
        totalSupply -= amount;
        emit Transfer(msg.sender, address(0), amount);
    }

    function blacklist(address account) public onlyOwner {
        isBlacklisted[account] = true;
        emit Blacklisted(account);
    }

    function unblacklist(address account) public onlyOwner {
        isBlacklisted[account] = false;
        emit Unblacklisted(account);
    }

    function setTaxRate(uint256 newTaxRate) public onlyOwner {
        require(newTaxRate <= 20, "Tax rate too high");
        taxRate = newTaxRate;
    }

    function setMaxTxAmount(uint256 newMaxTx) public onlyOwner {
        maxTxAmount = newMaxTx;
    }

    // Withdraw tax collected in contract
    function withdrawTax() public onlyOwner {
        uint256 contractBalance = balanceOf[address(this)];
        require(contractBalance > 0, "No tax to withdraw");
        balanceOf[address(this)] = 0;
        balanceOf[owner] += contractBalance;
        emit Transfer(address(this), owner, contractBalance);
    }

    // View functions
    function getTaxAmount(uint256 amount) public view returns (uint256) {
        return (amount * taxRate) / 100;
    }
}