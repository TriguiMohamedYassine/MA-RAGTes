// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

contract DAOGovernor {
    uint256 public constant VOTING_DELAY = 1 days;
    uint256 public constant VOTING_PERIOD = 5 days;
    uint256 public constant TIMELOCK_DELAY = 2 days;
    uint256 public constant QUORUM_BPS = 400; // 4% of total supply
    uint256 public constant BPS = 10000;

    enum ProposalState { Pending, Active, Defeated, Succeeded, Queued, Executed, Vetoed, Expired }
    enum VoteChoice { Against, For, Abstain }

    struct Proposal {
        uint256 id;
        address proposer;
        address[] targets;
        uint256[] values;
        bytes[] calldatas;
        string description;
        uint256 snapshotTime;
        uint256 voteStart;
        uint256 voteEnd;
        uint256 executionTime;
        uint256 forVotes;
        uint256 againstVotes;
        uint256 abstainVotes;
        bool executed;
        bool vetoed;
    }

    address public guardian;
    address public govToken;
    uint256 public proposalCount;
    bool private _locked;

    mapping(uint256 => Proposal) public proposals;
    mapping(uint256 => mapping(address => bool)) public hasVoted;
    mapping(uint256 => mapping(address => VoteChoice)) public votes;
    mapping(address => address) public delegates;
    mapping(address => uint256) public votingPower;
    mapping(address => mapping(uint256 => uint256)) public powerSnapshots; // addr => time => power
    uint256 public totalVotingPower;

    event ProposalCreated(uint256 indexed id, address proposer, string description);
    event VoteCast(uint256 indexed proposalId, address voter, VoteChoice choice, uint256 weight);
    event ProposalQueued(uint256 indexed id, uint256 executionTime);
    event ProposalExecuted(uint256 indexed id);
    event ProposalVetoed(uint256 indexed id);
    event DelegateChanged(address indexed delegator, address indexed fromDelegate, address indexed toDelegate);
    event PowerGranted(address indexed account, uint256 amount);

    modifier noReentrant() { require(!_locked, "Reentrant"); _locked = true; _; _locked = false; }
    modifier onlyGuardian() { require(msg.sender == guardian, "Not guardian"); _; }

    constructor(address _guardian) {
        guardian = _guardian;
    }

    function grantVotingPower(address account, uint256 amount) external onlyGuardian {
        votingPower[account] += amount;
        totalVotingPower += amount;
        _takeSnapshot(account);
        emit PowerGranted(account, amount);
    }

    function delegate(address to) external {
        address from = delegates[msg.sender];
        delegates[msg.sender] = to;
        if (from != address(0) && from != msg.sender) {
            votingPower[from] -= votingPower[msg.sender];
            _takeSnapshot(from);
        }
        if (to != address(0) && to != msg.sender) {
            votingPower[to] += votingPower[msg.sender];
            _takeSnapshot(to);
        }
        emit DelegateChanged(msg.sender, from, to);
    }

    function _takeSnapshot(address account) internal {
        powerSnapshots[account][block.timestamp] = votingPower[account];
    }

    function _getSnapshotPower(address account, uint256 snapshotTime) internal view returns (uint256) {
        if (powerSnapshots[account][snapshotTime] > 0) return powerSnapshots[account][snapshotTime];
        return votingPower[account];
    }

    function propose(
        address[] calldata targets,
        uint256[] calldata values,
        bytes[] calldata calldatas,
        string calldata description
    ) external returns (uint256) {
        require(targets.length > 0 && targets.length == values.length && targets.length == calldatas.length, "Invalid");
        require(votingPower[msg.sender] >= _quorumVotes() / 10, "Insufficient power to propose");
        uint256 id = ++proposalCount;
        uint256 snap = block.timestamp;
        proposals[id] = Proposal({
            id: id, proposer: msg.sender,
            targets: targets, values: values, calldatas: calldatas,
            description: description, snapshotTime: snap,
            voteStart: snap + VOTING_DELAY,
            voteEnd: snap + VOTING_DELAY + VOTING_PERIOD,
            executionTime: 0,
            forVotes: 0, againstVotes: 0, abstainVotes: 0,
            executed: false, vetoed: false
        });
        _takeSnapshot(msg.sender);
        emit ProposalCreated(id, msg.sender, description);
        return id;
    }

    function castVote(uint256 proposalId, VoteChoice choice) external {
        Proposal storage p = proposals[proposalId];
        require(state(proposalId) == ProposalState.Active, "Not active");
        require(!hasVoted[proposalId][msg.sender], "Already voted");
        uint256 weight = _getSnapshotPower(msg.sender, p.snapshotTime);
        require(weight > 0, "No voting power");
        hasVoted[proposalId][msg.sender] = true;
        votes[proposalId][msg.sender] = choice;
        if (choice == VoteChoice.For) p.forVotes += weight;
        else if (choice == VoteChoice.Against) p.againstVotes += weight;
        else p.abstainVotes += weight;
        emit VoteCast(proposalId, msg.sender, choice, weight);
    }

    function queue(uint256 proposalId) external {
        require(state(proposalId) == ProposalState.Succeeded, "Not succeeded");
        Proposal storage p = proposals[proposalId];
        p.executionTime = block.timestamp + TIMELOCK_DELAY;
        emit ProposalQueued(proposalId, p.executionTime);
    }

    function execute(uint256 proposalId) external payable noReentrant {
        require(state(proposalId) == ProposalState.Queued, "Not queued");
        Proposal storage p = proposals[proposalId];
        require(block.timestamp >= p.executionTime, "Timelock not elapsed");
        require(block.timestamp < p.executionTime + 7 days, "Proposal expired");
        p.executed = true;
        for (uint256 i = 0; i < p.targets.length; i++) {
            (bool ok,) = p.targets[i].call{value: p.values[i]}(p.calldatas[i]);
            require(ok, "Call failed");
        }
        emit ProposalExecuted(proposalId);
    }

    function veto(uint256 proposalId) external onlyGuardian {
        ProposalState s = state(proposalId);
        require(
            s == ProposalState.Pending ||
            s == ProposalState.Active ||
            s == ProposalState.Succeeded ||
            s == ProposalState.Queued,
            "Cannot veto"
        );
        proposals[proposalId].vetoed = true;
        emit ProposalVetoed(proposalId);
    }

    function state(uint256 proposalId) public view returns (ProposalState) {
        Proposal storage p = proposals[proposalId];
        if (p.vetoed) return ProposalState.Vetoed;
        if (p.executed) return ProposalState.Executed;
        if (block.timestamp < p.voteStart) return ProposalState.Pending;
        if (block.timestamp <= p.voteEnd) return ProposalState.Active;
        if (p.forVotes <= p.againstVotes || p.forVotes < _quorumVotes()) return ProposalState.Defeated;
        if (p.executionTime == 0) return ProposalState.Succeeded;
        if (block.timestamp < p.executionTime) return ProposalState.Queued;
        if (block.timestamp >= p.executionTime + 7 days) return ProposalState.Expired;
        return ProposalState.Queued;
    }

    function _quorumVotes() internal view returns (uint256) {
        return (totalVotingPower * QUORUM_BPS) / BPS;
    }

    function quorumVotes() external view returns (uint256) { return _quorumVotes(); }
    function getProposalTargets(uint256 id) external view returns (address[] memory) { return proposals[id].targets; }
    function getProposalCalldatas(uint256 id) external view returns (bytes[] memory) { return proposals[id].calldatas; }
    receive() external payable {}
}