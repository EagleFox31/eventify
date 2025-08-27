# Analyse du Projet "Eventify"

Ce document résume l'architecture et le fonctionnement du projet de billetterie "Eventify".

## 1. Vue d'ensemble

Eventify est une application web développée avec Django et Django Rest Framework, conçue pour gérer la vente de billets pour des événements. Elle offre une API RESTful complète pour la gestion des lieux, des événements, des types de billets, des commandes et des billets individuels.

Le projet intègre des fonctionnalités clés telles que la génération de billets en PDF avec des QR codes uniques, un système de scan pour le contrôle d'accès, et une structure de base de données robuste pour assurer l'intégrité des données.

## 2. Technologies et Dépendances

Le projet s'appuie sur les technologies suivantes :

- **Backend :**
  - **Django:** Framework web principal.
  - **Django Rest Framework (DRF):** Pour la création des API RESTful.
  - **drf-nested-routers:** Pour la gestion des routes d'API imbriquées (ex: lister les types de billets d'un événement spécifique).
- **Base de données :**
  - **SQLite:** Base de données par défaut de Django, utilisée pour le développement.
- **Génération de documents :**
  - **WeasyPrint:** Pour la création de billets au format PDF.
  - **qrcode:** Pour la génération de QR codes intégrés aux billets.
- **Tests :**
  - **Pytest** et **pytest-django:** Pour l'écriture et l'exécution des tests unitaires et d'intégration.

## 3. Structure du Projet

Le projet est organisé en deux applications principales :

- `eventify`: Le projet Django principal, qui gère la configuration globale (`settings.py`), le routage principal (`urls.py`) et le point d'entrée WSGI/ASGI.
- `tickets`: L'application cœur du projet, qui contient toute la logique métier :
  - `models.py`: Définit la structure de la base de données.
  - `views.py`: Contient la logique de l'API (ViewSets).
  - `serializers.py`: Gère la transformation des données entre le format JSON et les objets Django.
  - `urls.py`: Définit les routes spécifiques à l'application `tickets`.
  - `tests/`: Contient les tests pour l'application.
  - `utils/`: Contient des utilitaires, comme la logique de génération de PDF.

## 4. Modèles de Données (Base de Données)

La base de données est structurée autour des modèles suivants :

- **Venue:** Représente un lieu physique (salle de concert, centre de conférence).
- **Event:** Un événement spécifique (concert, festival) qui se déroule dans un `Venue`.
- **TicketType:** Une catégorie de billet pour un événement (ex: "Standard", "VIP"). Chaque type a son propre quota et son prix.
- **Order:** Une commande passée par un utilisateur, qui peut contenir plusieurs billets.
- **Ticket:** Un billet individuel, lié à une commande et à un type de billet. Chaque billet a un statut (`UNUSED`, `USED`) et un QR code unique pour le contrôle d'accès.
- **ScanLog:** Enregistre chaque tentative de scan d'un QR code, qu'elle soit valide, dupliquée ou invalide.
- **NotificationLog:** Trace l'envoi de notifications (ex: e-mail de confirmation).

## 5. API Endpoints

L'API est accessible via le préfixe `/api/`. Les principaux endpoints sont :

- `/venues/`: Gérer les lieux.
- `/events/`: Gérer les événements.
- `/events/{event_id}/ticket-types/`: Gérer les types de billets pour un événement spécifique.
- `/orders/`: Gérer les commandes.
- `/tickets/`: Gérer les billets.
- `/tickets/{ticket_id}/pdf/`: Télécharger le billet en format PDF.
- `/tickets/scan/`: Scanner un billet via son QR code.

## 6. Fonctionnalités Clés

- **Gestion complète des événements :** De la création du lieu à la vente de billets.
- **API RESTful bien structurée :** Utilisation de ViewSets et de routeurs imbriqués pour une API claire et facile à utiliser.
- **Génération de billets PDF :** Chaque billet peut être téléchargé en PDF, avec un QR code unique.
- **Contrôle d'accès par QR Code :** Un endpoint dédié permet de scanner les billets pour valider l'entrée.
- **Gestion des quotas :** Des quotas sont appliqués à la fois au niveau de l'événement global et pour chaque type de billet.
- **Tests :** Le projet inclut une suite de tests pour garantir la fiabilité du code.

## 7. Interfaces Utilisateur à Créer (Frontend)

Le backend étant une API RESTful, un frontend (client) doit être développé pour permettre aux utilisateurs d'interagir avec le système. On peut envisager plusieurs interfaces :

### A. Interface Publique (Site Web Client)

Destinée aux acheteurs de billets.

- **Accueil :** Liste des événements à venir.
- **Page Événement :** Détails d'un événement, liste des types de billets disponibles (Standard, VIP...), leur prix et les quotas restants.
- **Panier d'achat :** Permet à l'utilisateur de sélectionner plusieurs billets avant de passer à la caisse.
- **Processus de paiement :** Formulaire pour finaliser la commande (intégration avec une passerelle de paiement non incluse dans le backend actuel).
- **Espace Utilisateur :**
  - Voir l'historique de ses commandes.
  - Télécharger ses billets en PDF.

### B. Interface d'Administration (Dashboard)

Destinée aux organisateurs d'événements et aux administrateurs du site.

- **Gestion des Lieux (Venues) :** Créer, voir, modifier, supprimer des lieux.
- **Gestion des Événements :** Créer, voir, modifier, supprimer des événements. Associer un événement à un lieu, définir les dates et les quotas globaux.
- **Gestion des Types de Billets :** Pour chaque événement, créer, modifier ou supprimer des types de billets (ex: VIP, Normal), avec leur prix et quota respectif.
- **Suivi des Ventes :** Tableau de bord affichant les statistiques de vente par événement.
- **Gestion des Commandes :** Voir les détails de chaque commande, leur statut (payée, en attente, annulée).
- **Journal des Scans :** Consulter l'historique des scans pour un événement (billets valides, dupliqués, etc.).

### C. Application de Scan (Mobile ou Web App)

Destinée au personnel sur le lieu de l'événement pour le contrôle d'accès.

- **Interface de Scan :** Utilise la caméra de l'appareil pour scanner le QR code sur les billets.
- **Retour Visuel :**
  - **Succès :** Affiche un message "Valide" en vert.
  - **Échec (Dupliqué) :** Affiche un message "Déjà scanné" en orange/jaune, avec l'heure du premier scan.
  - **Échec (Invalide) :** Affiche un message "Ticket Inconnu" en rouge.
- **Mode hors-ligne (Optionnel) :** Possibilité de pré-charger les données des billets pour un événement afin de pouvoir scanner même avec une connexion internet instable.
