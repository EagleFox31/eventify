# tickets/views.py
from rest_framework import viewsets, permissions
from rest_framework.exceptions import ValidationError
from django.http import FileResponse
from rest_framework.decorators import action
from django.db import IntegrityError
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from .models import Venue, Event, TicketType, Order, Ticket, ScanLog
from .serializers import VenueSerializer, EventSerializer, TicketTypeSerializer, OrderSerializer, TicketSerializer

class VenueViewSet(viewsets.ModelViewSet):
    queryset           = Venue.objects.all()
    serializer_class   = VenueSerializer
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]

class EventViewSet(viewsets.ModelViewSet):
    queryset           = Event.objects.select_related("venue").prefetch_related("ticket_types")
    serializer_class   = EventSerializer
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]

class TicketTypeViewSet(viewsets.ModelViewSet):
    serializer_class   = TicketTypeSerializer
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]
    queryset           = TicketType.objects.select_related("event").all()  # ✅ permet la route racine

    def get_queryset(self):
        qs = super().get_queryset()
        event_pk = self.kwargs.get("event_pk")
        return qs.filter(event_id=event_pk) if event_pk else qs

    def get_serializer_context(self):
        ctx = super().get_serializer_context()
        event_pk = self.kwargs.get("event_pk")
        if event_pk:
            try:
                ctx["event"] = Event.objects.get(pk=event_pk)
            except Event.DoesNotExist:
                pass
        return ctx

    def perform_create(self, serializer):
        # Si on est en nested, on force l’event depuis l’URL
        ctx_event = self.get_serializer_context().get("event")
        if ctx_event:
            sent_event = serializer.validated_data.get("event")
            if sent_event and sent_event.id != ctx_event.id:
                raise ValidationError("Conflit d'événement : l'URL et le body ne correspondent pas.")
            try:
                serializer.save(event=ctx_event)
            except IntegrityError:
                raise ValidationError("Cette catégorie existe déjà pour cet événement.")
        else:
            # Route racine : event doit venir du body via event_id
            if "event" not in serializer.validated_data:
                raise ValidationError({"event_id": "Ce champ est requis."})
            try:
                serializer.save()
            except IntegrityError:
                raise ValidationError("Cette catégorie existe déjà pour cet événement.")

class OrderViewSet(viewsets.ModelViewSet):
    serializer_class   = OrderSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        qs = Order.objects.prefetch_related("tickets__ticket_type")
        return qs if self.request.user.is_staff else qs.filter(user=self.request.user)

class TicketViewSet(viewsets.ModelViewSet):
    queryset = Ticket.objects.select_related("ticket_type", "order")
    serializer_class = TicketSerializer
    permission_classes = [permissions.IsAuthenticated]

    @action(detail=True, methods=["get"])
    def pdf(self, request, pk=None):
        ticket = self.get_object()
        if not ticket.pdf_file:
            return Response({"error": "Aucun PDF généré pour ce billet."}, status=404)
        return FileResponse(
            ticket.pdf_file.open(),
            as_attachment=True,
            filename=f"ticket_{ticket.id}.pdf"
        )

class TicketScanView(APIView):
    """
    Vue API pour scanner un billet à partir de son QR code.
    Elle retourne un statut : 
    - VALID     → billet valide et première utilisation
    - DUPLICATE → billet déjà scanné
    - INVALID   → billet introuvable
    """

    def post(self, request):
        # Récupération du hash QR envoyé par le client (lecteur QR ou app mobile)
        qr_hash = request.data.get("qr_hash")
        if not qr_hash:
            # Si aucun hash n'est fourni → erreur
            return Response({"error": "QR hash requis"}, status=status.HTTP_400_BAD_REQUEST)

        try:
            # On cherche le ticket correspondant dans la base
            ticket = Ticket.objects.select_related("ticket_type__event").get(qr_hash=qr_hash)
        except Ticket.DoesNotExist:
            # Si aucun ticket trouvé → on log comme INVALID
            ScanLog.objects.create(result="INVALID", device_info=request.META.get("HTTP_USER_AGENT", ""))
            return Response({"result": "INVALID"}, status=status.HTTP_404_NOT_FOUND)

        # Si le ticket est encore valide et jamais scanné
        if ticket.status == "UNUSED":
            # On marque le ticket comme utilisé
            ticket.mark_used()
            # On log comme VALID
            ScanLog.objects.create(ticket=ticket, result="VALID", device_info=request.META.get("HTTP_USER_AGENT", ""))
            return Response({
                "result": "VALID",
                "event": ticket.ticket_type.event.title,   # Nom de l'évènement
                "category": ticket.ticket_type.name        # Type de billet
            })

        # Si le ticket existe mais a déjà été scanné → DUPLICATE
        ScanLog.objects.create(ticket=ticket, result="DUPLICATE", device_info=request.META.get("HTTP_USER_AGENT", ""))
        return Response({"result": "DUPLICATE"}, status=status.HTTP_400_BAD_REQUEST)
    def post(self, request):
        qr_hash = request.data.get("qr_hash")
        if not qr_hash:
            return Response({"error": "QR hash requis"}, status=status.HTTP_400_BAD_REQUEST)

        try:
            ticket = Ticket.objects.select_related("ticket_type__event").get(qr_hash=qr_hash)
        except Ticket.DoesNotExist:
            ScanLog.objects.create(result="INVALID", device_info=request.META.get("HTTP_USER_AGENT", ""))
            return Response({"result": "INVALID"}, status=status.HTTP_404_NOT_FOUND)

        if ticket.status == "UNUSED":
            ticket.mark_used()
            ScanLog.objects.create(ticket=ticket, result="VALID", device_info=request.META.get("HTTP_USER_AGENT", ""))
            return Response({
                "result": "VALID",
                "event": ticket.ticket_type.event.title,
                "category": ticket.ticket_type.name
            })

        ScanLog.objects.create(ticket=ticket, result="DUPLICATE", device_info=request.META.get("HTTP_USER_AGENT", ""))
        return Response({"result": "DUPLICATE"}, status=status.HTTP_400_BAD_REQUEST)