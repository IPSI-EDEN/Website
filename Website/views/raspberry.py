from .home import *

@login_required(login_url='login')
def manage_greenhouse(request, id):
    raspberry = get_object_or_404(Raspberry, id=id)
    sensor_locations = SensorLocation.objects.filter(raspberry=raspberry)
    plants = Plant.objects.all()

    # Préparation des données pour la visualisation D3.js
    sensor_locations_data = []
    for location in sensor_locations:
        sensor_locations_data.append({
            'location_name': location.location_name,
            'plant': {
                'name': location.plant.name,
                'soil_moisture_min': location.plant.soil_moisture_min,
                'soil_moisture_max': location.plant.soil_moisture_max,
            },
            'soil_moisture': location.soil_moisture,
            'x_position': location.x_position,
            'y_position': location.y_position,
        })

    # Création d'un formset pour gérer les formulaires de seuils des plantes
    PlantFormSet = modelformset_factory(Plant, form=PlantThresholdForm, extra=0)

    # Traitement spécifique pour le basculement des équipements
    if request.method == 'POST' and 'toggle_device' in request.POST:
        device = request.POST.get('toggle_device')
        if device == 'pump':
            raspberry.pump_state = not raspberry.pump_state
        elif device == 'fan':
            raspberry.fan_state = not raspberry.fan_state
        raspberry.save()
        messages.success(request, f"L'état de {device} a été modifié.")
        return redirect('raspberry_threshold', id=raspberry.id)

    # Traitement du formset pour les seuils
    if request.method == 'POST':
        formset = PlantFormSet(request.POST, queryset=plants)
        if formset.is_valid():
            formset.save()
            messages.success(request, "Les seuils des plantes ont été mis à jour.")
            return redirect('threshold', id=raspberry.id)
    else:
        formset = PlantFormSet(queryset=plants)

    context = {
        'raspberry': raspberry,
        'formset': formset,
        'sensor_locations_json': json.dumps(sensor_locations_data),
    }
    return render(request, 'manage_greenhouse.html', context)

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
        MAX_POINTS = 1000
        total_points = sensor_data.count()
        if total_points > MAX_POINTS:
            step = total_points // MAX_POINTS
            sensor_ids = list(sensor_data.values_list('pk', flat=True))
            sensor_ids = sensor_ids[::step]
            sensor_data = SensorData.objects.filter(pk__in=sensor_ids).order_by('timestamp')

        time_labels = [(data.timestamp + timedelta(hours=2)).strftime('%Y-%m-%d %H:%M:%S') for data in sensor_data]
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

    # Définir les plages fixes pour l'axe x uniquement si time_labels est non vide
    x_range = [time_labels[0], time_labels[-1]] if time_labels else []

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
                    'xaxis': {
                        'title': 'Temps',
                        'range': x_range,
                        'autorange': False
                    },
                    'yaxis': {
                        'title': '°C',
                        'range': [-10, 50],
                        'autorange': False
                    }
                }
            })
        },
        {
            'id': 'humidityChart',
            'title': "Évolution de l'humidité de l’air",
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
                    'xaxis': {
                        'title': 'Temps',
                        'range': x_range,
                        'autorange': False
                    },
                    'yaxis': {
                        'title': '%',
                        'range': [0, 100],
                        'autorange': False
                    }
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
                    'xaxis': {
                        'title': 'Temps',
                        'range': x_range,
                        'autorange': False
                    },
                    'yaxis': {
                        'title': '%',
                        'range': [0, 100],
                        'autorange': False
                    }
                }
            })
        },
        {
            'id': 'waterLevelChart',
            'title': "Évolution du niveau d’eau",
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
                    'xaxis': {
                        'title': 'Temps',
                        'range': x_range,
                        'autorange': False
                    },
                    'yaxis': {
                        'title': '%',
                        'range': [0, 100],
                        'autorange': False
                    }
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

@login_required(login_url='login')
def raspberry_delete(request, id):
    raspberry = get_object_or_404(Raspberry, id=id)
    raspberry.delete()
    return redirect('home')

@login_required(login_url='login')
def toggle_device(request, id, device):
    raspberry = get_object_or_404(Raspberry, id=id)
    if request.method == 'POST':
        if device == 'pump':
            raspberry.pump_state = not raspberry.pump_state
            messages.success(request, "L'état de la pompe a été modifié.")
        elif device == 'fan':
            raspberry.fan_state = not raspberry.fan_state
            messages.success(request, "L'état du ventilateur a été modifié.")
        else:
            messages.error(request, "Appareil inconnu.")
        raspberry.save()
    else:
        messages.error(request, "Méthode non autorisée.")
    # Rediriger vers la page de gestion de la serre
    return redirect('manage_greenhouse', id=raspberry.id)

