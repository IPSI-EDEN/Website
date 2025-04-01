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

    # Plage de temps (par défaut 24h)
    selected_time_range = int(request.GET.get('time_range', 24))
    end_time = now()
    start_time = end_time - timedelta(hours=selected_time_range)

    # Récupérer les données dans la période sélectionnée
    sensor_data_qs = SensorData.objects.filter(
        sensor_location__in=sensor_locations,
        timestamp__gte=start_time
    ).order_by('timestamp')

    # Limiter le nombre de points pour éviter d’en avoir trop
    MAX_POINTS = 200
    total_points = sensor_data_qs.count()
    if total_points > MAX_POINTS:
        step = total_points // MAX_POINTS
        ids = list(sensor_data_qs.values_list('pk', flat=True))
        ids = ids[::step]
        sensor_data_qs = SensorData.objects.filter(pk__in=ids).order_by('timestamp')

    sensor_data_list = list(sensor_data_qs)

    # Préparer les données pour l'humidité du sol (une courbe par capteur)
    soil_data_dict = {}
    for loc in sensor_locations:
        soil_data_dict[loc.id] = {
            'name': loc.location_name,
            'timestamps': [],
            'values': []
        }

    # Listes globales pour température, humidité de l’air et niveau d’eau
    time_labels = []
    temperature_list = []
    humidity_list = []
    water_list = []

    for data in sensor_data_list:
        t_str = data.timestamp.strftime('%Y-%m-%d %H:%M:%S')
        time_labels.append(t_str)
        temperature_list.append(data.temperature if data.temperature is not None else None)
        humidity_list.append(data.air_humidity if data.air_humidity is not None else None)
        water_list.append(data.water_level if data.water_level is not None else None)

        # Remplir les données pour le sol
        loc_id = data.sensor_location_id
        soil_val = data.soil_moisture if data.soil_moisture is not None else 0
        soil_data_dict[loc_id]['timestamps'].append(t_str)
        soil_data_dict[loc_id]['values'].append(soil_val)

    # Construire les traces pour l’humidité du sol
    soil_moisture_traces = []
    for loc_id, info in soil_data_dict.items():
        if not info['timestamps']:
            continue
        soil_moisture_traces.append({
            'x': info['timestamps'],
            'y': info['values'],
            'mode': 'lines+markers',
            'type': 'scatter',
            'name': info['name']
        })

    # Calculer la moyenne de la dernière valeur relevée pour chaque capteur de sol
    sum_soil = 0
    count_soil = 0
    for location in sensor_locations:
        if location.soil_moisture is not None:
            sum_soil += location.soil_moisture
            count_soil += 1
    current_soil_moisture = sum_soil / count_soil if count_soil > 0 else 0

    # Dernières valeurs pour température, humidité de l’air et niveau d’eau
    if sensor_data_list:
        latest = sensor_data_list[-1]
        current_temperature = latest.temperature or 0
        current_humidity = latest.air_humidity or 0
        current_water_level = latest.water_level or 0
    else:
        current_temperature = 0
        current_humidity = 0
        current_water_level = 0

    # Préparer les "gauges" pour Plotly
    gauges = [
        {
            'id': 'temperatureGauge',
            'title': 'Température',
            'json': json.dumps({
                'data': [{
                    'type': 'indicator',
                    'mode': 'gauge+number',
                    'value': current_temperature,
                    'gauge': {'axis': {'range': [-10, 50]}}
                }],
                'layout': {'title': 'Température'}
            })
        },
        {
            'id': 'humidityGauge',
            'title': 'Humidité',
            'json': json.dumps({
                'data': [{
                    'type': 'indicator',
                    'mode': 'gauge+number',
                    'value': current_humidity,
                    'gauge': {'axis': {'range': [0, 100]}}
                }],
                'layout': {'title': 'Humidité'}
            })
        },
        {
            'id': 'soilMoistureGauge',
            'title': 'Humidité du sol (moy)',
            'json': json.dumps({
                'data': [{
                    'type': 'indicator',
                    'mode': 'gauge+number',
                    'value': current_soil_moisture,
                    'gauge': {'axis': {'range': [0, 100]}}
                }],
                'layout': {'title': 'Humidité du sol (moy)'}
            })
        },
        {
            'id': 'waterLevelGauge',
            'title': "Niveau d’eau",
            'json': json.dumps({
                'data': [{
                    'type': 'indicator',
                    'mode': 'gauge+number',
                    'value': current_water_level,
                    'gauge': {'axis': {'range': [0, 100]}}
                }],
                'layout': {'title': "Niveau d’eau"}
            })
        }
    ]

    # Préparer les "charts" (les graphiques linéaires)
    charts = [
        {
            'id': 'temperatureChart',
            'title': 'Évolution température (°C)',
            'json': json.dumps({
                'data': [{
                    'x': time_labels,
                    'y': temperature_list,
                    'mode': 'lines+markers',
                    'type': 'scatter'
                }],
                'layout': {'title': 'Évolution température (°C)'}
            })
        },
        {
            'id': 'humidityChart',
            'title': "Évolution humidité de l'air (%)",
            'json': json.dumps({
                'data': [{
                    'x': time_labels,
                    'y': humidity_list,
                    'mode': 'lines+markers',
                    'type': 'scatter'
                }],
                'layout': {"title": "Évolution humidité de l'air (%)"}
            })
        },
        {
            'id': 'waterChart',
            'title': "Niveau d'eau (%)",
            'json': json.dumps({
                'data': [{
                    'x': time_labels,
                    'y': water_list,
                    'mode': 'lines+markers',
                    'type': 'scatter'
                }],
                'layout': {"title": "Niveau d'eau (%)"}
            })
        },
        {
            'id': 'soilChart',
            'title': "Évolution de l'humidité du sol",
            'json': json.dumps({
                'data': soil_moisture_traces,
                'layout': {"title": "Évolution de l'humidité du sol"}
            })
        }
    ]

    context = {
        'raspberry': raspberry,
        'gauges': gauges,
        'charts': charts,
        'selected_time_range': selected_time_range,
    }
    return render(request, 'graph.html', context)

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

