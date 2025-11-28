"""Interactive dashboard generator with drill-down capabilities"""

import json
import logging
from datetime import datetime
from typing import Dict, List, Any, Optional
from pathlib import Path
from collections import defaultdict
from jinja2 import Template

from ..core.interfaces import IDashboardGenerator
from ..core.models import EnhancedOrphanedResource, SeverityLevel
from ..utils.logger import setup_logger


class DashboardGenerator(IDashboardGenerator):
    """Generate interactive HTML dashboard with drill-down capabilities"""
    
    def __init__(self):
        self.logger = setup_logger(self.__class__.__name__)
    
    def generate_dashboard(
        self, 
        resources: List[EnhancedOrphanedResource], 
        output_path: str,
        config: Optional[Dict[str, Any]] = None
    ) -> str:
        """Generate interactive dashboard"""
        
        config = config or {}
        
        try:
            # Prepare dashboard data
            dashboard_data = self._prepare_dashboard_data(resources)
            
            # Load template
            template_content = self._get_dashboard_template()
            template = Template(template_content)
            
            # Render dashboard
            rendered_html = template.render(
                dashboard_data=json.dumps(dashboard_data, default=str),
                total_resources=len(resources),
                total_monthly_cost=sum(r.cost_analysis.current_monthly_cost for r in resources),
                timestamp=datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                config=config
            )
            
            # Write to file
            output_file = Path(output_path)
            output_file.parent.mkdir(parents=True, exist_ok=True)
            
            with open(output_file, 'w', encoding='utf-8') as f:
                f.write(rendered_html)
            
            self.logger.info(f"Interactive dashboard generated: {output_path}")
            return str(output_file.absolute())
            
        except Exception as e:
            self.logger.error(f"Failed to generate dashboard: {e}")
            raise
    
    def _prepare_dashboard_data(self, resources: List[EnhancedOrphanedResource]) -> Dict[str, Any]:
        """Prepare data for dashboard"""
        
        data = {
            'summary': self._get_summary_stats(resources),
            'resources': [],
            'charts': {
                'cost_by_type': self._get_cost_by_type(resources),
                'cost_by_subscription': self._get_cost_by_subscription(resources),
                'severity_distribution': self._get_severity_distribution(resources),
                'cleanup_priority': self._get_cleanup_priority_data(resources)
            }
        }
        
        # Prepare resource details for drill-down
        for resource in resources:
            resource_data = {
                'id': resource.resource_id,
                'name': resource.resource_name,
                'type': resource.resource_type.value,
                'type_display': resource.resource_type.value.split('/')[-1],
                'subscription': resource.subscription_id,
                'subscription_name': resource.subscription_name or resource.subscription_id[:8] + "...",
                'resource_group': resource.resource_group,
                'location': resource.location,
                'monthly_cost': resource.cost_analysis.current_monthly_cost,
                'annual_cost': resource.cost_analysis.projected_annual_cost,
                'potential_savings': resource.cost_analysis.potential_savings,
                'severity': resource.severity.value,
                'confidence': resource.confidence_score,
                'orphan_reason': resource.orphanage_reason.value,
                'cleanup_priority': resource.cleanup_priority,
                'created_date': resource.created_date.isoformat() if resource.created_date else None,
                'last_used': resource.last_used.isoformat() if resource.last_used else None,
                'tags': resource.tags,
                'details': resource.details,
                'recommended_actions': resource.recommended_actions,
                'alternative_solutions': resource.alternative_solutions,
                'security_risks': resource.security_analysis.security_risks,
                'dependencies': resource.dependencies,
                'dependents': resource.dependents,
                'business_owner': resource.business_owner,
                'project_code': resource.project_code,
                'environment': resource.environment,
                'cost_breakdown': resource.cost_analysis.cost_breakdown,
                'optimization_suggestions': resource.cost_analysis.optimization_suggestions
            }
            data['resources'].append(resource_data)
        
        return data
    
    def _get_summary_stats(self, resources: List[EnhancedOrphanedResource]) -> Dict[str, Any]:
        """Get summary statistics"""
        
        if not resources:
            return {
                'total_resources': 0,
                'total_monthly_cost': 0.0,
                'total_annual_cost': 0.0,
                'avg_confidence': 0.0,
                'by_severity': {},
                'subscription_count': 0,
                'high_priority_count': 0
            }
        
        total_monthly = sum(r.cost_analysis.current_monthly_cost for r in resources)
        by_severity = defaultdict(int)
        by_subscription = defaultdict(int)
        
        high_priority_count = 0
        total_confidence = 0.0
        
        for resource in resources:
            by_severity[resource.severity.value] += 1
            by_subscription[resource.subscription_id] += 1
            
            if resource.cleanup_priority <= 3:
                high_priority_count += 1
            
            total_confidence += resource.confidence_score
        
        return {
            'total_resources': len(resources),
            'total_monthly_cost': total_monthly,
            'total_annual_cost': total_monthly * 12,
            'avg_confidence': total_confidence / len(resources),
            'by_severity': dict(by_severity),
            'subscription_count': len(by_subscription),
            'high_priority_count': high_priority_count
        }
    
    def _get_cost_by_type(self, resources: List[EnhancedOrphanedResource]) -> List[Dict[str, Any]]:
        """Get cost breakdown by resource type"""
        by_type = defaultdict(lambda: {'cost': 0.0, 'count': 0})
        
        for resource in resources:
            resource_type = resource.resource_type.value.split('/')[-1]
            by_type[resource_type]['cost'] += resource.cost_analysis.current_monthly_cost
            by_type[resource_type]['count'] += 1
        
        return [
            {
                'type': k, 
                'cost': v['cost'], 
                'count': v['count'],
                'avg_cost': v['cost'] / v['count'] if v['count'] > 0 else 0
            }
            for k, v in sorted(by_type.items(), key=lambda x: x[1]['cost'], reverse=True)
        ]
    
    def _get_cost_by_subscription(self, resources: List[EnhancedOrphanedResource]) -> List[Dict[str, Any]]:
        """Get cost breakdown by subscription"""
        by_subscription = defaultdict(lambda: {'cost': 0.0, 'count': 0, 'name': ''})
        
        for resource in resources:
            sub_id = resource.subscription_id
            sub_name = resource.subscription_name or sub_id[:8] + "..."
            by_subscription[sub_id]['cost'] += resource.cost_analysis.current_monthly_cost
            by_subscription[sub_id]['count'] += 1
            by_subscription[sub_id]['name'] = sub_name
        
        return [
            {
                'subscription': v['name'], 
                'subscription_id': k,
                'cost': v['cost'], 
                'count': v['count']
            }
            for k, v in sorted(by_subscription.items(), key=lambda x: x[1]['cost'], reverse=True)
        ]
    
    def _get_severity_distribution(self, resources: List[EnhancedOrphanedResource]) -> List[Dict[str, Any]]:
        """Get severity distribution"""
        by_severity = defaultdict(lambda: {'count': 0, 'cost': 0.0})
        
        for resource in resources:
            severity = resource.severity.value
            by_severity[severity]['count'] += 1
            by_severity[severity]['cost'] += resource.cost_analysis.current_monthly_cost
        
        return [
            {
                'severity': k, 
                'count': v['count'], 
                'cost': v['cost']
            }
            for k, v in by_severity.items()
        ]
    
    def _get_cleanup_priority_data(self, resources: List[EnhancedOrphanedResource]) -> List[Dict[str, Any]]:
        """Get cleanup priority distribution"""
        by_priority = defaultdict(lambda: {'count': 0, 'cost': 0.0})
        
        for resource in resources:
            if resource.cleanup_priority <= 2:
                priority_range = "Critical (1-2)"
            elif resource.cleanup_priority <= 4:
                priority_range = "High (3-4)"
            elif resource.cleanup_priority <= 6:
                priority_range = "Medium (5-6)"
            else:
                priority_range = "Low (7-10)"
            
            by_priority[priority_range]['count'] += 1
            by_priority[priority_range]['cost'] += resource.cost_analysis.current_monthly_cost
        
        return [
            {
                'priority': k, 
                'count': v['count'], 
                'cost': v['cost']
            }
            for k, v in by_priority.items()
        ]
    
    def _get_dashboard_template(self) -> str:
        """Get the HTML template for the dashboard"""
        
        return '''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Azure Orphaned Resources Dashboard</title>
    <script src="https://cdnjs.cloudflare.com/ajax/libs/Chart.js/3.9.1/chart.min.js"></script>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh; color: #333;
        }
        .header {
            background: rgba(255, 255, 255, 0.95); backdrop-filter: blur(10px);
            padding: 2rem; box-shadow: 0 8px 32px rgba(0, 0, 0, 0.1); margin-bottom: 2rem;
        }
        .header h1 {
            color: #2c3e50; font-size: 2.5rem; margin-bottom: 1rem; text-align: center;
        }
        .header-stats {
            display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 1.5rem; margin-top: 1.5rem;
        }
        .header-stat {
            text-align: center; padding: 1rem;
            background: linear-gradient(45deg, #f8f9fa, #e9ecef);
            border-radius: 8px; border-left: 4px solid #4a90e2;
        }
        .header-stat-value {
            font-size: 2rem; font-weight: bold; color: #2c3e50; margin-bottom: 0.5rem;
        }
        .header-stat-label {
            color: #666; font-size: 0.9rem; text-transform: uppercase; letter-spacing: 1px;
        }
        .main-container { max-width: 1400px; margin: 0 auto; padding: 0 2rem 2rem 2rem; }
        .charts-grid {
            display: grid; grid-template-columns: repeat(auto-fit, minmax(400px, 1fr));
            gap: 1.5rem; margin-bottom: 2rem;
        }
        .chart-card {
            background: rgba(255, 255, 255, 0.95); backdrop-filter: blur(10px);
            border-radius: 12px; box-shadow: 0 8px 32px rgba(0, 0, 0, 0.1); padding: 1.5rem;
        }
        .chart-title { font-size: 1.3rem; font-weight: 600; color: #2c3e50; margin-bottom: 1rem; }
        .chart-container { position: relative; height: 300px; }
        .resources-section {
            background: rgba(255, 255, 255, 0.95); backdrop-filter: blur(10px);
            border-radius: 12px; box-shadow: 0 8px 32px rgba(0, 0, 0, 0.1); overflow: hidden;
        }
        .section-header {
            padding: 1.5rem; background: linear-gradient(45deg, #4a90e2, #7b68ee);
            color: white; font-size: 1.3rem; font-weight: 600;
        }
        .filters {
            padding: 1rem 1.5rem; background: #f8f9fa; border-bottom: 1px solid #e9ecef;
            display: flex; gap: 1rem; flex-wrap: wrap;
        }
        .filter-group { display: flex; flex-direction: column; gap: 0.25rem; }
        .filter-label {
            font-size: 0.8rem; color: #666; text-transform: uppercase; letter-spacing: 1px;
        }
        .filter-select, .filter-input {
            padding: 0.5rem; border: 1px solid #ddd; border-radius: 6px; font-size: 0.9rem;
        }
        .table-container { overflow-x: auto; max-height: 600px; }
        .resources-table { width: 100%; border-collapse: collapse; background: white; }
        .resources-table th {
            background: #f8f9fa; padding: 1rem; text-align: left; font-weight: 600;
            color: #495057; border-bottom: 2px solid #dee2e6; position: sticky; top: 0; z-index: 10;
        }
        .resources-table td { padding: 1rem; border-bottom: 1px solid #e9ecef; vertical-align: middle; }
        .resource-row { transition: background-color 0.2s ease; cursor: pointer; }
        .resource-row:hover { background-color: #f8f9fa; }
        .severity-badge {
            padding: 0.25rem 0.75rem; border-radius: 12px; font-size: 0.8rem;
            font-weight: 600; text-transform: uppercase; letter-spacing: 1px;
        }
        .severity-critical { background: #dc3545; color: white; }
        .severity-high { background: #fd7e14; color: white; }
        .severity-medium { background: #ffc107; color: #333; }
        .severity-low { background: #28a745; color: white; }
        .severity-info { background: #17a2b8; color: white; }
        .confidence-bar {
            width: 80px; height: 8px; background: #e9ecef; border-radius: 4px; overflow: hidden; position: relative;
        }
        .confidence-fill {
            height: 100%; background: linear-gradient(90deg, #dc3545, #fd7e14, #28a745);
            border-radius: 4px; transition: width 0.3s ease;
        }
        .cost-cell { font-weight: 600; color: #dc3545; }
        .modal {
            display: none; position: fixed; z-index: 1000; left: 0; top: 0; width: 100%; height: 100%;
            background-color: rgba(0, 0, 0, 0.5); backdrop-filter: blur(5px);
        }
        .modal-content {
            background: white; margin: 2% auto; padding: 0; border-radius: 12px; width: 95%;
            max-width: 1000px; max-height: 90vh; overflow-y: auto; box-shadow: 0 20px 60px rgba(0, 0, 0, 0.3);
        }
        .modal-header {
            padding: 1.5rem; background: linear-gradient(45deg, #4a90e2, #7b68ee); color: white;
            border-radius: 12px 12px 0 0; display: flex; justify-content: space-between; align-items: center;
        }
        .modal-title { font-size: 1.5rem; font-weight: 600; }
        .close { color: white; font-size: 2rem; font-weight: bold; cursor: pointer; transition: opacity 0.3s ease; }
        .close:hover { opacity: 0.7; }
        .modal-body { padding: 2rem; }
        .detail-grid {
            display: grid; grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
            gap: 1.5rem; margin-bottom: 2rem;
        }
        .detail-section {
            background: #f8f9fa; padding: 1.5rem; border-radius: 8px; border-left: 4px solid #4a90e2;
        }
        .detail-section h4 { color: #2c3e50; margin-bottom: 1rem; font-size: 1.1rem; font-weight: 600; }
        .detail-item { margin-bottom: 0.75rem; }
        .detail-label {
            font-size: 0.85rem; color: #666; text-transform: uppercase; letter-spacing: 1px; margin-bottom: 0.25rem;
        }
        .detail-value { font-weight: 600; color: #2c3e50; }
        .btn {
            padding: 0.75rem 1.5rem; border: none; border-radius: 6px; font-weight: 600;
            cursor: pointer; transition: all 0.3s ease; font-size: 0.9rem;
        }
        .btn-primary { background: #4a90e2; color: white; }
        .btn-primary:hover { background: #357abd; transform: translateY(-2px); }
        .export-buttons { display: flex; gap: 1rem; margin-bottom: 1.5rem; }
        @media (max-width: 768px) {
            .charts-grid { grid-template-columns: 1fr; }
            .header { padding: 1rem; }
            .header h1 { font-size: 1.8rem; }
            .filters { flex-direction: column; }
            .modal-content { width: 98%; margin: 1% auto; }
            .detail-grid { grid-template-columns: 1fr; }
        }
    </style>
</head>
<body>
    <div class="header">
        <h1>🔍 Azure Orphaned Resources Dashboard</h1>
        <div class="header-stats">
            <div class="header-stat">
                <div class="header-stat-value" id="totalResources">{{ total_resources }}</div>
                <div class="header-stat-label">Total Resources</div>
            </div>
            <div class="header-stat">
                <div class="header-stat-value" id="totalCost">${{ "%.2f"|format(total_monthly_cost) }}</div>
                <div class="header-stat-label">Monthly Savings</div>
            </div>
            <div class="header-stat">
                <div class="header-stat-value">${{ "%.2f"|format(total_monthly_cost * 12) }}</div>
                <div class="header-stat-label">Annual Savings</div>
            </div>
            <div class="header-stat">
                <div class="header-stat-value">{{ timestamp }}</div>
                <div class="header-stat-label">Generated</div>
            </div>
        </div>
    </div>

    <div class="main-container">
        <!-- Charts -->
        <div class="charts-grid">
            <div class="chart-card">
                <div class="chart-title">💰 Cost by Type</div>
                <div class="chart-container"><canvas id="costByTypeChart"></canvas></div>
            </div>
            <div class="chart-card">
                <div class="chart-title">📊 Cost by Subscription</div>
                <div class="chart-container"><canvas id="costBySubscriptionChart"></canvas></div>
            </div>
            <div class="chart-card">
                <div class="chart-title">🎯 Severity Distribution</div>
                <div class="chart-container"><canvas id="severityChart"></canvas></div>
            </div>
            <div class="chart-card">
                <div class="chart-title">📈 Cleanup Priority</div>
                <div class="chart-container"><canvas id="priorityChart"></canvas></div>
            </div>
        </div>

        <!-- Resources Table -->
        <div class="resources-section">
            <div class="section-header">📋 Detailed Resources</div>
            <div class="filters">
                <div class="export-buttons">
                    <button class="btn btn-primary" onclick="exportToCSV()">📊 Export CSV</button>
                </div>
                <div class="filter-group">
                    <div class="filter-label">Search</div>
                    <input type="text" class="filter-input" id="searchFilter" placeholder="Search resources..." onkeyup="filterResources()">
                </div>
                <div class="filter-group">
                    <div class="filter-label">Severity</div>
                    <select class="filter-select" id="severityFilter" onchange="filterResources()">
                        <option value="">All Severities</option>
                        <option value="critical">Critical</option>
                        <option value="high">High</option>
                        <option value="medium">Medium</option>
                        <option value="low">Low</option>
                        <option value="info">Info</option>
                    </select>
                </div>
                <div class="filter-group">
                    <div class="filter-label">Min Cost</div>
                    <input type="number" class="filter-input" id="costFilter" placeholder="$0" onchange="filterResources()">
                </div>
            </div>
            <div class="table-container">
                <table class="resources-table">
                    <thead>
                        <tr>
                            <th onclick="sortTable('name')">Resource Name 🔽</th>
                            <th onclick="sortTable('type_display')">Type 🔽</th>
                            <th onclick="sortTable('subscription_name')">Subscription 🔽</th>
                            <th onclick="sortTable('monthly_cost')">Monthly Cost 🔽</th>
                            <th onclick="sortTable('severity')">Severity 🔽</th>
                            <th onclick="sortTable('confidence')">Confidence 🔽</th>
                            <th>Actions</th>
                        </tr>
                    </thead>
                    <tbody id="resourcesTableBody">
                        <!-- Populated by JavaScript -->
                    </tbody>
                </table>
            </div>
        </div>
    </div>

    <!-- Resource Details Modal -->
    <div id="resourceModal" class="modal">
        <div class="modal-content">
            <div class="modal-header">
                <div class="modal-title" id="modalTitle">Resource Details</div>
                <span class="close" onclick="closeModal()">&times;</span>
            </div>
            <div class="modal-body" id="modalBody">
                <!-- Populated by JavaScript -->
            </div>
        </div>
    </div>

    <script>
        // Global variables
        let dashboardData = {{ dashboard_data|safe }};
        let filteredResources = [...dashboardData.resources];

        // Initialize dashboard
        document.addEventListener('DOMContentLoaded', function() {
            renderCharts();
            renderResourcesTable();
        });

        function renderCharts() {
            renderCostByTypeChart();
            renderCostBySubscriptionChart();
            renderSeverityChart();
            renderPriorityChart();
        }

        function renderCostByTypeChart() {
            const ctx = document.getElementById('costByTypeChart').getContext('2d');
            const data = dashboardData.charts.cost_by_type;
            
            new Chart(ctx, {
                type: 'doughnut',
                data: {
                    labels: data.map(d => d.type),
                    datasets: [{
                        data: data.map(d => d.cost),
                        backgroundColor: ['#FF6384', '#36A2EB', '#FFCE56', '#4BC0C0', '#9966FF']
                    }]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    plugins: { legend: { position: 'bottom' } }
                }
            });
        }

        function renderCostBySubscriptionChart() {
            const ctx = document.getElementById('costBySubscriptionChart').getContext('2d');
            const data = dashboardData.charts.cost_by_subscription;
            
            new Chart(ctx, {
                type: 'bar',
                data: {
                    labels: data.map(d => d.subscription),
                    datasets: [{
                        label: 'Monthly Cost ($)',
                        data: data.map(d => d.cost),
                        backgroundColor: '#4a90e2'
                    }]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    scales: { y: { beginAtZero: true } }
                }
            });
        }

        function renderSeverityChart() {
            const ctx = document.getElementById('severityChart').getContext('2d');
            const data = dashboardData.charts.severity_distribution;
            
            const severityColors = {
                'critical': '#dc3545', 'high': '#fd7e14', 'medium': '#ffc107',
                'low': '#28a745', 'info': '#17a2b8'
            };
            
            new Chart(ctx, {
                type: 'pie',
                data: {
                    labels: data.map(d => d.severity.toUpperCase()),
                    datasets: [{
                        data: data.map(d => d.count),
                        backgroundColor: data.map(d => severityColors[d.severity] || '#gray')
                    }]
                },
                options: { responsive: true, maintainAspectRatio: false }
            });
        }

        function renderPriorityChart() {
            const ctx = document.getElementById('priorityChart').getContext('2d');
            const data = dashboardData.charts.cleanup_priority;
            
            new Chart(ctx, {
                type: 'bar',
                data: {
                    labels: data.map(d => d.priority),
                    datasets: [{
                        label: 'Resource Count',
                        data: data.map(d => d.count),
                        backgroundColor: ['#dc3545', '#fd7e14', '#ffc107', '#28a745']
                    }]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    scales: { y: { beginAtZero: true } }
                }
            });
        }

        function renderResourcesTable() {
            const tbody = document.getElementById('resourcesTableBody');
            tbody.innerHTML = '';

            filteredResources.forEach((resource) => {
                const row = document.createElement('tr');
                row.className = 'resource-row';
                row.onclick = () => showResourceDetails(resource);

                row.innerHTML = `
                    <td>
                        <div style="font-weight: 600;">${resource.name}</div>
                        <div style="font-size: 0.8rem; color: #666;">${resource.resource_group}</div>
                    </td>
                    <td>${resource.type_display}</td>
                    <td>${resource.subscription_name}</td>
                    <td class="cost-cell">${resource.monthly_cost.toFixed(2)}</td>
                    <td>
                        <span class="severity-badge severity-${resource.severity}">${resource.severity}</span>
                    </td>
                    <td>
                        <div class="confidence-bar">
                            <div class="confidence-fill" style="width: ${resource.confidence * 100}%"></div>
                        </div>
                        <div style="font-size: 0.8rem; text-align: center; margin-top: 4px;">
                            ${Math.round(resource.confidence * 100)}%
                        </div>
                    </td>
                    <td>
                        <button class="btn btn-primary" style="padding: 0.5rem 1rem; font-size: 0.8rem;" onclick="event.stopPropagation(); showResourceDetails(resource)">
                            Details
                        </button>
                    </td>
                `;
                
                tbody.appendChild(row);
            });
        }

        function filterResources() {
            const searchTerm = document.getElementById('searchFilter').value.toLowerCase();
            const severityFilter = document.getElementById('severityFilter').value;
            const costFilter = parseFloat(document.getElementById('costFilter').value) || 0;

            filteredResources = dashboardData.resources.filter(resource => {
                const matchesSearch = !searchTerm || 
                    resource.name.toLowerCase().includes(searchTerm) ||
                    resource.resource_group.toLowerCase().includes(searchTerm) ||
                    resource.type_display.toLowerCase().includes(searchTerm);
                
                const matchesSeverity = !severityFilter || resource.severity === severityFilter;
                const matchesCost = resource.monthly_cost >= costFilter;

                return matchesSearch && matchesSeverity && matchesCost;
            });

            renderResourcesTable();
        }

        function sortTable(column) {
            filteredResources.sort((a, b) => {
                let aVal = a[column];
                let bVal = b[column];
                if (typeof aVal === 'string') {
                    return aVal.localeCompare(bVal);
                } else {
                    return aVal - bVal;
                }
            });
            renderResourcesTable();
        }

        function showResourceDetails(resource) {
            const modal = document.getElementById('resourceModal');
            const modalTitle = document.getElementById('modalTitle');
            const modalBody = document.getElementById('modalBody');

            modalTitle.textContent = `${resource.name} - Detailed Analysis`;

            modalBody.innerHTML = `
                <div class="detail-grid">
                    <div class="detail-section">
                        <h4>📋 Basic Information</h4>
                        <div class="detail-item">
                            <div class="detail-label">Resource Type</div>
                            <div class="detail-value">${resource.type_display}</div>
                        </div>
                        <div class="detail-item">
                            <div class="detail-label">Location</div>
                            <div class="detail-value">${resource.location}</div>
                        </div>
                        <div class="detail-item">
                            <div class="detail-label">Resource Group</div>
                            <div class="detail-value">${resource.resource_group}</div>
                        </div>
                        <div class="detail-item">
                            <div class="detail-label">Subscription</div>
                            <div class="detail-value">${resource.subscription_name}</div>
                        </div>
                    </div>

                    <div class="detail-section">
                        <h4>💰 Cost Analysis</h4>
                        <div class="detail-item">
                            <div class="detail-label">Monthly Cost</div>
                            <div class="detail-value" style="color: #dc3545; font-size: 1.2rem;">${resource.monthly_cost.toFixed(2)}</div>
                        </div>
                        <div class="detail-item">
                            <div class="detail-label">Annual Cost</div>
                            <div class="detail-value" style="color: #dc3545;">${resource.annual_cost.toFixed(2)}</div>
                        </div>
                        <div class="detail-item">
                            <div class="detail-label">Potential Savings</div>
                            <div class="detail-value" style="color: #28a745;">${resource.potential_savings.toFixed(2)}</div>
                        </div>
                    </div>

                    <div class="detail-section">
                        <h4>🎯 Risk Assessment</h4>
                        <div class="detail-item">
                            <div class="detail-label">Severity</div>
                            <div class="detail-value">
                                <span class="severity-badge severity-${resource.severity}">${resource.severity.toUpperCase()}</span>
                            </div>
                        </div>
                        <div class="detail-item">
                            <div class="detail-label">Confidence Score</div>
                            <div class="detail-value">
                                <div class="confidence-bar" style="width: 120px;">
                                    <div class="confidence-fill" style="width: ${resource.confidence * 100}%"></div>
                                </div>
                                <span style="margin-left: 10px;">${Math.round(resource.confidence * 100)}%</span>
                            </div>
                        </div>
                        <div class="detail-item">
                            <div class="detail-label">Cleanup Priority</div>
                            <div class="detail-value">${resource.cleanup_priority}/10</div>
                        </div>
                        <div class="detail-item">
                            <div class="detail-label">Orphan Reason</div>
                            <div class="detail-value">${resource.orphan_reason}</div>
                        </div>
                    </div>
                </div>

                ${resource.recommended_actions && resource.recommended_actions.length > 0 ? `
                <div style="margin: 2rem 0;">
                    <h4 style="margin-bottom: 1rem; color: #2c3e50;">💡 Recommended Actions</h4>
                    <ul style="list-style: none; padding: 0;">
                        ${resource.recommended_actions.map(action => 
                            `<li style="padding: 0.5rem 0; border-bottom: 1px solid #e9ecef;">• ${action}</li>`
                        ).join('')}
                    </ul>
                </div>
                ` : ''}

                ${resource.security_risks && resource.security_risks.length > 0 ? `
                <div style="margin: 2rem 0;">
                    <h4 style="margin-bottom: 1rem; color: #dc3545;">🔒 Security Risks</h4>
                    <ul style="list-style: none; padding: 0;">
                        ${resource.security_risks.map(risk => 
                            `<li style="padding: 0.5rem 0; border-bottom: 1px solid #e9ecef; color: #dc3545;">⚠ ${risk}</li>`
                        ).join('')}
                    </ul>
                </div>
                ` : ''}

                <div style="margin-top: 2rem; padding-top: 1.5rem; border-top: 1px solid #e9ecef;">
                    <div style="font-size: 0.8rem; color: #666;">
                        <strong>Resource ID:</strong><br>
                        <code style="background: #f8f9fa; padding: 0.5rem; border-radius: 4px; word-break: break-all; display: block; margin-top: 0.5rem;">
                            ${resource.id}
                        </code>
                    </div>
                </div>
            `;

            modal.style.display = 'block';
        }

        function closeModal() {
            document.getElementById('resourceModal').style.display = 'none';
        }

        // Close modal when clicking outside
        window.onclick = function(event) {
            const modal = document.getElementById('resourceModal');
            if (event.target === modal) {
                closeModal();
            }
        }

        function exportToCSV() {
            const headers = [
                'Name', 'Type', 'Subscription', 'Resource Group', 'Location', 
                'Monthly Cost', 'Annual Cost', 'Severity', 'Confidence', 'Priority'
            ];
            
            const csvContent = [
                headers.join(','),
                ...filteredResources.map(r => [
                    `"${r.name}"`,
                    `"${r.type_display}"`,
                    `"${r.subscription_name}"`,
                    `"${r.resource_group}"`,
                    `"${r.location}"`,
                    r.monthly_cost.toFixed(2),
                    r.annual_cost.toFixed(2),
                    `"${r.severity}"`,
                    (r.confidence * 100).toFixed(0) + '%',
                    r.cleanup_priority
                ].join(','))
            ].join('\\n');

            const blob = new Blob([csvContent], { type: 'text/csv' });
            const url = window.URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = `azure_orphaned_resources_${new Date().toISOString().split('T')[0]}.csv`;
            document.body.appendChild(a);
            a.click();
            document.body.removeChild(a);
            window.URL.revokeObjectURL(url);
        }
    </script>
</body>
</html>'''