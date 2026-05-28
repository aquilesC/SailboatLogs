import uuid
from django.db import migrations


def populate_share_slugs(apps, schema_editor):
    """Give every existing Trip a unique random share_slug."""
    Trip = apps.get_model('logbook', 'Trip')
    for trip in Trip.objects.all():
        trip.share_slug = uuid.uuid4().hex[:12]
        trip.save(update_fields=['share_slug'])


class Migration(migrations.Migration):

    dependencies = [
        ('logbook', '0003_boat_boat_model_boat_homeport_boat_mmsi_registration_and_more'),
    ]

    operations = [
        migrations.RunPython(populate_share_slugs, migrations.RunPython.noop),
    ]
