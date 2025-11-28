"""Configuration loading and management"""

import os
import yaml
import logging
from pathlib import Path
from typing import Dict, Any, Optional, List
from dataclasses import asdict

from ..core.models import ScanConfiguration
from ..utils.logger import setup_logger


class ConfigurationLoader:
    """Load and manage configuration from various sources"""
    
    def __init__(self):
        self.logger = setup_logger(self.__class__.__name__)
        self._config_cache = {}
    
    def load_configuration(
        self, 
        config_file: Optional[str] = None,
        **overrides
    ) -> ScanConfiguration:
        """Load configuration from file and environment variables"""
        
        # Start with default configuration
        config_dict = asdict(ScanConfiguration())
        
        # Load from config file if provided
        if config_file:
            file_config = self._load_from_file(config_file)
            if file_config:
                config_dict.update(file_config)
        else:
            # Try to find default config files
            default_config = self._load_default_config()
            if default_config:
                config_dict.update(default_config)
        
        # Load from environment variables
        env_config = self._load_from_environment()
        config_dict.update(env_config)
        
        # Apply any direct overrides
        config_dict.update({k: v for k, v in overrides.items() if v is not None})
        
        # Remove unknown keys for ScanConfiguration
        from inspect import signature
        scan_config_keys = set(signature(ScanConfiguration).parameters.keys())
        filtered_config_dict = {k: v for k, v in config_dict.items() if k in scan_config_keys}
        config = ScanConfiguration(**filtered_config_dict)
        self._validate_configuration(config)
        return config
    
    def _load_from_file(self, config_file: str) -> Optional[Dict[str, Any]]:
        """Load configuration from YAML file"""
        
        try:
            config_path = Path(config_file)
            if not config_path.exists():
                self.logger.warning(f"Configuration file not found: {config_file}")
                return None
            
            with open(config_path, 'r') as f:
                if config_path.suffix.lower() in ['.yml', '.yaml']:
                    config_data = yaml.safe_load(f)
                else:
                    self.logger.error(f"Unsupported config file format: {config_path.suffix}")
                    return None
            
            self.logger.info(f"Loaded configuration from: {config_file}")
            return self._flatten_config(config_data)
            
        except Exception as e:
            self.logger.error(f"Failed to load configuration file {config_file}: {e}")
            return None
    
    def _load_default_config(self) -> Optional[Dict[str, Any]]:
        """Try to load from default configuration locations"""
        
        default_locations = [
            "azure_orphan_detector.yml",
            "azure_orphan_detector.yaml",
            "config.yml",
            "config.yaml",
            os.path.expanduser("~/.azure_orphan_detector.yml"),
            os.path.expanduser("~/.config/azure_orphan_detector/config.yml"),
            "/etc/azure_orphan_detector/config.yml"
        ]
        
        for location in default_locations:
            if os.path.exists(location):
                return self._load_from_file(location)
        
        return None
    
    def _load_from_environment(self) -> Dict[str, Any]:
        """Load configuration from environment variables"""
        
        env_config = {}
        
        # Map environment variables to configuration keys
        env_mapping = {
            'AZURE_ORPHAN_DETECTOR_SUBSCRIPTION_IDS': ('subscription_ids', self._parse_list),
            'AZURE_ORPHAN_DETECTOR_RESOURCE_GROUPS': ('resource_groups', self._parse_list),
            'AZURE_ORPHAN_DETECTOR_EXCLUDED_RESOURCE_GROUPS': ('excluded_resource_groups', self._parse_list),
            'AZURE_ORPHAN_DETECTOR_COST_THRESHOLD_CRITICAL': ('cost_threshold_critical', float),
            'AZURE_ORPHAN_DETECTOR_COST_THRESHOLD_HIGH': ('cost_threshold_high', float),
            'AZURE_ORPHAN_DETECTOR_COST_THRESHOLD_MEDIUM': ('cost_threshold_medium', float),
            'AZURE_ORPHAN_DETECTOR_CONFIDENCE_THRESHOLD': ('confidence_threshold', float),
            'AZURE_ORPHAN_DETECTOR_INCLUDE_LOW_CONFIDENCE': ('include_low_confidence', self._parse_bool),
            'AZURE_ORPHAN_DETECTOR_MAX_AGE_DAYS': ('max_age_days', int),
            'AZURE_ORPHAN_DETECTOR_PARALLEL_WORKERS': ('parallel_workers', int),
            'AZURE_ORPHAN_DETECTOR_ENABLE_METRICS': ('enable_metrics', self._parse_bool),
            'AZURE_ORPHAN_DETECTOR_ENABLE_SECURITY_ANALYSIS': ('enable_security_analysis', self._parse_bool),
            'AZURE_ORPHAN_DETECTOR_ENABLE_COMPLIANCE_CHECK': ('enable_compliance_check', self._parse_bool),
        }
        
        for env_var, (config_key, parser) in env_mapping.items():
            value = os.getenv(env_var)
            if value is not None:
                try:
                    env_config[config_key] = parser(value)
                    self.logger.debug(f"Loaded {config_key} from environment: {value}")
                except Exception as e:
                    self.logger.warning(f"Failed to parse environment variable {env_var}={value}: {e}")
        
        return env_config
    
    def _flatten_config(self, config_data: Dict[str, Any]) -> Dict[str, Any]:
        """Flatten nested configuration dictionary"""
        
        flattened = {}
        
        def _flatten(obj, parent_key=''):
            if isinstance(obj, dict):
                for key, value in obj.items():
                    new_key = f"{parent_key}_{key}" if parent_key else key
                    _flatten(value, new_key)
            else:
                flattened[parent_key] = obj
        
        _flatten(config_data)
        return flattened
    
    def _parse_list(self, value: str) -> List[str]:
        """Parse comma-separated string into list"""
        if not value.strip():
            return []
        return [item.strip() for item in value.split(',') if item.strip()]
    
    def _parse_bool(self, value: str) -> bool:
        """Parse string into boolean"""
        return value.lower() in ('true', '1', 'yes', 'on', 'enabled')
    
    def _validate_configuration(self, config: ScanConfiguration) -> None:
        """Validate configuration values"""
        
        # Validate cost thresholds
        if config.cost_threshold_critical <= config.cost_threshold_high:
            self.logger.warning("Critical cost threshold should be higher than high threshold")
        
        if config.cost_threshold_high <= config.cost_threshold_medium:
            self.logger.warning("High cost threshold should be higher than medium threshold")
        
        # Validate confidence threshold
        if not 0.0 <= config.confidence_threshold <= 1.0:
            raise ValueError("Confidence threshold must be between 0.0 and 1.0")
        
        # Validate parallel workers
        if config.parallel_workers < 1:
            raise ValueError("Parallel workers must be at least 1")
        
        if config.parallel_workers > 20:
            self.logger.warning("High number of parallel workers may cause API rate limiting")
        
        # Validate max age
        if config.max_age_days < 1:
            raise ValueError("Max age days must be at least 1")
        
        self.logger.debug("Configuration validation completed")
    
    def save_configuration(self, config: ScanConfiguration, output_file: str) -> None:
        """Save configuration to file"""
        
        try:
            config_dict = asdict(config)
            
            # Create nested structure for better readability
            nested_config = {
                'scan_settings': {
                    'subscription_ids': config_dict['subscription_ids'],
                    'resource_groups': config_dict['resource_groups'],
                    'excluded_resource_groups': config_dict['excluded_resource_groups'],
                    'max_age_days': config_dict['max_age_days'],
                    'parallel_workers': config_dict['parallel_workers']
                },
                'cost_thresholds': {
                    'critical': config_dict['cost_threshold_critical'],
                    'high': config_dict['cost_threshold_high'],
                    'medium': config_dict['cost_threshold_medium']
                },
                'analysis_settings': {
                    'confidence_threshold': config_dict['confidence_threshold'],
                    'include_low_confidence': config_dict['include_low_confidence'],
                    'enable_metrics': config_dict['enable_metrics'],
                    'enable_security_analysis': config_dict['enable_security_analysis'],
                    'enable_compliance_check': config_dict['enable_compliance_check']
                },
                'excluded_tags': config_dict['excluded_tags']
            }
            
            output_path = Path(output_file)
            output_path.parent.mkdir(parents=True, exist_ok=True)
            
            with open(output_path, 'w') as f:
                yaml.dump(nested_config, f, default_flow_style=False, indent=2)
            
            self.logger.info(f"Configuration saved to: {output_file}")
            
        except Exception as e:
            self.logger.error(f"Failed to save configuration: {e}")
            raise


