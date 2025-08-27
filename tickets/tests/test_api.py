"""
tickets/tests/test_api.py

Batterie de tests CRUD + validations pour Venue, Event, TicketType, Order et Ticket
Contexte : Cameroun (Douala, Yaoundé)
Auteur   : QA Engineer Senior
Date     : 2025‑07‑30
───────────────────────────────────────────────────────────────────
Notions QA utilisées ici
───────────────────────────────────────────────────────────────────
✔ True Negative  : Scénario valide ⇒ test doit passer (200/201/204)  
✔ True Positive  : Scénario invalide ⇒ API renvoie une erreur, test passe   
✔ False Positive : Test rouge alors que le code est correct  (à éviter)  
✔ False Negative : Test vert alors qu'un bug existe (à éviter)  
Les cas négatifs ci‑dessous cherchent à produire **des true positives** :
l'API doit refuser la requête et retourner un code 4xx attendu.
"""

from decimal import Decimal 
from django.urls import reverse
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APITestCase
from django.contrib.auth import get_user_model
from tickets.models import Venue, Event, TicketType, Order, Ticket

User = get_user_model()


class VenueEventTicketTypeCRUDTest(APITestCase):
    """
    On couvre ici :
    - CRUD complet pour Venue, Event, TicketType
    - Règles métiers : quota, unicité, types de champs
    """

    def setUp(self):
        # Compte QA (supervisé) — true negative si login OK
        self.user = User.objects.create_user("qa_user", password="pass123")
        self.client.login(username="qa_user", password="pass123")

        # Adresse de référence pour Douala & Yaoundé
        self.douala_addr = "Rue du Port, Douala"
        self.yaounde_addr = "Boulevard du 20 Mai, Yaoundé"

    # ─────────────────────────── Venue ─────────────────────────── #

    def test_venue_create_read_update_delete(self):
        """True Negative : CRUD complet sur Venue"""

        # CREATE
        res = self.client.post(
            "/api/venues/",
            {
                "name": "Palais des Congrès",
                "address": self.yaounde_addr,
                "capacity": 800,
            },
            format="json",
        )
        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        venue_id = res.data["id"]

        # READ (liste)
        res = self.client.get("/api/venues/")
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertGreaterEqual(len(res.data), 1)

        # UPDATE
        res = self.client.patch(
            f"/api/venues/{venue_id}/", {"capacity": 900}, format="json"
        )
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data["capacity"], 900)

        # DELETE
        res = self.client.delete(f"/api/venues/{venue_id}/")
        self.assertEqual(res.status_code, status.HTTP_204_NO_CONTENT)

    def test_venue_missing_field(self):
        """True Positive : l'API doit refuser un Venue sans adresse"""
        res = self.client.post(
            "/api/venues/",
            {"name": "Salle incomplète", "capacity": 300},
            format="json",
        )
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)

    # ─────────────────────────── Event ─────────────────────────── #

    def _create_reference_venue(self):
        return Venue.objects.create(
            name="Stade de la Réunification",
            address=self.douala_addr,
            capacity=20000,
        )

    def test_event_create_valid(self):
        """True Negative : création d'un événement cohérent"""
        venue = self._create_reference_venue()
        res = self.client.post(
            "/api/events/",
            {
                "title": "Match Gala",
                "description": "Douala vs Yaoundé",
                "start_time": "2025-12-15T18:00:00Z",
                "end_time": "2025-12-15T21:00:00Z",
                "venue_id": venue.id,
                "quota_global": 15000,
            },
            format="json",
        )
        self.assertEqual(res.status_code, status.HTTP_201_CREATED)

    def test_event_end_before_start(self):
        """True Positive : l'API doit refuser end_time < start_time"""
        venue = self._create_reference_venue()
        res = self.client.post(
            "/api/events/",
            {
                "title": "Inversion horaire",
                "start_time": "2025-01-10T20:00:00Z",
                "end_time": "2025-01-10T18:00:00Z",
                "venue_id": venue.id,
                "quota_global": 100,
            },
            format="json",
        )
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)

    def test_event_quota_exceeds_capacity(self):
        """True Positive : quota_global > capacity du lieu => 400"""
        venue = self._create_reference_venue()  # capacity = 20000
        res = self.client.post(
            "/api/events/",
            {
                "title": "Quota trop grand",
                "start_time": "2025-09-10T18:00:00Z",
                "end_time": "2025-09-10T21:00:00Z",
                "venue_id": venue.id,
                "quota_global": 50000,  # > 20000
            },
            format="json",
        )
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)

    # ────────────────────── TicketType & quotas ────────────────────── #

    def _create_event(self, quota_global=300):
        venue = self._create_reference_venue()
        return Event.objects.create(
            title="Festival Afrobeat",
            start_time=timezone.now() + timezone.timedelta(days=30),
            end_time=timezone.now() + timezone.timedelta(days=30, hours=6),
            venue=venue,
            quota_global=quota_global,
        )

    def test_tickettype_create_valid(self):
        """True Negative : catégorie dans les limites de quota"""
        event = self._create_event()
        res = self.client.post(
            f"/api/events/{event.id}/ticket-types/",
            {
                "name": "Standard",
                "price": "10000.00",
                "quota": 250,
            },
            format="json",
        )
        self.assertEqual(res.status_code, status.HTTP_201_CREATED)

    def test_tickettype_quota_exceeds_event(self):
        """True Positive : dépassement quota_global → 400"""
        event = self._create_event(quota_global=100)
        res = self.client.post(
            f"/api/events/{event.id}/ticket-types/",
            {
                "name": "VIP+",
                "price": "50000.00",
                "quota": 120,  # > quota global
            },
            format="json",
        )
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)

    def test_tickettype_duplicate_name(self):
        """True Positive : même nom pour le même event → 400 (unique_together)"""
        event = self._create_event()
        TicketType.objects.create(
            event=event, name="Gold", price=Decimal("30000.00"), quota=50
        )
        res = self.client.post(
            f"/api/events/{event.id}/ticket-types/",
            {
                "name": "Gold",
                "price": "30000.00",
                "quota": 30,
            },
            format="json",
        )
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)

    def test_tickettype_negative_quota(self):
        """True Positive : quota négatif (= valeur invalide)"""
        event = self._create_event()
        res = self.client.post(
            f"/api/events/{event.id}/ticket-types/",
            {
                "name": "ErreurQuota",
                "price": "12000.00",
                "quota": -5,
            },
            format="json",
        )
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)


