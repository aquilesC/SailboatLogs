from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('logbook', '0004_populate_share_slugs'),
    ]

    operations = [
        migrations.AlterField(
            model_name='trip',
            name='share_slug',
            field=models.SlugField(blank=True, help_text='Randomized slug for public sharing links', unique=True),
        ),
    ]
