// SPDX-License-Identifier: MIT
pragma solidity ^0.8.19;

/**
 * @title AttendanceRecord
 * @dev Enregistre la présence des utilisateurs pour des sessions spécifiques.
 */
contract AttendanceRecord {
    
    struct Session {
        string name;
        uint256 startTime;
        uint256 endTime;
        bool isOpen;
        uint256 totalAttendees;
    }

    address public admin;
    uint256 public sessionCount;
    
    // Mapping: ID de Session => Détails de la session
    mapping(uint256 => Session) public sessions;
    
    // Mapping: ID de Session => (Adresse Participant => Est présent ?)
    mapping(uint256 => mapping(address => bool)) public isPresent;

    event SessionCreated(uint256 indexed sessionId, string name);
    event AttendanceMarked(uint256 indexed sessionId, address indexed attendee, uint256 timestamp);

    modifier onlyAdmin() {
        require(msg.sender == admin, "Attendance: Seul l'admin peut gerer les sessions");
        _;
    }

    constructor() {
        admin = msg.sender;
    }

    /**
     * @dev Crée une session d'émargement.
     * @param _name Nom de l'événement ou du cours.
     * @param _duration Duration en secondes pendant laquelle le pointage est ouvert.
     */
    function createSession(string memory _name, uint256 _duration) public onlyAdmin {
        uint256 sessionId = sessionCount;
        sessions[sessionId] = Session({
            name: _name,
            startTime: block.timestamp,
            endTime: block.timestamp + _duration,
            isOpen: true,
            totalAttendees: 0
        });

        emit SessionCreated(sessionId, _name);
        sessionCount++;
    }

    /**
     * @dev Marque la présence de l'appelant pour une session donnée.
     */
    function markAttendance(uint256 _sessionId) public {
        Session storage session = sessions[_sessionId];
        
        require(session.isOpen, "Attendance: Session fermee");
        require(block.timestamp <= session.endTime, "Attendance: Temps ecoule");
        require(!isPresent[_sessionId][msg.sender], "Attendance: Deja pointe");

        isPresent[_sessionId][msg.sender] = true;
        session.totalAttendees++;

        emit AttendanceMarked(_sessionId, msg.sender, block.timestamp);
    }

    /**
     * @dev Ferme manuellement une session avant la fin du temps imparti.
     */
    function closeSession(uint256 _sessionId) public onlyAdmin {
        sessions[_sessionId].isOpen = false;
    }
}