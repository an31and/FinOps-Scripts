"""
Dashboard Scripts - Core Module

Main orchestrator for JavaScript generation.
"""

from typing import Dict
from config_manager import Config
from dashboard_scripts_charts import DashboardChartsGenerator
from dashboard_scripts_interactions import DashboardInteractionsGenerator
from dashboard_scripts_utils import DashboardUtilsGenerator


class DashboardScriptsGenerator:
    """Generates JavaScript code for the interactive dashboard"""
    
    def __init__(self, config: Config):
        self.config = config
        self.charts_generator = DashboardChartsGenerator()
        self.interactions_generator = DashboardInteractionsGenerator(config)
        self.utils_generator = DashboardUtilsGenerator()
    
    def generate_javascript_code(self, dashboard_data: Dict, resources_by_subscription: Dict, 
                                safe_json) -> str:
        """Generate complete JavaScript code for dashboard functionality"""
        
        mandatory_tags = [t for t in self.config.mandatory_tags if t != 'NONE']
        
        # Generate all JavaScript components
        initialization_code = self._generate_initialization_code(
            dashboard_data, resources_by_subscription, mandatory_tags, safe_json
        )
        charts_code = self.charts_generator.generate_chart_initialization_code(
            dashboard_data, safe_json
        )
        interactions_code = self.interactions_generator.generate_drill_down_functions()
        utils_code = self.utils_generator.generate_utility_functions()
        
        # Combine all JavaScript code
        return f"""
        {initialization_code}
        
        {charts_code}
        
        {interactions_code}
        
        {utils_code}
        
        console.log('📊 Azure Tagging Interactive Dashboard loaded successfully!');
        console.log('Click on charts and metrics to drill down into detailed views.');
        """
    
    def _generate_initialization_code(self, dashboard_data: Dict, resources_by_subscription: Dict,
                                    mandatory_tags: list, safe_json) -> str:
        """Generate initialization JavaScript code"""
        return f"""
        // Store data for drill-down
        const subscriptionData = {safe_json(dashboard_data['subscription_performance'])};
        const resourcesBySubscription = {safe_json(resources_by_subscription)};
        const mandatoryTags = {safe_json(mandatory_tags)};
        
        // Chart.js configuration
        Chart.defaults.font.family = '-apple-system, BlinkMacSystemFont, "Segoe UI", "Roboto", sans-serif';
        Chart.defaults.font.size = 12;
        Chart.defaults.plugins.legend.position = 'bottom';
        Chart.defaults.plugins.legend.labels.padding = 20;

        // Initialize all charts
        initializeCharts();
        """
