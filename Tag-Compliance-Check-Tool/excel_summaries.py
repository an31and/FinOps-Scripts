"""
Excel Summaries Module

Handles summary sheet generation for the Azure Tagging Analysis Tool.
"""

import logging
from typing import List
from openpyxl import Workbook

from config_manager import Config
from data_models import TagData, ResourceGroupTagData, SubscriptionInfo
from excel_styles import ExcelStyleManager
from excel_worksheets import WorksheetGenerator
from constants import TagComplianceStatus

logger = logging.getLogger(__name__)


class SummaryGenerator:
    """Generates summary and analysis sheets"""
    
    def __init__(self, config: Config, style_manager: ExcelStyleManager):
        self.config = config
        self.style_manager = style_manager
        self.worksheet_generator = WorksheetGenerator(config, style_manager)
    
    def generate_enhanced_summary(self, wb: Workbook, resource_tags: List[TagData], 
                                rg_tags: List[ResourceGroupTagData], 
                                subscriptions: List[SubscriptionInfo]) -> None:
        """Generate enhanced summary with percentages and color coding"""
        
        # Calculate metrics
        total_resources = sum(sub.resource_count for sub in subscriptions)
        total_rgs = sum(sub.rg_count for sub in subscriptions)
        total_tagged_resources = sum(sub.tagged_resources for sub in subscriptions)
        total_tagged_rgs = sum(sub.tagged_rgs for sub in subscriptions)
        total_compliant_resources = sum(sub.mandatory_compliant_resources for sub in subscriptions)
        total_partial_resources = sum(sub.mandatory_partial_resources for sub in subscriptions)
        
        # Calculate percentages
        resource_tagging_pct = (total_tagged_resources / total_resources * 100) if total_resources > 0 else 0
        rg_tagging_pct = (total_tagged_rgs / total_rgs * 100) if total_rgs > 0 else 0
        compliance_pct = (total_compliant_resources / total_resources * 100) if total_resources > 0 else 0
        partial_pct = (total_partial_resources / total_resources * 100) if total_resources > 0 else 0
        combined_pct = ((total_compliant_resources + total_partial_resources) / total_resources * 100) if total_resources > 0 else 0
        
        missing_count = sum(1 for tag in resource_tags if tag.is_mandatory_missing)
        untagged_count = sum(1 for tag in resource_tags if tag.is_untagged)
        
        headers = ["Metric", "Count", "Total", "Percentage", "Status"]
        summary_data = [
            ["Resources with Tags", total_tagged_resources, total_resources, f"{resource_tagging_pct:.1f}%", self.style_manager.get_status_text(resource_tagging_pct)],
            ["Resource Groups with Tags", total_tagged_rgs, total_rgs, f"{rg_tagging_pct:.1f}%", self.style_manager.get_status_text(rg_tagging_pct)],
            ["Full Mandatory Compliance", total_compliant_resources, total_resources, f"{compliance_pct:.1f}%", self.style_manager.get_status_text(compliance_pct)],
            ["Partial Compliance (Variations)", total_partial_resources, total_resources, f"{partial_pct:.1f}%", self.style_manager.get_status_text(partial_pct)],
            ["Combined Compliance", total_compliant_resources + total_partial_resources, total_resources, f"{combined_pct:.1f}%", self.style_manager.get_status_text(combined_pct)],
            ["", "", "", "", ""],
            ["Total Subscriptions", len(subscriptions), len(subscriptions), "100.0%", "Complete"],
            ["Total Resources", total_resources, total_resources, "100.0%", "Complete"],
            ["Total Resource Groups", total_rgs, total_rgs, "100.0%", "Complete"],
            ["Untagged Resources", untagged_count, total_resources, f"{(untagged_count/total_resources*100):.1f}%" if total_resources > 0 else "0%", ""],
            ["Missing Mandatory Tags", missing_count, "", "", ""],
            ["Mandatory Tags Defined", len([t for t in self.config.mandatory_tags if t != "NONE"]), "", "", ""],
            ["Tag Variations Configured", len(self.config.tag_variations), "", "", ""],
        ]
        
        self.worksheet_generator.create_enhanced_worksheet_with_table(
            wb, "Executive Summary", headers, summary_data, percentage_columns=[4]
        )
    
    def generate_subscription_analysis(self, wb: Workbook, subscriptions: List[SubscriptionInfo]) -> None:
        """Generate subscription-level analysis with color coding"""
        
        headers = [
            "Subscription Name", "Subscription ID", "Resources", "Tagged Resources", 
            "Resource Tag %", "Resource Groups", "Tagged RGs", "RG Tag %", 
            "Full Compliant", "Full Compliance %", "Partial Compliant", "Partial %", "Combined %"
        ]
        
        sub_data = []
        for sub in sorted(subscriptions, key=lambda x: x.combined_compliance_percentage, reverse=True):
            sub_data.append([
                sub.name, sub.id, sub.resource_count, sub.tagged_resources,
                f"{sub.resource_tagging_percentage:.1f}%", sub.rg_count, sub.tagged_rgs,
                f"{sub.rg_tagging_percentage:.1f}%", sub.mandatory_compliant_resources,
                f"{sub.mandatory_compliance_percentage:.1f}%", sub.mandatory_partial_resources,
                f"{sub.mandatory_partial_percentage:.1f}%", f"{sub.combined_compliance_percentage:.1f}%"
            ])
        
        self.worksheet_generator.create_enhanced_worksheet_with_table(
            wb, "Subscription Analysis", headers, sub_data, percentage_columns=[5, 8, 10, 12, 13]
        )
    
    def generate_compliance_report(self, wb: Workbook, resource_tags: List[TagData], 
                                 subscriptions: List[SubscriptionInfo]) -> None:
        """Generate mandatory tag compliance report"""
        
        if not self.config.mandatory_tags or self.config.mandatory_tags == ["NONE"]:
            return
        
        compliance_data = {}
        
        for sub in subscriptions:
            sub_resources = [tag for tag in resource_tags if tag.subscription_name == sub.name]
            
            for mandatory_tag in self.config.mandatory_tags:
                if mandatory_tag == "NONE":
                    continue
                
                full_compliant = len(set(
                    tag.resource_id for tag in sub_resources 
                    if tag.canonical_tag_name == mandatory_tag and tag.compliance_status == TagComplianceStatus.COMPLIANT
                ))
                
                partial_compliant = len(set(
                    tag.resource_id for tag in sub_resources 
                    if tag.canonical_tag_name == mandatory_tag and tag.compliance_status == TagComplianceStatus.PARTIAL
                ))
                
                non_compliant = sub.resource_count - full_compliant - partial_compliant
                
                full_pct = (full_compliant / sub.resource_count * 100) if sub.resource_count > 0 else 0
                partial_pct = (partial_compliant / sub.resource_count * 100) if sub.resource_count > 0 else 0
                combined_pct = ((full_compliant + partial_compliant) / sub.resource_count * 100) if sub.resource_count > 0 else 0
                
                compliance_data[(sub.name, mandatory_tag)] = {
                    'subscription': sub.name, 'tag': mandatory_tag,
                    'full_compliant': full_compliant, 'partial_compliant': partial_compliant,
                    'non_compliant': non_compliant, 'total_resources': sub.resource_count,
                    'full_percentage': full_pct, 'partial_percentage': partial_pct,
                    'combined_percentage': combined_pct
                }
        
        headers = ["Subscription", "Mandatory Tag", "Full Compliant", "Full %", "Partial Compliant", 
                  "Partial %", "Non-Compliant", "Total Resources", "Combined %"]
        compliance_report_data = []
        
        for key, data in sorted(compliance_data.items()):
            compliance_report_data.append([
                data['subscription'], data['tag'], data['full_compliant'],
                f"{data['full_percentage']:.1f}%", data['partial_compliant'],
                f"{data['partial_percentage']:.1f}%", data['non_compliant'],
                data['total_resources'], f"{data['combined_percentage']:.1f}%"
            ])
        
        self.worksheet_generator.create_enhanced_worksheet_with_table(
            wb, "Compliance Report", headers, compliance_report_data, percentage_columns=[4, 6, 9]
        )
    
    def generate_tag_variation_analysis(self, wb: Workbook, resource_tags: List[TagData], 
                                      rg_tags: List[ResourceGroupTagData]) -> None:
        """Generate tag variation analysis report"""
        
        if not self.config.tag_variations:
            return
        
        variation_data = {}
        
        for tag in resource_tags:
            if not tag.is_mandatory_missing and not tag.is_untagged:
                canonical = tag.canonical_tag_name
                if canonical in self.config.tag_variations:
                    if canonical not in variation_data:
                        variation_data[canonical] = {
                            'canonical': canonical, 'variations': {}, 'total_usage': 0
                        }
                    
                    variation_key = tag.name
                    if variation_key not in variation_data[canonical]['variations']:
                        variation_data[canonical]['variations'][variation_key] = {
                            'count': 0, 'status': tag.compliance_status, 'examples': set()
                        }
                    
                    variation_data[canonical]['variations'][variation_key]['count'] += 1
                    variation_data[canonical]['variations'][variation_key]['examples'].add(f"{tag.resource_name} ({tag.subscription_name})")
                    variation_data[canonical]['total_usage'] += 1
        
        headers = ["Canonical Tag", "Variation Used", "Usage Count", "Usage %", "Compliance Status", "Example Resources"]
        variation_report_data = []
        
        for canonical, data in sorted(variation_data.items()):
            for variation, var_data in sorted(data['variations'].items(), key=lambda x: x[1]['count'], reverse=True):
                usage_pct = (var_data['count'] / data['total_usage'] * 100) if data['total_usage'] > 0 else 0
                examples = "; ".join(list(var_data['examples'])[:3])
                if len(var_data['examples']) > 3:
                    examples += f" ... (+{len(var_data['examples']) - 3} more)"
                
                variation_report_data.append([
                    canonical, variation, var_data['count'], f"{usage_pct:.1f}%",
                    var_data['status'], examples
                ])
        
        self.worksheet_generator.create_enhanced_worksheet_with_table(
            wb, "Tag Variations Analysis", headers, variation_report_data,
            percentage_columns=[4], compliance_columns=[5]
        )
