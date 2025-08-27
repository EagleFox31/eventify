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