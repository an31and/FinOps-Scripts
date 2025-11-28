"""
Dashboard HTML - Core Module

Main orchestrator for HTML content generation.
"""

import json
import logging
from datetime import datetime
from typing import Dict, List

from config_manager import Config
from data_models import SubscriptionInfo
from dashboard_html_styles import DashboardStylesGenerator
from dashboard_html_structure import DashboardStructureGenerator
from dashboard_scripts_core import DashboardScriptsGenerator

logger = logging.getLogger(__name__)


class DashboardHTMLGenerator:
    """Generates HTML content for the interactive dashboard"""
    
    def __init__(self, config: Config):
        self.config = config
        self.styles_generator = DashboardStylesGenerator()
        self.structure_generator = DashboardStructureGenerator(config)
        self.scripts_generator = DashboardScriptsGenerator(config)
    
    def generate_interactive_html(self, dashboard_data: Dict, resources_by_subscription: Dict, 
                                 subscriptions: List[SubscriptionInfo]) -> str:
        """Generate interactive HTML dashboard with drill-down capabilities"""
        
        # Safely serialize data
        def safe_json(data):
            return json.dumps(data, default=str).replace("'", "\\'")
        
        current_time = datetime.now().strftime('%B %d, %Y at %I:%M %p')
        
        # Generate components
        css_styles = self.styles_generator.generate_css_styles()
        javascript_code = self.scripts_generator.generate_javascript_code(
            dashboard_data, resources_by_subscription, safe_json
        )
        html_body = self.structure_generator.generate_html_body(
            dashboard_data, current_time
        )
        
        # Combine into complete HTML document
        html_content = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Azure Tagging Analysis - Interactive Dashboard</title>
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
    <style>
        {css_styles}
    </style>
</head>
<body>
    {html_body}
    <script>
        {javascript_code}
    </script>
</body>
</html>"""
        
        return html_content
