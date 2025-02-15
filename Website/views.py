from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, logout
from django.contrib.auth.decorators import login_required, user_passes_test
from django.views.decorators.http import require_POST
from rest_framework.permissions import IsAuthenticated, AllowAny
from django.contrib.auth.forms import AuthenticationForm
from django.views.decorators.csrf import csrf_exempt
from django.contrib import messages
from django.utils.timezone import now, timedelta, datetime
from django.db.models import Avg, Max, Min
from django.db.models.functions import TruncHour
from django.conf import settings
from cryptography.hazmat.primitives.ciphers.aead import AESGCM

import base64
import json
import os

import logging

from .models import SensorData, SensorLocation, Group
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework import status
from .serializers import IncomingDataSerializer, SensorDataSerializer
from django.db import transaction

from Website.models import *
from Website.forms import *


logger = logging.getLogger('Website')

def handler404(request, exception):
    request_id = str(uuid.uuid4())
    logger.warning(f"[{request_id}] 404 Not Found: URL={request.path}, User={request.user if request.user.is_authenticated else 'Anonymous'}")
    return redirect('login')


def login_view(request):
    request_id = str(uuid.uuid4())
    logger.debug(f"[{request_id}] Starting login_view. Method={request.method}, User Authenticated={request.user.is_authenticated}")

    if request.user.is_authenticated:
        logger.info(f"[{request_id}] User {request.user} already authenticated, redirecting to home.")
        return redirect('home')
    
    if request.method == 'POST':
        logger.debug(f"[{request_id}] Processing POST data for login: {request.POST}")
        form = AuthenticationForm(request, data=request.POST)
        if form.is_valid():
            user = form.get_user()
            login(request, user)
            logger.info(f"[{request_id}] User {user} logged in successfully.")
            return redirect('home')
        else:
            logger.warning(f"[{request_id}] Login failed for POST data. Errors={form.errors}")
            messages.error(request, "Nom d'utilisateur ou mot de passe incorrect.")
    else:
        logger.debug(f"[{request_id}] Rendering empty login form.")
        form = AuthenticationForm()
    
    return render(request, 'registration/login.html', {'form': form})


def logout_view(request):
    request_id = str(uuid.uuid4())
    logger.info(f"[{request_id}] User {request.user} logging out.")
    logout(request)
    messages.success(request, "Vous avez été déconnecté avec succès.")
    return redirect('login')

DEFAULT_GROUP_NAME = "Non Assigné"

def is_admin(user):
    return user.is_superuser or user.is_staff

@login_required(login_url='login')
def home_page(request):
    request_id = str(uuid.uuid4())
    logger.debug(f"[{request_id}] Starting home_page. User={request.user}, Method={request.method}")
    user = request.user

    try:
        # Admin or staff user
        if user.is_superuser or user.is_staff:
            logger.debug(f"[{request_id}] {user} is admin/staff. Fetching all active raspberries.")
            raspberries = Raspberry.objects.filter(active=True).annotate(
                last_data=Max('sensor_locations__sensor_data__timestamp')
            )
        else:
            logger.debug(f"[{request_id}] {user} is standard user. Fetching raspberries by group.")
            user_groups = Group.objects.filter(user_groups__user=user)
            if not user_groups.exists():
                logger.warning(f"[{request_id}] {user} has no associated groups.")
                return render(request, 'home.html', {
                    'raspberries': [],
                    'error': "Vous n'êtes associé à aucun groupe.",
                })
            raspberries = Raspberry.objects.filter(group__in=user_groups, active=True).annotate(
                last_data=Max('sensor_locations__sensor_data__timestamp')
            )

        current_time = now()
        raspberry_status = []
        for raspberry in raspberries:
            if raspberry.last_data and raspberry.last_data >= current_time - timedelta(hours=1):
                status = "En ligne"
            else:
                status = "Hors ligne"
            raspberry_status.append({
                'id': raspberry.id,
                'device_id': raspberry.device_id,
                'group': raspberry.group.name if raspberry.group else "Non Assigné",
                'location': raspberry.location_description or "Non spécifié",
                'status': status,
                'last_data': raspberry.last_data.strftime('%Y-%m-%d %H:%M:%S') if raspberry.last_data else "Aucune donnée",
            })

        logger.info(f"[{request_id}] Rendered home_page for User={user} with {len(raspberry_status)} raspberries.")
        return render(request, 'home.html', {
            'raspberry_status': raspberry_status,
        })
    except Exception as e:
        logger.exception(f"[{request_id}] Error rendering home_page for User={user}: {e}")
        return render(request, 'home.html', {
            'raspberries': [],
            'error': "Une erreur s'est produite lors de la récupération des données.",
        })

