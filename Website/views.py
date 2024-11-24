from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, logout
from django.contrib.auth.decorators import login_required, user_passes_test
from django.views.decorators.http import require_POST
from rest_framework.permissions import IsAuthenticated
from django.contrib.auth.forms import AuthenticationForm
from django.contrib import messages
from django.utils.timezone import now, timedelta
from django.db.models import Avg, Max
from django.db.models.functions import TruncHour
from django.conf import settings
from cryptography.hazmat.primitives.ciphers.aead import AESGCM

import base64
import json

import logging

from .models import SensorData, SensorLocation, Group
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework import status
from .serializers import SensorDataWriteSerializer, SensorDataReadSerializer
from django.db import transaction

from Website.models import *
from Website.forms import *


logger = logging.getLogger(__name__)

def handler404(request, exception):
    return redirect('login')

def login_view(request):
    if request.user.is_authenticated:
        return redirect('home')
    
    if request.method == 'POST':
        form = AuthenticationForm(request, data=request.POST)
        if form.is_valid():
            user = form.get_user()
            login(request, user)
            return redirect('home')
        else:
            messages.error(request, "Nom d'utilisateur ou mot de passe incorrect.")
    else:
        form = AuthenticationForm()
    
    return render(request, 'registration/login.html', {'form': form})

def logout_view(request):
    logout(request)
    messages.success(request, "Vous avez été déconnecté avec succès.")
    return redirect('login')

DEFAULT_GROUP_NAME = "Non Assigné"

def is_admin(user):
    return user.is_superuser or user.is_staff

@login_required(login_url='login')
def home_page(request):
    user = request.user

    # Vérification des permissions : superutilisateur ou staff
    if user.is_superuser or user.is_staff:
        raspberries = Raspberry.objects.filter(active=True).annotate(
            last_data=Max('sensor_locations__sensor_data__timestamp')
        )
    else:
        user_groups = Group.objects.filter(user_groups__user=user)
        if not user_groups.exists():
            return render(request, 'home.html', {
                'raspberries': [],
                'error': "Vous n'êtes associé à aucun groupe.",
            })
        raspberries = Raspberry.objects.filter(group__in=user_groups, active=True).annotate(
            last_data=Max('sensor_locations__sensor_data__timestamp')
        )

    # Calcul du statut "en ligne" ou "hors ligne" (si les données datent de moins d'une heure)
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

    return render(request, 'home.html', {
        'raspberry_status': raspberry_status,
    })

