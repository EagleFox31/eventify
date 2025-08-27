"""
tickets/tests/test_stress.py

Tests de stress et de concurrence pour l'application tickets
Exécution recommandée : pipeline nightly ou tests de régression
───────────────────────────────────────────────────────────────────
Ces tests simulent des conditions réelles avec plusieurs utilisateurs
qui tentent d'acheter des billets simultanément sur des quotas limités.
"""

from decimal import Decimal
from django.utils import timezone
from rest_framework.test import APITestCase
from django.contrib.auth import get_user_model
import threading
from threading import Thread
from tickets.models import Venue, Event, TicketType, Order, Ticket
import time

User = get_user_model()


class ConcurrentOrderStressTest(APITestCase):
    """
    Tests de concurrence pour la création simultanée de commandes
    avec quotas limités - pour identifier les race conditions
    """

    def setUp(self):
        self.user = User.objects.create_user("stress_user", password="pass123")
        self.venue = Venue.objects.create(
            name="Arena Test",
            address="Test Stress Address",
            capacity=100
        )
        self.event = Event.objects.create(
            title="Stress Test Event",
            start_time=timezone.now() + timezone.timedelta(days=1),
            end_time=timezone.now() + timezone.timedelta(days=1, hours=2),
            venue=self.venue,
            quota_global=50
        )

    def test_concurrent_ticket_creation_race_condition(self):
        """
        Test de concurrence : plusieurs threads tentent d'acheter les dernières places
        Objectif : détecter les race conditions dans la gestion des quotas
        """
        # Créer un ticket type avec quota très limité
        limited_type = TicketType.objects.create(
            event=self.event,
            name="Ultra Limited",
            price=Decimal("500.00"),
            quota=3  # Seulement 3 places disponibles
        )
        
        results = []
        exceptions = []
        
        def create_order_attempt():
            """Tentative de création d'une commande dans un thread séparé"""
            try:
                # Créer un client pour ce thread
                from rest_framework.test import APIClient
                client = APIClient()
                client.force_authenticate(user=self.user)
                
                res = client.post(
                    "/api/orders/",
                    {"tickets": [{"ticket_type": limited_type.id}]},
                    format="json"
                )
                results.append(res.status_code)
                
            except Exception as e:
                exceptions.append(str(e))
        
        # Lancer 6 threads simultanément pour 3 places seulement
        threads = []
        for _ in range(6):
            thread = Thread(target=create_order_attempt)
            threads.append(thread)
        
        # Démarrer tous les threads en même temps
        start_time = time.time()
        for thread in threads:
            thread.start()
        
        # Attendre que tous se terminent
        for thread in threads:
            thread.join(timeout=10)  # Timeout de sécurité
        
        end_time = time.time()
        
        # Analyser les résultats
        success_count = sum(1 for result in results if result == 201)
        error_count = sum(1 for result in results if result == 400)
        
        # Assertions
        self.assertEqual(success_count, 3, f"Exactement 3 commandes doivent réussir, {success_count} ont réussi")
        self.assertEqual(error_count, 3, f"Exactement 3 commandes doivent échouer, {error_count} ont échoué")
        self.assertEqual(len(exceptions), 0, f"Aucune exception ne devrait être levée: {exceptions}")
        
        # Vérifier l'état final des quotas
        limited_type.refresh_from_db()
        self.assertEqual(limited_type.quota_remaining(), 0, "Quota doit être épuisé")
        
        # Vérifier que les billets ont bien été créés
        total_tickets = Ticket.objects.filter(ticket_type=limited_type).count()
        self.assertEqual(total_tickets, 3, f"3 billets doivent exister, {total_tickets} trouvés")
        
        print(f"Test de concurrence terminé en {end_time - start_time:.2f}s")

    def test_quota_exhaustion_under_load(self):
        """
        Test de charge : épuisement progressif des quotas sous forte charge
        Simule une vente de billets en conditions réelles
        """
        # Événement avec quota modéré
        load_event = Event.objects.create(
            title="Load Test Concert",
            start_time=timezone.now() + timezone.timedelta(days=7),
            end_time=timezone.now() + timezone.timedelta(days=7, hours=3),
            venue=self.venue,
            quota_global=20
        )
        
        # Plusieurs catégories de billets
        standard = TicketType.objects.create(
            event=load_event,
            name="Standard",
            price=Decimal("1000.00"),
            quota=15
        )
        
        vip = TicketType.objects.create(
            event=load_event,
            name="VIP",
            price=Decimal("5000.00"),
            quota=5
        )
        
        results = []
        
        def bulk_purchase():
            """Achat en lot dans un thread"""
            try:
                from rest_framework.test import APIClient
                client = APIClient()
                client.force_authenticate(user=self.user)
                
                # Tentative d'achat mixte (2 standard + 1 VIP)
                res = client.post(
                    "/api/orders/",
                    {
                        "tickets": [
                            {"ticket_type": standard.id},
                            {"ticket_type": standard.id},
                            {"ticket_type": vip.id}
                        ]
                    },
                    format="json"
                )
                results.append({
                    'status': res.status_code,
                    'thread_id': threading.current_thread().ident
                })
                
            except Exception as e:
                results.append({
                    'error': str(e),
                    'thread_id': threading.current_thread().ident
                })
        
        # Lancer 10 threads pour épuiser les quotas
        threads = []
        for i in range(10):
            thread = Thread(target=bulk_purchase, name=f"Buyer-{i}")
            threads.append(thread)
        
        # Exécution simultanée
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join()
        
        # Analyse des résultats
        successful_orders = [r for r in results if r.get('status') == 201]
        failed_orders = [r for r in results if r.get('status') == 400]
        errors = [r for r in results if 'error' in r]
        
        # Les quotas étant 15 standard + 5 VIP = 20 total, mais quota_global = 20
        # Chaque commande réussie consomme 3 billets (2 standard + 1 VIP)
        # Donc maximum 6 commandes peuvent réussir (6 * 3 = 18 ≤ 20)
        # Mais le VIP (quota=5) va être le facteur limitant : max 5 commandes
        
        expected_success = min(5, 20 // 3)  # Limité par VIP ou quota global
        
        self.assertEqual(len(successful_orders), expected_success, 
                        f"Attendu {expected_success} commandes réussies, obtenu {len(successful_orders)}")
        self.assertEqual(len(errors), 0, f"Aucune exception attendue: {errors}")
        
        # Vérifier l'état final
        standard.refresh_from_db()
        vip.refresh_from_db()
        load_event.refresh_from_db()
        
        # Le VIP doit être épuisé en premier
        self.assertEqual(vip.quota_remaining(), 0, "VIP doit être épuisé")
        
        print(f"Résultats du test de charge:")
        print(f"- Commandes réussies: {len(successful_orders)}")
        print(f"- Commandes échouées: {len(failed_orders)}")
        print(f"- Quota Standard restant: {standard.quota_remaining()}")
        print(f"- Quota VIP restant: {vip.quota_remaining()}")
        print(f"- Quota global restant: {load_event.quota_remaining()}")

    def test_database_integrity_under_stress(self):
        """
        Test d'intégrité : vérifier que les contraintes DB tiennent sous stress
        Focus sur les contraintes unique et les clés étrangères
        """
        # Créer plusieurs utilisateurs pour éviter les conflits d'auth
        users = []
        for i in range(5):
            user = User.objects.create_user(f"stress_user_{i}", password="pass123")
            users.append(user)
        
        # TicketType avec quota suffisant pour ce test
        integrity_ticket = TicketType.objects.create(
            event=self.event,
            name="Integrity Test",
            price=Decimal("1500.00"),
            quota=50
        )
        
        results = []
        ticket_ids = []
        
        def create_order_with_user(user_index):
            """Création de commande avec un utilisateur spécifique"""
            try:
                from rest_framework.test import APIClient
                client = APIClient()
                client.force_authenticate(user=users[user_index])
                
                res = client.post(
                    "/api/orders/",
                    {"tickets": [{"ticket_type": integrity_ticket.id}]},
                    format="json"
                )
                
                if res.status_code == 201:
                    # Récupérer les IDs des tickets créés
                    order_id = res.data['id']
                    order = Order.objects.get(id=order_id)
                    for ticket in order.tickets.all():
                        ticket_ids.append(ticket.id)
                
                results.append({
                    'status': res.status_code,
                    'user': user_index,
                    'order_id': res.data.get('id') if res.status_code == 201 else None
                })
                
            except Exception as e:
                results.append({
                    'error': str(e),
                    'user': user_index
                })
        
        # Lancer un thread par utilisateur, plusieurs fois
        threads = []
        for round_num in range(3):  # 3 rounds d'achats
            for user_idx in range(len(users)):
                thread = Thread(
                    target=create_order_with_user, 
                    args=(user_idx,),
                    name=f"Round{round_num}-User{user_idx}"
                )
                threads.append(thread)
        
        # Exécution
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join()
        
        # Vérifications d'intégrité
        successful = [r for r in results if r.get('status') == 201]
        errors = [r for r in results if 'error' in r]
        
        self.assertEqual(len(errors), 0, f"Aucune erreur d'intégrité: {errors}")
        
        # Vérifier l'unicité des tickets créés
        unique_ticket_ids = set(ticket_ids)
        self.assertEqual(len(ticket_ids), len(unique_ticket_ids), 
                        "Tous les tickets doivent avoir des IDs uniques")
        
        # Vérifier que tous les tickets existent bien en base
        existing_tickets = Ticket.objects.filter(id__in=ticket_ids).count()
        self.assertEqual(existing_tickets, len(ticket_ids), 
                        "Tous les tickets créés doivent exister en base")
        
        # Vérifier l'unicité des QR codes
        qr_hashes = list(Ticket.objects.filter(id__in=ticket_ids).values_list('qr_hash', flat=True))
        unique_qr_hashes = set(qr_hashes)
        self.assertEqual(len(qr_hashes), len(unique_qr_hashes), 
                        "Tous les QR codes doivent être uniques")
        
        print(f"Test d'intégrité terminé:")
        print(f"- {len(successful)} commandes créées avec succès")
        print(f"- {len(ticket_ids)} billets générés")
        print(f"- Intégrité des QR codes: OK")


class PerformanceStressTest(APITestCase):
    """
    Tests de performance pour identifier les goulots d'étranglement
    """
    
    def setUp(self):
        self.user = User.objects.create_user("perf_user", password="pass123")
        self.venue = Venue.objects.create(
            name="Performance Arena",
            address="Performance Test Street",
            capacity=10000
        )
    
    def test_large_event_creation_performance(self):
        """
        Test de performance : création d'un événement avec beaucoup de catégories
        """
        start_time = time.time()
        
        # Événement avec quota important
        big_event = Event.objects.create(
            title="Festival Géant",
            start_time=timezone.now() + timezone.timedelta(days=30),
            end_time=timezone.now() + timezone.timedelta(days=32),
            venue=self.venue,
            quota_global=5000
        )
        
        # Créer 20 catégories de billets différentes
        ticket_types = []
        for i in range(20):
            ticket_type = TicketType.objects.create(
                event=big_event,
                name=f"Catégorie-{i:02d}",
                price=Decimal(f"{1000 + i * 500}.00"),
                quota=250  # 20 * 250 = 5000 total
            )
            ticket_types.append(ticket_type)
        
        creation_time = time.time() - start_time
        
        # Test de requête : récupérer l'événement avec toutes ses catégories
        query_start = time.time()
        
        from django.db import connection
        with connection.cursor() as cursor:
            cursor.execute("""
                SELECT e.id, e.title, e.quota_global,
                       COUNT(tt.id) as nb_categories,
                       SUM(tt.quota) as total_quota_categories
                FROM tickets_event e
                LEFT JOIN tickets_tickettype tt ON e.id = tt.event_id
                WHERE e.id = %s
                GROUP BY e.id, e.title, e.quota_global
            """, [big_event.id])
            result = cursor.fetchone()
        
        query_time = time.time() - query_start
        
        # Assertions de performance
        self.assertLess(creation_time, 2.0, f"Création trop lente: {creation_time:.2f}s")
        self.assertLess(query_time, 0.1, f"Requête trop lente: {query_time:.2f}s")
        
        # Vérifications fonctionnelles
        self.assertEqual(result[1], "Festival Géant")
        self.assertEqual(result[2], 5000)  # quota_global
        self.assertEqual(result[3], 20)    # nb_categories
        self.assertEqual(result[4], 5000)  # total_quota_categories
        
        print(f"Performance test - Événement avec 20 catégories:")
        print(f"- Temps de création: {creation_time:.3f}s")
        print(f"- Temps de requête: {query_time:.3f}s")