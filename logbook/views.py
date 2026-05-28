import re
import json
import logging
from io import BytesIO
from django.conf import settings
from django.core.files.base import ContentFile
from django.http import HttpResponse, JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.utils import timezone
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth import login
from django.db.models import Q, Count, Sum
from dateutil import parser
import requests
from .models import Profile, Boat, Trip, Tag, LogEntry, GPXFile, LogEntryPhoto

logger = logging.getLogger(__name__)


# ═══════════════════════════════════════════
# Twilio Webhook
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

        # Handle media attachments (photos and GPX files)
        num_media = int(request.POST.get('NumMedia', 0))
        for i in range(num_media):
            media_url = request.POST.get(f'MediaUrl{i}')
            media_type = request.POST.get(f'MediaContentType{i}', '')

            if not media_url:
                continue

            try:
                # Download media from Twilio (requires Basic Auth)
                auth = None
                if settings.TWILIO_ACCOUNT_SID and settings.TWILIO_AUTH_TOKEN:
                    auth = (settings.TWILIO_ACCOUNT_SID, settings.TWILIO_AUTH_TOKEN)

                response = requests.get(media_url, auth=auth, timeout=30)
                response.raise_for_status()
                file_content = response.content

                # Determine filename from Content-Disposition or URL
                content_disp = response.headers.get('Content-Disposition', '')
                if 'filename=' in content_disp:
                    filename = content_disp.split('filename=')[-1].strip('"\'')
                else:
                    filename = media_url.split('/')[-1].split('?')[0]

                if media_type in ('application/gpx+xml', 'application/xml', 'text/xml') or filename.lower().endswith('.gpx'):
                    # Save as GPX file
                    gpx_file = GPXFile(
                        trip=active_trip,
                        original_filename=filename or f'whatsapp_track_{i}.gpx',
                        source='whatsapp',
                    )
                    gpx_file.file.save(filename or f'whatsapp_track_{i}.gpx', ContentFile(file_content))
                    gpx_file.save()

                elif media_type.startswith('image/'):
                    # Save as photo on the log entry
                    ext = media_type.split('/')[-1].replace('jpeg', 'jpg')
                    photo_filename = filename or f'whatsapp_photo_{i}.{ext}'
                    photo = LogEntryPhoto(
                        log_entry=log_entry,
                        caption=body[:255] if body else '',
                        source='whatsapp',
                    )
                    photo.image.save(photo_filename, ContentFile(file_content))
                    photo.save()

            except Exception as e:
                logger.error(f"Error downloading media {i} from Twilio: {e}")

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
# Profile
# ═══════════════════════════════════════════