class OrderTicketCRUDTest(APITestCase):
    """
    Tests CRUD pour Order et Ticket
    - Création de commandes avec billets
    - Gestion des quotas lors de l'achat
    - Isolation des données utilisateur
    """

    def setUp(self):
        # Deux utilisateurs pour tester l'isolation
        self.user1 = User.objects.create_user("buyer1", password="pass123")
        self.user2 = User.objects.create_user("buyer2", password="pass123")
        self.admin = User.objects.create_superuser("admin", "admin@test.com", "admin123")
        
        # Données de test
        self.venue = Venue.objects.create(
            name="Complexe Omnisports",
            address="Carrefour Obili, Yaoundé",
            capacity=1000
        )
        
        self.event = Event.objects.create(
            title="Concert Makossa",
            start_time=timezone.now() + timezone.timedelta(days=15),
            end_time=timezone.now() + timezone.timedelta(days=15, hours=4),
            venue=self.venue,
            quota_global=500
        )
        
        self.standard_ticket = TicketType.objects.create(
            event=self.event,
            name="Standard",
            price=Decimal("5000.00"),
            quota=400
        )
        
        self.vip_ticket = TicketType.objects.create(
            event=self.event,
            name="VIP",
            price=Decimal("15000.00"),
            quota=100
        )

    # ─────────────────────────── Order Tests ─────────────────────────── #

    def test_order_create_valid(self):
        """True Negative : création d'une commande valide"""
        self.client.force_authenticate(user=self.user1)
        
        res = self.client.post(
            "/api/orders/",
            {
                "tickets": [
                    {"ticket_type": self.standard_ticket.id},
                    {"ticket_type": self.vip_ticket.id}
                ]
            },
            format="json"
        )
        
        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        self.assertEqual(res.data["user"], self.user1.id)
        self.assertEqual(res.data["status"], "PENDING")
        self.assertEqual(res.data["total_amount"], "20000.00")  # 5000 + 15000

    def test_order_read_user_isolation(self):
        """True Negative : chaque utilisateur voit ses commandes"""
        # Commandes pour user1
        self.client.force_authenticate(user=self.user1)
        order1_res = self.client.post(
            "/api/orders/",
            {"tickets": [{"ticket_type": self.standard_ticket.id}]},
            format="json"
        )
        
        # Commandes pour user2
        self.client.force_authenticate(user=self.user2)
        order2_res = self.client.post(
            "/api/orders/",
            {"tickets": [{"ticket_type": self.vip_ticket.id}]},
            format="json"
        )
        
        # User1 ne voit que ses commandes
        self.client.force_authenticate(user=self.user1)
        res = self.client.get("/api/orders/")
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(len(res.data), 1)
        self.assertEqual(res.data[0]["user"], self.user1.id)
        
        # User2 ne voit que ses commandes
        self.client.force_authenticate(user=self.user2)
        res = self.client.get("/api/orders/")
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(len(res.data), 1)
        self.assertEqual(res.data[0]["user"], self.user2.id)

    def test_order_admin_sees_all(self):
        """True Negative : l'admin voit toutes les commandes"""
        # Créer quelques commandes
        self.client.force_authenticate(user=self.user1)
        self.client.post(
            "/api/orders/",
            {"tickets": [{"ticket_type": self.standard_ticket.id}]},
            format="json"
        )
        
        self.client.force_authenticate(user=self.user2)
        self.client.post(
            "/api/orders/",
            {"tickets": [{"ticket_type": self.vip_ticket.id}]},
            format="json"
        )
        
        # Admin voit tout
        self.client.force_authenticate(user=self.admin)
        res = self.client.get("/api/orders/")
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertGreaterEqual(len(res.data), 2)

    def test_order_unauthenticated_denied(self):
        """True Positive : utilisateur non connecté → 401 ou 403"""
        self.client.force_authenticate(user=None)
        res = self.client.post(
            "/api/orders/",
            {"tickets": [{"ticket_type": self.standard_ticket.id}]},
            format="json"
        )
        # DRF peut retourner 401 ou 403 selon la configuration des permissions
        self.assertIn(res.status_code, [status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN])

    def test_order_empty_tickets_invalid(self):
        """True Positive : commande sans billets → 400"""
        self.client.force_authenticate(user=self.user1)
        res = self.client.post(
            "/api/orders/",
            {"tickets": []},
            format="json"
        )
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)

    def test_order_nonexistent_ticket_type(self):
        """True Positive : référence à un TicketType inexistant → 400"""
        self.client.force_authenticate(user=self.user1)
        res = self.client.post(
            "/api/orders/",
            {"tickets": [{"ticket_type": 99999}]},
            format="json"
        )
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)

    # ─────────────────────────── Quota Tests ─────────────────────────── #

    def test_order_quota_exhausted_tickettype(self):
        """True Positive : quota TicketType épuisé → 400"""
        self.client.force_authenticate(user=self.user1)
        
        # Créer un TicketType avec quota=1
        limited_ticket = TicketType.objects.create(
            event=self.event,
            name="Limité",
            price=Decimal("10000.00"),
            quota=1
        )
        
        # Premier achat OK
        res1 = self.client.post(
            "/api/orders/",
            {"tickets": [{"ticket_type": limited_ticket.id}]},
            format="json"
        )
        self.assertEqual(res1.status_code, status.HTTP_201_CREATED)
        
        # Deuxième achat doit échouer
        res2 = self.client.post(
            "/api/orders/",
            {"tickets": [{"ticket_type": limited_ticket.id}]},
            format="json"
        )
        self.assertEqual(res2.status_code, status.HTTP_400_BAD_REQUEST)

    def test_order_quota_exhausted_event(self):
        """True Positive : quota global événement épuisé → 400"""
        self.client.force_authenticate(user=self.user1)
        
        # Créer un événement avec quota_global=1
        small_event = Event.objects.create(
            title="Mini Event",
            start_time=timezone.now() + timezone.timedelta(days=10),
            end_time=timezone.now() + timezone.timedelta(days=10, hours=2),
            venue=self.venue,
            quota_global=1
        )
        
        small_ticket = TicketType.objects.create(
            event=small_event,
            name="Unique",
            price=Decimal("1000.00"),
            quota=10  # Plus grand que quota_global
        )
        
        # Premier achat OK
        res1 = self.client.post(
            "/api/orders/",
            {"tickets": [{"ticket_type": small_ticket.id}]},
            format="json"
        )
        self.assertEqual(res1.status_code, status.HTTP_201_CREATED)
        
        # Deuxième achat doit échouer
        res2 = self.client.post(
            "/api/orders/",
            {"tickets": [{"ticket_type": small_ticket.id}]},
            format="json"
        )
        self.assertEqual(res2.status_code, status.HTTP_400_BAD_REQUEST)

    # ─────────────────────────── Ticket Management ─────────────────────────── #

    def test_ticket_auto_creation(self):
        """True Negative : les billets sont créés automatiquement"""
        self.client.force_authenticate(user=self.user1)
        
        res = self.client.post(
            "/api/orders/",
            {
                "tickets": [
                    {"ticket_type": self.standard_ticket.id},
                    {"ticket_type": self.standard_ticket.id},
                    {"ticket_type": self.vip_ticket.id}
                ]
            },
            format="json"
        )
        
        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        order_id = res.data["id"]
        
        # Vérifier que 3 tickets ont été créés
        order = Order.objects.get(id=order_id)
        self.assertEqual(order.tickets.count(), 3)
        
        # Vérifier les statuts par défaut
        for ticket in order.tickets.all():
            self.assertEqual(ticket.status, "UNUSED")
            self.assertIsNotNone(ticket.qr_hash)

    def test_total_amount_calculation(self):
        """True Negative : calcul automatique du montant total"""
        self.client.force_authenticate(user=self.user1)
        
        res = self.client.post(
            "/api/orders/",
            {
                "tickets": [
                    {"ticket_type": self.standard_ticket.id},  # 5000
                    {"ticket_type": self.standard_ticket.id},  # 5000
                    {"ticket_type": self.vip_ticket.id}        # 15000
                ]
            },
            format="json"
        )
        
        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        self.assertEqual(res.data["total_amount"], "25000.00")  # 5000 + 5000 + 15000

    def test_multiple_orders_quota_tracking(self):
        """True Negative : suivi correct des quotas avec plusieurs commandes"""
        self.client.force_authenticate(user=self.user1)
        
        # Première commande : 2 billets Standard
        res1 = self.client.post(
            "/api/orders/",
            {
                "tickets": [
                    {"ticket_type": self.standard_ticket.id},
                    {"ticket_type": self.standard_ticket.id}
                ]
            },
            format="json"
        )
        self.assertEqual(res1.status_code, status.HTTP_201_CREATED)
        
        # Vérifier les quotas restants
        self.standard_ticket.refresh_from_db()
        self.assertEqual(self.standard_ticket.quota_remaining(), 398)  # 400 - 2
        
        # Deuxième commande : 1 billet VIP
        res2 = self.client.post(
            "/api/orders/",
            {"tickets": [{"ticket_type": self.vip_ticket.id}]},
            format="json"
        )
        self.assertEqual(res2.status_code, status.HTTP_201_CREATED)
        
        # Vérifier quotas
        self.vip_ticket.refresh_from_db()
        self.assertEqual(self.vip_ticket.quota_remaining(), 99)  # 100 - 1
        
        # Quota global de l'événement
        self.event.refresh_from_db()
        self.assertEqual(self.event.quota_remaining(), 497)  # 500 - 3

    def test_qr_hash_uniqueness(self):
        """True Negative : chaque ticket a un QR hash unique"""
        self.client.force_authenticate(user=self.user1)
        
        # Créer plusieurs commandes avec plusieurs billets
        for i in range(3):
            res = self.client.post(
                "/api/orders/",
                {
                    "tickets": [
                        {"ticket_type": self.standard_ticket.id},
                        {"ticket_type": self.vip_ticket.id}
                    ]
                },
                format="json"
            )
            self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        
        # Vérifier que tous les QR hashes sont uniques
        all_tickets = Ticket.objects.all()
        qr_hashes = [ticket.qr_hash for ticket in all_tickets]
        self.assertEqual(len(qr_hashes), len(set(qr_hashes)))  # No duplicates
        
        # Vérifier que chaque hash existe (pas de validation sur le format spécifique)
        for qr_hash in qr_hashes:
            self.assertIsNotNone(qr_hash)
            self.assertTrue(len(qr_hash) > 0)


