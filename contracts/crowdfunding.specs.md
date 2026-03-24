# CrowdFunding — Spécifications de test

## Contexte
Contrat de crowdfunding décentralisé permettant à des organisations de créer
des campagnes de collecte de fonds et à des donateurs d'y contribuer en ETH.

## Fonctionnalités à tester

### Organisations
- Créer une organisation avec un nom et un email valides
- Vérifier que l'événement OrganizationCreated est émis
- Récupérer la liste de toutes les organisations (getOrganizations)
- Récupérer une organisation par son adresse (getOrganizationByAddress)
- Revert si l'organisation demandée n'existe pas (address(0))

### Campagnes
- Créer une campagne avec owner, title, description et target valides
- Vérifier que l'événement CampaignCreated est émis
- Vérifier que numberOfCampaigns est incrémenté après chaque création
- Récupérer toutes les campagnes (getCampaigns)
- Vérifier que amountCollected démarre à 0

### Donations
- Donner à une campagne existante avec msg.value > 0
- Vérifier que l'événement DonationReceived est émis
- Vérifier que totalDonationsAmount est correctement mis à jour
- Vérifier que getDonations retourne la liste correcte
- Vérifier que getDonors retourne les adresses uniques
- Vérifier qu'un même donateur n'est compté qu'une seule fois dans donors
- getDonationCount retourne le bon nombre de donations
- getTotalDonationsAmount retourne le bon montant cumulé

### Cas limites et reverts
- Revert si msg.value == 0 dans donateToCampaign
- Donations multiples du même donateur : donors ne contient qu'une entrée
- Plusieurs donateurs différents sur la même campagne
- Campagne avec 0 donations : getDonors retourne tableau vide