@login_required(login_url='login')
def threshold(request, id):
    raspberry = get_object_or_404(Raspberry, id=id)
    sensor_locations = SensorLocation.objects.filter(raspberry=raspberry)
    plants = Plant.objects.all()

    if request.method == 'POST':
        # Traitement des données du formulaire pour mettre à jour les seuils des plantes
        forms = []
        for plant in plants:
            form = PlantThresholdForm(request.POST, instance=plant, prefix=str(plant.id))
            if form.is_valid():
                form.save()
            forms.append(form)
        # Rediriger ou afficher un message de succès
        return redirect('threshold', id=raspberry.id)
    else:
        # Préparation des formulaires pour chaque plante
        forms = []
        for plant in plants:
            form = PlantThresholdForm(instance=plant, prefix=str(plant.id))
            forms.append(form)
        
        # Préparation des données des emplacements des capteurs
        sensor_locations_data = []
        for location in sensor_locations:
            sensor_locations_data.append({
                'location_name': location.location_name,
                'plant': {
                    'name': location.plant.name,
                },
                'soil_moisture': location.soil_moisture,
                'x_position': location.x_position,
                'y_position': location.y_position,
            })

        context = {
            'raspberry': raspberry,
            'sensor_locations': sensor_locations,
            'forms': forms,
            'sensor_locations_json': json.dumps(sensor_locations_data),
        }
        return render(request, 'threshold.html', context)