class TicketManagementTest(APITestCase):
    """
    Tests spécifiques à la gestion des billets individuels
    """
    
    def setUp(self):
        self.user = User.objects.create_user("ticket_user", password="pass123")
        self.venue = Venue.objects.create(name="Test Venue", address="Test Address", capacity=100)
        self.event = Event.objects.create(
            title="Test Event",
            start_time=timezone.now() + timezone.timedelta(days=1),
            end_time=timezone.now() + timezone.timedelta(days=1, hours=2),
            venue=self.venue,
            quota_global=50
        )
        self.ticket_type = TicketType.objects.create(
            event=self.event,
            name="Test Ticket",
            price=Decimal("1000.00"),
            quota=25
        )

    def test_ticket_status_transitions(self):
        """True Negative : transitions d'état des billets"""
        # Créer un billet
        order = Order.objects.create(user=self.user)
        ticket = Ticket.objects.create(order=order, ticket_type=self.ticket_type)
        
        # État initial
        self.assertEqual(ticket.status, "UNUSED")
        self.assertIsNone(ticket.scanned_at)
        
        # Marquer comme utilisé
        ticket.mark_used()
        self.assertEqual(ticket.status, "USED")
        self.assertIsNotNone(ticket.scanned_at)
        
        # Tentative de réutilisation doit échouer
        with self.assertRaises(ValueError):
            ticket.mark_used()