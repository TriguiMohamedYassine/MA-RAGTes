// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

import "@openzeppelin/contracts/token/ERC20/ERC20.sol";
import "@openzeppelin/contracts/access/Ownable.sol";

contract WasteManagement is ERC20, Ownable {

    // ------------------- Structures -------------------
    struct Bin {
        uint256 id;
        string location;
        uint256 capacity;
        uint256 currentWeight;
        bool exists;
    }

    struct Citizen {
        address addr;
        bool exists;
    }

    struct Shipper {
        address addr;
        bool exists;
    }

    struct Waste {
        uint256 id;
        uint256 binId;
        uint256 weight;
        address owner;
    }

    struct Collection {
        uint256 id;
        uint256[] wasteIds;
        address shipper;
        string status; // "Created" / "Recycled"
    }

    // ------------------- Mappings -------------------
    mapping(uint256 => Bin) public bins;
    mapping(address => Citizen) public citizens;
    mapping(address => Shipper) public shippers;
    mapping(uint256 => Waste) public wastes;
    mapping(uint256 => Collection) public collections;

    uint256 public nextBinId = 1;
    uint256 public nextWasteId = 1;
    uint256 public nextCollectionId = 1;

    address public recycler;

    // ------------------- Constructor -------------------
    // [Fix] Mint vers address(this) pour que le contrat puisse distribuer les récompenses WST
    constructor(uint256 initialSupply)
        ERC20("WasteToken", "WST")
        Ownable(msg.sender)
    {
        _mint(address(this), initialSupply);
    }

    // ------------------- Bin Management -------------------
    function createBin(string memory location, uint256 capacity) external onlyOwner {
        require(capacity > 0, "Invalid capacity");
        bins[nextBinId] = Bin(nextBinId, location, capacity, 0, true);
        nextBinId++;
    }

    function modifyBin(uint256 binId, string memory location, uint256 capacity) external onlyOwner {
        require(bins[binId].exists, "Bin does not exist");
        require(capacity > 0, "Invalid capacity");
        bins[binId].location = location;
        bins[binId].capacity = capacity;
    }

    function deleteBin(uint256 binId) external onlyOwner {
        require(bins[binId].exists, "Bin does not exist");
        require(bins[binId].currentWeight == 0, "Bin not empty");
        delete bins[binId];
    }

    // ------------------- Citizen Management -------------------
    function createCitizen(address _addr) external onlyOwner {
        require(!citizens[_addr].exists, "Citizen exists");
        citizens[_addr] = Citizen(_addr, true);
    }

    function deleteCitizen(address _addr) external onlyOwner {
        require(citizens[_addr].exists, "Citizen not found");
        delete citizens[_addr];
    }

    // ------------------- Shipper Management -------------------
    function createShipper(address _addr) external onlyOwner {
        require(!shippers[_addr].exists, "Shipper exists");
        shippers[_addr] = Shipper(_addr, true);
    }

    function deleteShipper(address _addr) external onlyOwner {
        require(shippers[_addr].exists, "Shipper not found");
        delete shippers[_addr];
    }

    // ------------------- Waste Management -------------------
    function createWaste(uint256 binId, uint256 weight) external {
        require(citizens[msg.sender].exists, "Not citizen");
        require(bins[binId].exists, "Bin not found");
        require(bins[binId].currentWeight + weight <= bins[binId].capacity, "Capacity exceeded");

        wastes[nextWasteId] = Waste(nextWasteId, binId, weight, msg.sender);
        bins[binId].currentWeight += weight;
        nextWasteId++;
    }

    // ------------------- Collection Management -------------------
    function setRecycler(address _recycler) external onlyOwner {
        require(_recycler != address(0), "Invalid recycler address");
        recycler = _recycler;
    }

    function createCollection(uint256[] memory wasteIds, address shipper, uint256 binId) external onlyOwner {
        require(shippers[shipper].exists, "Invalid shipper");
        require(bins[binId].exists, "Invalid bin");

        collections[nextCollectionId] = Collection(nextCollectionId, wasteIds, shipper, "Created");
        nextCollectionId++;
    }

    // [Fix 1] Décrémente currentWeight pour chaque déchet → permet deleteBin après recyclage
    // [Fix 2] Transfère des tokens WST au propriétaire de chaque déchet
    function recycleCollection(uint256 collectionId) external {
        require(msg.sender == recycler, "Not recycler");
        require(collections[collectionId].id != 0, "Collection not found");

        collections[collectionId].status = "Recycled";

        uint256[] memory wasteIds = collections[collectionId].wasteIds;
        for (uint256 i = 0; i < wasteIds.length; i++) {
            uint256 wid = wasteIds[i];
            Waste memory w = wastes[wid];

            // [Fix 1] Libère le poids dans le bin
            bins[w.binId].currentWeight -= w.weight;

            // [Fix 2] Récompense le citoyen : 1 WST (18 décimales) par unité de poids
            uint256 reward = w.weight * (10 ** decimals());
            if (balanceOf(address(this)) >= reward) {
                _transfer(address(this), w.owner, reward);
            }
        }
    }
}
