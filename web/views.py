from django.shortcuts import render
from tickets.models import Event

def home(request):
    events = Event.objects.all().order_by('start_time')
    return render(request, 'web/home.html', {'events': events})

def event_detail(request, event_id):
    event = Event.objects.get(pk=event_id)
    return render(request, 'web/event_detail.html', {'event': event})
