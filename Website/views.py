from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib.auth.forms import AuthenticationForm
from django.contrib import messages
from django.utils import timezone
from django.db.models import Avg, Max
from django.db.models import Avg, OuterRef, Subquery
from django.db.models.functions import TruncHour
from django.conf import settings
from cryptography.hazmat.primitives.ciphers.aead import AESGCM

import base64
import plotly.graph_objs as go
import plotly.express as px
import plotly
import json

from .models import SensorData, SensorLocation, Group
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework import status
from .serializers import SensorDataSerializer

from Website.models import *

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
@user_passes_test(is_admin)
def example_page(request):
    # Créer un Raspberry Pi factice si il n'existe pas
    default_group, created = Group.objects.get_or_create(
        name=DEFAULT_GROUP_NAME,
        defaults={
            'description': 'Group par défaut pour les Raspberries non assignés.'
        }
    )
    
    raspberry, created = Raspberry.objects.get_or_create(
        device_id='raspberry_factice',
        defaults={
            'group': default_group,
            'active': True,
            'status': 'unassigned'
        }
    )
    
    # Créer une SensorLocation factice si elle n'existe pas
    plant, created = Plant.objects.get_or_create(
        name='Plante Factice',
        defaults={
            'description': 'Plante pour démonstration.',
            'temperature_min': 10.0,
            'temperature_max': 35.0,
            'humidity_min': 30.0,
            'humidity_max': 90.0,
            'soil_moisture_min': 10.0,
            'soil_moisture_max': 80.0,
        }
    )
    
    sensor_location, created = SensorLocation.objects.get_or_create(
        raspberry=raspberry,
        location_name='Emplacement Factice',
        plant=plant
    )
    
    # Générer des données factices si aucune donnée n'existe
    if not SensorData.objects.filter(sensor_location=sensor_location).exists():
        for i in range(5):
            SensorData.objects.create(
                sensor_location=sensor_location,
                timestamp=timezone.now() - timezone.timedelta(hours=24 - i*4),
                temperature=20 + i,
                air_humidity=50 + i*2,
                soil_moisture=30 + i*3,
            )
    
    # Définir la fenêtre temporelle (par exemple, les dernières 24 heures)
    now = timezone.now()
    start_time = now - timezone.timedelta(hours=24)
    
    # Sous-requête pour obtenir la dernière timestamp par SensorLocation
    latest_sensor_data_subquery = SensorData.objects.filter(
        sensor_location=OuterRef('sensor_location'),
        timestamp__gte=start_time
    ).order_by('-timestamp').values('timestamp')[:1]
    
    # Récupérer les dernières données pour l'emplacement de capteur factice
    latest_sensor_data = SensorData.objects.filter(
        sensor_location=sensor_location,
        timestamp=Subquery(latest_sensor_data_subquery)
    )
    
    # Agréger les données par heure et calculer la moyenne pour chaque métrique
    aggregated_data = latest_sensor_data.annotate(hour=TruncHour('timestamp')).values('hour').annotate(
        avg_temperature=Avg('temperature'),
        avg_humidity=Avg('air_humidity'),
        avg_soil_moisture=Avg('soil_moisture'),
    ).order_by('hour')

    # Préparer les étiquettes de temps et les listes de données
    time_labels = [entry['hour'].strftime('%H:%M') for entry in aggregated_data]
    temperature_data = [entry['avg_temperature'] for entry in aggregated_data]
    humidity_data = [entry['avg_humidity'] for entry in aggregated_data]
    moist_data = [entry['avg_soil_moisture'] for entry in aggregated_data]
    
    # Définir la palette de couleurs
    colors = {
        'primary': '#0d6efd',
        'secondary': '#6c757d',
        'success': '#198754',
        'danger': '#dc3545',
        'warning': '#ffc107',
        'info': '#0dcaf0',
        'light': '#f8f9fa',
        'dark': '#212529',
    }
    
    # Créer un template Plotly personnalisé
    custom_template = go.layout.Template(
        layout=go.Layout(
            font=dict(family="Arial, sans-serif", size=12, color=colors['dark']),
            paper_bgcolor=colors['light'],
            plot_bgcolor=colors['light'],
            colorway=[colors['primary'], colors['secondary'], colors['success'], colors['danger'], colors['warning'], colors['info']],
            xaxis=dict(gridcolor=colors['secondary']),
            yaxis=dict(gridcolor=colors['secondary']),
            title=dict(x=0.5),
            margin=dict(l=10, r=10, t=50, b=50),
        )
    )
    
    # Créer les graphiques
    charts = []
    data_list = [
        {'data': temperature_data, 'title': 'Température au fil du temps', 'y_label': 'Température (°C)', 'id': 'temperatureChart', 'color': colors['primary']},
        {'data': humidity_data, 'title': 'Humidité au fil du temps', 'y_label': 'Humidité (%)', 'id': 'humidityChart', 'color': colors['info']},
        {'data': moist_data, 'title': 'Humidité du sol au fil du temps', 'y_label': 'Humidité du sol (%)', 'id': 'moistChart', 'color': colors['success']},
    ]

    for item in data_list:
        fig = go.Figure()
        fig.add_trace(go.Scatter(
            x=time_labels,
            y=item['data'],
            mode='lines+markers',
            line=dict(color=item['color'], width=3),
            marker=dict(size=6)
        ))
        fig.update_layout(
            xaxis_title='Heure',
            yaxis_title=item['y_label'],
            template=custom_template,
            autosize=True,
        )
        fig.update_layout(margin=dict(l=40, r=40, t=40, b=40))
        fig_json = json.dumps(fig, cls=plotly.utils.PlotlyJSONEncoder)
        charts.append({'title': item['title'], 'id': item['id'], 'json': fig_json})

    # Créer les jauges basées sur les dernières données
    gauges = []
    # Calculer les valeurs moyennes pour les jauges
    if latest_sensor_data.exists():
        latest_values = {
            'temperature': [data.temperature for data in latest_sensor_data],
            'humidity': [data.air_humidity for data in latest_sensor_data],
            'soil_moisture': [data.soil_moisture for data in latest_sensor_data],
        }

        current_temperature = sum(latest_values['temperature']) / len(latest_values['temperature'])
        current_humidity = sum(latest_values['humidity']) / len(latest_values['humidity'])
        current_soil_moisture = sum(latest_values['soil_moisture']) / len(latest_values['soil_moisture'])
    else:
        current_temperature = 0
        current_humidity = 0
        current_soil_moisture = 0

    gauge_data = [
        {'value': current_temperature, 'title': 'Température actuelle', 'id': 'temperatureGauge', 'range': [0, 50], 'color': colors['primary']},
        {'value': current_humidity, 'title': 'Humidité actuelle', 'id': 'humidityGauge', 'range': [0, 100], 'color': colors['info']},
        {'value': current_soil_moisture, 'title': 'Humidité du sol actuelle', 'id': 'moistGauge', 'range': [0, 100], 'color': colors['success']},
    ]

    for gauge in gauge_data:
        fig = go.Figure(go.Indicator(
            mode="gauge+number",
            value=gauge['value'],
            title={'text': gauge['title'], 'font': {'size': 14}},
            gauge={
                'axis': {'range': gauge['range'], 'tickwidth': 1, 'tickcolor': colors['dark']},
                'bar': {'color': gauge['color']},
                'bgcolor': colors['light'],
                'borderwidth': 1,
                'bordercolor': colors['secondary'],
            },
        ))
        fig.update_layout(
            font=dict(family="Arial, sans-serif", size=12, color=colors['dark']),
            paper_bgcolor=colors['light'],
            autosize=True,
            margin=dict(l=10, r=10, t=40, b=10),
        )
        fig_json = json.dumps(fig, cls=plotly.utils.PlotlyJSONEncoder)
        gauges.append({'title': gauge['title'], 'id': gauge['id'], 'json': fig_json})

    context = {
        'gauges': gauges,
        'charts': charts,
    }

    return render(request, 'home.html', context)

