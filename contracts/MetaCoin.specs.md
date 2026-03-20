🪙 User Stories Principales (Core Features)
US1 : Initialisation de la supply (Déploiement)

En tant que déployeur du contrat (créateur),

Je souhaite recevoir un solde initial de 10 000 MetaCoins lors de la création du contrat,

Afin de posséder la réserve initiale de tokens pour la distribuer aux futurs utilisateurs.

US2 : Transfert de tokens

En tant qu' utilisateur possédant des MetaCoins,

Je souhaite pouvoir envoyer un montant précis de mes pièces à une autre adresse (sendCoin),

Afin de transférer de la valeur ou payer un autre utilisateur.

US3 : Vérification du solde (Consultation)

En tant que n'importe quel utilisateur ou application tierce,

Je souhaite pouvoir consulter le solde exact de n'importe quelle adresse (getBalance),

Afin de savoir combien de MetaCoins je possède ou combien en possède un autre utilisateur.

🛡️ User Stories de Sécurité et d'Intégration
US4 : Protection contre les doubles dépenses / soldes négatifs

En tant que système (règle métier),

Je souhaite qu'un transfert soit rejeté avec le message "Solde insuffisant" si l'expéditeur essaie d'envoyer plus de MetaCoins qu'il n'en possède,

Afin de garantir l'intégrité de l'économie du token et empêcher la création de monnaie à partir de rien.

US5 : Traçabilité des transactions (Événements)

En tant que développeur front-end ou observateur de la blockchain,

Je souhaite qu'un événement (Transfer) soit émis à chaque fois qu'un transfert réussit (contenant l'expéditeur, le destinataire et le montant),

Afin de pouvoir écouter le réseau et mettre à jour l'interface utilisateur (UI) ou l'historique des transactions en temps réel.

US6 : Compatibilité d'interface (Legacy/Alias)

En tant que service tiers utilisant le contrat,

Je souhaite pouvoir appeler la fonction getBalanceInEth pour obtenir mon solde exact,

Afin de maintenir la compatibilité avec d'anciens systèmes ou interfaces qui s'attendent à l'existence de cette fonction (même si la logique de conversion *2 a été retirée).