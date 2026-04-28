// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

/**
 * @title PureERC20
 * @notice Fully self-contained ERC-20 token — zero imports.
 *         Implements EIP-20 with permit (EIP-2612), capped supply,
 *         and role-based minting. All cryptography hand-rolled.
 */
contract PureERC20 {

    // ─── EIP-20 Storage ────────────────────────────────────────────────────
    string  public name;
    string  public symbol;
    uint8   public constant decimals = 18;
    uint256 public totalSupply;
    uint256 public immutable maxSupply;

    mapping(address => uint256)                     public balanceOf;
    mapping(address => mapping(address => uint256)) public allowance;

    // ─── Access control ────────────────────────────────────────────────────
    address public owner;
    mapping(address => bool) public minters;

    // ─── EIP-2612 Permit ───────────────────────────────────────────────────
    bytes32 public immutable DOMAIN_SEPARATOR;
    bytes32 public constant  PERMIT_TYPEHASH =
        keccak256("Permit(address owner,address spender,uint256 value,uint256 nonce,uint256 deadline)");
    mapping(address => uint256) public nonces;

    // ─── Events ────────────────────────────────────────────────────────────
    event Transfer(address indexed from, address indexed to, uint256 value);
    event Approval(address indexed owner, address indexed spender, uint256 value);
    event MinterSet(address indexed account, bool status);
    event OwnershipTransferred(address indexed prev, address indexed next);

    // ─── Errors ────────────────────────────────────────────────────────────
    error Unauthorized();
    error ZeroAddress();
    error InsufficientBalance(uint256 have, uint256 need);
    error InsufficientAllowance(uint256 have, uint256 need);
    error CapExceeded(uint256 cap, uint256 requested);
    error PermitExpired();
    error InvalidSignature();

    // ─── Modifiers ─────────────────────────────────────────────────────────
    modifier onlyOwner() {
        if (msg.sender != owner) revert Unauthorized();
        _;
    }
    modifier onlyMinter() {
        if (!minters[msg.sender] && msg.sender != owner) revert Unauthorized();
        _;
    }

    constructor(
        string memory _name,
        string memory _symbol,
        uint256 _maxSupply,
        uint256 _initialSupply,
        address _owner
    ) {
        if (_owner == address(0)) revert ZeroAddress();
        require(_initialSupply <= _maxSupply, "initial>max");
        name      = _name;
        symbol    = _symbol;
        maxSupply = _maxSupply;
        owner     = _owner;

        DOMAIN_SEPARATOR = keccak256(abi.encode(
            keccak256("EIP712Domain(string name,string version,uint256 chainId,address verifyingContract)"),
            keccak256(bytes(_name)),
            keccak256("1"),
            block.chainid,
            address(this)
        ));

        if (_initialSupply > 0) _mint(_owner, _initialSupply);
    }

    // ─── EIP-20 Core ───────────────────────────────────────────────────────
    function transfer(address to, uint256 amount) external returns (bool) {
        _transfer(msg.sender, to, amount);
        return true;
    }

    function approve(address spender, uint256 amount) external returns (bool) {
        _approve(msg.sender, spender, amount);
        return true;
    }

    function transferFrom(address from, address to, uint256 amount) external returns (bool) {
        uint256 allowed = allowance[from][msg.sender];
        if (allowed != type(uint256).max) {
            if (allowed < amount) revert InsufficientAllowance(allowed, amount);
            unchecked { allowance[from][msg.sender] = allowed - amount; }
        }
        _transfer(from, to, amount);
        return true;
    }

    // ─── EIP-2612 Permit ───────────────────────────────────────────────────
    function permit(
        address _owner,
        address spender,
        uint256 value,
        uint256 deadline,
        uint8 v, bytes32 r, bytes32 s
    ) external {
        if (block.timestamp > deadline) revert PermitExpired();
        bytes32 digest = keccak256(abi.encodePacked(
            "\x19\x01",
            DOMAIN_SEPARATOR,
            keccak256(abi.encode(PERMIT_TYPEHASH, _owner, spender, value, nonces[_owner]++, deadline))
        ));
        address recovered = ecrecover(digest, v, r, s);
        if (recovered == address(0) || recovered != _owner) revert InvalidSignature();
        _approve(_owner, spender, value);
    }

    // ─── Minting / Burning ─────────────────────────────────────────────────
    function mint(address to, uint256 amount) external onlyMinter {
        if (totalSupply + amount > maxSupply)
            revert CapExceeded(maxSupply, totalSupply + amount);
        _mint(to, amount);
    }

    function burn(uint256 amount) external {
        _burn(msg.sender, amount);
    }

    function burnFrom(address from, uint256 amount) external {
        uint256 allowed = allowance[from][msg.sender];
        if (allowed != type(uint256).max) {
            if (allowed < amount) revert InsufficientAllowance(allowed, amount);
            unchecked { allowance[from][msg.sender] = allowed - amount; }
        }
        _burn(from, amount);
    }

    // ─── Admin ─────────────────────────────────────────────────────────────
    function setMinter(address account, bool status) external onlyOwner {
        if (account == address(0)) revert ZeroAddress();
        minters[account] = status;
        emit MinterSet(account, status);
    }

    function transferOwnership(address newOwner) external onlyOwner {
        if (newOwner == address(0)) revert ZeroAddress();
        emit OwnershipTransferred(owner, newOwner);
        owner = newOwner;
    }

    // ─── Internals ─────────────────────────────────────────────────────────
    function _transfer(address from, address to, uint256 amount) internal {
        if (to == address(0)) revert ZeroAddress();
        uint256 bal = balanceOf[from];
        if (bal < amount) revert InsufficientBalance(bal, amount);
        unchecked {
            balanceOf[from] = bal - amount;
            balanceOf[to]  += amount;
        }
        emit Transfer(from, to, amount);
    }

    function _approve(address _owner, address spender, uint256 amount) internal {
        if (spender == address(0)) revert ZeroAddress();
        allowance[_owner][spender] = amount;
        emit Approval(_owner, spender, amount);
    }

    function _mint(address to, uint256 amount) internal {
        if (to == address(0)) revert ZeroAddress();
        unchecked {
            totalSupply    += amount;
            balanceOf[to]  += amount;
        }
        emit Transfer(address(0), to, amount);
    }

    function _burn(address from, uint256 amount) internal {
        uint256 bal = balanceOf[from];
        if (bal < amount) revert InsufficientBalance(bal, amount);
        unchecked {
            balanceOf[from] = bal - amount;
            totalSupply    -= amount;
        }
        emit Transfer(from, address(0), amount);
    }
}
