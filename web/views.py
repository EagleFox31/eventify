from django.shortcuts import render, get_object_or_404
from django.db.utils import ProgrammingError
from django.core.exceptions import ObjectDoesNotExist
from tickets.models import Event


def home(request):
    try:
        events = Event.objects.all().order_by('start_time')
    except ProgrammingError:
        # La table n'existe pas encore (migrations non appliquées)
        events = []
    return render(request, 'web/home.html', {'events': events})


def event_detail(request, event_id):
    try:
        event = Event.objects.get(pk=event_id)
    except (ProgrammingError, ObjectDoesNotExist):
        # Si la table n'existe pas ou que l'event n'existe pas
        event = None
    return render(request, 'web/event_detail.html', {'event': event})
