from .home import *

@login_required(login_url='login')
def manage_greenhouse(request, id):
    raspberry = get_object_or_404(Raspberry, id=id)
    sensor_locations = SensorLocation.objects.filter(raspberry=raspberry)
    plants = Plant.objects.all()

    sensor_locations_data = []
    for location in sensor_locations:
        sensor_locations_data.append({
            'location_name': '',
            'plant': {
                'name': '',
                'soil_moisture_min': '',
                'soil_moisture_max': '',
            },
            'soil_moisture': '',
            'x_position': '',
            'y_position': '',
        })

    PlantFormSet = modelformset_factory(Plant, form=PlantThresholdForm, extra=0)

    if request.method == 'POST' and 'toggle_device' in request.POST:
        device = request.POST.get('toggle_device')
        if device == 'pump':
            raspberry.pump_state = not raspberry.pump_state
        elif device == 'fan':
            raspberry.fan_state = not raspberry.fan_state
        raspberry.save()
        messages.success(request, f"L'état de {device} a été modifié.")
        return redirect('raspberry_threshold', id=raspberry.id)

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

    sensor_data_qs = SensorData.objects.filter(
        sensor_location__in=sensor_locations,
        timestamp__gte=start_time
    ).order_by('timestamp')

    MAX_POINTS = 200
    total_points = sensor_data_qs.count()
    if total_points > MAX_POINTS:
        step = total_points // MAX_POINTS
        ids = list(sensor_data_qs.values_list('pk', flat=True))
        ids = ids[::step]
        sensor_data_qs = SensorData.objects.filter(pk__in=ids).order_by('timestamp')

    sensor_data_list = list(sensor_data_qs)

    TEMPERATURE_COLOR = "#FF5733"  # Rouge/orangé
    HUMIDITY_COLOR = "#33CFFF"     # Bleu clair
    WATER_COLOR = "#1f77b4"        # Bleu
    SOIL_COLOR = "#2ca02c"         # Vert

    soil_colors = ["#1f77b4", "#ff7f0e", "#2ca02c", "#d62728", "#9467bd"]

    soil_data_dict = {}
    for loc in sensor_locations:
        soil_data_dict[loc.id] = {
            'name': loc.location_name,
            'timestamps': [],
            'values': []
        }

    time_labels = []
    temperature_list = []
    humidity_list = []
    water_list = []

    for data in sensor_data_list:
        t_str = (data.timestamp + timedelta(hours=2)).strftime('%Y-%m-%d %H:%M:%S')
        time_labels.append(t_str)
        temperature_list.append(data.temperature if data.temperature is not None else None)
        humidity_list.append(data.air_humidity if data.air_humidity is not None else None)
        water_list.append(data.water_level if data.water_level is not None else None)

        loc_id = data.sensor_location_id
        soil_val = data.soil_moisture if data.soil_moisture is not None else 0
        if isinstance(soil_val, list):
            soil_val = soil_val[0] if soil_val else 0
        soil_data_dict[loc_id]['timestamps'].append(t_str)
        soil_data_dict[loc_id]['values'].append(soil_val)

    soil_moisture_traces = []
    for idx, (loc_id, info) in enumerate(soil_data_dict.items()):
        if not info['timestamps']:
            continue
        trace = {
            'x': info['timestamps'],
            'y': info['values'],
            'mode': 'lines+markers',
            'type': 'scatter',
            'name': info['name'],
            'line': {'color': soil_colors[idx % len(soil_colors)]}
        }
        soil_moisture_traces.append(trace)

    logger.debug(f"Soil moisture traces: {soil_moisture_traces}")
    sum_soil = 0
    count_soil = 0
    for location in sensor_locations:
        if location.soil_moisture is not None:
            sum_soil += location.soil_moisture
            count_soil += 1
    current_soil_moisture = sum_soil / count_soil if count_soil > 0 else 0

    if sensor_data_list:
        latest = sensor_data_list[-1]
        current_temperature = latest.temperature or 0
        current_humidity = latest.air_humidity or 0
        current_water_level = latest.water_level or 0
    else:
        current_temperature = 0
        current_humidity = 0
        current_water_level = 0

    default_layout = {
        "font":          {"color": "white"},
        "paper_bgcolor": "rgba(0,0,0,0)",
        "plot_bgcolor":  "rgba(0,0,0,0)",
        "margin":        {"l": 30, "r": 30, "t": 30, "b": 30}
    }

    gauges = [
        {
            "id": "temperatureGauge",
            "title": "Température (°C)",
            "json": json.dumps({
                "data": [{
                    "type":   "indicator",
                    "mode":   "gauge+number",
                    "value":  current_temperature,
                    "number": {"font": {"color": "white"}},
                    "gauge":  {
                        "axis": {"range": [-10, 50], "tickcolor": "white"},
                        "bar":  {"color": TEMPERATURE_COLOR}
                    }
                }],
                "layout": default_layout
            })
        },
        {
            "id": "humidityGauge",
            "title": "Humidité de l’air (%)",
            "json": json.dumps({
                "data": [{
                    "type":   "indicator",
                    "mode":   "gauge+number",
                    "value":  current_humidity,
                    "number": {"font": {"color": "white"}},
                    "gauge":  {
                        "axis": {"range": [0, 100], "tickcolor": "white"},
                        "bar":  {"color": HUMIDITY_COLOR}
                    }
                }],
                "layout": default_layout
            })
        },
        {
            "id": "soilMoistureGauge",
            "title": "Humidité du sol (%)",
            "json": json.dumps({
                "data": [{
                    "type":   "indicator",
                    "mode":   "gauge+number",
                    "value":  current_soil_moisture,
                    "number": {"font": {"color": "white"}},
                    "gauge":  {
                        "axis": {"range": [0, 100], "tickcolor": "white"},
                        "bar":  {"color": SOIL_COLOR}
                    }
                }],
                "layout": default_layout
            })
        },
        {
            "id": "waterLevelGauge",
            "title": "Niveau d’eau (%)",
            "json": json.dumps({
                "data": [{
                    "type":   "indicator",
                    "mode":   "gauge+number",
                    "value":  current_water_level,
                    "number": {"font": {"color": "white"}},
                    "gauge":  {
                        "axis": {"range": [0, 100], "tickcolor": "white"},
                        "bar":  {"color": WATER_COLOR}
                    }
                }],
                "layout": default_layout
            })
        }
    ]

    charts = [
        {
            "id": "temperatureChart",
            "title": "Évolution température (°C)",
            "json": json.dumps({
                "data": [{
                    "x":     time_labels,
                    "y":     temperature_list,
                    "mode":  "lines+markers",
                    "type":  "scatter",
                    "line":  {"color": TEMPERATURE_COLOR}
                }],
                "layout": {
                    **default_layout,
                    "margin": {"l": 50, "r": 50, "t": 50, "b": 50},
                    "xaxis":  {
                        "tickmode":  "auto",
                        "nticks":    10,
                        "tickfont":  {"color": "white"},
                        "title_font":{"color": "white"},
                        "color":     "white"
                    },
                    "yaxis":  {
                        "range":     [0, 50],
                        "tickfont":  {"color": "white"},
                        "title_font":{"color": "white"},
                        "color":     "white"
                    }
                }
            })
        },
        {
            "id": "humidityChart",
            "title": "Évolution humidité de l'air (%)",
            "json": json.dumps({
                "data": [{
                    "x":     time_labels,
                    "y":     humidity_list,
                    "mode":  "lines+markers",
                    "type":  "scatter",
                    "line":  {"color": HUMIDITY_COLOR}
                }],
                "layout": {
                    **default_layout,
                    "margin": {"l": 50, "r": 50, "t": 50, "b": 50},
                    "xaxis":  {
                        "tickmode":  "auto",
                        "nticks":    10,
                        "tickfont":  {"color": "white"},
                        "title_font":{"color": "white"},
                        "color":     "white"
                    },
                    "yaxis":  {
                        "range":     [0, 100],
                        "tickfont":  {"color": "white"},
                        "title_font":{"color": "white"},
                        "color":     "white"
                    }
                }
            })
        },
        {
            "id": "waterChart",
            "title": "Niveau d'eau (%)",
            "json": json.dumps({
                "data": [{
                    "x":     time_labels,
                    "y":     water_list,
                    "mode":  "lines+markers",
                    "type":  "scatter",
                    "line":  {"color": WATER_COLOR}
                }],
                "layout": {
                    **default_layout,
                    "margin": {"l": 50, "r": 50, "t": 50, "b": 50},
                    "xaxis":  {
                        "tickmode":  "auto",
                        "nticks":    10,
                        "tickfont":  {"color": "white"},
                        "title_font":{"color": "white"},
                        "color":     "white"
                    },
                    "yaxis":  {
                        "range":     [0, 100],
                        "tickfont":  {"color": "white"},
                        "title_font":{"color": "white"},
                        "color":     "white"
                    }
                }
            })
        },
        {
            "id": "soilChart",
            "title": "Évolution de l'humidité du sol (%)",
            "json": json.dumps({
                "data": soil_moisture_traces,
                "layout": {
                    **default_layout,
                    "margin": {"l": 50, "r": 50, "t": 50, "b": 50},
                    "xaxis":  {
                        "tickmode":  "auto",
                        "nticks":    10,
                        "tickfont":  {"color": "white"},
                        "title_font":{"color": "white"},
                        "color":     "white"
                    },
                    "yaxis":  {
                        "range":     [0, 100],
                        "tickfont":  {"color": "white"},
                        "title_font":{"color": "white"},
                        "color":     "white"
                    }
                }
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

def guest_graph_page(request, id):
    raspberry = get_object_or_404(Raspberry, id=id)
    sensor_locations = SensorLocation.objects.filter(raspberry=raspberry)

    selected_time_range = int(request.GET.get('time_range', 24))
    end_time = now()
    start_time = end_time - timedelta(hours=selected_time_range)

    sensor_data_qs = SensorData.objects.filter(
        sensor_location__in=sensor_locations,
        timestamp__gte=start_time
    ).order_by('timestamp')

    MAX_POINTS = 200
    total_points = sensor_data_qs.count()
    if total_points > MAX_POINTS:
        step = total_points // MAX_POINTS
        ids = list(sensor_data_qs.values_list('pk', flat=True))
        ids = ids[::step]
        sensor_data_qs = SensorData.objects.filter(pk__in=ids).order_by('timestamp')

    sensor_data_list = list(sensor_data_qs)

    TEMPERATURE_COLOR = "#FF5733"  # Rouge/orangé
    HUMIDITY_COLOR = "#33CFFF"     # Bleu clair
    WATER_COLOR = "#1f77b4"        # Bleu
    SOIL_COLOR = "#2ca02c"         # Vert

    soil_colors = ["#1f77b4", "#ff7f0e", "#2ca02c", "#d62728", "#9467bd"]

    soil_data_dict = {}
    for loc in sensor_locations:
        soil_data_dict[loc.id] = {
            'name': loc.location_name,
            'timestamps': [],
            'values': []
        }

    time_labels = []
    temperature_list = []
    humidity_list = []
    water_list = []

    for data in sensor_data_list:
        t_str = (data.timestamp + timedelta(hours=2)).strftime('%Y-%m-%d %H:%M:%S')
        time_labels.append(t_str)
        temperature_list.append(data.temperature if data.temperature is not None else None)
        humidity_list.append(data.air_humidity if data.air_humidity is not None else None)
        water_list.append(data.water_level if data.water_level is not None else None)

        loc_id = data.sensor_location_id
        soil_val = data.soil_moisture if data.soil_moisture is not None else 0
        if isinstance(soil_val, list):
            soil_val = soil_val[0] if soil_val else 0
        soil_data_dict[loc_id]['timestamps'].append(t_str)
        soil_data_dict[loc_id]['values'].append(soil_val)

    soil_moisture_traces = []
    for idx, (loc_id, info) in enumerate(soil_data_dict.items()):
        if not info['timestamps']:
            continue
        trace = {
            'x': info['timestamps'],
            'y': info['values'],
            'mode': 'lines+markers',
            'type': 'scatter',
            'name': info['name'],
            'line': {'color': soil_colors[idx % len(soil_colors)]}
        }
        soil_moisture_traces.append(trace)

    logger.debug(f"Soil moisture traces: {soil_moisture_traces}")
    sum_soil = 0
    count_soil = 0
    for location in sensor_locations:
        if location.soil_moisture is not None:
            sum_soil += location.soil_moisture
            count_soil += 1
    current_soil_moisture = sum_soil / count_soil if count_soil > 0 else 0

    if sensor_data_list:
        latest = sensor_data_list[-1]
        current_temperature = latest.temperature or 0
        current_humidity = latest.air_humidity or 0
        current_water_level = latest.water_level or 0
    else:
        current_temperature = 0
        current_humidity = 0
        current_water_level = 0

    gauges = [
        {
            'id': 'temperatureGauge',
            'title': 'Température (°C)',
            'json': json.dumps({
                'data': [{
                    'type': 'indicator',
                    'mode': 'gauge+number',
                    'value': current_temperature,
                    'gauge': {
                        'axis': {'range': [-10, 50]},
                        'bar': {'color': TEMPERATURE_COLOR}
                    }
                }],
                'layout': {'margin': {'l': 30, 'r': 30, 't': 30, 'b': 30}}
            })
        },
        {
            'id': 'humidityGauge',
            'title': 'Humidité de l’air (%)',
            'json': json.dumps({
                'data': [{
                    'type': 'indicator',
                    'mode': 'gauge+number',
                    'value': current_humidity,
                    'gauge': {
                        'axis': {'range': [0, 100]},
                        'bar': {'color': HUMIDITY_COLOR}
                    }
                }],
                'layout': {'margin': {'l': 30, 'r': 30, 't': 30, 'b': 30}}
            })
        },
        {
            'id': 'soilMoistureGauge',
            'title': 'Humidité du sol (%)',
            'json': json.dumps({
                'data': [{
                    'type': 'indicator',
                    'mode': 'gauge+number',
                    'value': current_soil_moisture,
                    'gauge': {
                        'axis': {'range': [0, 100]},
                        'bar': {'color': SOIL_COLOR}
                    }
                }],
                'layout': {'margin': {'l': 30, 'r': 30, 't': 30, 'b': 30}}
            })
        },
        {
            'id': 'waterLevelGauge',
            'title': "Niveau d’eau (%)",
            'json': json.dumps({
                'data': [{
                    'type': 'indicator',
                    'mode': 'gauge+number',
                    'value': current_water_level,
                    'gauge': {
                        'axis': {'range': [0, 100]},
                        'bar': {'color': WATER_COLOR}
                    }
                }],
                'layout': {'margin': {'l': 30, 'r': 30, 't': 30, 'b': 30}}
            })
        }
    ]

    charts = [
        {
            'id': 'temperatureChart',
            'title': 'Évolution température (°C)',
            'json': json.dumps({
                'data': [{
                    'x': time_labels,
                    'y': temperature_list,
                    'mode': 'lines+markers',
                    'type': 'scatter',
                    'line': {'color': TEMPERATURE_COLOR}
                }],
                'layout': {
                    'xaxis': {
                        'tickmode': 'auto',
                        'nticks': 10 
                    },
                    'yaxis': {'range': [-10, 50]},
                    'margin': {'l': 50, 'r': 50, 't': 50, 'b': 50}
                }
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
                    'type': 'scatter',
                    'line': {'color': HUMIDITY_COLOR}
                }],
                'layout': {
                    'xaxis': {
                        'tickmode': 'auto',
                        'nticks': 10 
                    },
                    'yaxis': {'range': [0, 100]},
                    'margin': {'l': 50, 'r': 50, 't': 50, 'b': 50}
                }
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
                    'type': 'scatter',
                    'line': {'color': WATER_COLOR}
                }],
                'layout': {
                    'xaxis': {
                        'tickmode': 'auto',
                        'nticks': 10 
                    },
                    'yaxis': {'range': [0, 100]},
                    'margin': {'l': 50, 'r': 50, 't': 50, 'b': 50}
                }
            })
        },
        {
            'id': 'soilChart',
            'title': "Évolution de l'humidité du sol (%)",
            'json': json.dumps({
                'data': soil_moisture_traces,
                'layout': {
                    'xaxis': {
                        'tickmode': 'auto',
                        'nticks': 10 
                    },
                    'yaxis': {'range': [0, 100]},
                    'margin': {'l': 50, 'r': 50, 't': 50, 'b': 50}
                }
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
    return redirect('manage_greenhouse', id=raspberry.id)