@login_required(login_url='login')
def home_page(request):
    user = request.user

    # Vérifier si l'utilisateur est admin
    if user.is_superuser or user.is_staff:
        # Administrateur : récupérer toutes les Raspberry actives
        raspberries = Raspberry.objects.filter(active=True)
    else:
        # Utilisateur standard : récupérer les groupes de l'utilisateur
        user_groups = Group.objects.filter(user_groups__user=user)
        if not user_groups.exists():
            # Gérer les utilisateurs sans groupe
            context = {
                'gauges': [],
                'charts': [],
                'error': "Vous n'êtes associé à aucun groupe."
            }
            return render(request, 'home.html', context)
        # Récupérer les Raspberry actives appartenant aux groupes de l'utilisateur
        raspberries = Raspberry.objects.filter(group__in=user_groups, active=True)

    # Récupérer toutes les locations de capteurs dans ces Raspberry
    sensor_locations = SensorLocation.objects.filter(raspberry__in=raspberries)

    # Définir la fenêtre temporelle (par exemple, les dernières 24 heures)
    now = timezone.now()
    start_time = now - timezone.timedelta(hours=24)

    # Sous-requête pour obtenir la dernière timestamp par SensorLocation
    latest_sensor_data_subquery = SensorData.objects.filter(
        sensor_location=OuterRef('sensor_location'),
        timestamp__gte=start_time
    ).order_by('-timestamp').values('timestamp')[:1]

    # Récupérer les dernières données par SensorLocation
    latest_sensor_data = SensorData.objects.filter(
        sensor_location__in=sensor_locations,
        timestamp=Subquery(latest_sensor_data_subquery)
    )

    # Agréger les données par heure et calculer la moyenne pour chaque métrique
    aggregated_data = latest_sensor_data.annotate(hour=TruncHour('timestamp')).values('hour').annotate(
        avg_temperature=Avg('temperature'),
        avg_humidity=Avg('air_humidity'),
        avg_soil_moisture=Avg('soil_moisture'),
    ).order_by('hour')

    # Préparer les étiquettes de temps et les listes de données
    time_labels = [entry['hour'].strftime('%H:%M') for entry in aggregated_data]
    temperature_data = [entry['avg_temperature'] for entry in aggregated_data]
    humidity_data = [entry['avg_humidity'] for entry in aggregated_data]
    moist_data = [entry['avg_soil_moisture'] for entry in aggregated_data]

    # Définir la palette de couleurs
    colors = {
        'primary': '#0d6efd',
        'secondary': '#6c757d',
        'success': '#198754',
        'danger': '#dc3545',
        'warning': '#ffc107',
        'info': '#0dcaf0',
        'light': '#f8f9fa',
        'dark': '#212529',
    }

    # Créer un template Plotly personnalisé
    custom_template = go.layout.Template(
        layout=go.Layout(
            font=dict(family="Arial, sans-serif", size=12, color=colors['dark']),
            paper_bgcolor=colors['light'],
            plot_bgcolor=colors['light'],
            colorway=[colors['primary'], colors['secondary'], colors['success'], colors['danger'], colors['warning'], colors['info']],
            xaxis=dict(gridcolor=colors['secondary']),
            yaxis=dict(gridcolor=colors['secondary']),
            title=dict(x=0.5),
            margin=dict(l=10, r=10, t=50, b=50),
        )
    )

    # Créer les graphiques
    charts = []
    data_list = [
        {'data': temperature_data, 'title': 'Température au fil du temps', 'y_label': 'Température (°C)', 'id': 'temperatureChart', 'color': colors['primary']},
        {'data': humidity_data, 'title': 'Humidité au fil du temps', 'y_label': 'Humidité (%)', 'id': 'humidityChart', 'color': colors['info']},
        {'data': moist_data, 'title': 'Humidité du sol au fil du temps', 'y_label': 'Humidité du sol (%)', 'id': 'moistChart', 'color': colors['success']},
    ]

    for item in data_list:
        fig = go.Figure()
        fig.add_trace(go.Scatter(
            x=time_labels,
            y=item['data'],
            mode='lines+markers',
            line=dict(color=item['color'], width=3),
            marker=dict(size=6)
        ))
        fig.update_layout(
            xaxis_title='Heure',
            yaxis_title=item['y_label'],
            template=custom_template,
            autosize=True,
        )
        fig.update_layout(margin=dict(l=40, r=40, t=40, b=40))
        fig_json = json.dumps(fig, cls=plotly.utils.PlotlyJSONEncoder)
        charts.append({'title': item['title'], 'id': item['id'], 'json': fig_json})

    # Créer les jauges basées sur les dernières données
    gauges = []
    # Calculer les valeurs moyennes pour les jauges
    if latest_sensor_data.exists():
        latest_values = {
            'temperature': [data.temperature for data in latest_sensor_data],
            'humidity': [data.air_humidity for data in latest_sensor_data],
            'soil_moisture': [data.soil_moisture for data in latest_sensor_data],
        }

        current_temperature = sum(latest_values['temperature']) / len(latest_values['temperature'])
        current_humidity = sum(latest_values['humidity']) / len(latest_values['humidity'])
        current_soil_moisture = sum(latest_values['soil_moisture']) / len(latest_values['soil_moisture'])
    else:
        current_temperature = 0
        current_humidity = 0
        current_soil_moisture = 0

    gauge_data = [
        {'value': current_temperature, 'title': 'Température actuelle', 'id': 'temperatureGauge', 'range': [0, 50], 'color': colors['primary']},
        {'value': current_humidity, 'title': 'Humidité actuelle', 'id': 'humidityGauge', 'range': [0, 100], 'color': colors['info']},
        {'value': current_soil_moisture, 'title': 'Humidité du sol actuelle', 'id': 'moistGauge', 'range': [0, 100], 'color': colors['success']},
    ]

    for gauge in gauge_data:
        fig = go.Figure(go.Indicator(
            mode="gauge+number",
            value=gauge['value'],
            title={'text': gauge['title'], 'font': {'size': 14}},
            gauge={
                'axis': {'range': gauge['range'], 'tickwidth': 1, 'tickcolor': colors['dark']},
                'bar': {'color': gauge['color']},
                'bgcolor': colors['light'],
                'borderwidth': 1,
                'bordercolor': colors['secondary'],
            },
        ))
        fig.update_layout(
            font=dict(family="Arial, sans-serif", size=12, color=colors['dark']),
            paper_bgcolor=colors['light'],
            autosize=True,
            margin=dict(l=10, r=10, t=40, b=10),
        )
        fig_json = json.dumps(fig, cls=plotly.utils.PlotlyJSONEncoder)
        gauges.append({'title': gauge['title'], 'id': gauge['id'], 'json': fig_json})

    context = {
        'gauges': gauges,
        'charts': charts,
    }

    return render(request, 'home.html', context)

@api_view(['POST'])
@permission_classes([AllowAny])  # Ajustez les permissions selon vos besoins
def receive_sensor_data(request):
    try:
        # Attendez que les données chiffrées soient dans un champ spécifique, par exemple 'encrypted_data'
        encrypted_data_b64 = request.data.get('encrypted_data')
        if not encrypted_data_b64:
            return Response({"error": "Données chiffrées manquantes."}, status=status.HTTP_400_BAD_REQUEST)
        
        # Décoder les données de base64
        encrypted_data = base64.b64decode(encrypted_data_b64)
        
        # Séparer le nonce (12 octets pour AES-GCM) et le ciphertext
        nonce = encrypted_data[:12]
        ciphertext = encrypted_data[12:]
        
        # Déchiffrer les données
        aesgcm = AESGCM(settings.AES_SECRET_KEY)
        decrypted_data = aesgcm.decrypt(nonce, ciphertext, None)
        
        # Charger les données JSON
        data = json.loads(decrypted_data.decode('utf-8'))
        
        # Valider et sauvegarder les données
        serializer = SensorDataSerializer(data=data)
        if serializer.is_valid():
            serializer.save()
            return Response({"message": "Données reçues et déchiffrées avec succès."}, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    except Exception as e:
        return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)