@login_required(login_url='login')
def graph_page(request, id):
    raspberry = get_object_or_404(Raspberry, id=id)
    sensor_locations = SensorLocation.objects.filter(raspberry=raspberry)

    selected_time_range = int(request.GET.get('time_range', 24))
    end_time = now()
    start_time = end_time - timedelta(hours=selected_time_range)

    sensor_data = SensorData.objects.filter(
        sensor_location__in=sensor_locations,
        timestamp__gte=start_time
    ).order_by('timestamp')

    if not sensor_data.exists():
        time_labels = []
        temperature_data = []
        humidity_data = []
        soil_moisture_data = []
        water_level_data = []
        current_temperature = 0
        current_humidity = 0
        current_soil_moisture = 0
        current_water_level = 0
    else:
        MAX_POINTS = 2000
        total_points = sensor_data.count()
        if total_points > MAX_POINTS:
            step = total_points // MAX_POINTS
            sensor_data = sensor_data[::step]

        time_labels = [data.timestamp.strftime('%Y-%m-%d %H:%M:%S') for data in sensor_data]
        temperature_data = [data.temperature for data in sensor_data]
        humidity_data = [data.air_humidity for data in sensor_data]
        soil_moisture_data = [data.soil_moisture for data in sensor_data]

        water_level_data = []
        if hasattr(SensorData, 'water_level'):
            water_level_data = [data.water_level for data in sensor_data]

        latest_data = sensor_data.last()
        current_temperature = latest_data.temperature if latest_data.temperature is not None else 0
        current_humidity = latest_data.air_humidity if latest_data.air_humidity is not None else 0
        current_soil_moisture = latest_data.soil_moisture if latest_data.soil_moisture is not None else 0
        current_water_level = 0
        if hasattr(latest_data, 'water_level') and latest_data.water_level is not None:
            current_water_level = latest_data.water_level

    gauges = [
        {
            'id': 'temperatureGauge',
            'title': 'Température actuelle',
            'json': json.dumps({
                'data': [{
                    'type': 'indicator',
                    'mode': 'gauge+number',
                    'value': current_temperature,
                    'gauge': {
                        'axis': {'range': [0, 50]},
                        'bar': {'color': 'blue'},
                        'borderwidth': 2,
                        'bordercolor': '#888'
                    }
                }],
                'layout': {
                    'title': 'Température (°C)',
                    'paper_bgcolor': 'white',
                    'plot_bgcolor': 'white',
                    'font': {'color': '#333'}
                }
            })
        },
        {
            'id': 'humidityGauge',
            'title': 'Humidité actuelle',
            'json': json.dumps({
                'data': [{
                    'type': 'indicator',
                    'mode': 'gauge+number',
                    'value': current_humidity,
                    'gauge': {
                        'axis': {'range': [0, 100]},
                        'bar': {'color': 'green'},
                        'borderwidth': 2,
                        'bordercolor': '#888'
                    }
                }],
                'layout': {
                    'title': 'Humidité (%)',
                    'paper_bgcolor': 'white',
                    'plot_bgcolor': 'white',
                    'font': {'color': '#333'}
                }
            })
        },
        {
            'id': 'soilMoistureGauge',
            'title': 'Humidité du sol',
            'json': json.dumps({
                'data': [{
                    'type': 'indicator',
                    'mode': 'gauge+number',
                    'value': current_soil_moisture,
                    'gauge': {
                        'axis': {'range': [0, 100]},
                        'bar': {'color': '#8B4513'},
                        'borderwidth': 2,
                        'bordercolor': '#888'
                    }
                }],
                'layout': {
                    'title': 'Humidité du sol (%)',
                    'paper_bgcolor': 'white',
                    'plot_bgcolor': 'white',
                    'font': {'color': '#333'}
                }
            })
        },
        {
            'id': 'waterLevelGauge',
            'title': 'Niveau d’eau',
            'json': json.dumps({
                'data': [{
                    'type': 'indicator',
                    'mode': 'gauge+number',
                    'value': current_water_level,
                    'gauge': {
                        'axis': {'range': [0, 100]},
                        'bar': {'color': 'blue'},
                        'borderwidth': 2,
                        'bordercolor': '#888'
                    }
                }],
                'layout': {
                    'title': 'Niveau d’eau (%)',
                    'paper_bgcolor': 'white',
                    'plot_bgcolor': 'white',
                    'font': {'color': '#333'}
                }
            })
        },
    ]

    charts = [
        {
            'id': 'temperatureChart',
            'title': 'Évolution de la température',
            'json': json.dumps({
                'data': [{
                    'x': time_labels,
                    'y': temperature_data,
                    'mode': 'lines+markers',
                    'type': 'scatter',
                    'line': {'color': 'red'},
                    'marker': {'color': 'red'}
                }],
                'layout': {
                    'title': 'Température (°C)',
                    'paper_bgcolor': '#f9f9f9',
                    'plot_bgcolor': '#f9f9f9',
                    'font': {'color': '#333'},
                    'xaxis': {'title': 'Temps'},
                    'yaxis': {'title': '°C'},
                }
            })
        },
        {
            'id': 'humidityChart',
            'title': 'Évolution de l\'humidité de l’air',
            'json': json.dumps({
                'data': [{
                    'x': time_labels,
                    'y': humidity_data,
                    'mode': 'lines+markers',
                    'type': 'scatter',
                    'line': {'color': 'blue'},
                    'marker': {'color': 'blue'}
                }],
                'layout': {
                    'title': 'Humidité (%)',
                    'paper_bgcolor': '#f9f9f9',
                    'plot_bgcolor': '#f9f9f9',
                    'font': {'color': '#333'},
                    'xaxis': {'title': 'Temps'},
                    'yaxis': {'title': '%'}
                }
            })
        },
        {
            'id': 'soilMoistureChart',
            'title': 'Évolution de l’humidité du sol',
            'json': json.dumps({
                'data': [{
                    'x': time_labels,
                    'y': soil_moisture_data,
                    'mode': 'lines+markers',
                    'type': 'scatter',
                    'line': {'color': '#8B4513'},
                    'marker': {'color': '#8B4513'}
                }],
                'layout': {
                    'title': 'Humidité du sol (%)',
                    'paper_bgcolor': '#f9f9f9',
                    'plot_bgcolor': '#f9f9f9',
                    'font': {'color': '#333'},
                    'xaxis': {'title': 'Temps'},
                    'yaxis': {'title': '%'}
                }
            })
        },
        {
            'id': 'waterLevelChart',
            'title': 'Évolution du niveau d’eau',
            'json': json.dumps({
                'data': [{
                    'x': time_labels,
                    'y': water_level_data,
                    'mode': 'lines+markers',
                    'type': 'scatter',
                    'line': {'color': 'dodgerblue'},
                    'marker': {'color': 'dodgerblue'}
                }],
                'layout': {
                    'title': 'Niveau d’eau (%)',
                    'paper_bgcolor': '#f9f9f9',
                    'plot_bgcolor': '#f9f9f9',
                    'font': {'color': '#333'},
                    'xaxis': {'title': 'Temps'},
                    'yaxis': {'title': '%'}
                }
            })
        },
    ]

    return render(request, 'graph.html', {
        'raspberry': raspberry,
        'gauges': gauges,
        'charts': charts,
        'selected_time_range': selected_time_range
    })


