if (typeof ChartDataLabels !== 'undefined') {
    Chart.register(ChartDataLabels);
}

/**
 * Initialise les graphiques pour chaque clé de chartDataMap non nulle.
 * La correspondance entre la clé et le conteneur est définie dans chartConfigs.
 */
export function initCharts(chartDataMap = {}) {
    const chartConfigs = [
        { key: 'chart', containerId: 'charts-container' },
        { key: 'compare', containerId: 'charts-container-compare' },
        { key: 'radar', containerId: 'charts-container-radar' }
    ];

    chartConfigs.forEach(({ key, containerId }) => {
        // On ne traite que si des données existent pour cette clé
        if (!chartDataMap.hasOwnProperty(key) || chartDataMap[key] === null) {
            console.log(`Aucune donnée pour la clé '${key}' — graphique non initialisé.`);
            return;
        }

        let chartData = chartDataMap[key];

        // Si les données sont une chaîne, on essaie de les parser
        if (typeof chartData === 'string') {
            try {
                chartData = JSON.parse(chartData);
            } catch (e) {
                console.error("Erreur lors du parsing des données pour la clé", key, e);
                return;
            }
        }

        // Récupération du conteneur et nettoyage de son contenu
        const container = document.getElementById(containerId);
        if (!container) {
            console.warn(`Conteneur '${containerId}' introuvable pour la clé '${key}'.`);
            return;
        }
        container.innerHTML = "";
        const chartColor = container.dataset.chartColor || "#333333";

        // Parcours de chaque configuration de graphique contenu dans chartData
        chartData.forEach((chartConfig, index) => {
            const canvas = document.createElement('canvas');
            canvas.id = `${containerId}-chart-${index}`;
            container.appendChild(canvas);
            const ctx = canvas.getContext('2d');

            let config;
            if (chartConfig.type === 'radar' && chartConfig.options) {
                // Mise à jour du titre et des options spécifiques au graphique radar
                if (chartConfig.options.plugins && chartConfig.options.plugins.title && chartColor) {
                    chartConfig.options.plugins.title.color = chartColor;
                }
                chartConfig.options.scales = chartConfig.options.scales || {};
                chartConfig.options.scales.r = chartConfig.options.scales.r || {};

                // Ticks
                chartConfig.options.scales.r.ticks = chartConfig.options.scales.r.ticks || {};
                chartConfig.options.scales.r.ticks.color = chartColor;
                chartConfig.options.scales.r.ticks.font = {
                    family: 'Arial',
                    size: 14,
                    weight: 'bold'
                };
                chartConfig.options.scales.r.ticks.backdropColor = 'transparent';

                // Labels périphériques
                chartConfig.options.scales.r.pointLabels = chartConfig.options.scales.r.pointLabels || {};
                chartConfig.options.scales.r.pointLabels.color = chartColor;
                chartConfig.options.scales.r.pointLabels.font = {
                    family: 'Arial',
                    size: 16,
                    weight: 'bold'
                };

                // Grille
                chartConfig.options.scales.r.grid = chartConfig.options.scales.r.grid || {};
                chartConfig.options.scales.r.grid.color = chartColor.toLowerCase() === '#e0e0e0'
                    ? "rgba(224, 224, 224, 0.3)"
                    : "rgba(0, 0, 0, 0.1)";

                // Lignes d'angle
                chartConfig.options.scales.r.angleLines = chartConfig.options.scales.r.angleLines || {};
                chartConfig.options.scales.r.angleLines.color = chartColor.toLowerCase() === '#e0e0e0'
                    ? "rgba(224, 224, 224, 0.3)"
                    : "rgba(128, 128, 128, 0.2)";

                // Légende
                chartConfig.options.plugins = chartConfig.options.plugins || {};
                chartConfig.options.plugins.legend = chartConfig.options.plugins.legend || {
                    labels: {
                        color: chartColor,
                        font: {
                            family: 'Arial',
                            size: 14,
                            weight: 'bold'
                        }
                    }
                };
                if (chartConfig.options.plugins.legend.labels) {
                    chartConfig.options.plugins.legend.labels.color = chartColor;
                    chartConfig.options.plugins.legend.labels.font = {
                        family: 'Arial',
                        size: 14,
                        weight: 'bold'
                    };
                }

                // Désactivation des DataLabels pour le radar
                chartConfig.options.plugins.datalabels = { display: false };

                config = chartConfig;
            } else {
                // Configuration par défaut pour les autres types de graphiques
                let options = {
                    responsive: true,
                    plugins: {
                        title: {
                            display: true,
                            text: chartConfig.chartTitle,
                            font: { size: 18 },
                            color: chartColor
                        },
                        legend: {
                            display: true,
                            position: 'top',
                            labels: {
                                font: { size: 14 },
                                color: chartColor,
                                padding: 20
                            }
                        },
                        datalabels: chartConfig.type === 'bar'
                            ? {
                                display: true,
                                anchor: 'center',
                                align: 'center',
                                color: 'white',
                                font: {
                                    size: 16,
                                    weight: 'bold'
                                },
                                formatter: function(value, context) {
                                    return context.dataset.originalData
                                        ? context.dataset.originalData[context.dataIndex]
                                        : value;
                                }
                            }
                            : { display: false }
                    }
                };

                config = {
                    type: chartConfig.type,
                    data: {
                        labels: chartConfig.labels,
                        datasets: chartConfig.datasets
                    },
                    options: options
                };
            }

            try {
                new Chart(ctx, config);
                console.log(`Graphique créé pour '${containerId}' à l'index ${index}`);
            } catch (e) {
                console.error(`Erreur lors de la création du graphique dans '${containerId}' à l'index ${index}:`, e);
            }
        });
    });

    // En cas d'absence de conteneur pour l'une des configurations, on réessaie après un court délai.
    if (!chartConfigs.some(({ containerId, key }) =>
        document.getElementById(containerId) && chartDataMap.hasOwnProperty(key)
    )) {
        console.warn("Aucun conteneur de graphiques trouvé. Nouvel essai dans 100ms...");
        setTimeout(() => initCharts(chartDataMap), 100);
    }
}

