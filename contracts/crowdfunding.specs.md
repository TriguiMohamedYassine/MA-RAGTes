# Crowdfunding - Specifications fonctionnelles

## Portee
Ce document decrit le comportement attendu du contrat `CrowdFunding` dans `crowdfunding.sol`.

## User stories principales

### US1 - Creation d'organisation
En tant qu'utilisateur,
je veux creer une organisation avec mon nom et mon email,
afin d'etre reference dans la plateforme.

Critere d'acceptation:
- `createOrganization(name, email)` enregistre `organizations[msg.sender]`.
- L'adresse est ajoutee dans `organizationList`.
- L'evenement `OrganizationCreated(owner, name, email)` est emis.

### US2 - Consultation des organisations
En tant qu'utilisateur,
je veux lister les organisations existantes,
afin de consulter les profils enregistres.

Critere d'acceptation:
- `getOrganizations()` retourne un tableau de meme taille que `organizationList`.
- `getOrganizationByAddress(owner)` retourne l'organisation liee a `owner`.
- Si l'organisation n'existe pas, `getOrganizationByAddress` revert avec `"Organisation non trouvee"`.

### US3 - Creation de campagne
En tant qu'organisateur,
je veux creer une campagne avec un owner, un titre, une description et une cible,
afin de lancer une collecte de fonds.

Critere d'acceptation:
- `createCampaign(_owner, _title, _description, _target)` cree une entree dans `campaigns[numberOfCampaigns]`.
- `amountCollected` est initialise a `0`.
- L'evenement `CampaignCreated(id, owner, target)` est emis.
- `numberOfCampaigns` est incremente.

### US4 - Consultation des campagnes
En tant qu'utilisateur,
je veux consulter toutes les campagnes,
afin de voir les informations disponibles.

Critere d'acceptation:
- `getCampaigns()` retourne un tableau de taille `numberOfCampaigns`.
- Chaque element contient `owner`, `title`, `description`, `target`, `amountCollected`.

### US5 - Faire un don
En tant que donateur,
je veux envoyer de l'ETH a une campagne,
afin de contribuer financierement.

Critere d'acceptation:
- `donateToCampaign(campaignId)` exige `msg.value > 0`, sinon revert avec `"Donation must be greater than zero"`.
- Le don est ajoute dans `donations[campaignId]`.
- `totalDonationsAmount[campaignId]` est incremente.
- L'evenement `DonationReceived(campaignId, donor, amount)` est emis.

### US6 - Donateurs uniques
En tant que systeme,
je veux garder une liste unique des donateurs par campagne,
afin d'eviter les doublons d'adresses.

Critere d'acceptation:
- Lors d'un second don de la meme adresse sur la meme campagne, `donors[campaignId]` ne doit pas ajouter de doublon.

### US7 - Consultation des dons
En tant qu'utilisateur,
je veux consulter l'historique et les agragats d'une campagne,
afin de verifier la transparence.

Critere d'acceptation:
- `getDonations(campaignId)` retourne la liste detaillee des dons.
- `getDonors(campaignId)` retourne la liste des adresses uniques.
- `getDonationCount(campaignId)` retourne `donations[campaignId].length`.
- `getTotalDonationsAmount(campaignId)` retourne le total cumule.

## Notes importantes
- Le contrat ne transfere pas les fonds vers `campaign.owner` lors d'un don; il ne fait qu'enregistrer les contributions et garde l'ETH dans le contrat.
- Le champ `Campaign.amountCollected` n'est pas mis a jour par `donateToCampaign`; la source du total de dons est `totalDonationsAmount[campaignId]`.

## Cas de tests minimaux recommandes
- Creation et lecture d'une organisation.
- Revert sur `getOrganizationByAddress` pour une adresse non enregistree.
- Creation d'une campagne et verification de `numberOfCampaigns`.
- Don valide et emission de `DonationReceived`.
- Revert si `msg.value == 0`.
- Verification d'absence de doublons dans `getDonors`.