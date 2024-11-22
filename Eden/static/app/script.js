// Initialisation des variables WebSocket
var ws;
var wsUri = (window.location.protocol === "https:") ? "wss://" : "ws://";
wsUri += window.location.host + "/ws/eden";

// Configuration des graphiques
var temperatureData = [];
var humidityData = [];
var moistData = [];
var voltageData = [];
var powerData = [];
var timeStamp = [];
var powerTimestamp = [];

var initialized = false;

// Fonction pour établir la connexion WebSocket
function wsConnect() {
    ws = new WebSocket(wsUri);

    ws.onopen = function () {
        
    };

    ws.onclose = function () {
        setTimeout(wsConnect, 3000);
    };

    ws.onmessage = function (msg) {
        var dataArray = JSON.parse(msg.data);

        // Remplacez la partie correspondante de la fonction ws.onmessage
        if (Array.isArray(dataArray) && dataArray.length > 0) {
            var data = dataArray[dataArray.length - 1];

            updateCharts(dataArray);

            // Ajouter les nouvelles données aux tableaux de données des graphiques
            temperatureData.push(data.temperature);
            humidityData.push(data.humidity);
            moistData.push(data.moist);
            voltageData.push(data.voltage);
            powerData.push(data.power);

            configWaterLevel.data.datasets[0].data[0] = data.water_level;
            configCurrentTemp.data.datasets[0].data[0] = data.temperature;
            configCurrentHumidity.data.datasets[0].data[0] = data.humidity;
            configCurrentMoist.data.datasets[0].data[0] = data.moist;

            updatePumpStatus(data.pump);
            updateWindowStatus(data.window);

        
            timeStamp.push(data.timestamp);
            if (data.powerTimestamp != null) {
                console.log(data.voltage);  
                powerTimestamp.push(data.powerTimestamp);
            }

            // Mettre à jour les graphiques avec les nouvelles données
            updateCharts();
        }

    };

    function updatePumpStatus(status) {
        var pumpStatusElement = document.getElementById('pump-status');
        pumpStatusElement.innerHTML = status ? '<i class="fas fa-check-circle" style="color: green;"></i><p> Allumée<p/>' : '<i class="fas fa-times-circle" style="color: red;"></i><p> Éteinte<p/>';
    }

    function updateWindowStatus(status) {
        var windowStatusElement = document.getElementById('window-status');
        windowStatusElement.innerHTML = status ? '<i class="fas fa-check-circle" style="color: green;"></i><p> Ouverte<p/>' : '<i class="fas fa-times-circle" style="color: red;"></i><p> Fermée<p/>';
    }
}

// Fonction pour envoyer un message WebSocket
function sendWebSocketMessage(message) {
    if (ws) {
        ws.send(message);
    }
}

// Appel initial pour établir la connexion WebSocket
wsConnect();

// Configuration de vos graphiques avec les nouvelles étiquettes de temps et de dates
const configTemperature = {
    type: 'line',
    data: {
        labels: timeStamp,
        datasets: [{
            label: 'Température (°C)',
            backgroundColor: 'rgba(255, 99, 132, 0.2)',
            borderColor: 'rgba(255, 99, 132, 1)',
            data: temperatureData,
            fill: false,
        }]
    },
    options: {
        tooltips: {
            callbacks: {
                title: function(tooltipItems, data) {
                    // Prend l'étiquette actuelle et la divise pour insérer un saut de ligne entre la date et l'heure.
                    // Cette opération suppose que la date et l'heure dans l'étiquette sont séparées par un espace,
                    // un tiret, ou tout autre caractère spécifique qui ne nécessite pas de formatage complexe.
                    var label = tooltipItems[0].label;
                    return label.replace(' ', '\n');
                }
            }
        },
        scales: {
            xAxes: [{
                type: 'time',
                distribution: 'linear',
                time: {
                    parser: 'DD/MM/YYYY HH:mm:ss', // Adaptez ce format au format de vos données si nécessaire
                    tooltipFormat: 'DD/MM/YYYY HH:mm:ss'
                },
                ticks: {
                    autoSkip: true,
                    maxTicksLimit: 20
                }
            }],
            yAxes: [{
                ticks: {
                    beginAtZero: true
                }
            }]
        }
    }
    
};

const configHumidity = {
    type: 'line',
    data: {
        labels: timeStamp,
        datasets: [{
            label: 'Humidité (%)',
            backgroundColor: 'rgba(92, 184, 92, 0.2)', // Vert
            borderColor: 'rgba(92, 184, 92, 1)',
            data: humidityData,
            fill: false,
        }]
    },
};

