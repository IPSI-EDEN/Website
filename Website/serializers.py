from rest_framework import serializers
from .models import Group, Raspberry, Plant, SensorLocation, SensorData

class GroupSerializer(serializers.ModelSerializer):
    class Meta:
        model = Group
        fields = ['id', 'name', 'description']

class RaspberrySerializer(serializers.ModelSerializer):
    group = GroupSerializer(read_only=True)
    class Meta:
        model = Raspberry
        fields = ['id', 'device_id', 'group', 'active', 'status', 'location_description']

class PlantSerializer(serializers.ModelSerializer):
    class Meta:
        model = Plant
        fields = ['id', 'name', 'description', 'temperature_min', 'temperature_max', 'humidity_min', 'humidity_max', 'soil_moisture_min', 'soil_moisture_max']

class SensorLocationSerializer(serializers.ModelSerializer):
    raspberry = serializers.CharField(source='raspberry.device_id', read_only=True)
    plant = PlantSerializer(read_only=True)

    class Meta:
        model = SensorLocation
        fields = ['raspberry', 'location_name', 'plant', 'soil_moisture']

class SensorDataSerializer(serializers.ModelSerializer):
    sensor_location = SensorLocationSerializer(read_only=True)

    class Meta:
        model = SensorData
        fields = ['sensor_location', 'timestamp', 'temperature', 'air_humidity', 'soil_moisture']

class IncomingLocationSerializer(serializers.Serializer):
    location_name = serializers.CharField()
    soil_moisture = serializers.FloatField(
        allow_null=True,  
        required=False
    )

class IncomingDataSerializer(serializers.Serializer):
    timestamp = serializers.DateTimeField()
    raspberry = serializers.DictField()
    locations = IncomingLocationSerializer(many=True)
    temperature = serializers.FloatField()
    air_humidity = serializers.FloatField()
