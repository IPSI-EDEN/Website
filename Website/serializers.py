from rest_framework import serializers
from .models import SensorData

class SensorDataSerializer(serializers.ModelSerializer):
    class Meta:
        model = SensorData
        fields = ['sensor_location', 'timestamp', 'temperature', 'air_humidity', 'soil_moisture']
