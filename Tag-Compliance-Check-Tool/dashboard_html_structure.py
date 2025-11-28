"""
Dashboard HTML - Structure Module

Handles HTML structure generation for the dashboard.
"""

from typing import Dict
from config_manager import Config


class DashboardStructureGenerator:
    """Generates HTML structure for the interactive dashboard"""
    
    def __init__(self, config: Config):
        self.config = config
    
    def generate_html_body(self, dashboard_data: Dict, current_time: str) -> str:
        """Generate the main HTML body structure"""
        
        def get_performance_class(value):
            """Get CSS class based on performance value"""
            if value >= 90:
                return 'excellent'
            elif value >= 70:
                return 'good'
            elif value >= 40:
                return 'warning'
            else:
                return 'danger'
        
        return f"""
    <div class="dashboard-header">
        <h1>🏷️ Azure Tagging Analysis - Interactive Dashboard</h1>
        <p>Comprehensive Tag Compliance Analytics with Drill-Down Capabilities</p>
        <p style="margin-top: 0.5rem; font-size: 0.9rem; color: #95a5a6;">
            Generated on {current_time}
        </p>
    </div>

    {self._generate_metrics_grid(dashboard_data, get_performance_class)}
    
    {self._generate_charts_grid()}
    
    {self._generate_subscription_chart()}
    
    {self._generate_drill_down_container()}
    
    {self._generate_footer(dashboard_data)}
        """
    
    def _generate_metrics_grid(self, dashboard_data: Dict, get_performance_class) -> str:
        """Generate the metrics grid section"""
        return f"""
    <div class="metrics-grid">
        <div class="metric-card" onclick="showSubscriptionDrillDown()">
            <div class="metric-value excellent">{dashboard_data['key_metrics']['total_subscriptions']}</div>
            <div class="metric-label">Subscriptions Analyzed</div>
        </div>
        <div class="metric-card">
            <div class="metric-value">{dashboard_data['key_metrics']['total_resources']:,}</div>
            <div class="metric-label">Total Resources</div>
        </div>
        <div class="metric-card">
            <div class="metric-value {get_performance_class(dashboard_data['key_metrics']['overall_compliance'])}">{dashboard_data['key_metrics']['overall_compliance']}%</div>
            <div class="metric-label">Overall Compliance</div>
        </div>
        <div class="metric-card">
            <div class="metric-value {get_performance_class(dashboard_data['key_metrics']['resource_tagging_pct'])}">{dashboard_data['key_metrics']['resource_tagging_pct']}%</div>
            <div class="metric-label">Resources Tagged</div>
        </div>
        <div class="metric-card">
            <div class="metric-value">{dashboard_data['key_metrics']['unique_tags_found']}</div>
            <div class="metric-label">Unique Tags Found</div>
        </div>
        <div class="metric-card">
            <div class="metric-value">{dashboard_data['key_metrics']['tag_variations_configured']}</div>
            <div class="metric-label">Tag Variations Configured</div>
        </div>
    </div>
        """
    
    def _generate_charts_grid(self) -> str:
        """Generate the main charts grid section"""
        return """
    <div class="charts-grid">
        <div class="chart-container">
            <div class="chart-title">📊 Overall Compliance Status</div>
            <div class="chart-canvas">
                <canvas id="complianceChart"></canvas>
            </div>
        </div>
        
        <div class="chart-container">
            <div class="chart-title">🏷️ Resource Tagging Status</div>
            <div class="chart-canvas">
                <canvas id="taggingChart"></canvas>
            </div>
        </div>
        
        <div class="chart-container">
            <div class="chart-title">📈 Compliance Score Distribution</div>
            <div class="chart-canvas">
                <canvas id="scoreDistChart"></canvas>
            </div>
        </div>
        
        <div class="chart-container">
            <div class="chart-title">🔧 Top Resource Types</div>
            <div class="chart-canvas">
                <canvas id="resourceTypeChart"></canvas>
            </div>
        </div>
    </div>
        """
    
    def _generate_subscription_chart(self) -> str:
        """Generate the subscription analysis chart section"""
        return """
    <div class="charts-grid">
        <div class="chart-container full-width">
            <div class="chart-title">📊 Subscription Compliance Analysis (Click bars to drill down)</div>
            <div class="chart-canvas" style="height: 500px;">
                <canvas id="subscriptionChart"></canvas>
            </div>
        </div>
    </div>
        """
    
    def _generate_drill_down_container(self) -> str:
        """Generate the drill-down container section"""
        return """
    <!-- Drill-down container -->
    <div id="drillDownContainer" class="drill-down-container">
        <div class="drill-down-header">
            <h2 class="drill-down-title" id="drillDownTitle">Resource Details</h2>
            <div>
                <button class="export-btn" onclick="exportTableData()">📥 Export CSV</button>
                <button class="close-btn" onclick="closeDrillDown()">✖ Close</button>
            </div>
        </div>
        <input type="text" id="searchBox" class="search-box" placeholder="Search resources..." onkeyup="filterTable()">
        <div class="table-wrapper">
            <table id="dataTable" class="data-table">
                <thead id="tableHeader"></thead>
                <tbody id="tableBody"></tbody>
            </table>
        </div>
    </div>
        """
    
    def _generate_footer(self, dashboard_data: Dict) -> str:
        """Generate the footer section"""
        return f"""
    <div class="footer">
        <p>Azure Tagging Analysis Tool - Interactive Dashboard v2.0</p>
        <div style="margin: 0.5rem 0 0.5rem 0; padding: 0.5rem; background: #f4f8fb; border-radius: 8px; border: 1px solid #e1e8ed;">
            <ul style="list-style: none; padding-left: 0; margin-bottom: 0.5rem;">
                <li><span style='font-weight:bold; color:#2d7dd2;'>Built by</span> <span style='color:#222;'>AHEAD</span></li>
                <li><span style='font-weight:bold; color:#2d7dd2;'>Guided by</span> <span style='color:#222;'>patrick.warnke@ahead.com</span></li>
                <li><span style='font-weight:bold; color:#2d7dd2;'>Developed by POD3-(FinOps)</li>
            </ul>
            <div style="margin-top:0.5rem;">
                <span style="font-weight:bold; color:#2d7dd2;">4. Please contact POD3-Team:</span>
                <ul style="list-style: disc inside; margin-top:0.2rem;">
                    <li><span style="font-weight:bold; color:#222;">Patrick Warnke</span> - <a href='mailto:patrick.warnke@ahead.com' style='color:#2d7dd2;'>patrick.warnke@ahead.com</a></li>
                    <li><span style="font-weight:bold; color:#222;">Anand Lakhera</span> - <a href='mailto:anand.lakhera@ahead.com' style='color:#2d7dd2;'>anand.lakhera@ahead.com</a></li>
                    <li><span style="font-weight:bold; color:#222;">Carson Kreitz</span> - <a href='mailto:carson.kreitz@ahead.com' style='color:#2d7dd2;'>carson.kreitz@ahead.com</a></li>
                    <li><span style="font-weight:bold; color:#222;">Dan Barrio</span> - <a href='mailto:daniel.barrio@ahead.com' style='color:#2d7dd2;'>daniel.barrio@ahead.com</a></li>
                </ul>
            </div>
        </div>
        <p>Best Performing Subscription: <strong>{dashboard_data['key_metrics']['best_subscription']}</strong> | 
           Average Compliance: <strong>{dashboard_data['key_metrics']['avg_compliance']}%</strong></p>
        <p style="margin-top: 0.5rem; font-size: 0.8rem;">Click on charts and metrics for detailed drill-down views</p>
    </div>
        """ 
