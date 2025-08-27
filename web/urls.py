from django.urls import path
from . import views

app_name = 'web'

urlpatterns = [
    path('', views.home, name='home'),
    path('event/<int:event_id>/', views.event_detail, name='event_detail'),
]
