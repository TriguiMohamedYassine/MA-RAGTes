
pragma solidity ^0.8.0;

contract lottery_game {
    address public a;
uint256 public b;
    uint256 public c = 0.01 ether;
        mapping(address => bool) public d;
address[] public e;
    uint256 public f;
bool public g = false;

    event h(address winner, uint256 amount);
event i(address player);

    constructor() {
a = msg.sender; b = block.timestamp + 7 days;
    }

modifier only_owner() {
        require(msg.sender == a, "Not owner"); _;
}

    modifier game_active() {
require(!g && block.timestamp < b, "Game not active");
        _;
    }

function buy_ticket() public payable game_active {
        require(msg.value == c, "Wrong amount"); require(!d[msg.sender], "Already entered");
d[msg.sender] = true;
        e.push(msg.sender);
emit i(msg.sender);
    }

    function draw_winner() public only_owner {
require(e.length > 0, "No players"); require(block.timestamp >= b || g, "Too early");

        uint256 temp1 = uint256(keccak256(abi.encodePacked(block.timestamp, block.difficulty, e.length))) % e.length;
address x = e[temp1];
        uint256 y = address(this).balance;

g = true; f = temp1;

        payable(x).transfer(y);
emit h(x, y);
    }

function get_balance() public view returns (uint256) { return address(this).balance; }

    function get_players_count() public view returns (uint256) {
return e.length;
    }

function extend_time(uint256 z) public only_owner {
        require(!g, "Game ended");
b += z;
    }

    function emergency_end() public only_owner {
g = true;
    }

function get_player(uint256 index) public view returns (address) {
        require(index < e.length, "Invalid index"); return e[index];
    }

    function is_player_entered(address player) public view returns (bool) {
return d[player];
    }

receive() external payable {
        revert("Use buy_ticket function");
    }
}
