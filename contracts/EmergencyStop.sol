// SPDX-License-Identifier: MIT
pragma solidity ^0.8.19;

/**
 * @title EmergencyStop
 * @dev Permet d'arrêter les fonctions du contrat en cas d'urgence.
 */
contract EmergencyStop {
    address public admin;
    bool public paused;

    event Paused(address account);
    event Unpaused(address account);

    modifier onlyAdmin() {
        require(msg.sender == admin, "EmergencyStop: reserve a l'administrateur");
        _;
    }

    /**
     * @dev Modificateur pour les fonctions qui ne doivent fonctionner que si le contrat n'est pas en pause.
     */
    modifier whenNotPaused() {
        require(!paused, "EmergencyStop: le contrat est en pause");
        _;
    }

    /**
     * @dev Modificateur pour les fonctions qui ne doivent fonctionner que si le contrat EST en pause.
     */
    modifier whenPaused() {
        require(paused, "EmergencyStop: le contrat n'est pas en pause");
        _;
    }

    constructor() {
        admin = msg.sender;
        paused = false;
    }

    /**
     * @dev Active la pause. Seul l'admin peut le faire.
     */
    function pause() public onlyAdmin whenNotPaused {
        paused = true;
        emit Paused(msg.sender);
    }

    /**
     * @dev Désactive la pause. Seul l'admin peut le faire.
     */
    function unpause() public onlyAdmin whenPaused {
        paused = false;
        emit Unpaused(msg.sender);
    }

    /**
     * @dev Exemple de fonction sensible (comme un transfert) protégée par la pause.
     */
    function sensitiveAction() public whenNotPaused {
        // Logique métier qui s'arrête si paused est vrai
    }
}