const configMoist = {
    type: 'line',
    data: {
        labels: timeStamp,
        datasets: [{
            label: 'Humidité (%)',
            backgroundColor: 'rgba(92, 184, 92, 0.2)', // Vert
            borderColor: 'rgba(92, 184, 92, 1)',
            data: moistData,
            fill: false,
        }]
    },
};

var configVoltage = {
    type: 'line',
    data: {
        labels: powerTimestamp,
        datasets: [{
            label: 'Puissance (W)',
            backgroundColor: 'rgba(255, 206, 86, 0.2)',
            borderColor: 'rgba(255, 206, 86, 1)',
            data: voltageData,
            fill: true,
        }]
    },
};

const lines =
{
    id: 'lines',
    afterDatasetsDraw(chart) {
        const { ctx, data, chartArea: { height, bottom } } = chart;
        ctx.save();
        const meta = chart.getDatasetMeta(0);

        if (meta && meta.data && meta.data.length > 0) {
            const xPos = meta.data[0].x;
            const barThickness = meta.data[0].width / 2;
            const singleUnit = height / data.datasets[0].max;

            ctx.translate(xPos, bottom);

            drawLine(barThickness, 10, data.datasets[0].low)
            drawLine(barThickness, 10, data.datasets[0].mid)
            drawLine(barThickness, 10, data.datasets[0].high)

            function drawLine(x, y, val) {
                ctx.beginPath();
                ctx.strokeStyle = 'grey';
                ctx.moveTo(x, y - singleUnit * val);
                ctx.lineTo(x, y - singleUnit * val);
                ctx.stroke();
            }

            ctx.font = 'bold 12px sans-serif';
            ctx.fillStyle = 'grey';
            ctx.textBaseline = 'middle';
            ctx.textAlign = 'center';
            ctx.fillText(data.datasets[0].low, barThickness + 25, 0 - singleUnit * data.datasets[0].low)
            ctx.fillText(data.datasets[0].mid, barThickness + 25, 0 - singleUnit * data.datasets[0].mid)
            ctx.fillText(data.datasets[0].high, barThickness + 25, 0 - singleUnit * data.datasets[0].high)

            ctx.font = 'bold 14px sans-serif';
            ctx.fillStyle = 'grey';
            ctx.fillText(data.datasets[0].data, barThickness - 80, 0 - singleUnit * data.datasets[0].data)

            ctx.restore();
        }
    }
}

var configCurrentTemp = {
    type: 'bar',
    data: {
        labels: ["Température (°C)"],
        datasets: [{
            backgroundColor: 'rgba(255, 99, 132, 0.2)',
            data: [],
            fill: true,
            high: 40,
            mid: 20,
            low: 0,
            max: 50,
        }]
    },
    options: {
        barPercentage: 0.2,
        borderRadius: 20,
        scales: {
            x: {
                grid: {
                    display: false
                },
                border: {
                    display: false
                }
            },
            y: {
                max: 50,
                grid: {
                    display: false
                },
                border: {
                    display: false
                },
                ticks: {
                    display: false
                }
            }
        },
        aspectRatio: 0.8,
        plugins: {
            legend: {
                display: false
            },
        }
    },
    plugins: [lines],
};

var configCurrentHumidity = {
    type: 'bar',
    data: {
        labels: ["Humidité (%)"],
        datasets: [{
            backgroundColor: 'rgba(92, 184, 92, 0.2)',
            data: [],
            fill: true,
            high: 90,
            mid: 50,
            low: 10,
            max: 100,
        }]
    },
    options: {
        barPercentage: 0.2,
        borderRadius: 20,
        scales: {
            x: {
                grid: {
                    display: false
                },
                border: {
                    display: false
                }
            },
            y: {
                beginAtZero: true,
                max: 100,
                grid: {
                    display: false
                },
                border: {
                    display: false
                },
                ticks: {
                    display: false
                }
            }
        },
        aspectRatio: 0.8,
        plugins: {
            legend: {
                display: false
            },
        }
    },
    plugins: [lines],
};

var configWaterLevel = {
    type: 'bar',
    data: {
        labels: ["Niveau de l'eau (%)"],
        datasets: [{
            backgroundColor: 'rgba(75, 192, 192, 0.2)',
            data: [],
            fill: true,
            high: 90,
            mid: 50,
            low: 10,
            max: 100,
        }]
    },
    options: {
        barPercentage: 0.2,
        borderRadius: 20,
        scales: {
            x: {
                grid: {
                    display: false
                },
                border: {
                    display: false
                }
            },
            y: {
                beginAtZero: true,
                max: 100,
                grid: {
                    display: false
                },
                border: {
                    display: false
                },
                ticks: {
                    display: false
                }
            }
        },
        aspectRatio: 0.8,
        plugins: {
            legend: {
                display: false
            },
        }
    },
    plugins: [lines],
};

