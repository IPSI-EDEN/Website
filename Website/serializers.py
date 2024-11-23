from rest_framework import serializers
from .models import Group, Raspberry, Plant, SensorLocation, SensorData

class GroupSerializer(serializers.ModelSerializer):
    class Meta:
        model = Group
        fields = ['name', 'description']

class RaspberrySerializer(serializers.ModelSerializer):
    group = GroupSerializer()

    class Meta:
        model = Raspberry
        fields = ['device_id', 'group', 'active', 'status']

class PlantSerializer(serializers.ModelSerializer):
    class Meta:
        model = Plant
        fields = ['name', 'description', 'temperature_min', 'temperature_max',
                  'humidity_min', 'humidity_max', 'soil_moisture_min', 'soil_moisture_max']

class SensorLocationSerializer(serializers.ModelSerializer):
    raspberry = serializers.CharField()  # Utilise device_id comme identifiant
    plant = serializers.IntegerField()  # Assure que le plant est un ID numérique

    class Meta:
        model = SensorLocation
        fields = ['raspberry', 'location_name', 'plant', 'soil_moisture']

class SensorDataSerializer(serializers.ModelSerializer):
    sensor_location = SensorLocationSerializer()

    class Meta:
        model = SensorData
        fields = ['sensor_location', 'timestamp', 'temperature', 'air_humidity']

    def create(self, validated_data):
        # Extraire les données de SensorLocation
        sensor_location_data = validated_data.pop('sensor_location')

        # Récupérer les relations liées
        plant_id = sensor_location_data['plant']
        raspberry_device_id = sensor_location_data['raspberry']

        # Assurer que le Raspberry existe
        raspberry = Raspberry.objects.get(device_id=raspberry_device_id)

        # Récupérer ou créer SensorLocation
        sensor_location, _ = SensorLocation.objects.get_or_create(
            raspberry=raspberry,
            plant_id=plant_id,
            location_name=sensor_location_data['location_name'],
            defaults={'soil_moisture': sensor_location_data.get('soil_moisture')}
        )

        # Créer SensorData
        return SensorData.objects.create(
            sensor_location=sensor_location,
            **validated_data
        )
