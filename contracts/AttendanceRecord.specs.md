# Spécifications du Smart Contract : Attendance Record

## 1. Présentation
**Catégorie** : Événement  
**Nom du Contrat** : AttendanceRecord  
**Rôle** : Servir de registre d'émargement numérique décentralisé, garantissant qu'un participant était "présent" (possédait sa clé privée) à un moment précis.

## 2. User Story
> **En tant qu'** enseignant ou chef de projet,  
> **je veux** que mes étudiants ou collaborateurs enregistrent leur présence via une transaction blockchain,  
> **afin de** disposer d'une liste de présence impossible à modifier rétroactivement.

## 3. Acteurs
* **Organisateur (Admin)** : Crée les sessions et définit la durée de validité du pointage.
* **Participant** : Signe une transaction pour prouver sa présence durant le créneau imparti.

## 4. Flux (Acceptance Criteria)
### Scénario A : Ouverture d'un cours
1. **Action** : L'admin crée une session "Réunion PFA" pour une durée de 15 minutes (900 secondes).
2. **Résultat** : Un ID de session est généré et le décompte commence.

### Scénario B : Pointage valide
1. **Action** : Un participant appelle `markAttendance(ID)`.
2. **Condition** : La transaction arrive avant la fin du `endTime` et l'adresse n'a pas encore pointé.
3. **Résultat** : L'adresse est marquée `true` dans le registre. L'événement `AttendanceMarked` est émis.

### Scénario C : Pointage hors délai
1. **Action** : Un participant tente de pointer après les 15 minutes.
2. **Résultat** : La transaction échoue avec le message "Attendance: Temps ecoule".

## 5. Propriétés Techniques
* **Preuve d'existence** : Utilise le `block.timestamp` pour valider la fenêtre de tir.
* **Intégrité** : Personne (même l'admin) ne peut supprimer un émargement une fois la transaction validée dans un bloc.
* **Auditabilité** : La liste des présences peut être extraite facilement en filtrant les événements `AttendanceMarked` pour un `sessionId` spécifique.