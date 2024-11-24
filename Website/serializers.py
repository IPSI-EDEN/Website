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

class SensorLocationWriteSerializer(serializers.ModelSerializer):
    raspberry = serializers.CharField()  
    plant = serializers.IntegerField()

    class Meta:
        model = SensorLocation
        fields = ['raspberry', 'location_name', 'plant', 'soil_moisture']

class SensorDataWriteSerializer(serializers.ModelSerializer):
    sensor_location = SensorLocationWriteSerializer()

    class Meta:
        model = SensorData
        fields = ['sensor_location', 'timestamp', 'temperature', 'air_humidity']

    def create(self, validated_data):
        sensor_location_data = validated_data.pop('sensor_location')
        plant_id = sensor_location_data['plant']
        raspberry_device_id = sensor_location_data['raspberry']

        raspberry = Raspberry.objects.get(device_id=raspberry_device_id)

        sensor_location, _ = SensorLocation.objects.get_or_create(
            raspberry=raspberry,
            plant_id=plant_id,
            location_name=sensor_location_data['location_name'],
            defaults={'soil_moisture': sensor_location_data.get('soil_moisture')}
        )

        return SensorData.objects.create(
            sensor_location=sensor_location,
            **validated_data
        )

class SensorLocationReadSerializer(serializers.ModelSerializer):
    raspberry = serializers.CharField(source='raspberry.device_id', read_only=True)
    plant = PlantSerializer(read_only=True)

    class Meta:
        model = SensorLocation
        fields = ['raspberry', 'location_name', 'plant', 'soil_moisture']

class SensorDataReadSerializer(serializers.ModelSerializer):
    sensor_location = SensorLocationReadSerializer(read_only=True)

    class Meta:
        model = SensorData
        fields = ['sensor_location', 'timestamp', 'temperature', 'air_humidity']