@login_required(login_url='login')
def graph_page(request, id):
    # Récupérer le Raspberry
    raspberry = get_object_or_404(Raspberry, id=id)
    sensor_locations = SensorLocation.objects.filter(raspberry=raspberry)

    # Récupérer la plage de temps ou définir 24h par défaut
    selected_time_range = int(request.GET.get('time_range', 24))
    end_time = now()
    start_time = end_time - timedelta(hours=selected_time_range)

    # Récupérer toutes les données dans l'intervalle de temps
    sensor_data = SensorData.objects.filter(
        sensor_location__in=sensor_locations,
        timestamp__gte=start_time
    ).order_by('timestamp')

    # Préparer les données pour les graphiques
    time_labels = [data.timestamp.strftime('%Y-%m-%d %H:%M:%S') for data in sensor_data]
    temperature_data = [data.temperature for data in sensor_data]
    humidity_data = [data.air_humidity for data in sensor_data]

    latest_data = sensor_data.last()

    current_temperature = latest_data.temperature if latest_data else 0
    current_humidity = latest_data.air_humidity if latest_data else 0

    gauges = [
        {
            'id': 'temperatureGauge',
            'title': 'Température actuelle',
            'json': json.dumps({
                'data': [{
                    'type': 'indicator',
                    'mode': 'gauge+number',
                    'value': current_temperature,
                    'gauge': {'axis': {'range': [0, 50]}, 'bar': {'color': 'blue'}}
                }],
                'layout': {'title': 'Température (°C)'}
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
                    'gauge': {'axis': {'range': [0, 100]}, 'bar': {'color': 'green'}}
                }],
                'layout': {'title': 'Humidité (%)'}
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
                    'type': 'scatter'
                }],
                'layout': {
                    'title': 'Température (°C)',
                    'xaxis': {'title': 'Temps'},
                    'yaxis': {'title': 'Température (°C)'}
                }
            })
        },
        {
            'id': 'humidityChart',
            'title': 'Évolution de l\'humidité',
            'json': json.dumps({
                'data': [{
                    'x': time_labels,
                    'y': humidity_data,
                    'mode': 'lines+markers',
                    'type': 'scatter'
                }],
                'layout': {
                    'title': 'Humidité (%)',
                    'xaxis': {'title': 'Temps'},
                    'yaxis': {'title': 'Humidité (%)'}
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
    

@require_POST
@api_view(['POST'])
def receive_sensor_data(request):
    try:
        # Récupérer les données chiffrées
        encrypted_data_b64 = request.data.get('encrypted_data')
        if not encrypted_data_b64:
            return Response({"error": "Données chiffrées manquantes."}, status=status.HTTP_400_BAD_REQUEST)

        # Décoder les données de base64
        encrypted_data = base64.b64decode(encrypted_data_b64)

        # Extraire le nonce (12 octets pour AES-GCM) et le ciphertext
        nonce = encrypted_data[:12]
        ciphertext = encrypted_data[12:]

        # Déchiffrer les données
        aesgcm = AESGCM(settings.AES_SECRET_KEY)
        decrypted_data = aesgcm.decrypt(nonce, ciphertext, None)

        data = json.loads(decrypted_data.decode('utf-8'))

        with transaction.atomic():
            group_data = data['sensor_location']['raspberry']['group']
            group, _ = Group.objects.get_or_create(
                name=group_data['name'],
                defaults={'description': group_data.get('description', '')}
            )
            data['sensor_location']['raspberry']['group'] = group.id 

            raspberry_data = data['sensor_location']['raspberry']
            raspberry, _ = Raspberry.objects.get_or_create(
                device_id=raspberry_data['device_id'],
                defaults={
                    'group': group,
                    'active': raspberry_data.get('active', True),
                    'status': raspberry_data.get('status', 'unassigned')
                }
            )
            data['sensor_location']['raspberry'] = raspberry.device_id 

            plant_data = data['sensor_location']['plant']
            plant, _ = Plant.objects.get_or_create(
                name=plant_data['name'],
                defaults={
                    'description': plant_data.get('description', ''),
                    'temperature_min': plant_data.get('temperature_min'),
                    'temperature_max': plant_data.get('temperature_max'),
                    'humidity_min': plant_data.get('humidity_min'),
                    'humidity_max': plant_data.get('humidity_max'),
                    'soil_moisture_min': plant_data.get('soil_moisture_min'),
                    'soil_moisture_max': plant_data.get('soil_moisture_max'),
                }
            )
            data['sensor_location']['plant'] = plant.id 
        # Valider et enregistrer les données
        serializer = SensorDataWriteSerializer(data=data)
        if serializer.is_valid():
            serializer.save()
            return Response({"message": "Données reçues avec succès."}, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    except Exception as e:
        return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)
    
@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_latest_sensor_data(request, raspberry_id):
    try:
        raspberry = get_object_or_404(Raspberry, id=raspberry_id)
        logger.info(f"Utilisateur {request.user} a accédé aux données de Raspberry {raspberry_id}")

        # Vérifier si l'utilisateur a accès à ce Raspberry
        if not request.user.is_superuser and not request.user.is_staff:
            # Vérifier si l'utilisateur appartient au groupe du Raspberry
            user_groups = Group.objects.filter(
                raspberries=raspberry,
                user_groups__user=request.user
            )
            if not user_groups.exists():
                logger.warning(f"Utilisateur {request.user} n'a pas accès au Raspberry {raspberry_id}")
                return Response({"error": "Accès non autorisé."}, status=status.HTTP_403_FORBIDDEN)

        # Définir la plage de temps
        time_range = request.GET.get('time_range', '24')
        try:
            time_range = int(time_range)
        except ValueError:
            logger.error(f"Valeur de time_range invalide: {time_range}")
            return Response({"error": "Valeur de time_range invalide."}, status=status.HTTP_400_BAD_REQUEST)

        end_time = now()
        start_time = end_time - timedelta(hours=time_range)

        sensor_locations = SensorLocation.objects.filter(raspberry=raspberry)
        sensor_data = SensorData.objects.filter(
            sensor_location__in=sensor_locations,
            timestamp__gte=start_time
        ).order_by('timestamp')

        serializer = SensorDataReadSerializer(sensor_data, many=True)
        logger.info(f"Renvoyé {sensor_data.count()} enregistrements de SensorData pour Raspberry {raspberry_id}")
        return Response(serializer.data, status=status.HTTP_200_OK)

    except Exception as e:
        logger.exception(f"Erreur dans get_latest_sensor_data: {e}")
        return Response({"error": "Erreur interne du serveur."}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)