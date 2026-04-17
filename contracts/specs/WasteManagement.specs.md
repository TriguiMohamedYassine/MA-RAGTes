# WasteManagement - Specifications fonctionnelles

## Portee
Ce document couvre le contrat `WasteManagement` dans `WasteManagement.sol`.

## User stories principales

### US1 - Deploiement et token ERC20
En tant que deployeur,
je veux initialiser le token `WST` avec une supply initiale,
afin d'alimenter le systeme de recompense.

Critere d'acceptation:
- Le contrat herite de `ERC20` et `Ownable`.
- Le constructeur mint `initialSupply` vers `msg.sender`.
- Le deploiement definit obligatoirement `recycler` via `setRecycler()` avant tout appel a `recycleCollection()` (sinon `recycler == address(0)` et la fonction est definitivement bloquee).

---

### US2 - Gestion des bins (owner)
En tant que owner,
je veux creer, modifier et supprimer des bins,
afin de gerer les points de collecte.

Critere d'acceptation:
- `createBin(location, capacity)` exige `capacity > 0`.
- `modifyBin(binId, location, capacity)` exige que le bin existe et `capacity > 0`.
- `deleteBin(binId)` exige que le bin existe et que `currentWeight == 0`.
- **[Fix bug]** `currentWeight` doit etre decremente lors du recyclage (voir US7) ; sans cela `deleteBin` revert toujours meme apres collecte complete.

---

### US3 - Gestion des citizens (owner)
En tant que owner,
je veux enregistrer ou retirer des citoyens,
afin de controler qui peut deposer des dechets.

Critere d'acceptation:
- `createCitizen(addr)` exige que le citoyen n'existe pas deja.
- `deleteCitizen(addr)` exige que le citoyen existe.
- **[Limitation connue]** Supprimer un citoyen ayant des dechets existants laisse des objets `Waste` orphelins. A prendre en compte lors d'une evolution future.

---

### US4 - Gestion des shippers (owner)
En tant que owner,
je veux enregistrer ou retirer des transporteurs,
afin de controler les acteurs logistiques.

Critere d'acceptation:
- `createShipper(addr)` exige que le shipper n'existe pas deja.
- `deleteShipper(addr)` exige que le shipper existe.

---

### US5 - Depot de dechets par citoyen
En tant que citoyen,
je veux declarer un dechet dans un bin,
afin d'alimenter le flux de collecte.

Critere d'acceptation:
- `createWaste(binId, weight)` exige que `msg.sender` soit un citizen.
- Le bin cible doit exister.
- `currentWeight + weight` ne doit pas depasser `capacity`.
- Un nouvel objet `Waste` est cree avec `owner = msg.sender`.
- `bins[binId].currentWeight` est incremente de `weight`.

---

### US6 - Gestion des collections (owner)
En tant que owner,
je veux definir l'adresse du recycler et creer des collections,
afin d'organiser le traitement.

Critere d'acceptation:
- `setRecycler(recycler)` est reserve au owner.
- `recycler` ne doit pas etre `address(0)`.
- `createCollection(wasteIds, shipper, binId)` exige shipper valide et bin valide.
- **[Fix bug]** Chaque `wasteId` fourni doit exister (`wastes[id].id != 0`).
- **[Fix bug]** Chaque `wasteId` doit appartenir au `binId` specifie pour garantir la coherence entre la poubelle et les dechets collectes (le parametre `binId` etait verifie mais non utilise).
- **[Fix bug]** Un `wasteId` deja present dans une collection existante ne peut pas etre reutilise (risque de double collecte).
- Une collection est creee avec statut initial `"Created"`.

---

### US7 - Validation de recyclage et recompense
En tant que recycler,
je veux marquer une collection comme recyclee et recompenser les citoyens,
afin de finaliser le traitement et d'incentiver les depots.

Critere d'acceptation:
- `recycleCollection(collectionId)` exige `msg.sender == recycler`.
- La collection doit exister (`id != 0`).
- Le statut devient `"Recycled"`.
- **[Fix bug]** Pour chaque `wasteId` de la collection, `bins[binId].currentWeight` doit etre decremente du poids correspondant, afin de liberer la capacite du bin.
- **[Fix bug]** Pour chaque `wasteId` de la collection, le token `WST` doit etre transfere vers `wastes[wasteId].owner` en recompense (le token ERC20 etait presente mais non distribue).

---

## Notes importantes
- Le contrat ne definit pas d'evenements applicatifs pour bins/collections/dechets.
- Les specs et tests ne doivent donc pas attendre `BinCreated` ou `CollectionCreated`.
- `recycler` doit imperativement etre initialise avant le premier appel a `recycleCollection()`.

---

## Cas de tests minimaux recommandes

Tests existants :
- Verification du mint initial ERC20 au deploiement.
- Verification des restrictions `onlyOwner` sur fonctions d'administration.
- Reverts sur capacite invalide, bin inexistant ou bin non vide a la suppression.
- Reverts sur creation de citizen/shipper deja existant et suppression inexistante.
- Reverts sur depot par non-citoyen, bin invalide, capacite depassee.
- Reverts sur `recycleCollection` pour non-recycler et collection inexistante.

Tests supplementaires (bugs corriges) :
- Verification que `currentWeight` est bien decremente apres `recycleCollection()`.
- Verification que `deleteBin` reussit apres que tous les dechets du bin ont ete recycles.
- Verification que `createCollection` revert si un `wasteId` n'existe pas.
- Verification que `createCollection` revert si un `wasteId` appartient a un bin different de `binId`.
- Verification que le meme `wasteId` ne peut pas etre inclus dans deux collections distinctes.
- Verification que `recycleCollection` transfere des tokens `WST` vers le citoyen proprietaire du dechet.
- Verification que `setRecycler(address(0))` revert ou que `recycleCollection` revert si `recycler` n'est pas initialise.