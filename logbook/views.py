import re
import json
from django.http import HttpResponse, JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.utils import timezone
from dateutil import parser
from .models import Profile, Trip, Tag, LogEntry

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