/**
 * Charge les données via AJAX, affiche les messages d'erreur et initialise les graphiques
 * uniquement si au moins une des parties de data.charts n'est pas null.
 */
export function loadChartsData() {
    fetch('/BDM/ajax/get-charts/')
        .then(response => response.json())
        .then(data => {
            console.log("Données AJAX reçues :", data);

            // Traitement générique des messages d'erreur
            if (data.error) {
                Object.keys(data.error).forEach(errorKey => {
                    const errorMessage = data.error[errorKey];
                    const chartName = errorKey.replace('error_message_', '');
                    const errorEl = document.getElementById(`error-message-${chartName}`);
                    const contentEl = document.getElementById(`${chartName}-content`);

                    if (errorEl) {
                        if (errorMessage) {
                            errorEl.textContent = errorMessage;
                            errorEl.style.display = 'block';
                            if (contentEl) contentEl.style.display = 'none';
                        } else {
                            errorEl.style.display = 'none';
                            if (contentEl) contentEl.style.display = 'block';
                        }
                    }
                });
            }

            // Vérifier si au moins une partie des données de charts est non nulle
            let hasChartData = false;
            if (data.charts && typeof data.charts === 'object') {
                Object.keys(data.charts).forEach(key => {
                    if (data.charts[key] !== null) {
                        hasChartData = true;
                    }
                });
            }

            if (hasChartData) {
                initCharts(data.charts);
            } else {
                console.log("Aucun graphique à initialiser : toutes les parties de data.charts sont null.");
            }
        })
        .catch(error => {
            console.error("Erreur lors du chargement des données graphiques AJAX :", error);
        });
}