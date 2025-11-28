"""
Dashboard Generator - Core Module

Main orchestrator for interactive HTML dashboard generation.
"""

import logging
from typing import List

from config_manager import Config
from data_models import TagData, ResourceGroupTagData, SubscriptionInfo
from dashboard_data import DashboardDataPreparator
from dashboard_html_core import DashboardHTMLGenerator

logger = logging.getLogger(__name__)


class InteractiveDashboardGenerator:
    """Generate interactive HTML dashboard with drill-down capabilities"""
    
    def __init__(self, config: Config):
        self.config = config
        self.data_preparator = DashboardDataPreparator(config)
        self.html_generator = DashboardHTMLGenerator(config)
    
    def generate_dashboard(self, resource_tags: List[TagData], rg_tags: List[ResourceGroupTagData], 
                          subscriptions: List[SubscriptionInfo], output_file: str) -> str:
        """Generate complete HTML dashboard with drill-down capabilities"""
        
        logger.info("🌐 Starting interactive HTML dashboard generation...")
        
        try:
            # Prepare data for charts and tables
            dashboard_data = self.data_preparator.prepare_dashboard_data(
                resource_tags, rg_tags, subscriptions
            )
            
            # Prepare resource data for drill-down
            resources_by_subscription = self.data_preparator.prepare_drill_down_data(
                resource_tags, subscriptions
            )
            
            # Generate HTML content
            html_content = self.html_generator.generate_interactive_html(
                dashboard_data, resources_by_subscription, subscriptions
            )
            
            # Save to file
            dashboard_file = output_file.replace('.xlsx', '_dashboard.html')
            
            with open(dashboard_file, 'w', encoding='utf-8') as f:
                f.write(html_content)
            
            logger.info(f"📊 Interactive HTML dashboard generated: {dashboard_file}")
            return dashboard_file
            
        except Exception as e:
            logger.error(f"❌ Failed to generate HTML dashboard: {e}")
            raise
