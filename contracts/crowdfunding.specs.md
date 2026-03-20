1. Gestion des Organisations

"En tant qu'utilisateur, je veux pouvoir créer une organisation en fournissant un nom et un email, afin d'être identifié sur la plateforme."
Critère d'acceptation : L'adresse de l'utilisateur est enregistrée, l'organisation est ajoutée à la liste, et un événement OrganizationCreated est émis.

2. Création de Campagne

"En tant qu'organisateur, je veux créer une campagne de financement avec un titre, une description et un objectif (target), afin de commencer à collecter des fonds."
Critère d'acceptation : La campagne est stockée avec un ID unique, le montant collecté initial est 0, et un événement CampaignCreated est émis.

3. Faire un Don (Logique Critique)

"En tant que donateur, je veux envoyer de l'ETH à une campagne spécifique (donateToCampaign), et le système doit mettre à jour le montant total collecté pour cette campagne."
Critère d'acceptation : Le solde de la campagne augmente du montant envoyé. Le don doit être supérieur à 0.

4. Gestion des Donateurs Uniques

"En tant que système, je veux m'assurer qu'un donateur n'est ajouté à la liste des donors qu'une seule fois, même s'il fait plusieurs dons différents à la même campagne."
Critère d'acceptation : Si l'adresse existe déjà dans le tableau des donateurs pour cet ID, elle ne doit pas être dupliquée.

5. Transparence et Consultation

"En tant qu'utilisateur, je veux pouvoir consulter la liste de toutes les campagnes et voir leurs détails (titre, cible, montant actuel collecté)."