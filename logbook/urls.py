from django.urls import path
from . import views

urlpatterns = [
    # Webhook (existing)
    path('webhook/twilio/', views.twilio_webhook, name='twilio_webhook'),

    # Authentication
    path('accounts/signup/', views.signup_view, name='signup'),

    # Profile
    path('profile/', views.profile_view, name='profile'),

    # Dashboard
    path('dashboard/', views.dashboard_view, name='dashboard'),
    path('', views.dashboard_view, name='home'),

    # Boat Management
    path('boats/add/', views.boat_create_view, name='boat_create'),
    path('boats/<int:pk>/', views.boat_detail_view, name='boat_detail'),
    path('boats/<int:pk>/edit/', views.boat_edit_view, name='boat_edit'),

    # Trip Management
    path('trips/', views.trip_list_view, name='trip_list'),
    path('trips/start/', views.trip_start_view, name='trip_start'),
    path('trips/<int:pk>/', views.trip_detail_view, name='trip_detail'),

    # Public Shared Trip
    path('shared/<slug:share_slug>/', views.trip_public_view, name='trip_public'),

    # Tags
    path('tags/<str:tag_name>/', views.tag_detail_view, name='tag_detail'),
]