var configCurrentMoist = {
    type: 'bar',
    data: {
        labels: ["Humidité dans le sol (%)"],
        datasets: [{
            backgroundColor: 'rgba(92, 184, 92, 0.2)',
            data: [],
            fill: true,
            high: 90,
            mid: 50,
            low: 10,
            max: 100,
        }]
    },
    options: {
        barPercentage: 0.2,
        borderRadius: 20,
        scales: {
            x: {
                grid: {
                    display: false
                },
                border: {
                    display: false
                }
            },
            y: {
                beginAtZero: true,
                max: 100,
                grid: {
                    display: false
                },
                border: {
                    display: false
                },
                ticks: {
                    display: false
                }
            }
        },
        aspectRatio: 0.8,
        plugins: {
            legend: {
                display: false
            },
        }
    },
    plugins: [lines],
};

var configPower = {
    type: 'line',
    data: {
        labels: powerTimestamp,
        datasets: [{
            label: 'Puissance (W)',
            backgroundColor: 'rgba(255, 206, 86, 0.2)',
            borderColor: 'rgba(255, 206, 86, 1)',
            data: powerData,
            fill: true,
        }]
    },
};

// Réinitialisation de vos graphiques avec les nouvelles configurations
var temperatureChart = new Chart(document.getElementById('temperatureChart').getContext('2d'), configTemperature);
var humidityChart = new Chart(document.getElementById('humidityChart').getContext('2d'), configHumidity);
var moistChart = new Chart(document.getElementById('moistChart').getContext('2d'), configMoist);
var voltageChart = new Chart(document.getElementById('voltageChart').getContext('2d'), configVoltage);
var waterChart = new Chart(document.getElementById('waterLevelChart').getContext('2d'), configWaterLevel);
var temperatureGauge = new Chart(document.getElementById('temperatureGauge').getContext('2d'), configCurrentTemp);
var humidityGauge = new Chart(document.getElementById('humidityGauge').getContext('2d'), configCurrentHumidity);
var moistGauge = new Chart(document.getElementById('moistGauge').getContext('2d'), configCurrentMoist);
var powerChart = new Chart(document.getElementById('powerChart').getContext('2d'), configPower);

var temperatureChartCarousel = new Chart(document.getElementById('temperatureChartCarousel').getContext('2d'), configTemperature);
var humidityChartCarousel = new Chart(document.getElementById('humidityChartCarousel').getContext('2d'), configHumidity);
var moistChartCarousel = new Chart(document.getElementById('moistChartCarousel').getContext('2d'), configMoist);
var voltageChartCarousel = new Chart(document.getElementById('voltageChartCarousel').getContext('2d'), configVoltage);
var waterChartCarousel = new Chart(document.getElementById('waterLevelChartCarousel').getContext('2d'), configWaterLevel);
var temperatureGaugeCarousel = new Chart(document.getElementById('temperatureGaugeCarousel').getContext('2d'), configCurrentTemp);
var humidityGaugeCarousel = new Chart(document.getElementById('humidityGaugeCarousel').getContext('2d'), configCurrentHumidity);
var moistGaugeCarousel = new Chart(document.getElementById('moistGaugeCarousel').getContext('2d'), configCurrentMoist);
var powerChartCarousel = new Chart(document.getElementById('powerChartCarousel').getContext('2d'), configPower);

// Fonction pour mettre à jour les graphiques
function updateCharts(data) {

    if (!initialized) {
        data.forEach(function (item) {
            temperatureData.push(item.temperature);
            humidityData.push(item.humidity);
            moistData.push(item.moist);
            voltageData.push(item.voltage);
            powerData.push(item.power);
            timeStamp.push(item.timestamp);
            if(item.powerTimestamp != null) {
                powerTimestamp.push(item.powerTimestamp);
            }
        });
    }

    initialized = true;

    temperatureChart.update();
    humidityChart.update();
    moistChart.update();
    voltageChart.update(); 
    powerChart.update();
    waterChart.update();
    temperatureGauge.update();
    humidityGauge.update();
    moistGauge.update();

    temperatureChartCarousel.update();
    humidityChartCarousel.update();
    moistChartCarousel.update();
    voltageChartCarousel.update(); 
    powerChartCarousel.update();
    waterChartCarousel.update();
    temperatureGaugeCarousel.update();
    humidityGaugeCarousel.update();
    moistGaugeCarousel.update();
}