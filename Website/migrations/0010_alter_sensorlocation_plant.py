# Generated by Django 4.2.18 on 2025-04-01 22:00

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('Website', '0009_alter_plant_humidity_max_alter_plant_humidity_min_and_more'),
    ]

    operations = [
        migrations.AlterField(
            model_name='sensorlocation',
            name='plant',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='sensor_locations', to='Website.plant'),
        ),
    ]
