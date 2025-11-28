"""
Utilities Module

Contains utility functions, logging setup, and helper functions
for the Azure Tagging Analysis Tool.
"""

import logging
import re
import sys
from typing import List
from constants import ColorThresholds
from data_models import SubscriptionInfo
from config_manager import Config


def setup_logging(debug_mode: bool = False):
    """Setup logging configuration with optional debug mode"""
    log_level = logging.DEBUG if debug_mode else logging.INFO
    log_format = '%(asctime)s - %(levelname)s - %(funcName)s:%(lineno)d - %(message)s' if debug_mode else '%(asctime)s - %(levelname)s - %(message)s'
    
    # Clear any existing handlers
    for handler in logging.root.handlers[:]:
        logging.root.removeHandler(handler)
    
    logging.basicConfig(
        level=log_level,
        format=log_format,
        handlers=[
            logging.FileHandler('azure_tagging.log'),
            logging.StreamHandler(sys.stdout)
        ]
    )
    
    if debug_mode:
        logging.getLogger().info("🐛 Debug mode enabled - verbose logging active")


def sanitize_for_excel(value: str) -> str:
    """
    Sanitize string values for Excel compatibility.
    Remove or replace characters that Excel/OpenPyXL considers illegal.
    """
    if not isinstance(value, str):
        return str(value)
    
    # Remove control characters (0x00-0x1F except tab, newline, carriage return)
    # and other problematic characters
    sanitized = re.sub(r'[\x00-\x08\x0B-\x0C\x0E-\x1F\x7F-\x9F]', '', value)
    
    # Replace problematic characters that might cause issues
    sanitized = sanitized.replace('\x00', '')  # NULL character
    sanitized = sanitized.replace('\x0B', ' ')  # Vertical tab
    sanitized = sanitized.replace('\x0C', ' ')  # Form feed
    
    # Limit length to prevent Excel issues (Excel has a 32,767 character limit per cell)
    if len(sanitized) > 32000:
        sanitized = sanitized[:32000] + "..."
    
    return sanitized


def print_summary_stats(subscriptions: List[SubscriptionInfo], config: Config) -> None:
    """Print enhanced summary statistics to console with variation info"""
    
    total_resources = sum(sub.resource_count for sub in subscriptions)
    total_rgs = sum(sub.rg_count for sub in subscriptions)
    total_tagged_resources = sum(sub.tagged_resources for sub in subscriptions)
    total_tagged_rgs = sum(sub.tagged_rgs for sub in subscriptions)
    total_compliant = sum(sub.mandatory_compliant_resources for sub in subscriptions)
    total_partial = sum(sub.mandatory_partial_resources for sub in subscriptions)
    
    resource_tagging_pct = (total_tagged_resources / total_resources * 100) if total_resources > 0 else 0
    rg_tagging_pct = (total_tagged_rgs / total_rgs * 100) if total_rgs > 0 else 0
    compliance_pct = (total_compliant / total_resources * 100) if total_resources > 0 else 0
    partial_pct = (total_partial / total_resources * 100) if total_resources > 0 else 0
    combined_pct = ((total_compliant + total_partial) / total_resources * 100) if total_resources > 0 else 0
    
    print("\n" + "="*80)
    print("📊 ENHANCED AZURE TAGGING ANALYSIS SUMMARY")
    print("="*80)
    print(f"📋 Total Subscriptions Analyzed: {len(subscriptions)}")
    if config.excluded_subscription_ids:
        print(f"🚫 Excluded Subscriptions: {len(config.excluded_subscription_ids)}")
    print(f"🔧 Total Resources: {total_resources:,}")
    print(f"📁 Total Resource Groups: {total_rgs:,}")
    print(f"🏷️  Mandatory Tags Defined: {len([t for t in config.mandatory_tags if t != 'NONE'])}")
    print(f"🔄 Tag Variations Configured: {len(config.tag_variations)}")
    print()
    
    # Color-coded status indicators
    def get_status_indicator(percentage):
        if percentage >= ColorThresholds.EXCELLENT:
            return "🟢 EXCELLENT"
        elif percentage >= ColorThresholds.GOOD:
            return "🟢 GOOD"
        elif percentage >= ColorThresholds.FAIR:
            return "🟡 NEEDS IMPROVEMENT"
        else:
            return "🔴 POOR"
    
    print("📈 TAGGING PERFORMANCE:")
    print(f"   Resources Tagged: {total_tagged_resources:,}/{total_resources:,} ({resource_tagging_pct:.1f}%) - {get_status_indicator(resource_tagging_pct)}")
    print(f"   Resource Groups Tagged: {total_tagged_rgs:,}/{total_rgs:,} ({rg_tagging_pct:.1f}%) - {get_status_indicator(rg_tagging_pct)}")
    
    if config.mandatory_tags != ["NONE"]:
        print("\n🎯 MANDATORY TAG COMPLIANCE:")
        print(f"   ✅ Full Compliance (Exact Match): {total_compliant:,}/{total_resources:,} ({compliance_pct:.1f}%) - {get_status_indicator(compliance_pct)}")
        print(f"   ⚠️  Partial Compliance (Variations): {total_partial:,}/{total_resources:,} ({partial_pct:.1f}%) - {get_status_indicator(partial_pct)}")
        print(f"   📊 Combined Compliance: {total_compliant + total_partial:,}/{total_resources:,} ({combined_pct:.1f}%) - {get_status_indicator(combined_pct)}")
    print()
    
    # Top and bottom performing subscriptions
    if len(subscriptions) > 1:
        sorted_subs = sorted(subscriptions, key=lambda x: x.combined_compliance_percentage, reverse=True)
        print("🏆 TOP PERFORMING SUBSCRIPTIONS (Combined Compliance):")
        for sub in sorted_subs[:3]:
            if sub.resource_count > 0:
                print(f"   {sub.name}: {sub.combined_compliance_percentage:.1f}% ({sub.mandatory_compliant_resources + sub.mandatory_partial_resources}/{sub.resource_count})")
        print()
        
        print("⚠️  LOWEST PERFORMING SUBSCRIPTIONS:")
        for sub in sorted_subs[-3:]:
            if sub.resource_count > 0:
                print(f"   {sub.name}: {sub.combined_compliance_percentage:.1f}% ({sub.mandatory_compliant_resources + sub.mandatory_partial_resources}/{sub.resource_count})")
        print()
    
    # Tag variation summary
    if config.tag_variations:
        print("🔄 TAG VARIATION CONFIGURATION:")
        for canonical, variation_config in config.tag_variations.items():
            print(f"   {canonical}: {len(variation_config.variations)} variations (threshold: {variation_config.fuzzy_threshold}%)")
        print()
    
    print("="*80)
