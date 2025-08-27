import uuid
import hashlib
from decimal import Decimal
from django.db import models, transaction
from django.utils import timezone
from django.contrib.auth import get_user_model

User = get_user_model()

# ──────────────────── 1. Référentiels ──────────────────── #
class Venue(models.Model):
    """Lieu physique réutilisable par plusieurs événements."""
    name       = models.CharField(max_length=120)
    address    = models.TextField()
    capacity   = models.PositiveIntegerField()
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name


class Event(models.Model):
    """Événement unique (concert, conférence, etc.)."""
    title        = models.CharField(max_length=120)
    description  = models.TextField(blank=True)
    start_time   = models.DateTimeField()
    end_time     = models.DateTimeField()
    venue        = models.ForeignKey(Venue, on_delete=models.PROTECT, related_name="events")
    quota_global = models.PositiveIntegerField(help_text="Nombre total de billets toutes catégories confondues.")
    created_at   = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["start_time"]

    def __str__(self) -> str:
        return self.title

    # --- Logiciel : contrôles simples -------------------- #
    def quota_used(self) -> int:
        return Ticket.objects.filter(ticket_type__event=self).count()

    def quota_remaining(self) -> int:
        return max(self.quota_global - self.quota_used(), 0)


class TicketType(models.Model):
    """Catégorie de billet (Standard, VIP…)."""
    event       = models.ForeignKey(Event, on_delete=models.CASCADE, related_name="ticket_types")
    name        = models.CharField(max_length=60)
    price       = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal("0.00"))
    quota       = models.PositiveIntegerField()
    created_at  = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("event", "name")
        ordering = ["price"]

    def __str__(self) -> str:
        return f"{self.event.title} – {self.name}"

    # Disponibilités restantes pour ce type précis
    def quota_used(self) -> int:
        return Ticket.objects.filter(ticket_type=self).count()

    def quota_remaining(self) -> int:
        return max(self.quota - self.quota_used(), 0)


# ──────────────────── 2. Commande & paiement ──────────────────── #
class Order(models.Model):
    """Transaction regroupant un ou plusieurs billets."""
    STATUS = [
        ("PENDING", "En attente de paiement"),
        ("PAID", "Payée"),
        ("CANCELLED", "Annulée"),
    ]

    id          = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user        = models.ForeignKey(User, on_delete=models.CASCADE, related_name="orders")
    status      = models.CharField(max_length=10, choices=STATUS, default="PENDING")
    total_amount = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal("0.00"))
    created_at  = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return f"Order {self.id} – {self.status}"

    # Calcul automatique du montant total
    def recompute_total(self) -> None:
        self.total_amount = sum(t.ticket_type.price for t in self.tickets.all())
        self.save(update_fields=["total_amount"])


# ──────────────────── 3. Billets & contrôle d'accès ──────────────────── #
class Ticket(models.Model):
    """Billet individuel contenant un QR‑code."""
    STATUS = [
        ("UNUSED", "Valide – non scanné"),
        ("USED", "Déjà scanné"),
        ("REFUNDED", "Remboursé / Invalide"),
    ]

    id           = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    order        = models.ForeignKey(Order, on_delete=models.CASCADE, related_name="tickets")
    ticket_type  = models.ForeignKey(TicketType, on_delete=models.PROTECT, related_name="tickets")
    status       = models.CharField(max_length=10, choices=STATUS, default="UNUSED")
    qr_hash      = models.CharField(max_length=64, unique=True, editable=False)  # SHA‑256 stocké en hexa
    pdf_file = models.FileField(upload_to="tickets/", null=True, blank=True)
    created_at   = models.DateTimeField(auto_now_add=True)
    scanned_at   = models.DateTimeField(null=True, blank=True)

    def __str__(self) -> str:
        return f"{self.ticket_type.name} – {self.id}"

    def save(self, *args, **kwargs):
        # Generate QR hash if not already set
        if not self.qr_hash:
            self.qr_hash = self._generate_qr_hash()
        super().save(*args, **kwargs)

    def _generate_qr_hash(self):
        """Generate a unique QR hash for this ticket"""
        # Use ticket ID, order ID, and current timestamp to ensure uniqueness
        unique_string = f"{self.id}-{self.order.id}-{timezone.now().isoformat()}"
        return hashlib.sha256(unique_string.encode()).hexdigest()

    # Validation simple (utilisé par le scan)
    def mark_used(self) -> None:
        if self.status != "UNUSED":
            raise ValueError("Ticket déjà utilisé ou invalide.")
        self.status = "USED"
        self.scanned_at = timezone.now()
        self.save(update_fields=["status", "scanned_at"])


class ScanLog(models.Model):
    """Historique de tous les scans de QR‑codes."""
    RESULT = [
        ("VALID", "OK – premier scan"),
        ("DUPLICATE", "Dupliqué – déjà scanné"),
        ("INVALID", "Échec – ticket inconnu"),
    ]

    id          = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    ticket      = models.ForeignKey(Ticket, on_delete=models.SET_NULL, null=True, blank=True)
    scanner     = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    result      = models.CharField(max_length=9, choices=RESULT)
    device_info = models.CharField(max_length=120, blank=True)
    scanned_at  = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-scanned_at"]


# ──────────────────── 4. Notifications ──────────────────── #
class NotificationLog(models.Model):
    """Trace toute notification sortante (e‑mail, SMS…)."""
    CHANNEL = [("EMAIL", "Email"), ("SMS", "SMS")]

    id          = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user        = models.ForeignKey(User, on_delete=models.CASCADE, related_name="notifications")
    event       = models.ForeignKey(Event, on_delete=models.SET_NULL, null=True, blank=True)
    channel     = models.CharField(max_length=8, choices=CHANNEL)
    template    = models.CharField(max_length=80)         # ex: 'ticket_confirmation'
    status      = models.CharField(max_length=20, default="SENT")  # SENT, FAILED
    payload     = models.JSONField(blank=True, default=dict)       # extra data
    created_at  = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]