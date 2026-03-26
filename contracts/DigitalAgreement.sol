// SPDX-License-Identifier: MIT
pragma solidity ^0.8.19;

/**
 * @title DigitalAgreement
 * @dev Permet à deux parties de signer numériquement un accord basé sur un hachage de document.
 */
contract DigitalAgreement {
    address public partyA;
    address public partyB;
    string public documentHash; // Hachage du contrat (ex: CID IPFS)
    
    bool public signedByA;
    bool public signedByB;
    uint256 public signatureDate;

    event AgreementSigned(address indexed signer, uint256 timestamp);
    event AgreementFullyExecuted(uint256 timestamp);

    modifier onlyParties() {
        require(msg.sender == partyA || msg.sender == partyB, "Agreement: Vous n'etes pas partie au contrat");
        _;
    }

    /**
     * @dev Initialise l'accord avec les deux signataires et le hachage du document.
     */
    constructor(address _partyB, string memory _documentHash) {
        partyA = msg.sender;
        partyB = _partyB;
        documentHash = _documentHash;
        signedByA = false;
        signedByB = false;
    }

    /**
     * @dev Signe l'accord pour la partie appelante.
     */
    function sign() external onlyParties {
        if (msg.sender == partyA) {
            require(!signedByA, "Agreement: Deja signe par Partie A");
            signedByA = true;
        } else {
            require(!signedByB, "Agreement: Deja signe par Partie B");
            signedByB = true;
        }

        emit AgreementSigned(msg.sender, block.timestamp);

        // Vérifier si les deux ont signé
        if (signedByA && signedByB) {
            signatureDate = block.timestamp;
            emit AgreementFullyExecuted(signatureDate);
        }
    }

    /**
     * @dev Vérifie si l'accord est pleinement valide.
     */
    function isEffectivelySigned() public view returns (bool) {
        return (signedByA && signedByB);
    }
}