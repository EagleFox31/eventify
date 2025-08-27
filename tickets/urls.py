# tickets/urls.py
from django.urls import path, include
from rest_framework_nested import routers
from .views import VenueViewSet, EventViewSet, TicketTypeViewSet, OrderViewSet, TicketViewSet, TicketScanView

router = routers.DefaultRouter()
router.register("venues", VenueViewSet)
router.register("events", EventViewSet)
router.register("ticket-types", TicketTypeViewSet, basename="tickettype")  # ✅ racine
router.register("orders", OrderViewSet, basename="order")
router.register("tickets", TicketViewSet, basename="ticket")  # ✅ basename ajouté

event_router = routers.NestedDefaultRouter(router, "events", lookup="event")
event_router.register("ticket-types", TicketTypeViewSet, basename="event-ticket-types")  # ✅ nested

urlpatterns = [
    path("", include(router.urls)),
    path("", include(event_router.urls)),
    # Route explicite vers le téléchargement PDF si besoin hors DRF router
    path("tickets/<uuid:pk>/pdf/", TicketViewSet.as_view({"get": "pdf"}), name="ticket-pdf"),
    path("tickets/scan/", TicketScanView.as_view(), name="ticket-scan"),
]
