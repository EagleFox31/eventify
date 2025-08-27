# On importe DRF
from rest_framework import serializers
from rest_framework.validators import UniqueTogetherValidator
from django.db import transaction

# On importe nos modèles
from .models import Venue, Event, TicketType, Order, Ticket

# 1) Serializer pour Venue
class VenueSerializer(serializers.ModelSerializer):
    class Meta:
        model = Venue
        fields = '__all__'  # Tous les champs de Venue

# 2) Serializer pour TicketType
class TicketTypeSerializer(serializers.ModelSerializer):
    # Lecture : on peut renvoyer l'event complet (optionnel)
    event = serializers.SerializerMethodField(read_only=True)
    # Écriture : l’API attend event_id pour lier l’event
    event_id = serializers.PrimaryKeyRelatedField(
        queryset=Event.objects.all(),
        write_only=True,
        source="event"
    )

    class Meta:
        model = TicketType
        fields = ["id", "event", "event_id", "name", "price", "quota", "created_at"]

    def get_event(self, obj):
        # Option simple : renvoyer juste l'id (ou un sous-serializer si tu préfères)
        return {"id": obj.event_id, "title": obj.event.title}

    def validate(self, data):
        event = data.get("event") or self.context.get("event")
        quota = data.get("quota")
        if event and quota is not None and quota > event.quota_global:
            raise serializers.ValidationError(
                {"quota": f"Le quota ({quota}) dépasse le quota global de l’événement ({event.quota_global})."}
            )
        return data
# 3) Serializer pour Event
class EventSerializer(serializers.ModelSerializer):
    # On veut inclure le détail du lieu (lecture seule)
    venue = VenueSerializer(read_only=True)
    # Mais permettre d'envoyer juste l'ID du lieu quand on crée un événement
    venue_id = serializers.PrimaryKeyRelatedField(
        queryset=Venue.objects.all(),  # Liste de lieux valides
        write_only=True,               # Utilisé seulement en entrée
        source="venue"                 # On stocke dans le champ venue
    )
    # On veut aussi voir les ticket types attachés à l'événement
    ticket_types = TicketTypeSerializer(read_only=True, many=True)

    class Meta:
        model = Event
        fields = [
            "id",
            "title",
            "description",
            "start_time",
            "end_time",
            "venue",       # détails du lieu (lecture)
            "venue_id",    # pour création
            "quota_global",
            "created_at",
            "ticket_types" # liste des catégories
        ]

    def validate(self, data):
        # Validation : end_time > start_time
        if data["end_time"] <= data["start_time"]:
            raise serializers.ValidationError(
                {"end_time": "La date de fin doit être postérieure à la date de début."}
            )
        
        # Validation : quota_global <= venue.capacity
        venue = data["venue"]
        if data["quota_global"] > venue.capacity:
            raise serializers.ValidationError(
                {"quota_global": "Le quota global dépasse la capacité du lieu."}
            )
        
        return data

class TicketSerializer(serializers.ModelSerializer):
    class Meta:
        model = Ticket
        fields = ["id", "ticket_type", "status", "created_at", "qr_hash"]
        read_only_fields = ["id", "status", "created_at", "qr_hash"]

class OrderSerializer(serializers.ModelSerializer):
    tickets = TicketSerializer(many=True, write_only=True)

    class Meta:
        model = Order
        fields = ["id", "user", "status", "total_amount", "tickets", "created_at"]
        read_only_fields = ["id", "status", "total_amount", "created_at", "user"]

    def validate_tickets(self, value):
        """Validate that at least one ticket is provided"""
        if not value:
            raise serializers.ValidationError("Au moins un billet doit être commandé.")
        return value

    def create(self, validated_data):
        ticket_data = validated_data.pop("tickets")
        user = self.context["request"].user
        
        with transaction.atomic():  # si quelque chose plante, rien n'est enregistré
            order = Order.objects.create(user=user)
            
            for t in ticket_data:
                tt = TicketType.objects.select_for_update().get(pk=t["ticket_type"].id)

                # Vérification des quotas
                if tt.quota_remaining() <= 0:
                    raise serializers.ValidationError(f"Plus de places pour {tt.name}")
                if tt.event.quota_remaining() <= 0:
                    raise serializers.ValidationError("Quota global de l'événement atteint")

                Ticket.objects.create(order=order, ticket_type=tt)
            
            order.recompute_total()
        return order