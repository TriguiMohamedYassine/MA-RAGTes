// SPDX-License-Identifier: MIT
pragma solidity ^0.8.19;

/**
 * @title CandidateElection
 * @dev Permet de voter pour des candidats spécifiques dans une liste prédéfinie.
 */
contract CandidateElection {
    
    struct Candidate {
        uint256 id;
        string name;
        uint256 voteCount;
    }

    address public admin;
    Candidate[] public candidates;
    mapping(address => bool) public hasVoted;

    event VoteCast(address indexed voter, uint256 indexed candidateId);
    event ElectionResults(uint256 candidateId, string name, uint256 totalVotes);

    modifier onlyAdmin() {
        require(msg.sender == admin, "Election: Seul l'admin peut effectuer cette action");
        _;
    }

    /**
     * @dev Initialise l'élection avec une liste de noms de candidats.
     */
    constructor(string[] memory _candidateNames) {
        admin = msg.sender;
        for (uint256 i = 0; i < _candidateNames.length; i++) {
            candidates.push(Candidate({
                id: i,
                name: _candidateNames[i],
                voteCount: 0
            }));
        }
    }

    /**
     * @dev Enregistre un vote pour un candidat via son ID.
     */
    function vote(uint256 _candidateId) public {
        require(!hasVoted[msg.sender], "Election: Vous avez deja vote");
        require(_candidateId < candidates.length, "Election: Candidat invalide");

        candidates[_candidateId].voteCount++;
        hasVoted[msg.sender] = true;

        emit VoteCast(msg.sender, _candidateId);
    }

    /**
     * @dev Retourne le nombre total de candidats.
     */
    function getCandidatesCount() public view returns (uint256) {
        return candidates.length;
    }

    /**
     * @dev Affiche les détails d'un candidat.
     */
    function getCandidate(uint256 _candidateId) public view returns (string memory name, uint256 voteCount) {
        require(_candidateId < candidates.length, "Election: Candidat inexistant");
        Candidate storage c = candidates[_candidateId];
        return (c.name, c.voteCount);
    }
}