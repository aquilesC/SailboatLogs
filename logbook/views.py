import re
import json
from django.http import HttpResponse, JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.utils import timezone
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth import login
from django.db.models import Q, Count, Sum
from dateutil import parser
from .models import Profile, Boat, Trip, Tag, LogEntry


# ═══════════════════════════════════════════
# Twilio Webhook (existing — untouched)
# ═══════════════════════════════════════════

@csrf_exempt
def twilio_webhook(request):
    if request.method == 'POST':
        # Twilio sends data as form-urlencoded
        from_number = request.POST.get('From', '')
        body = request.POST.get('Body', '')
        
        # WhatsApp numbers are typically prefixed with 'whatsapp:'
        if from_number.startswith('whatsapp:'):
            from_number = from_number.replace('whatsapp:', '')
            
        # Parse location if sent (WhatsApp location messages)
        latitude = request.POST.get('Latitude')
        longitude = request.POST.get('Longitude')

        # Twilio doesn't always send a timestamp in the body for inbound messages,
        # but if one is provided (e.g., via a custom header or field), parse it.
        # Otherwise, fallback to the current time.
        timestamp_str = request.POST.get('Timestamp') or request.headers.get('Date')
        if timestamp_str:
            try:
                timestamp = parser.parse(timestamp_str)
            except Exception:
                timestamp = timezone.now()
        else:
            timestamp = timezone.now()

        # Find user by phone number
        try:
            profile = Profile.objects.get(phone_number=from_number)
            user = profile.user
        except Profile.DoesNotExist:
            return HttpResponse("User not found for this phone number.", status=404)

        # Find an active trip for this user.
        # A user has access to trips via the boats they are shared on.
        active_trip = Trip.objects.filter(
            boat__shared_users=user,
            is_active=True
        ).order_by('-start_date').first()

        if not active_trip:
            return HttpResponse("No active trip found for this user.", status=404)

        # Create LogEntry
        log_entry = LogEntry(
            trip=active_trip,
            entry_text=body,
            timestamp=timestamp,
            latitude=latitude if latitude else None,
            longitude=longitude if longitude else None
        )
        log_entry.save()

        # Parse tags (hashtags) from body
        hashtags = re.findall(r'#(\w+)', body)
        for tag_name in hashtags:
            # lowercase tags for consistency
            tag, _ = Tag.objects.get_or_create(name=tag_name.lower())
            log_entry.tags.add(tag)

        # Return TwiML response or a simple 200 OK. 
        # Twilio expects an XML response, but an empty 200 is also accepted.
        return HttpResponse("<Response></Response>", content_type="text/xml")

    return HttpResponse("Method not allowed", status=405)


# ═══════════════════════════════════════════
# Authentication
# ═══════════════════════════════════════════

def signup_view(request):
    if request.method == 'POST':
        form = UserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            return redirect('dashboard')
    else:
        form = UserCreationForm()
    return render(request, 'logbook/signup.html', {'form': form})


# ═══════════════════════════════════════════
# Dashboard
# ═══════════════════════════════════════════

@login_required
def dashboard_view(request):
    user = request.user
    boats = Boat.objects.filter(shared_users=user)
    active_trip = Trip.objects.filter(
        boat__shared_users=user,
        is_active=True
    ).select_related('boat').first()
    recent_logs = LogEntry.objects.filter(
        trip__boat__shared_users=user
    ).select_related('trip', 'trip__boat').order_by('-timestamp')[:10]

    return render(request, 'logbook/dashboard.html', {
        'boats': boats,
        'active_trip': active_trip,
        'recent_logs': recent_logs,
    })


# ═══════════════════════════════════════════
# Boat Management
# ═══════════════════════════════════════════

@login_required
def boat_detail_view(request, pk):
    boat = get_object_or_404(Boat, pk=pk, shared_users=request.user)
    trips = boat.trips.all().order_by('-start_date')
    crew = boat.shared_users.all()
    total_distance = trips.aggregate(total=Sum('total_distance'))['total'] or 0

    return render(request, 'logbook/boat_detail.html', {
        'boat': boat,
        'trips': trips,
        'crew': crew,
        'total_distance': total_distance,
    })


