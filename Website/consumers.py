import json
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from .models import Raspberry, Group, SensorData, SensorLocation, DEFAULT_GROUP_NAME
from django.conf import settings
import base64

class SensorDataConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        await self.accept()

    async def disconnect(self, close_code):
        pass

    async def receive(self, text_data):
        try:
            data = json.loads(text_data)
            device_id = data.get('device_id')
            api_token = data.get('api_token')  # Authentification par token
            encrypted_payload_b64 = data.get('payload')

            if not device_id or not api_token or not encrypted_payload_b64:
                await self.send(json.dumps({"error": "Champs requis manquants."}))
                return

            # Authentifier le Raspberry Pi
            raspberry = await self.get_raspberry(device_id, api_token)
            if not raspberry:
                await self.send(json.dumps({"error": "Raspberry inconnu ou token invalide."}))
                return

            # Déchiffrer le payload (si nécessaire)
            # Puisque vous ne souhaitez pas gérer les clés manuellement, assurez-vous que les données sont sécurisées via TLS

            # Décoder le payload de base64
            try:
                encrypted_payload = base64.b64decode(encrypted_payload_b64)
                # Si vous avez besoin de déchiffrer, implémentez ici une méthode de déchiffrement
                # Par exemple, utiliser une clé partagée ou d'autres méthodes sécurisées
                # Pour simplifier, supposons que les données ne sont pas chiffrées ici
                payload_data = json.loads(encrypted_payload.decode('utf-8'))
            except Exception as e:
                await self.send(json.dumps({"error": f"Erreur de décodage: {str(e)}"}))
                return

            # Extraire les données de capteur
            sensor_location_id = payload_data.get("sensor_location_id")
            temperature = payload_data.get("temperature")
            air_humidity = payload_data.get("air_humidity")
            soil_moisture = payload_data.get("soil_moisture")

            if not all([sensor_location_id, temperature, air_humidity, soil_moisture]):
                await self.send(json.dumps({"error": "Données de capteur incomplètes."}))
                return

            # Vérifier si SensorLocation existe
            sensor_location = await self.get_sensor_location(sensor_location_id, raspberry)
            if not sensor_location:
                await self.send(json.dumps({"error": "Emplacement du capteur invalide."}))
                return

            # Créer les données de capteur
            await self.create_sensor_data(sensor_location, temperature, air_humidity, soil_moisture)

            await self.send(json.dumps({"message": "Données reçues avec succès."}))

        except json.JSONDecodeError:
            await self.send(json.dumps({"error": "Format JSON invalide."}))
        except Exception as e:
            await self.send(json.dumps({"error": f"Erreur serveur: {str(e)}"}))

    @database_sync_to_async
    def get_raspberry(self, device_id, api_token):
        try:
            return Raspberry.objects.get(device_id=device_id, api_token=api_token)
        except Raspberry.DoesNotExist:
            return None

    @database_sync_to_async
    def get_sensor_location(self, sensor_location_id, raspberry):
        try:
            return SensorLocation.objects.get(id=sensor_location_id, raspberry=raspberry)
        except SensorLocation.DoesNotExist:
            return None

    @database_sync_to_async
    def create_sensor_data(self, sensor_location, temperature, air_humidity, soil_moisture):
        return SensorData.objects.create(
            sensor_location=sensor_location,
            temperature=temperature,
            air_humidity=air_humidity,
            soil_moisture=soil_moisture
        )
