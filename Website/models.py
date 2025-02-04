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

class Plant(models.Model):
    name = models.CharField(max_length=100, unique=True)
    description = models.TextField(blank=True, null=True)
    temperature_min = models.FloatField(help_text="Minimum temperature threshold", default=10.0)
    temperature_max = models.FloatField(help_text="Maximum temperature threshold", default=35.0)
    humidity_min = models.FloatField(help_text="Minimum air humidity threshold", default=30.0)
    humidity_max = models.FloatField(help_text="Maximum air humidity threshold", default=80.0)
    soil_moisture_min = models.FloatField(help_text="Minimum soil moisture threshold", default=20.0)
    soil_moisture_max = models.FloatField(help_text="Maximum soil moisture threshold", default=70.0)

    def __str__(self):
        return self.name

class Raspberry(models.Model):
    device_id = models.CharField(max_length=100, unique=True)
    api_token = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    group = models.ForeignKey(Group, on_delete=models.SET_NULL, null=True, related_name='raspberries')
    location_description = models.TextField(blank=True, null=True)
    active = models.BooleanField(default=True)
    STATUS_CHOICES = [
        ('unassigned', 'Non Assigné'),
        ('assigned', 'Assigné'),
        ('offline', 'Hors Ligne'),
    ]
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='unassigned')

    def __str__(self):
        return f"Raspberry {self.device_id} in {self.group.name if self.group else 'No Group'}"

class SensorLocation(models.Model):
    raspberry = models.ForeignKey(Raspberry, on_delete=models.CASCADE, related_name='sensor_locations')
    location_name = models.CharField(max_length=100)  
    plant = models.ForeignKey(Plant, on_delete=models.CASCADE, related_name='sensor_locations')
    soil_moisture = models.FloatField(blank=True, null=True, help_text="Current soil moisture level")
    x_position = models.FloatField(help_text="Position X dans la serre", blank=True, null=True)
    y_position = models.FloatField(help_text="Position Y dans la serre", blank=True, null=True)

    class Meta:
        unique_together = ('raspberry', 'location_name')

    def __str__(self):
        return f"{self.location_name} ({self.plant.name})"

class SensorData(models.Model):
    sensor_location = models.ForeignKey(SensorLocation, on_delete=models.CASCADE, related_name='sensor_data')
    timestamp = models.DateTimeField()
    temperature = models.FloatField(blank=True, null=True)
    air_humidity = models.FloatField(blank=True, null=True)
    soil_moisture = models.FloatField(blank=True, null=True)
    water_level = models.FloatField(blank=True, null=True)

    def __str__(self):
        return f"Data at {self.sensor_location} on {self.timestamp}"

class Action(models.Model):
    raspberry = models.ForeignKey(Raspberry, on_delete=models.CASCADE, related_name='actions')
    timestamp = models.DateTimeField(auto_now_add=True)
    ACTION_TYPES = [
        ('ventilation', 'Ventilation'),
        ('irrigation', 'Irrigation'),
    ]
    STATUS_CHOICES = [
        ('success', 'Success'),
        ('failed', 'Failed'),
        ('pending', 'Pending'),
    ]
    action_type = models.CharField(max_length=50, choices=ACTION_TYPES)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES)

    def __str__(self):
        return f"{self.action_type} at {self.raspberry.device_id} on {self.timestamp}"

class DataPayload(models.Model):
    raspberry = models.ForeignKey(Raspberry, on_delete=models.CASCADE, related_name='data_payloads')
    timestamp = models.DateTimeField(auto_now_add=True)
    payload = models.JSONField()

    def __str__(self):
        return f"Payload from {self.raspberry.device_id} on {self.timestamp}"

class UserGroup(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='user_groups')
    group = models.ForeignKey(Group, on_delete=models.CASCADE, related_name='user_groups')

    class Meta:
        unique_together = ('user', 'group')

    def __str__(self):
        return f"{self.user.username} in {self.group.name}"