@login_required
def profile_view(request):
    user = request.user
    # Get or create profile
    profile, _ = Profile.objects.get_or_create(user=user, defaults={'phone_number': ''})

    if request.method == 'POST':
        from django.contrib import messages

        # Update user fields
        user.first_name = request.POST.get('first_name', '').strip()
        user.last_name = request.POST.get('last_name', '').strip()
        user.email = request.POST.get('email', '').strip()
        user.save(update_fields=['first_name', 'last_name', 'email'])

        # Update profile fields
        profile.phone_number = request.POST.get('phone_number', '').strip()
        profile.save(update_fields=['phone_number'])

        messages.success(request, 'Profile updated successfully.')
        return redirect('profile')

    return render(request, 'logbook/profile.html', {
        'profile': profile,
    })


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
    ).select_related('trip', 'trip__boat').prefetch_related('tags', 'photos').order_by('-timestamp')[:10]

    # Tags used across this user's log entries
    tags = Tag.objects.filter(
        log_entries__trip__boat__shared_users=user
    ).annotate(entry_count=Count('log_entries')).order_by('-entry_count').distinct()

    return render(request, 'logbook/dashboard.html', {
        'boats': boats,
        'active_trip': active_trip,
        'recent_logs': recent_logs,
        'tags': tags,
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

    # Tags used across this boat's log entries
    tags = Tag.objects.filter(
        log_entries__trip__boat=boat
    ).annotate(entry_count=Count('log_entries')).order_by('-entry_count').distinct()

    return render(request, 'logbook/boat_detail.html', {
        'boat': boat,
        'trips': trips,
        'crew': crew,
        'total_distance': total_distance,
        'tags': tags,
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

def _build_gpx_tracks_json(trip):
    """Build a JSON-safe list of GPX tracks for the map.

    Each track includes:
    - points: [[lat, lng], ...] for Leaflet polyline rendering
    - timed_points: [{lat, lng, time}, ...] for photo interpolation (only points with timestamps)
    - filename: original GPX filename
    """
    tracks = []
    for gpx in trip.gpx_files.all():
        if gpx.track_points:
            # Handle both old format ([lat, lng] arrays) and new format (dicts)
            polyline_points = []
            timed_points = []
            for pt in gpx.track_points:
                if isinstance(pt, dict):
                    polyline_points.append([pt['lat'], pt['lng']])
                    if 'time' in pt:
                        timed_points.append({
                            'lat': pt['lat'],
                            'lng': pt['lng'],
                            'time': pt['time'],
                        })
                else:
                    # Legacy [lat, lng] format
                    polyline_points.append(pt)

            tracks.append({
                'points': polyline_points,
                'timed_points': timed_points,
                'filename': gpx.original_filename,
            })
    return json.dumps(tracks)


def _build_photos_json(log_entries):
    """Build a JSON list of photos with timestamps and thumbnail URLs for map placement.

    Returns JSON string of:
    [{
        id: photo.pk,
        url: full image URL,
        thumb_url: thumbnail URL (or full if no thumbnail),
        caption: photo caption,
        timestamp: ISO 8601 effective timestamp,
        lat: log entry latitude (if available),
        lng: log entry longitude (if available),
    }, ...]
    """
    photos = []
    for entry in log_entries:
        for photo in entry.photos.all():
            p = {
                'id': photo.pk,
                'url': photo.image.url,
                'thumb_url': photo.thumbnail.url if photo.thumbnail else photo.image.url,
                'caption': photo.caption or '',
                'timestamp': photo.effective_timestamp.isoformat(),
            }
            if entry.latitude and entry.longitude:
                p['lat'] = float(entry.latitude)
                p['lng'] = float(entry.longitude)
            photos.append(p)
    return json.dumps(photos)


def _associate_photos_to_locations(trip, log_entries):
    """Associate photos without coordinates to nearby log entry locations.

    For each photo whose log entry has no coordinates and that cannot be placed
    on a GPX track, find the nearest log entry (by timestamp) that HAS coordinates,
    within ±30 minutes.

    Returns a JSON string of: { photo_id: { lat, lng, source_entry_id } }
    """
    from datetime import timedelta

    # Collect entries with coordinates
    entries_with_coords = [
        e for e in log_entries
        if e.latitude and e.longitude
    ]

    if not entries_with_coords:
        return json.dumps({})

    # Get the time range covered by GPX tracks (to exclude photos that can be placed on track)
    gpx_time_ranges = []
    for gpx in trip.gpx_files.all():
        if gpx.track_points:
            times = []
            for pt in gpx.track_points:
                if isinstance(pt, dict) and 'time' in pt:
                    try:
                        from dateutil import parser as dt_parser
                        times.append(dt_parser.parse(pt['time']))
                    except Exception:
                        pass
            if times:
                gpx_time_ranges.append((min(times), max(times)))

    proximity_limit = timedelta(minutes=30)
    associations = {}

    for entry in log_entries:
        if entry.latitude and entry.longitude:
            continue  # Entry already has coordinates

        for photo in entry.photos.all():
            photo_time = photo.effective_timestamp

            # Check if this photo can be placed on a GPX track
            on_track = False
            for start_t, end_t in gpx_time_ranges:
                if start_t <= photo_time <= end_t:
                    on_track = True
                    break

            if on_track:
                continue  # Will be handled by GPX interpolation in JS

            # Find nearest entry with coordinates within ±30 minutes
            best_entry = None
            best_delta = None
            for coord_entry in entries_with_coords:
                delta = abs(photo_time - coord_entry.timestamp)
                if delta <= proximity_limit:
                    if best_delta is None or delta < best_delta:
                        best_delta = delta
                        best_entry = coord_entry

            if best_entry:
                associations[str(photo.pk)] = {
                    'lat': float(best_entry.latitude),
                    'lng': float(best_entry.longitude),
                    'source_entry_id': best_entry.pk,
                }

    return json.dumps(associations)



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
    log_entries = trip.log_entries.all().order_by('-timestamp').prefetch_related('tags', 'photos')

    if request.method == 'POST':
        # Handle GPX upload (multiple files)
        gpx_files = request.FILES.getlist('gpx_file')
        if gpx_files:
            for f in gpx_files:
                gpx = GPXFile(
                    trip=trip,
                    original_filename=f.name,
                    source='web',
                )
                gpx.file.save(f.name, f)
                gpx.save()
            return redirect('trip_detail', pk=pk)

        # Handle share slug regeneration
        if 'regenerate_slug' in request.POST:
            trip.regenerate_share_slug()
            return redirect('trip_detail', pk=pk)

        # Handle GPX file deletion
        delete_gpx = request.POST.get('delete_gpx')
        if delete_gpx:
            gpx = trip.gpx_files.filter(pk=delete_gpx).first()
            if gpx:
                gpx.file.delete(save=False)
                gpx.delete()
                # Re-aggregate after deletion
                from .signals import _aggregate_trip_stats
                _aggregate_trip_stats(trip)
            return redirect('trip_detail', pk=pk)

    gpx_tracks_json = _build_gpx_tracks_json(trip)
    photos_json = _build_photos_json(log_entries)
    photo_locations_json = _associate_photos_to_locations(trip, log_entries)

    return render(request, 'logbook/trip_detail_internal.html', {
        'trip': trip,
        'log_entries': log_entries,
        'gpx_tracks_json': gpx_tracks_json,
        'photos_json': photos_json,
        'photo_locations_json': photo_locations_json,
    })


@login_required
def trip_start_view(request):
    boats = Boat.objects.filter(shared_users=request.user)
    active_trip = Trip.objects.filter(
        boat__shared_users=request.user,
        is_active=True,
    ).select_related('boat').first()

    if request.method == 'POST':
        boat = get_object_or_404(Boat, pk=request.POST.get('boat'), shared_users=request.user)

        # If there's an active trip and user chose to end it
        if active_trip and 'end_active_trip' in request.POST:
            active_trip.is_active = False
            active_trip.end_date = timezone.now().date()
            active_trip.save(update_fields=['is_active', 'end_date'])

        # If there's still an active trip and user didn't confirm ending it, reject
        if active_trip and 'end_active_trip' not in request.POST:
            from django.contrib import messages
            messages.warning(request, 'You must end your current active trip before starting a new one.')
            return redirect('trip_start')

        trip = Trip.objects.create(
            boat=boat,
            title=request.POST.get('title', ''),
            start_date=timezone.now().date(),
            is_active=True,
        )
        return redirect('trip_detail', pk=trip.pk)

    return render(request, 'logbook/trip_form.html', {
        'boats': boats,
        'active_trip': active_trip,
    })


@login_required
def trip_end_view(request, pk):
    """End an active trip (POST only)."""
    trip = get_object_or_404(Trip, pk=pk, boat__shared_users=request.user)

    if request.method == 'POST' and trip.is_active:
        trip.is_active = False
        trip.end_date = timezone.now().date()
        trip.save(update_fields=['is_active', 'end_date'])

        from django.contrib import messages
        messages.success(request, f'Trip "{trip.title}" has been ended.')

    # Redirect to the 'next' URL if provided, otherwise to the referring page
    next_url = request.POST.get('next', '')
    if next_url:
        return redirect(next_url)
    return redirect('trip_detail', pk=pk)


@login_required
def log_entry_create_view(request, pk):
    """Create a manual log entry and upload photos."""
    trip = get_object_or_404(Trip, pk=pk, boat__shared_users=request.user)

    if request.method == 'POST':
        entry_text = request.POST.get('entry_text', '').strip()
        photos = request.FILES.getlist('photos')

        if entry_text or photos:
            log_entry = LogEntry.objects.create(
                trip=trip,
                boat=trip.boat,
                entry_text=entry_text,
                timestamp=timezone.now(),
            )

            for photo_file in photos:
                photo_obj = LogEntryPhoto(
                    log_entry=log_entry,
                    image=photo_file,
                    source='web',
                )
                # The post_save signal will handle EXIF extraction and resizing
                photo_obj.save()

            from django.contrib import messages
            messages.success(request, 'Log entry added successfully.')
            return redirect('trip_detail', pk=trip.pk)
        else:
            from django.contrib import messages
            messages.error(request, 'Please provide text or at least one photo.')

    return render(request, 'logbook/log_entry_form.html', {
        'trip': trip,
    })


def trip_public_view(request, share_slug):
    trip = get_object_or_404(Trip, share_slug=share_slug)
    log_entries = trip.log_entries.all().order_by('-timestamp').prefetch_related('tags', 'photos')
    gpx_tracks_json = _build_gpx_tracks_json(trip)
    photos_json = _build_photos_json(log_entries)
    photo_locations_json = _associate_photos_to_locations(trip, log_entries)

    return render(request, 'logbook/trip_detail_public.html', {
        'trip': trip,
        'log_entries': log_entries,
        'gpx_tracks_json': gpx_tracks_json,
        'photos_json': photos_json,
        'photo_locations_json': photo_locations_json,
    })


# ═══════════════════════════════════════════
# Tags
# ═══════════════════════════════════════════

@login_required
def tag_detail_view(request, tag_name):
    tag = get_object_or_404(Tag, name=tag_name.lower())
    log_entries = tag.log_entries.all().select_related(
        'trip', 'trip__boat'
    ).prefetch_related('tags', 'photos').order_by('-timestamp')

    return render(request, 'logbook/tag_detail.html', {
        'tag': tag,
        'log_entries': log_entries,
    })
