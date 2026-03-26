// SPDX-License-Identifier: MIT
pragma solidity ^0.8.19;

/**
 * @title Whitelist
 * @dev Gère une liste d'adresses autorisées à interagir avec certaines fonctions du contrat.
 */
contract Whitelist {
    address public owner;
    
    // Mapping pour stocker le statut de chaque adresse
    mapping(address => bool) private _whitelist;

    event AddressAdded(address indexed account);
    event AddressRemoved(address indexed account);

    modifier onlyOwner() {
        require(msg.sender == owner, "Whitelist: l'appelant n'est pas le proprietaire");
        _;
    }

    modifier onlyWhitelisted() {
        require(_whitelist[msg.sender], "Whitelist: l'adresse n'est pas autorisee");
        _;
    }

    constructor() {
        owner = msg.sender;
        // Le propriétaire est souvent ajouté par défaut
        _whitelist[msg.sender] = true;
    }

    /**
     * @dev Ajoute une adresse à la liste blanche.
     */
    function addToWhitelist(address _address) public onlyOwner {
        require(!_whitelist[_address], "L'adresse est deja dans la liste.");
        _whitelist[_address] = true;
        emit AddressAdded(_address);
    }

    /**
     * @dev Retire une adresse de la liste blanche.
     */
    function removeFromWhitelist(address _address) public onlyOwner {
        require(_whitelist[_address], "L'adresse n'est pas dans la liste.");
        _whitelist[_address] = false;
        emit AddressRemoved(_address);
    }

    /**
     * @dev Vérifie si une adresse est autorisée.
     */
    function isWhitelisted(address _address) public view returns (bool) {
        return _whitelist[_address];
    }

    /**
     * @dev Exemple de fonction restreinte à la liste blanche.
     */
    function restrictedAction() public onlyWhitelisted {
        // Logique spécifique aux membres autorisés
    }
}