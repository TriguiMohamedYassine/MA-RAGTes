// SPDX-License-Identifier: MIT
pragma solidity ^0.8.19;

contract CrowdFunding {

 struct Organization {
 address owner;
 string name;
 string email;
 }
 
 struct Campaign {
 address owner;
 string title;
 string description;
 uint256 target;
 uint256 amountCollected;
 }
 
 struct Donation {
 address donor;
 uint256 amount;
 }

 mapping(address => Organization) public organizations;
 address[] public organizationList;

 mapping(uint256 => Donation[]) private donations; 
 mapping(uint256 => address[]) private donors; 
 mapping(uint256 => uint256) private totalDonationsAmount; 
 mapping(uint256 => Campaign) public campaigns;
 uint256 public numberOfCampaigns = 0;

 event OrganizationCreated(address indexed owner, string name, string email);
 event CampaignCreated(uint256 id, address owner, uint256 target);
 event DonationReceived(uint256 campaignId, address donor, uint256 amount);

 constructor() {}

 function createOrganization(string memory name, string memory email) public {
 
 organizations[msg.sender] = Organization(msg.sender, name, email);
 organizationList.push(msg.sender);

 emit OrganizationCreated(msg.sender, name, email);
 }

 function getOrganizations() public view returns (Organization[] memory) {
 Organization[] memory allOrganizations = new Organization[](organizationList.length);

 for (uint256 i = 0; i < organizationList.length; i++) {
 address orgAddress = organizationList[i];
 allOrganizations[i] = organizations[orgAddress];
 }

 return allOrganizations;
 }

 function getOrganizationByAddress(address owner) public view returns (Organization memory) {
 require(organizations[owner].owner != address(0), "Organisation non trouvee");
 return organizations[owner];
 }

 // Create a new campaign
 function createCampaign(
 address _owner,
 string memory _title,
 string memory _description,
 uint256 _target
 
 ) public returns (uint256) {
 Campaign storage campaign = campaigns[numberOfCampaigns];
 campaign.owner = _owner;
 campaign.title = _title;
 campaign.description = _description;
 campaign.target = _target;
 campaign.amountCollected = 0;
 
 emit CampaignCreated(numberOfCampaigns, _owner, _target);
 numberOfCampaigns++;
 return numberOfCampaigns - 1;
 }


 // Get all campaigns
 function getCampaigns() public view returns (Campaign[] memory) {
 Campaign[] memory allCampaigns = new Campaign[](numberOfCampaigns);

 for (uint256 i = 0; i < numberOfCampaigns; i++) {
 Campaign storage item = campaigns[i];
 allCampaigns[i] = item;
 }
 return allCampaigns;
 }

 function donateToCampaign(uint256 _campaignId) public payable {
 require(msg.value > 0, "Donation must be greater than zero");

 donations[_campaignId].push(Donation(msg.sender, msg.value));
 totalDonationsAmount[_campaignId] += msg.value;

 // Vérifier si le donateur a déjà donné
 bool alreadyDonated = false;
 for (uint256 i = 0; i < donors[_campaignId].length; i++) {
 if (donors[_campaignId][i] == msg.sender) {
 alreadyDonated = true;
 break;
 }
 }

 // Ajouter uniquement si ce n'est pas un donateur existant
 if (!alreadyDonated) {
 donors[_campaignId].push(msg.sender);
 }

 emit DonationReceived(_campaignId, msg.sender, msg.value);
 }

 function getDonations(uint256 _campaignId) public view returns (Donation[] memory) {
 return donations[_campaignId];
 }

 function getDonors(uint256 _campaignId) public view returns (address[] memory) {
 return donors[_campaignId];
 }

 function getDonationCount(uint256 _campaignId) public view returns (uint256) {
 return donations[_campaignId].length;
 }

 function getTotalDonationsAmount(uint256 _campaignId) public view returns (uint256) {
 return totalDonationsAmount[_campaignId];
 } 
}