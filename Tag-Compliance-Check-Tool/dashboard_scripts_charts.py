"""
Dashboard Scripts - Charts Module

Handles Chart.js initialization and configuration.
"""

from typing import Dict


class DashboardChartsGenerator:
    """Generates Chart.js related JavaScript code"""
    
    def generate_chart_initialization_code(self, dashboard_data: Dict, safe_json) -> str:
        """Generate chart initialization JavaScript code"""
        return f"""
        function initializeCharts() {{
            // Compliance Status Pie Chart
            const complianceCtx = document.getElementById('complianceChart').getContext('2d');
            new Chart(complianceCtx, {{
                type: 'doughnut',
                data: {{
                    labels: {safe_json(dashboard_data['compliance_data']['labels'])},
                    datasets: [{{
                        data: {safe_json(dashboard_data['compliance_data']['data'])},
                        backgroundColor: {safe_json(dashboard_data['compliance_data']['colors'])},
                        borderWidth: 3,
                        borderColor: '#fff',
                        hoverBorderWidth: 5
                    }}]
                }},
                options: {{
                    responsive: true,
                    maintainAspectRatio: false,
                    plugins: {{
                        legend: {{
                            position: 'bottom',
                            labels: {{
                                usePointStyle: true,
                                padding: 20
                            }}
                        }},
                        tooltip: {{
                            callbacks: {{
                                label: function(context) {{
                                    const total = context.dataset.data.reduce((a, b) => a + b, 0);
                                    const percentage = ((context.parsed / total) * 100).toFixed(1);
                                    return context.label + ': ' + context.parsed.toLocaleString() + ' (' + percentage + '%)';
                                }}
                            }}
                        }}
                    }},
                    cutout: '50%'
                }}
            }});

            {self._generate_tagging_chart(dashboard_data, safe_json)}
            
            {self._generate_score_distribution_chart(dashboard_data, safe_json)}
            
            {self._generate_resource_type_chart(dashboard_data, safe_json)}
            
            {self._generate_subscription_chart()}
        }}
        """
    
    def _generate_tagging_chart(self, dashboard_data: Dict, safe_json) -> str:
        """Generate tagging status chart"""
        return f"""
            // Tagging Status Pie Chart
            const taggingCtx = document.getElementById('taggingChart').getContext('2d');
            new Chart(taggingCtx, {{
                type: 'doughnut',
                data: {{
                    labels: {safe_json(dashboard_data['tagging_data']['labels'])},
                    datasets: [{{
                        data: {safe_json(dashboard_data['tagging_data']['data'])},
                        backgroundColor: {safe_json(dashboard_data['tagging_data']['colors'])},
                        borderWidth: 3,
                        borderColor: '#fff',
                        hoverBorderWidth: 5
                    }}]
                }},
                options: {{
                    responsive: true,
                    maintainAspectRatio: false,
                    plugins: {{
                        legend: {{
                            position: 'bottom',
                            labels: {{
                                usePointStyle: true,
                                padding: 20
                            }}
                        }},
                        tooltip: {{
                            callbacks: {{
                                label: function(context) {{
                                    const total = context.dataset.data.reduce((a, b) => a + b, 0);
                                    const percentage = ((context.parsed / total) * 100).toFixed(1);
                                    return context.label + ': ' + context.parsed.toLocaleString() + ' (' + percentage + '%)';
                                }}
                            }}
                        }}
                    }},
                    cutout: '50%'
                }}
            }});
        """
    
    def _generate_score_distribution_chart(self, dashboard_data: Dict, safe_json) -> str:
        """Generate score distribution chart"""
        return f"""
            // Score Distribution Chart
            const scoreDistCtx = document.getElementById('scoreDistChart').getContext('2d');
            new Chart(scoreDistCtx, {{
                type: 'bar',
                data: {{
                    labels: {safe_json(dashboard_data['score_distribution']['labels'])},
                    datasets: [{{
                        label: 'Subscriptions',
                        data: {safe_json(dashboard_data['score_distribution']['data'])},
                        backgroundColor: {safe_json(dashboard_data['score_distribution']['colors'])},
                        borderRadius: 8,
                        borderWidth: 2,
                        borderColor: '#fff'
                    }}]
                }},
                options: {{
                    responsive: true,
                    maintainAspectRatio: false,
                    plugins: {{
                        legend: {{
                            display: false
                        }}
                    }},
                    scales: {{
                        y: {{
                            beginAtZero: true,
                            ticks: {{
                                stepSize: 1
                            }},
                            title: {{
                                display: true,
                                text: 'Number of Subscriptions'
                            }}
                        }},
                        x: {{
                            title: {{
                                display: true,
                                text: 'Compliance Score Range'
                            }}
                        }}
                    }}
                }}
            }});
        """
    
    def _generate_resource_type_chart(self, dashboard_data: Dict, safe_json) -> str:
        """Generate resource type chart"""
        return f"""
            // Resource Type Chart
            const resourceTypeCtx = document.getElementById('resourceTypeChart').getContext('2d');
            new Chart(resourceTypeCtx, {{
                type: 'bar',
                data: {{
                    labels: {safe_json(dashboard_data['resource_type_data']['labels'])},
                    datasets: [{{
                        label: 'Resource Count',
                        data: {safe_json(dashboard_data['resource_type_data']['data'])},
                        backgroundColor: 'rgba(68, 114, 196, 0.8)',
                        borderColor: 'rgba(68, 114, 196, 1)',
                        borderWidth: 2,
                        borderRadius: 5
                    }}]
                }},
                options: {{
                    responsive: true,
                    maintainAspectRatio: false,
                    indexAxis: 'y',
                    plugins: {{
                        legend: {{
                            display: false
                        }}
                    }},
                    scales: {{
                        x: {{
                            beginAtZero: true,
                            title: {{
                                display: true,
                                text: 'Number of Resources'
                            }}
                        }}
                    }}
                }}
            }});
        """
    
    def _generate_subscription_chart(self) -> str:
        """Generate subscription chart with drill-down"""
        return """
            // Subscription Chart with drill-down capability
            const subCtx = document.getElementById('subscriptionChart').getContext('2d');
            new Chart(subCtx, {
                type: 'bar',
                data: {
                    labels: subscriptionData.labels,
                    datasets: [{
                        label: 'Full Compliance %',
                        data: subscriptionData.full_compliance,
                        backgroundColor: 'rgba(40, 167, 69, 0.8)',
                        borderColor: 'rgba(40, 167, 69, 1)',
                        borderWidth: 2,
                        borderRadius: 8,
                        stack: 'stack0'
                    }, {
                        label: 'Partial Compliance %',
                        data: subscriptionData.partial_compliance,
                        backgroundColor: 'rgba(255, 193, 7, 0.8)',
                        borderColor: 'rgba(255, 193, 7, 1)',
                        borderWidth: 2,
                        borderRadius: 8,
                        stack: 'stack0'
                    }, {
                        label: 'Resource Count',
                        data: subscriptionData.resource_counts,
                        backgroundColor: 'rgba(108, 117, 125, 0.3)',
                        borderColor: 'rgba(108, 117, 125, 1)',
                        borderWidth: 2,
                        borderRadius: 8,
                        yAxisID: 'y1',
                        type: 'line'
                    }]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    interaction: {
                        mode: 'index',
                        intersect: false
                    },
                    plugins: {
                        legend: {
                            position: 'top'
                        }
                    },
                    scales: {
                        y: {
                            beginAtZero: true,
                            max: 100,
                            stacked: true,
                            title: {
                                display: true,
                                text: 'Compliance Percentage (%)'
                            }
                        },
                        y1: {
                            beginAtZero: true,
                            position: 'right',
                            title: {
                                display: true,
                                text: 'Resource Count'
                            },
                            grid: {
                                drawOnChartArea: false
                            }
                        },
                        x: {
                            stacked: true,
                            ticks: {
                                maxRotation: 45,
                                minRotation: 0
                            }
                        }
                    },
                    onClick: (event, elements) => {
                        if (elements.length > 0) {
                            const index = elements[0].index;
                            const subscriptionName = subscriptionData.labels[index];
                            const subscriptionId = subscriptionData.ids[index];
                            showResourceDrillDown(subscriptionName, subscriptionId);
                        }
                    }
                }
            });
        """
