from django.db import models
from django.contrib.auth.models import User
import uuid

DEFAULT_GROUP_NAME = "Non Assigné"

class Group(models.Model):
    name = models.CharField(max_length=100, unique=True)
    logo = models.ImageField(upload_to='group_logos', blank=True, null=True)
    description = models.TextField(blank=True, null=True)
    is_default = models.BooleanField(default=False)

    def __str__(self):
        return self.name

class UserGroup(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='user_groups')
    group = models.ForeignKey(Group, on_delete=models.CASCADE, related_name='user_groups')

    class Meta:
        unique_together = ('user', 'group')

    def __str__(self):
        return f"{self.user.username} in {self.group.name}"

class Raspberry(models.Model):
    device_id = models.CharField(max_length=100, unique=True)
    api_token = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    group = models.ForeignKey(Group, on_delete=models.SET_NULL, null=True, related_name='raspberries')
    location_description = models.TextField(blank=True, null=True)
    active = models.BooleanField(default=True)
    status = models.CharField(max_length=50, default='unassigned')
    pump_state = models.BooleanField(default=False)
    fan_state = models.BooleanField(default=False)

    def __str__(self):
        return f"Raspberry: {self.device_id}"

class Plant(models.Model):
    name = models.CharField(max_length=200)
    description = models.TextField(blank=True, null=True)
    temperature_min = models.FloatField(blank=True, null=True)
    temperature_max = models.FloatField(blank=True, null=True)
    humidity_min = models.FloatField(blank=True, null=True)
    humidity_max = models.FloatField(blank=True, null=True)
    soil_moisture_min = models.FloatField(blank=True, null=True)
    soil_moisture_max = models.FloatField(blank=True, null=True)

    def __str__(self):
        return self.name

class SensorLocation(models.Model):
    raspberry = models.ForeignKey(Raspberry, on_delete=models.CASCADE, related_name='sensor_locations')
    location_name = models.CharField(max_length=100)  
    plant = models.ForeignKey(Plant, on_delete=models.CASCADE, related_name='sensor_locations', blank=True, null=True)
    soil_moisture = models.FloatField(blank=True, null=True, help_text="Current soil moisture level")
    x_position = models.FloatField(help_text="Position X dans la serre", blank=True, null=True)
    y_position = models.FloatField(help_text="Position Y dans la serre", blank=True, null=True)

    class Meta:
        unique_together = ('raspberry', 'location_name')

    def __str__(self):
        plant_name = self.plant.name if self.plant else "Pas de plante assignée"
        return f"{self.location_name} ({plant_name})"

class SensorData(models.Model):
    sensor_location = models.ForeignKey(SensorLocation, on_delete=models.CASCADE, related_name='sensor_data')
    timestamp = models.DateTimeField()
    temperature = models.FloatField(blank=True, null=True)
    air_humidity = models.FloatField(blank=True, null=True)
    soil_moisture = models.JSONField(blank=True, null=True, help_text="Ensemble des valeurs d'humidité du sol")
    water_level = models.FloatField(blank=True, null=True)

    def __str__(self):
        return f"Data at {self.sensor_location} on {self.timestamp}"