@user_passes_test(is_admin)
@login_required(login_url='login')
def raspberry_update(request, id):
    raspberry = get_object_or_404(Raspberry, id=id)

    if request.method == 'POST':
        form = RaspberryForm(request.POST, instance=raspberry)
        if form.is_valid():
            form.save()
            return redirect('home')
    else:
        form = RaspberryForm(instance=raspberry)

    return render(request, 'raspberry_form.html', {
        'form': form,
        'raspberry': raspberry,
        'action': 'Modifier'
    })

@user_passes_test(is_admin)
@login_required(login_url='login')
def raspberry_delete(request, id):
    raspberry = get_object_or_404(Raspberry, id=id)
    raspberry.delete()
    return redirect('home')
    

@csrf_exempt
@api_view(['POST'])
@permission_classes([AllowAny])
def receive_sensor_data(request):
    request_id = str(uuid.uuid4())
    logger.debug(f"[{request_id}] Starting receive_sensor_data. Method={request.method}")

    try:
        encrypted_data_b64 = request.data.get('encrypted')
        logger.info(f"[{request_id}] Received encrypted data payload.")

        if not encrypted_data_b64:
            logger.warning(f"[{request_id}] Missing encrypted data in request.")
            return Response({"error": "Données chiffrées manquantes."}, status=status.HTTP_400_BAD_REQUEST)

        # Décryptage des données
        encrypted_data = base64.b64decode(encrypted_data_b64)
        nonce = encrypted_data[:12]
        ciphertext = encrypted_data[12:]

        aesgcm = AESGCM(settings.AES_SECRET_KEY)
        decrypted_data = aesgcm.decrypt(nonce, ciphertext, None)
        data = json.loads(decrypted_data.decode('utf-8'))
        logger.debug(f"[{request_id}] Decrypted data: {data}")

        # Validation des données
        serializer = IncomingDataSerializer(data=data)
        if not serializer.is_valid():
            logger.error(f"[{request_id}] Validation errors: {serializer.errors}")
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        validated_data = serializer.validated_data

        # Conversion du timestamp reçu (en ISO, avec "Z" indiquant UTC) en datetime
        timestamp = datetime.fromisoformat(validated_data['timestamp'].replace("Z", "+00:00"))
        # Le timestamp est maintenant un objet datetime en UTC.

        raspberry_data = validated_data['raspberry']
        device_name = raspberry_data.get('device_name')
        locations = validated_data['locations']
        temperature = validated_data['temperature']
        air_humidity = validated_data['air_humidity']

        with transaction.atomic():
            # Récupérer ou créer le groupe par défaut
            group, _ = Group.objects.get_or_create(
                name=DEFAULT_GROUP_NAME,
                defaults={'description': "Default group for unassigned Raspberries."}
            )

            # Récupérer ou créer le Raspberry
            raspberry, created_raspberry = Raspberry.objects.get_or_create(
                device_id=device_name,
                defaults={
                    'group': group,
                    'active': True,
                    'status': 'unassigned'
                }
            )
            if created_raspberry:
                logger.info(f"[{request_id}] Created new Raspberry device_id={raspberry.device_id}")

            # Pour chaque emplacement, récupérer/créer le Plant et le SensorLocation, puis enregistrer les données
            for loc in locations:
                location_name = loc['location_name']
                loc_soil_moisture = loc['soil_moisture']

                plant, _ = Plant.objects.get_or_create(
                    name=location_name,
                    defaults={
                        'description': f'Plant for {location_name}',
                        'temperature_min': 10.0,
                        'temperature_max': 35.0,
                        'humidity_min': 30.0,
                        'humidity_max': 80.0,
                        'soil_moisture_min': 20.0,
                        'soil_moisture_max': 70.0,
                    }
                )

                sensor_location, _ = SensorLocation.objects.get_or_create(
                    raspberry=raspberry,
                    location_name=location_name,
                    defaults={'plant': plant}
                )
                sensor_location.soil_moisture = loc_soil_moisture
                sensor_location.save()

                SensorData.objects.create(
                    sensor_location=sensor_location,
                    timestamp=timestamp,
                    temperature=temperature,
                    air_humidity=air_humidity,
                    soil_moisture=loc_soil_moisture
                )

        logger.info(f"[{request_id}] Sensor data saved successfully.")
        raspberry_data = {
            'id': raspberry.id,
            'device_id': raspberry.device_id,
            'group': raspberry.group.name if raspberry.group else "Non Assigné",
            'active': raspberry.active,
            'pump': True,
            'fan': True,
        }

        success_message = {
            "message": "Données enregistrées avec succès.",
            "raspberry": raspberry_data
        }

        nonce = os.urandom(12)
        data_bytes = json.dumps(success_message).encode('utf-8')
        ciphertext = aesgcm.encrypt(nonce, data_bytes, None)
        encrypted_data = nonce + ciphertext
        encrypted_data_b64 = base64.b64encode(encrypted_data).decode('utf-8')

        logger.debug(f"[{request_id}] Sending encrypted response back.")
        return Response({"encrypted": encrypted_data_b64}, status=status.HTTP_201_CREATED)

    except Exception as e:
        logger.exception(f"[{request_id}] Error processing sensor data: {e}")
        return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)
    

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_latest_sensor_data(request, raspberry_id):
    request_id = str(uuid.uuid4())
    logger.debug(f"[{request_id}] Starting get_latest_sensor_data. User={request.user}, RaspberryID={raspberry_id}")

    try:
        raspberry = get_object_or_404(Raspberry, id=raspberry_id)
        logger.info(f"[{request_id}] Accessing data for Raspberry {raspberry_id}, User={request.user}")

        if not request.user.is_superuser and not request.user.is_staff:
            user_groups = Group.objects.filter(
                raspberries=raspberry,
                user_groups__user=request.user
            )
            if not user_groups.exists():
                logger.warning(f"[{request_id}] User {request.user} does not have access to Raspberry {raspberry_id}.")
                return Response({"error": "Accès non autorisé."}, status=status.HTTP_403_FORBIDDEN)

        time_range = request.GET.get('time_range', '24')
        logger.debug(f"[{request_id}] time_range={time_range}")

        try:
            time_range = int(time_range)
        except ValueError:
            logger.error(f"[{request_id}] Invalid time_range: {time_range}")
            return Response({"error": "Valeur de time_range invalide."}, status=status.HTTP_400_BAD_REQUEST)

        end_time = now()
        start_time = end_time - timedelta(hours=time_range)

        sensor_locations = SensorLocation.objects.filter(raspberry=raspberry)
        sensor_data = SensorData.objects.filter(
            sensor_location__in=sensor_locations,
            timestamp__gte=start_time
        ).order_by('timestamp')

        serializer = SensorDataSerializer(sensor_data, many=True)
        logger.info(f"[{request_id}] Returning {sensor_data.count()} records of SensorData for Raspberry {raspberry_id} to User={request.user}.")
        return Response(serializer.data, status=status.HTTP_200_OK)

    except Exception as e:
        logger.exception(f"[{request_id}] Error in get_latest_sensor_data for Raspberry={raspberry_id}: {e}")
        return Response({"error": "Erreur interne du serveur."}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)