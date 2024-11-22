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

// Fonction pour établir la connexion WebSocket
function wsConnect() {
    ws = new WebSocket(wsUri);

    ws.onmessage = function (msg) {
        var dataArray = JSON.parse(msg.data);

        initializeCharts(dataArray);

        // Remplacez la partie correspondante de la fonction ws.onmessage
        if (Array.isArray(dataArray) && dataArray.length > 0) {
            var data = dataArray[dataArray.length - 1];

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

            // Mettre à jour les graphiques avec les nouvelles données
            updateCharts();
        }

    };

    ws.onopen = function () {
        updateStatus("connected");
    };

    ws.onclose = function () {
        updateStatus("not connected");
        setTimeout(wsConnect, 3000);
    };

    function updateStatus(status) {
        var badge = document.getElementById('badge');
        badge.className = 'badge ' + (status === 'connected' ? 'badge-green' : 'badge-red');
    }

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
        labels: timeStamp,
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
            ctx.fillText(data.datasets[0].data, barThickness - 60, 0 - singleUnit * data.datasets[0].data)

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
        labels: timeStamp,
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
var temperatureGauge = new Chart(document.getElementById('tempetureGauge').getContext('2d'), configCurrentTemp);
var humidityGauge = new Chart(document.getElementById('humidityGauge').getContext('2d'), configCurrentHumidity);
var moistGauge = new Chart(document.getElementById('moistGauge').getContext('2d'), configCurrentMoist);
var powerChart = new Chart(document.getElementById('powerChart').getContext('2d'), configPower);

var initialized = false;

// Fonction pour initialiser les graphiques
function initializeCharts(data) {
    if (!initialized) {
        data.forEach(function (item) {
            temperatureData.push(item.temperature);
            humidityData.push(item.humidity);
            moistData.push(item.moist);
            voltageData.push(item.voltage);
            powerData.push(item.power);
            timeStamp.push(item.timestamp);
        });
        // Mettre à jour les graphiques avec les valeurs initiales
        updateCharts();

        // Marquer les tableaux comme initialisés
        initialized = true;
    }
}

// Fonction pour mettre à jour les graphiques
function updateCharts() {
    temperatureChart.update();
    humidityChart.update();
    moistChart.update();
    voltageChart.update();
    powerChart.update();
    waterChart.update();
    temperatureGauge.update();
    humidityGauge.update();
    moistGauge.update();
}