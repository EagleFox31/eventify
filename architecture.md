Architecture du Projet Eventify
🏗️ Type d'Architecture Utilisée
Le projet Eventify utilise principalement l'architecture MVT (Model-View-Template) de Django, adaptée pour une API REST avec les patterns suivants :

1. Architecture MVT (Model-View-Template) - Django Standard

┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│     MODEL       │    │      VIEW       │    │    TEMPLATE     │
│   (models.py)   │◄──►│   (views.py)    │◄──►│   (JSON/API)    │
│                 │    │                 │    │                 │
│ • Venue         │    │ • VenueViewSet  │    │ • Serializers   │
│ • Event         │    │ • EventViewSet  │    │ • JSON Response │
│ • TicketType    │    │ • OrderViewSet  │    │ • REST API      │
│ • Order         │    │                 │    │                 │
│ • Ticket        │    │                 │    │                 │
└─────────────────┘    └─────────────────┘    └─────────────────┘
2. Architecture en Couches (Layered Architecture)

┌─────────────────────────────────────────────────────────────┐
│                    COUCHE PRÉSENTATION                     │
│                   (REST API Endpoints)                     │
│  /api/venues/  /api/events/  /api/orders/                 │
└─────────────────────────────────────────────────────────────┘
                              │
┌─────────────────────────────────────────────────────────────┐
│                    COUCHE LOGIQUE MÉTIER                   │
│                      (ViewSets + Serializers)              │
│  VenueViewSet, EventViewSet, OrderViewSet                 │
│  VenueSerializer, EventSerializer, OrderSerializer        │
└─────────────────────────────────────────────────────────────┘
                              │
┌─────────────────────────────────────────────────────────────┐
│                    COUCHE ACCÈS DONNÉES                    │
│                        (Models Django)                     │
│  Venue, Event, TicketType, Order, Ticket, ScanLog         │
└─────────────────────────────────────────────────────────────┘
                              │
┌─────────────────────────────────────────────────────────────┐
│                    COUCHE PERSISTANCE                      │
│                      (Base de données)                     │
│                        SQLite / PostgreSQL                 │
└─────────────────────────────────────────────────────────────┘
3. Architecture REST API (Representational State Transfer)
Le projet implémente une architecture REST pure avec :


# Structure REST classique
GET    /api/venues/           # Liste des ressources
POST   /api/venues/           # Création d'une ressource
GET    /api/venues/{id}/      # Lecture d'une ressource
PUT    /api/venues/{id}/      # Mise à jour complète
PATCH  /api/venues/{id}/      # Mise à jour partielle
DELETE /api/venues/{id}/      # Suppression d'une ressource
4. Patterns de Conception Utilisés
Repository Pattern (via Django ORM)

# Les modèles Django agissent comme des repositories
class Event(models.Model):
    def quota_used(self) -> int:
        return Ticket.objects.filter(ticket_type__event=self).count()
    
    def quota_remaining(self) -> int:
        return max(self.quota_global - self.quota_used(), 0)
Serializer Pattern (DRF)

# Transformation bidirectionnelle données ↔ JSON
class EventSerializer(serializers.ModelSerializer):
    venue_name = serializers.CharField(source='venue.name', read_only=True)
    ticket_types = TicketTypeSerializer(many=True, read_only=True)
ViewSet Pattern (DRF)

# Regroupement logique des actions CRUD
class EventViewSet(viewsets.ModelViewSet):
    queryset = Event.objects.select_related("venue").prefetch_related("ticket_types")
    serializer_class = EventSerializer
5. Architecture de Sécurité - Permission-Based

# Contrôle d'accès par permissions
class OrderViewSet(viewsets.ModelViewSet):
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        # Isolation des données par utilisateur
        qs = Order.objects.prefetch_related("tickets__ticket_type")
        return qs if self.request.user.is_staff else qs.filter(user=self.request.user)

        
🎯 Comparaison avec d'autres Architectures
❌ Ce que ce N'EST PAS :
Clean Architecture (Hexagonale)
Manque : Pas de séparation explicite entre domaine/infrastructure
Manque : Pas d'interfaces/ports pour découpler les couches
Manque : Logique métier mélangée avec Django ORM
CQRS (Command Query Responsibility Segregation)
Manque : Pas de séparation lecture/écriture
Manque : Pas de bus de commandes/événements
Manque : Modèles unifiés pour lecture et écriture
Event Sourcing
Manque : Pas de stockage d'événements
Manque : État reconstruit par agrégation d'événements
Manque : Pas d'Event Store
Microservices
Manque : Application monolithique
Manque : Pas de services découplés
Manque : Base de données partagée
✅ Ce que c'EST :
Architecture MVT Django + REST API

Caractéristiques confirmées :
✅ Modèles Django pour la persistance
✅ ViewSets pour la logique de présentation
✅ Serializers comme "Templates" JSON
✅ URLs routing pour le dispatching
✅ Middleware pour les préoccupations transversales
✅ Architecture en couches classique
Monolithe Modulaire

✅ Application unique avec modules séparés
✅ Base de données centralisée
✅ Déploiement unifié
✅ Communication interne directe (pas de réseau)
🔧 Architecture Détaillée par Composant
Couche Modèle (Data Layer)

# Responsabilités :
- Définition des entités métier
- Règles de validation de base
- Relations entre entités
- Méthodes de calcul simples (quota_remaining)
Couche Vue (Business Logic Layer)

# Responsabilités :
- Traitement des requêtes HTTP
- Validation métier complexe
- Orchestration des opérations
- Gestion des permissions
- Optimisation des requêtes
Couche Sérialisation (Presentation Layer)

# Responsabilités :
- Transformation données ↔ JSON
- Validation des entrées
- Formatage des sorties
- Gestion des relations imbriquées
🎯 Conclusion sur l'Architecture
Le projet Eventify utilise une architecture MVT Django classique, organisée en couches, avec une API REST complète.

Type principal : MVT (Model-View-Template) + Architecture en Couches

Patterns secondaires :

Repository Pattern (via Django ORM)
Serializer Pattern (DRF)
ViewSet Pattern (DRF)
Permission-Based Security
Style architectural : Monolithe Modulaire avec API REST

Cette architecture est appropriée pour une application de taille moyenne avec des besoins de performance standards et une équipe de développement Django expérimentée.