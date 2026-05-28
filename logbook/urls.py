from django.urls import path
from . import views

urlpatterns = [
    path('webhook/twilio/', views.twilio_webhook, name='twilio_webhook'),
]
