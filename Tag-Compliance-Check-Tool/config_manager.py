"""
Configuration Management Module

Handles all configuration loading, validation, and sample file generation
for the Azure Tagging Analysis Tool.
"""

import json
import logging
import os
from dataclasses import dataclass, field
from typing import Dict, List, Set, Any
from tag_variations import TagVariation

logger = logging.getLogger(__name__)

@dataclass
class Config:
    """Configuration for the Azure Tagging Analysis Tool"""
    mandatory_tags: List[str] = field(default_factory=list)
    tag_variations: Dict[str, TagVariation] = field(default_factory=dict)
    output_file: str = "azure-tagging-report.xlsx"
    subscription_ids: List[str] = field(default_factory=list)
    excluded_subscription_ids: List[str] = field(default_factory=list)
    max_workers: int = 5
    exclude_resource_types: Set[str] = field(default_factory=set)
    timeout: int = 60
    api_version: str = "2021-04-01"
    fuzzy_matching_threshold: int = 85
    dashboard_options: Dict[str, Any] = field(default_factory=lambda: {
        "enable_export": True,
        "max_drill_down_rows": 10000,
        "chart_animation_duration": 1000,
        "enable_real_time_search": True
    })


def load_config() -> Config:
    """Load configuration from environment variables"""
    from constants import NON_TAGGABLE_RESOURCE_TYPES
    
    config = Config()
    
    # Set default non-taggable resource types
    config.exclude_resource_types = NON_TAGGABLE_RESOURCE_TYPES.copy()
    
    # Load mandatory tags from environment
    mandatory_tags = os.getenv("MANDATORY_TAGS", "").split(",")
    config.mandatory_tags = [tag.strip() for tag in mandatory_tags if tag.strip()]
    if not config.mandatory_tags:
        config.mandatory_tags = ["NONE"]
    
    # Load tag variations from environment (JSON format)
    tag_variations_json = os.getenv("TAG_VARIATIONS", "{}")
    try:
        variations_dict = json.loads(tag_variations_json)
        for canonical, variation_config in variations_dict.items():
            config.tag_variations[canonical] = TagVariation(
                canonical_name=canonical,
                variations=variation_config.get("variations", []),
                fuzzy_threshold=variation_config.get("fuzzy_threshold", 85),
                case_sensitive=variation_config.get("case_sensitive", False)
            )
    except json.JSONDecodeError:
        logger.warning("Invalid TAG_VARIATIONS JSON format, using default empty configuration")
    
    config.output_file = os.getenv("OUTPUT_FILE", config.output_file)
    
    # Load subscription configuration
    subscription_ids = os.getenv("AZURE_SUBSCRIPTION_IDS", "").split(",")
    config.subscription_ids = [sub.strip() for sub in subscription_ids if sub.strip()]
    
    excluded_subscription_ids = os.getenv("EXCLUDED_SUBSCRIPTION_IDS", "").split(",")
    config.excluded_subscription_ids = [sub.strip() for sub in excluded_subscription_ids if sub.strip()]
    
    config.max_workers = int(os.getenv("MAX_WORKERS", config.max_workers))
    
    # Add additional exclude types from environment
    exclude_types = os.getenv("EXCLUDE_RESOURCE_TYPES", "").split(",")
    for rtype in exclude_types:
        if rtype.strip():
            config.exclude_resource_types.add(rtype.strip())
    
    config.fuzzy_matching_threshold = int(os.getenv("FUZZY_MATCHING_THRESHOLD", config.fuzzy_matching_threshold))
    
    return config


def generate_sample_config_file(config: Config) -> None:
    """Generate a comprehensive sample configuration file with all parameters"""
    
    sample_config = {
        "// ===================================": "",
        "// Azure Tagging Analysis Configuration": "",
        "// ===================================": "",
        "// This file contains all available configuration options": "",
        "// Uncomment parameters by removing '//' to use them": "",
        "": "",
        "// === MANDATORY TAGS CONFIGURATION ===": "",
        "// Define tags that all resources must have": "",
        "mandatory_tags": [
            "Environment",
            "Portfolio",
            "Application",
            "BillTo",
            "DataClassification",
            "ContactEmail",
            "BusinessCriticality",
            "Project"
        ],
        "": "",
        "// === TAG VARIATIONS CONFIGURATION ===": "",
        "// This is the main configuration - defines acceptable variations for each tag": "",
        "// Compliance Status:": "",
        "//   - COMPLIANT (Green): Exact match (e.g., 'Environment' = 'Environment')": "",
        "//   - PARTIAL (Yellow): Variation match (e.g., 'env' or 'Env' matches 'Environment')": "",
        "//   - NON_COMPLIANT (Red): Tag missing or no match found": "",
        "tag_variations": {
            "Environment": {
                "canonical_name": "Environment",
                "variations": [
                    "environment", " Environment", "Envrionment", "x_Environment", 
                    "csva-environment", "Env", "env", "Environment ", "ENVIRONMENT"
                ],
                "fuzzy_threshold": 80,
                "case_sensitive": False
            },
            "Portfolio": {
                "canonical_name": "Portfolio",
                "variations": [
                    "portfolio", "PortFolio", "x_Portfolio", "portfolio ", 
                    " Portfolio", "Portfolio "
                ],
                "fuzzy_threshold": 80,
                "case_sensitive": False
            },
            "Application": {
                "canonical_name": "Application",
                "variations": [
                    "application", "App", "AppName", "Application ", 
                    "application ", " Application", "x_Application", 
                    "ApplicationType", "Application Type"
                ],
                "fuzzy_threshold": 80,
                "case_sensitive": False
            },
            "BillTo": {
                "canonical_name": "BillTo",
                "variations": [
                    "billTo", "Bill", "Billing", "Bill-To", "bill_to", 
                    " BillTo", "BillTo ", "billTo ", "x_BillTo", 
                    "billToDetails", "BillToDetails"
                ],
                "fuzzy_threshold": 80,
                "case_sensitive": False
            }
        },
        "": "",
        "// === OUTPUT CONFIGURATION ===": "",
        "//output_file": "azure-tagging-report.xlsx",
        "": "",
        "// === SUBSCRIPTION CONFIGURATION ===": "",
        "//subscription_ids": ["sub-id-1", "sub-id-2"],
        "//excluded_subscription_ids": ["sub-id-to-exclude-1", "sub-id-to-exclude-2"],
        "": "",
        "// === PERFORMANCE SETTINGS ===": "",
        "//max_workers": 5,
        "//timeout": 60,
        "": "",
        "// === RESOURCE TYPE FILTERING ===": "",
        "//exclude_resource_types": [
            "microsoft.insights/components",
            "microsoft.operationsmanagement/solutions"
        ],
        "": "",
        "// === FUZZY MATCHING CONFIGURATION ===": "",
        "//fuzzy_matching_threshold": 85,
        "": "",
        "// === AZURE API CONFIGURATION ===": "",
        "//api_version": "2021-04-01",
        "": "",
        "// === DASHBOARD OPTIONS ===": "",
        "//dashboard_options": {
            "enable_export": True,
            "max_drill_down_rows": 10000,
            "chart_animation_duration": 1000,
            "enable_real_time_search": True
        }
    }
    
    try:
        # Write config file with proper formatting
        with open("sample_config.json", "w") as f:
            json.dump(sample_config, f, indent=2, default=str)
        
        logger.info("📝 Generated sample_config.json with all available parameters")
        
    except Exception as e:
        logger.warning(f"Could not generate config files: {e}")