def create_sample_config(output_file: str = "azure_orphan_detector_sample.yml") -> None:
    """Create a sample configuration file"""
    
    sample_config = {
        'scan_settings': {
            'subscription_ids': [
                '# Add your subscription IDs here',
                '# "12345678-1234-1234-1234-123456789012"'
            ],
            'resource_groups': [
                '# Specific resource groups to scan (leave empty for all)',
                '# "my-resource-group"'
            ],
            'excluded_resource_groups': [
                '# Resource groups to exclude from scanning',
                '"system-resource-group"',
                '"backup-resource-group"'
            ],
            'max_age_days': 90,
            'parallel_workers': 4
        },
        'cost_thresholds': {
            'critical': 100.0,
            'high': 50.0,
            'medium': 10.0
        },
        'analysis_settings': {
            'confidence_threshold': 0.7,
            'include_low_confidence': False,
            'enable_metrics': True,
            'enable_security_analysis': True,
            'enable_compliance_check': True
        },
        'excluded_tags': {
            'Environment': ['Production', 'Prod'],
            'DoNotDelete': ['true', 'yes', '1'],
            'Backup': ['enabled', 'true']
        }
    }
    
    try:
        with open(output_file, 'w') as f:
            f.write("# Azure Orphan Detector Configuration\n")
            f.write("# This file contains configuration settings for the Azure Orphan Detector\n\n")
            yaml.dump(sample_config, f, default_flow_style=False, indent=2)
        
        print(f"Sample configuration created: {output_file}")
        
    except Exception as e:
        print(f"Failed to create sample configuration: {e}")


if __name__ == "__main__":
    # Create sample config when run directly
    create_sample_config()