@login_required
def boat_create_view(request):
    if request.method == 'POST':
        boat = Boat.objects.create(
            name=request.POST.get('name', ''),
            description=request.POST.get('description', ''),
            boat_model=request.POST.get('boat_model', ''),
            homeport=request.POST.get('homeport', ''),
            mmsi_registration=request.POST.get('mmsi_registration', ''),
        )
        boat.shared_users.add(request.user)
        return redirect('boat_detail', pk=boat.pk)

    return render(request, 'logbook/boat_form.html', {'boat': None})


@login_required
def boat_edit_view(request, pk):
    boat = get_object_or_404(Boat, pk=pk, shared_users=request.user)
    if request.method == 'POST':
        boat.name = request.POST.get('name', boat.name)
        boat.description = request.POST.get('description', boat.description)
        boat.boat_model = request.POST.get('boat_model', boat.boat_model)
        boat.homeport = request.POST.get('homeport', boat.homeport)
        boat.mmsi_registration = request.POST.get('mmsi_registration', boat.mmsi_registration)
        boat.save()
        return redirect('boat_detail', pk=boat.pk)

    return render(request, 'logbook/boat_form.html', {'boat': boat})


# ═══════════════════════════════════════════
# Trip Management
# ═══════════════════════════════════════════

@login_required
def trip_list_view(request):
    trips = Trip.objects.filter(
        boat__shared_users=request.user
    ).select_related('boat').order_by('-start_date')

    query = request.GET.get('q', '')
    if query:
        trips = trips.filter(
            Q(title__icontains=query) | Q(boat__name__icontains=query)
        )

    return render(request, 'logbook/trip_list.html', {
        'trips': trips,
        'query': query,
    })


@login_required
def trip_detail_view(request, pk):
    trip = get_object_or_404(Trip, pk=pk, boat__shared_users=request.user)
    log_entries = trip.log_entries.all().order_by('timestamp').prefetch_related('tags')

    if request.method == 'POST':
        # Handle GPX upload
        gpx_file = request.FILES.get('gpx_file')
        if gpx_file:
            trip.gpx_file = gpx_file
            trip.save()
            return redirect('trip_detail', pk=pk)

        # Handle share slug regeneration
        if 'regenerate_slug' in request.POST:
            trip.regenerate_share_slug()
            return redirect('trip_detail', pk=pk)

    return render(request, 'logbook/trip_detail_internal.html', {
        'trip': trip,
        'log_entries': log_entries,
    })


@login_required
def trip_start_view(request):
    boats = Boat.objects.filter(shared_users=request.user)

    if request.method == 'POST':
        boat = get_object_or_404(Boat, pk=request.POST.get('boat'), shared_users=request.user)
        trip = Trip.objects.create(
            boat=boat,
            title=request.POST.get('title', ''),
            start_date=timezone.now().date(),
            is_active=True,
        )
        return redirect('trip_detail', pk=trip.pk)

    return render(request, 'logbook/trip_form.html', {
        'boats': boats,
    })


def trip_public_view(request, share_slug):
    trip = get_object_or_404(Trip, share_slug=share_slug)
    log_entries = trip.log_entries.all().order_by('timestamp').prefetch_related('tags')

    return render(request, 'logbook/trip_detail_public.html', {
        'trip': trip,
        'log_entries': log_entries,
    })


# ═══════════════════════════════════════════
# Tags
# ═══════════════════════════════════════════

@login_required
def tag_detail_view(request, tag_name):
    tag = get_object_or_404(Tag, name=tag_name.lower())
    log_entries = tag.log_entries.all().select_related(
        'trip', 'trip__boat'
    ).order_by('-timestamp')

    return render(request, 'logbook/tag_detail.html', {
        'tag': tag,
        'log_entries': log_entries,
    })
