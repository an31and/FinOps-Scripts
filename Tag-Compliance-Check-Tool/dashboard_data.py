"""
Dashboard Data Module

Handles data preparation and processing for the interactive dashboard.
"""

import logging
from typing import Dict, List

from config_manager import Config
from data_models import TagData, ResourceGroupTagData, SubscriptionInfo

logger = logging.getLogger(__name__)


class DashboardDataPreparator:
    """Prepares and processes data for dashboard visualization"""
    
    def __init__(self, config: Config):
        self.config = config
    
    def prepare_dashboard_data(self, resource_tags: List[TagData], rg_tags: List[ResourceGroupTagData], 
                              subscriptions: List[SubscriptionInfo]) -> Dict:
        """Prepare all data needed for the interactive dashboard"""
        
        # Overall metrics
        total_resources = sum(sub.resource_count for sub in subscriptions)
        total_tagged_resources = sum(sub.tagged_resources for sub in subscriptions)
        total_compliant = sum(sub.mandatory_compliant_resources for sub in subscriptions)
        total_partial = sum(sub.mandatory_partial_resources for sub in subscriptions)
        total_non_compliant = total_resources - total_compliant - total_partial
        
        # Compliance overview data
        compliance_data = {
            'labels': ['Fully Compliant', 'Partially Compliant', 'Non-Compliant'],
            'data': [total_compliant, total_partial, total_non_compliant],
            'colors': ['#28a745', '#ffc107', '#dc3545']
        }
        
        # Tagging status data
        tagging_data = {
            'labels': ['Tagged Resources', 'Untagged Resources'],
            'data': [total_tagged_resources, total_resources - total_tagged_resources],
            'colors': ['#007bff', '#6c757d']
        }
        
        # Subscription performance data
        subscription_performance = self._prepare_subscription_performance(subscriptions)
        
        # Tag usage distribution
        tag_usage_data = self._prepare_tag_usage_data(resource_tags)
        
        # Resource type distribution
        resource_type_data = self._prepare_resource_type_data(resource_tags)
        
        # Compliance score distribution
        score_distribution = self._prepare_score_distribution(subscriptions)
        
        # Key metrics
        key_metrics = self._prepare_key_metrics(
            subscriptions, total_resources, total_tagged_resources, 
            total_compliant, total_partial, resource_tags
        )
        
        return {
            'compliance_data': compliance_data,
            'tagging_data': tagging_data,
            'subscription_performance': subscription_performance,
            'tag_usage_data': tag_usage_data,
            'resource_type_data': resource_type_data,
            'score_distribution': score_distribution,
            'key_metrics': key_metrics
        }
    
    def _prepare_subscription_performance(self, subscriptions: List[SubscriptionInfo]) -> Dict:
        """Prepare subscription performance data"""
        sorted_subs = sorted(subscriptions, key=lambda x: x.combined_compliance_percentage, reverse=True)
        return {
            'labels': [sub.name for sub in sorted_subs],
            'ids': [sub.id for sub in sorted_subs],
            'compliance_data': [round(sub.combined_compliance_percentage, 1) for sub in sorted_subs],
            'full_compliance': [round(sub.mandatory_compliance_percentage, 1) for sub in sorted_subs],
            'partial_compliance': [round(sub.mandatory_partial_percentage, 1) for sub in sorted_subs],
            'resource_counts': [sub.resource_count for sub in sorted_subs]
        }
    
    def _prepare_tag_usage_data(self, resource_tags: List[TagData]) -> Dict:
        """Prepare tag usage distribution data"""
        tag_distribution = {}
        for tag in resource_tags:
            if not tag.is_mandatory_missing and not tag.is_untagged:
                canonical = tag.canonical_tag_name or tag.name
                tag_distribution[canonical] = tag_distribution.get(canonical, 0) + 1
        
        top_tags = sorted(tag_distribution.items(), key=lambda x: x[1], reverse=True)[:10]
        return {
            'labels': [tag for tag, _ in top_tags],
            'data': [count for _, count in top_tags]
        }
    
    def _prepare_resource_type_data(self, resource_tags: List[TagData]) -> Dict:
        """Prepare resource type distribution data"""
        resource_types = {}
        for tag in resource_tags:
            if tag.resource_type and not tag.is_mandatory_missing:
                rt = tag.resource_type.split('/')[-1] if '/' in tag.resource_type else tag.resource_type
                resource_types[rt] = resource_types.get(rt, 0) + 1
        
        top_resource_types = sorted(resource_types.items(), key=lambda x: x[1], reverse=True)[:10]
        return {
            'labels': [rt for rt, _ in top_resource_types],
            'data': [count for _, count in top_resource_types]
        }
    
    def _prepare_score_distribution(self, subscriptions: List[SubscriptionInfo]) -> Dict:
        """Prepare compliance score distribution data"""
        score_ranges = {"90-100%": 0, "70-89%": 0, "50-69%": 0, "30-49%": 0, "0-29%": 0}
        for sub in subscriptions:
            score = sub.combined_compliance_percentage
            if score >= 90:
                score_ranges["90-100%"] += 1
            elif score >= 70:
                score_ranges["70-89%"] += 1
            elif score >= 50:
                score_ranges["50-69%"] += 1
            elif score >= 30:
                score_ranges["30-49%"] += 1
            else:
                score_ranges["0-29%"] += 1
        
        return {
            'labels': list(score_ranges.keys()),
            'data': list(score_ranges.values()),
            'colors': ['#28a745', '#20c997', '#ffc107', '#fd7e14', '#dc3545']
        }
    
    def _prepare_key_metrics(self, subscriptions: List[SubscriptionInfo], total_resources: int,
                           total_tagged_resources: int, total_compliant: int, total_partial: int,
                           resource_tags: List[TagData]) -> Dict:
        """Prepare key metrics data"""
        tag_distribution = {}
        for tag in resource_tags:
            if not tag.is_mandatory_missing and not tag.is_untagged:
                canonical = tag.canonical_tag_name or tag.name
                tag_distribution[canonical] = tag_distribution.get(canonical, 0) + 1
        
        return {
            'total_subscriptions': len(subscriptions),
            'total_resources': total_resources,
            'overall_compliance': round(((total_compliant + total_partial) / total_resources * 100) if total_resources > 0 else 0, 1),
            'resource_tagging_pct': round((total_tagged_resources / total_resources * 100) if total_resources > 0 else 0, 1),
            'avg_compliance': round(sum(sub.combined_compliance_percentage for sub in subscriptions) / len(subscriptions) if subscriptions else 0, 1),
            'best_subscription': max(subscriptions, key=lambda x: x.combined_compliance_percentage).name if subscriptions else 'N/A',
            'tag_variations_configured': len(self.config.tag_variations),
            'unique_tags_found': len(tag_distribution)
        }
    
    def prepare_drill_down_data(self, resource_tags: List[TagData], 
                               subscriptions: List[SubscriptionInfo]) -> Dict:
        """Prepare resource data for drill-down functionality"""
        max_resources = self.config.dashboard_options.get('max_drill_down_rows', 10000)
        
        # Group resources by subscription for efficient drill-down
        resources_by_subscription = {}
        unique_resources = {}
        
        for tag in resource_tags[:max_resources]:
            if tag.resource_id not in unique_resources:
                unique_resources[tag.resource_id] = {
                    'resource_name': tag.resource_name,
                    'resource_type': tag.resource_type,
                    'resource_id': tag.resource_id,
                    'location': tag.resource_location,
                    'subscription_id': tag.subscription_id,
                    'subscription_name': tag.subscription_name,
                    'tags': tag.all_resource_tags,
                    'tag_compliance': {}
                }
            
            # Update compliance for mandatory tags
            for mandatory_tag in self.config.mandatory_tags:
                if mandatory_tag != "NONE":
                    if tag.canonical_tag_name == mandatory_tag:
                        if tag.compliance_status == "compliant":
                            unique_resources[tag.resource_id]['tag_compliance'][mandatory_tag] = "✅"
                        elif tag.compliance_status == "partial":
                            unique_resources[tag.resource_id]['tag_compliance'][mandatory_tag] = "⚠️"
                    elif mandatory_tag not in unique_resources[tag.resource_id]['tag_compliance']:
                        if tag.is_mandatory_missing and tag.name == mandatory_tag:
                            unique_resources[tag.resource_id]['tag_compliance'][mandatory_tag] = "❌"
        
        # Fill in missing compliance statuses
        for resource_id, resource_info in unique_resources.items():
            for mandatory_tag in self.config.mandatory_tags:
                if mandatory_tag != "NONE" and mandatory_tag not in resource_info['tag_compliance']:
                    resource_info['tag_compliance'][mandatory_tag] = "❌"
            
            # Group by subscription
            sub_id = resource_info['subscription_id']
            if sub_id not in resources_by_subscription:
                resources_by_subscription[sub_id] = []
            resources_by_subscription[sub_id].append(resource_info)
        
        return resources_by_subscription
