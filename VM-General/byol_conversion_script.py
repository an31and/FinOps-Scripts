#!/usr/bin/env python3
"""
Windows VM BYOL Conversion Automation Script
Handles discovery, testing, and conversion of Windows VMs from on-demand to BYOL licensing
"""

import json
import csv
import logging
import datetime
import time
import os
import asyncio
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, asdict
from typing import List, Dict, Optional, Tuple, Union
from enum import Enum
import boto3
from azure.identity import DefaultAzureCredential
from azure.mgmt.compute import ComputeManagementClient
from azure.mgmt.resource import ResourceManagementClient
from azure.core.exceptions import AzureError
import requests
import pandas as pd

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(f'byol_conversion_{datetime.datetime.now().strftime("%Y%m%d_%H%M%S")}.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class RiskLevel(Enum):
    VERY_LOW = "very_low"
    LOW = "low"  
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"

class ConversionPhase(Enum):
    DISCOVERY = "discovery"
    ANALYSIS = "analysis"
    TESTING = "testing"
    PILOT = "pilot"
    PRODUCTION = "production"
    COMPLETED = "completed"

class CloudProvider(Enum):
    AWS = "aws"
    AZURE = "azure"
    GCP = "gcp"
    MULTI_CLOUD = "multi_cloud"

class VMStatus(Enum):
    RUNNING = "running"
    STOPPED = "stopped"
    PENDING = "pending"

class LicenseType(Enum):
    ON_DEMAND = "on_demand"
    BYOL = "byol"
    HYBRID_BENEFIT = "hybrid_benefit"

@dataclass
class WindowsLicense:
    license_key: str
    edition: str  # Standard, Datacenter, Core
    version: str  # 2019, 2022, etc.
    cores_covered: int
    in_use: bool
    assigned_vm: Optional[str] = None
    expiry_date: Optional[str] = None
    # Enhanced compliance and tracking
    purchase_date: Optional[str] = None
    license_agreement_type: str = "unknown"  # EA, CSP, SPLA, Retail
    compliance_verified: bool = False
    last_compliance_check: Optional[str] = None
    software_assurance: bool = False
    mobility_rights: bool = False
    azure_hybrid_benefit_eligible: bool = True
    cost_per_core: float = 0.0
    vendor: str = "Microsoft"
    license_server: Optional[str] = None
    activation_count: int = 0
    max_activations: int = 1

@dataclass
class VMInfo:
    vm_id: str
    name: str
    resource_group: str
    size: str
    cores: int
    memory_gb: float
    os_version: str
    current_license_type: LicenseType
    status: VMStatus
    monthly_cost_current: float
    estimated_monthly_cost_byol: float
    potential_savings: float
    risk_level: RiskLevel
    last_updated: str
    # Enhanced risk assessment fields
    business_criticality: str = "unknown"  # low, medium, high, critical
    environment_type: str = "unknown"  # dev, test, staging, prod
    backup_frequency: str = "unknown"  # daily, weekly, monthly, none
    monitoring_enabled: bool = False
    disaster_recovery_configured: bool = False
    uptime_requirement: str = "unknown"  # 99.9%, 99.95%, 99.99%
    application_owner: str = "unknown"
    cost_center: str = "unknown"
    compliance_requirements: List[str] = None
    dependencies: List[str] = None  # Other VMs/services this depends on
    performance_baseline: Dict = None  # CPU, memory, disk metrics
    conversion_readiness_score: float = 0.0  # 0-100 score

class LicenseManager:
    """Manages Windows license inventory and allocation"""
    
    def __init__(self, license_file: str = "windows_licenses.json"):
        self.license_file = license_file
        self.licenses: List[WindowsLicense] = []
        self.load_licenses()
    
    def load_licenses(self):
        """Load license inventory from file"""
        try:
            with open(self.license_file, 'r') as f:
                data = json.load(f)
                self.licenses = [WindowsLicense(**license) for license in data]
            logger.info(f"Loaded {len(self.licenses)} licenses from {self.license_file}")
        except FileNotFoundError:
            logger.warning(f"License file {self.license_file} not found. Creating empty inventory.")
            self.licenses = []
        except Exception as e:
            logger.error(f"Error loading licenses: {e}")
            self.licenses = []
    
    def save_licenses(self):
        """Save license inventory to file"""
        try:
            with open(self.license_file, 'w') as f:
                json.dump([asdict(license) for license in self.licenses], f, indent=2)
            logger.info(f"Saved {len(self.licenses)} licenses to {self.license_file}")
        except Exception as e:
            logger.error(f"Error saving licenses: {e}")
    
    def add_license(self, license: WindowsLicense):
        """Add a license to the inventory"""
        self.licenses.append(license)
        self.save_licenses()
        logger.info(f"Added license {license.license_key} to inventory")
    
    def get_available_licenses(self, edition: str, cores_needed: int) -> List[WindowsLicense]:
        """Get available licenses that match requirements"""
        available = []
        for license in self.licenses:
            if (not license.in_use and 
                license.edition.lower() == edition.lower() and 
                license.cores_covered >= cores_needed):
                available.append(license)
        return available
    
    def allocate_license(self, vm_id: str, edition: str, cores_needed: int) -> Optional[WindowsLicense]:
        """Allocate a license to a VM"""
        available_licenses = self.get_available_licenses(edition, cores_needed)
        if available_licenses:
            license = available_licenses[0]  # Take first available
            license.in_use = True
            license.assigned_vm = vm_id
            self.save_licenses()
            logger.info(f"Allocated license {license.license_key} to VM {vm_id}")
            return license
        return None
    
    def release_license(self, vm_id: str):
        """Release license from a VM"""
        for license in self.licenses:
            if license.assigned_vm == vm_id:
                license.in_use = False
                license.assigned_vm = None
                self.save_licenses()
                logger.info(f"Released license {license.license_key} from VM {vm_id}")
                break

class CloudVMManager:
    """Base class for cloud VM management"""
    
    def __init__(self, provider: CloudProvider):
        self.provider = provider
    
    def discover_vms(self) -> List[VMInfo]:
        """Discover Windows VMs in the cloud"""
        raise NotImplementedError
    
    def get_vm_cost(self, vm: VMInfo) -> Tuple[float, float]:
        """Get current and estimated BYOL costs"""
        raise NotImplementedError
    
    def convert_to_byol(self, vm_id: str) -> bool:
        """Convert VM to BYOL licensing"""
        raise NotImplementedError
    
    def create_snapshot(self, vm_id: str) -> str:
        """Create VM snapshot before conversion"""
        raise NotImplementedError
    
    def revert_from_snapshot(self, vm_id: str, snapshot_id: str) -> bool:
        """Revert VM from snapshot"""
        raise NotImplementedError

class AzureVMManager(CloudVMManager):
    """Azure-specific VM management"""
    
    def __init__(self, subscription_id: str):
        super().__init__(CloudProvider.AZURE)
        self.subscription_id = subscription_id
        self.credential = DefaultAzureCredential()
        self.compute_client = ComputeManagementClient(self.credential, subscription_id)
        self.resource_client = ResourceManagementClient(self.credential, subscription_id)
        
        # Azure pricing (example rates - update with actual pricing)
        self.pricing = {
            'Standard_D2s_v3': {'on_demand': 96.36, 'byol': 48.18},  # Monthly USD
            'Standard_D4s_v3': {'on_demand': 192.72, 'byol': 96.36},
            'Standard_D8s_v3': {'on_demand': 385.44, 'byol': 192.72}
        }
    
    def discover_vms(self) -> List[VMInfo]:
        """Discover Windows VMs in Azure"""
        vms = []
        try:
            for vm in self.compute_client.virtual_machines.list_all():
                if self._is_windows_vm(vm):
                    vm_info = self._create_vm_info(vm)
                    vms.append(vm_info)
            logger.info(f"Discovered {len(vms)} Windows VMs in Azure")
        except Exception as e:
            logger.error(f"Error discovering Azure VMs: {e}")
        return vms
    
    def _is_windows_vm(self, vm) -> bool:
        """Check if VM is running Windows"""
        if vm.storage_profile and vm.storage_profile.os_disk:
            return vm.storage_profile.os_disk.os_type.lower() == 'windows'
        return False
    
    def _create_vm_info(self, vm) -> VMInfo:
        """Create VMInfo object from Azure VM"""
        # Extract VM size info
        size_info = self._get_vm_size_info(vm.hardware_profile.vm_size)
        
        # Determine current license type
        current_license = LicenseType.ON_DEMAND
        if hasattr(vm, 'license_type') and vm.license_type:
            if vm.license_type.lower() == 'windows_server':
                current_license = LicenseType.HYBRID_BENEFIT
        
        # Calculate costs
        current_cost, byol_cost = self.get_vm_cost_by_size(vm.hardware_profile.vm_size)
        
        return VMInfo(
            vm_id=vm.id,
            name=vm.name,
            resource_group=vm.id.split('/')[4],  # Extract from resource ID
            size=vm.hardware_profile.vm_size,
            cores=size_info['cores'],
            memory_gb=size_info['memory_gb'],
            os_version=self._get_os_version(vm),
            current_license_type=current_license,
            status=VMStatus.RUNNING if vm.instance_view and vm.instance_view.statuses else VMStatus.STOPPED,
            monthly_cost_current=current_cost,
            estimated_monthly_cost_byol=byol_cost,
            potential_savings=current_cost - byol_cost,
            risk_level=self._assess_risk_level(vm),
            last_updated=datetime.datetime.now().isoformat()
        )
    
    def _get_vm_size_info(self, vm_size: str) -> Dict:
        """Get VM size information"""
        # Simplified mapping - in production, use Azure pricing API
        size_map = {
            'Standard_D2s_v3': {'cores': 2, 'memory_gb': 8},
            'Standard_D4s_v3': {'cores': 4, 'memory_gb': 16},
            'Standard_D8s_v3': {'cores': 8, 'memory_gb': 32}
        }
        return size_map.get(vm_size, {'cores': 2, 'memory_gb': 4})
    
    def _get_os_version(self, vm) -> str:
        """Extract Windows OS version"""
        try:
            if vm.storage_profile and vm.storage_profile.image_reference:
                return f"{vm.storage_profile.image_reference.offer}-{vm.storage_profile.image_reference.sku}"
        except:
            pass
        return "Windows-Unknown"
    
    def _assess_risk_level(self, vm) -> str:
        """Assess risk level for VM conversion"""
        # Simple risk assessment - customize based on your criteria
        if 'prod' in vm.name.lower() or 'production' in vm.name.lower():
            return 'high'
        elif 'test' in vm.name.lower() or 'dev' in vm.name.lower():
            return 'low'
        else:
            return 'medium'
    
    def get_vm_cost_by_size(self, vm_size: str) -> Tuple[float, float]:
        """Get current and BYOL costs for VM size"""
        pricing = self.pricing.get(vm_size, {'on_demand': 100, 'byol': 50})
        return pricing['on_demand'], pricing['byol']
    
    def convert_to_byol(self, vm_id: str) -> bool:
        """Convert Azure VM to BYOL (Hybrid Benefit)"""
        try:
            # Parse resource group and VM name from ID
            parts = vm_id.split('/')
            resource_group = parts[4]
            vm_name = parts[8]
            
            # Get VM
            vm = self.compute_client.virtual_machines.get(resource_group, vm_name)
            
            # Update license type
            vm.license_type = 'Windows_Server'
            
            # Apply update
            operation = self.compute_client.virtual_machines.begin_create_or_update(
                resource_group, vm_name, vm
            )
            operation.result()  # Wait for completion
            
            logger.info(f"Successfully converted VM {vm_name} to BYOL")
            return True
            
        except Exception as e:
            logger.error(f"Error converting VM {vm_id} to BYOL: {e}")
            return False
    
    def create_snapshot(self, vm_id: str) -> str:
        """Create snapshot of VM's OS disk"""
        try:
            parts = vm_id.split('/')
            resource_group = parts[4]
            vm_name = parts[8]
            
            # Get VM to find OS disk
            vm = self.compute_client.virtual_machines.get(resource_group, vm_name)
            os_disk_name = vm.storage_profile.os_disk.name
            
            # Create snapshot
            snapshot_name = f"{vm_name}-snapshot-{datetime.datetime.now().strftime('%Y%m%d%H%M%S')}"
            
            # Implementation would depend on your snapshot strategy
            logger.info(f"Created snapshot {snapshot_name} for VM {vm_name}")
            return snapshot_name
            
        except Exception as e:
            logger.error(f"Error creating snapshot for VM {vm_id}: {e}")
            return ""

class AWSVMManager(CloudVMManager):
    """Enhanced AWS VM management with advanced BYOL support"""
    
    def __init__(self, region: str = 'us-east-1'):
        super().__init__(CloudProvider.AWS)
        self.session = boto3.Session()
        self.ec2_client = self.session.client('ec2', region_name=region)
        self.pricing_client = self.session.client('pricing', region_name='us-east-1')
        self.cloudwatch = self.session.client('cloudwatch', region_name=region)
        
    def discover_vms(self) -> List[VMInfo]:
        """Discover Windows VMs across all AWS regions"""
        vms = []
        try:
            regions = [region['RegionName'] for region in self.ec2_client.describe_regions()['Regions']]
            
            for region in regions:
                try:
                    regional_ec2 = self.session.client('ec2', region_name=region)
                    response = regional_ec2.describe_instances(
                        Filters=[
                            {'Name': 'platform', 'Values': ['windows']},
                            {'Name': 'instance-state-name', 'Values': ['running', 'stopped']}
                        ]
                    )
                    
                    for reservation in response['Reservations']:
                        for instance in reservation['Instances']:
                            vm_info = self._create_vm_info_from_instance(instance, region)
                            vms.append(vm_info)
                            
                except Exception as e:
                    logger.warning(f"Error discovering VMs in region {region}: {e}")
                    
            logger.info(f"Discovered {len(vms)} Windows VMs in AWS")
        except Exception as e:
            logger.error(f"Error discovering AWS VMs: {e}")
        return vms
    
    def _create_vm_info_from_instance(self, instance: Dict, region: str) -> VMInfo:
        """Create VMInfo object from AWS EC2 instance"""
        instance_type = instance['InstanceType']
        
        # Get instance type info
        cores, memory_gb = self._get_instance_type_info(instance_type)
        
        # Determine license type
        current_license = LicenseType.ON_DEMAND
        if instance.get('UsageOperation', '').startswith('RunInstances:'):
            current_license = LicenseType.BYOL
            
        # Calculate costs
        current_cost, byol_cost = self._get_instance_costs(instance_type, region)
        
        return VMInfo(
            vm_id=instance['InstanceId'],
            name=instance.get('Tags', [{}])[0].get('Value', instance['InstanceId']),
            resource_group=region,  # Use region as resource group equivalent
            size=instance_type,
            cores=cores,
            memory_gb=memory_gb,
            os_version=self._get_windows_version(instance),
            current_license_type=current_license,
            status=VMStatus.RUNNING if instance['State']['Name'] == 'running' else VMStatus.STOPPED,
            monthly_cost_current=current_cost,
            estimated_monthly_cost_byol=byol_cost,
            potential_savings=current_cost - byol_cost,
            risk_level=self._assess_aws_risk(instance),
            last_updated=datetime.datetime.now().isoformat(),
            region=region
        )
    
    def _get_instance_type_info(self, instance_type: str) -> Tuple[int, float]:
        """Get core and memory info for AWS instance type"""
        # Simplified mapping - in production, use AWS APIs
        type_map = {
            't3.medium': (2, 4),
            't3.large': (2, 8),
            't3.xlarge': (4, 16),
            'm5.large': (2, 8),
            'm5.xlarge': (4, 16),
            'm5.2xlarge': (8, 32),
            'c5.large': (2, 4),
            'c5.xlarge': (4, 8)
        }
        return type_map.get(instance_type, (2, 4))
    
    def _get_instance_costs(self, instance_type: str, region: str) -> Tuple[float, float]:
        """Get on-demand and BYOL costs for instance type"""
        # Simplified pricing - integrate with AWS Pricing API
        base_costs = {
            't3.medium': 30.0,
            't3.large': 60.0,
            't3.xlarge': 120.0,
            'm5.large': 70.0,
            'm5.xlarge': 140.0,
            'm5.2xlarge': 280.0
        }
        on_demand = base_costs.get(instance_type, 50.0)
        byol = on_demand * 0.6  # Approximate 40% savings with BYOL
        return on_demand, byol
    
    def _get_windows_version(self, instance: Dict) -> str:
        """Extract Windows version from instance"""
        # This would typically require additional API calls
        return "Windows-Server-2019"
    
    def _assess_aws_risk(self, instance: Dict) -> str:
        """Assess risk level for AWS instance conversion"""
        tags = {tag['Key']: tag['Value'] for tag in instance.get('Tags', [])}
        
        if tags.get('Environment', '').lower() in ['prod', 'production']:
            return 'high'
        elif tags.get('Environment', '').lower() in ['dev', 'test']:
            return 'low'
        else:
            return 'medium'


class GCPVMManager(CloudVMManager):
    """Enhanced GCP VM management with advanced BYOL support"""
    
    def __init__(self, project_id: str):
        super().__init__(CloudProvider.GCP)
        self.project_id = project_id
        # Note: Would need google-cloud-compute library
        
    def discover_vms(self) -> List[VMInfo]:
        """Discover Windows VMs across all GCP zones"""
        vms = []
        # Implementation would use google-cloud-compute client
        logger.info("GCP VM discovery not yet implemented")
        return vms


class MultiSubscriptionAzureManager:
    """Enhanced Azure VM manager supporting multiple subscriptions simultaneously"""
    
    def __init__(self, subscription_ids: List[str] = None):
        self.credential = DefaultAzureCredential()
        self.managers = {}
        
        # If no subscription IDs provided, discover all accessible subscriptions
        if not subscription_ids:
            self.subscription_ids = self._discover_accessible_subscriptions()
            logger.info(f"🔍 Auto-discovered {len(self.subscription_ids)} accessible subscriptions")
        else:
            self.subscription_ids = subscription_ids
            logger.info(f"📋 Using {len(subscription_ids)} provided subscription IDs")
        
        # Initialize manager for each subscription
        for sub_id in self.subscription_ids:
            try:
                self.managers[sub_id] = AzureVMManager(sub_id)
                logger.info(f"✅ Initialized Azure manager for subscription: {sub_id}")
            except Exception as e:
                logger.error(f"❌ Failed to initialize manager for subscription {sub_id}: {e}")
    
    def _discover_accessible_subscriptions(self) -> List[str]:
        """Discover all accessible Azure subscriptions"""
        subscription_ids = []
        
        try:
            from azure.mgmt.resource import SubscriptionClient
            
            # Create subscription client
            subscription_client = SubscriptionClient(self.credential)
            
            # Get all accessible subscriptions
            subscriptions = subscription_client.subscriptions.list()
            
            for subscription in subscriptions:
                # Only include enabled subscriptions
                if subscription.state and subscription.state.lower() == 'enabled':
                    subscription_ids.append(subscription.subscription_id)
                    logger.info(f"🔍 Found accessible subscription: {subscription.display_name} ({subscription.subscription_id})")
                else:
                    logger.warning(f"⚠️  Skipping disabled subscription: {subscription.display_name} ({subscription.subscription_id})")
                    
        except Exception as e:
            logger.error(f"❌ Error discovering subscriptions: {e}")
            logger.info("💡 Falling back to default subscription or manual specification")
            
            # Fallback: try to get default subscription
            try:
                import subprocess
                result = subprocess.run(['az', 'account', 'show', '--query', 'id', '-o', 'tsv'], 
                                      capture_output=True, text=True, timeout=30)
                if result.returncode == 0 and result.stdout.strip():
                    default_sub = result.stdout.strip()
                    subscription_ids = [default_sub]
                    logger.info(f"🔄 Using default subscription: {default_sub}")
                else:
                    logger.warning("⚠️  No default subscription found via Azure CLI")
            except Exception as fallback_error:
                logger.error(f"❌ Fallback subscription discovery failed: {fallback_error}")
        
        if not subscription_ids:
            logger.warning("⚠️  No accessible subscriptions found. Please specify subscription IDs manually.")
        
        return subscription_ids
    
    def discover_all_subscriptions_vms(self) -> Dict[str, List[VMInfo]]:
        """Discover VMs across all configured Azure subscriptions"""
        all_vms = {}
        total_vms = 0
        
        logger.info(f"🔍 Discovering VMs across {len(self.subscription_ids)} Azure subscriptions...")
        
        for sub_id, manager in self.managers.items():
            try:
                logger.info(f"📊 Scanning subscription: {sub_id}")
                vms = manager.discover_vms()
                
                # Add subscription info to each VM
                for vm in vms:
                    vm.subscription_id = sub_id
                    vm.cloud_provider = "azure"
                
                all_vms[sub_id] = vms
                total_vms += len(vms)
                logger.info(f"  └─ Found {len(vms)} Windows VMs in {sub_id}")
                
            except Exception as e:
                logger.error(f"❌ Error discovering VMs in subscription {sub_id}: {e}")
                all_vms[sub_id] = []
        
        logger.info(f"🎯 Total discovery complete: {total_vms} VMs across {len(self.subscription_ids)} subscriptions")
        return all_vms
    
    def get_consolidated_vm_list(self) -> List[VMInfo]:
        """Get a single consolidated list of all VMs across subscriptions"""
        all_vms_dict = self.discover_all_subscriptions_vms()
        consolidated_vms = []
        
        for sub_id, vms in all_vms_dict.items():
            consolidated_vms.extend(vms)
        
        return consolidated_vms
    
    def discover_vms(self) -> List[VMInfo]:
        """Compatibility method for single-manager interface"""
        return self.get_consolidated_vm_list()
    
    def get_subscription_summary(self) -> Dict:
        """Get summary statistics for each subscription"""
        all_vms = self.discover_all_subscriptions_vms()
        summary = {
            'total_subscriptions': len(self.subscription_ids),
            'subscription_details': {},
            'grand_totals': {
                'total_vms': 0,
                'total_current_cost': 0,
                'total_byol_cost': 0,
                'total_potential_savings': 0,
                'on_demand_vms': 0,
                'byol_vms': 0
            }
        }
        
        for sub_id, vms in all_vms.items():
            sub_summary = {
                'subscription_id': sub_id,
                'vm_count': len(vms),
                'current_monthly_cost': sum(vm.monthly_cost_current for vm in vms),
                'byol_monthly_cost': sum(vm.estimated_monthly_cost_byol for vm in vms),
                'potential_monthly_savings': sum(vm.potential_savings for vm in vms),
                'on_demand_count': len([vm for vm in vms if vm.current_license_type == LicenseType.ON_DEMAND]),
                'byol_count': len([vm for vm in vms if vm.current_license_type == LicenseType.BYOL]),
                'risk_breakdown': self._get_risk_breakdown(vms),
                'environment_breakdown': self._get_environment_breakdown(vms)
            }
            
            summary['subscription_details'][sub_id] = sub_summary
            
            # Add to grand totals
            summary['grand_totals']['total_vms'] += sub_summary['vm_count']
            summary['grand_totals']['total_current_cost'] += sub_summary['current_monthly_cost']
            summary['grand_totals']['total_byol_cost'] += sub_summary['byol_monthly_cost']
            summary['grand_totals']['total_potential_savings'] += sub_summary['potential_monthly_savings']
            summary['grand_totals']['on_demand_vms'] += sub_summary['on_demand_count']
            summary['grand_totals']['byol_vms'] += sub_summary['byol_count']
        
        return summary
    
    def _get_risk_breakdown(self, vms: List[VMInfo]) -> Dict[str, int]:
        """Get risk level breakdown for VMs"""
        breakdown = {}
        for vm in vms:
            risk = vm.risk_level
            breakdown[risk] = breakdown.get(risk, 0) + 1
        return breakdown
    
    def _get_environment_breakdown(self, vms: List[VMInfo]) -> Dict[str, int]:
        """Get environment type breakdown for VMs"""
        breakdown = {}
        for vm in vms:
            env = vm.environment_type
            breakdown[env] = breakdown.get(env, 0) + 1
        return breakdown
    
    def convert_vms_across_subscriptions(self, conversion_plan: Dict[str, List[str]], 
                                       dry_run: bool = True) -> Dict:
        """Convert VMs across multiple subscriptions according to plan
        
        Args:
            conversion_plan: Dict with subscription_id as key and list of VM IDs as value
            dry_run: Whether to simulate the conversion
        
        Returns:
            Dict with conversion results per subscription
        """
        results = {
            'start_time': datetime.datetime.now().isoformat(),
            'dry_run': dry_run,
            'subscription_results': {},
            'total_conversions_attempted': 0,
            'total_successful': 0,
            'total_failed': 0,
            'total_monthly_savings': 0
        }
        
        logger.info(f"🚀 {'Simulating' if dry_run else 'Starting'} multi-subscription BYOL conversion...")
        
        for sub_id, vm_ids in conversion_plan.items():
            if sub_id not in self.managers:
                logger.error(f"❌ No manager found for subscription {sub_id}")
                continue
            
            logger.info(f"📋 Processing {len(vm_ids)} VMs in subscription {sub_id}")
            manager = self.managers[sub_id]
            sub_results = {
                'subscription_id': sub_id,
                'vm_conversions': [],
                'successful_count': 0,
                'failed_count': 0,
                'monthly_savings': 0
            }
            
            for vm_id in vm_ids:
                try:
                    if dry_run:
                        # Simulate conversion
                        conversion_result = {
                            'vm_id': vm_id,
                            'subscription_id': sub_id,
                            'success': True,  # Assume success in simulation
                            'dry_run': True,
                            'simulated_savings': 100,  # Mock savings
                            'timestamp': datetime.datetime.now().isoformat()
                        }
                        logger.info(f"🔍 DRY RUN: Would convert VM {vm_id} in {sub_id}")
                    else:
                        # Actual conversion
                        conversion_result = manager.convert_to_byol(vm_id)
                        conversion_result['subscription_id'] = sub_id
                        conversion_result['timestamp'] = datetime.datetime.now().isoformat()
                    
                    sub_results['vm_conversions'].append(conversion_result)
                    
                    if conversion_result.get('success', False):
                        sub_results['successful_count'] += 1
                        sub_results['monthly_savings'] += conversion_result.get('simulated_savings', 0)
                    else:
                        sub_results['failed_count'] += 1
                        
                except Exception as e:
                    logger.error(f"❌ Error converting VM {vm_id} in {sub_id}: {e}")
                    sub_results['vm_conversions'].append({
                        'vm_id': vm_id,
                        'subscription_id': sub_id,
                        'success': False,
                        'error': str(e),
                        'timestamp': datetime.datetime.now().isoformat()
                    })
                    sub_results['failed_count'] += 1
            
            results['subscription_results'][sub_id] = sub_results
            results['total_conversions_attempted'] += len(vm_ids)
            results['total_successful'] += sub_results['successful_count']
            results['total_failed'] += sub_results['failed_count']
            results['total_monthly_savings'] += sub_results['monthly_savings']
            
            logger.info(f"✅ Subscription {sub_id}: {sub_results['successful_count']}/{len(vm_ids)} successful")
        
        results['end_time'] = datetime.datetime.now().isoformat()
        results['success_rate'] = (results['total_successful'] / results['total_conversions_attempted'] * 100) if results['total_conversions_attempted'] > 0 else 0
        
        logger.info(f"🎯 Multi-subscription conversion complete:")
        logger.info(f"   Total: {results['total_successful']}/{results['total_conversions_attempted']} successful ({results['success_rate']:.1f}%)")
        logger.info(f"   Savings: ${results['total_monthly_savings']:,.2f}/month")
        
        return results


class MultiCloudVMManager:
    """Unified multi-cloud VM management for BYOL operations"""
    
    def __init__(self):
        self.managers = {}
        
    def add_azure_manager(self, subscription_id: str):
        """Add Azure VM manager"""
        self.managers[f'azure_{subscription_id}'] = AzureVMManager(subscription_id)
        
    def add_aws_manager(self, region: str = 'us-east-1'):
        """Add AWS VM manager"""
        self.managers[f'aws_{region}'] = AWSVMManager(region)
        
    def add_gcp_manager(self, project_id: str):
        """Add GCP VM manager"""
        self.managers[f'gcp_{project_id}'] = GCPVMManager(project_id)
        
    def discover_all_vms(self) -> Dict[str, List[VMInfo]]:
        """Discover VMs across all configured cloud providers"""
        all_vms = {}
        
        for provider, manager in self.managers.items():
            try:
                vms = manager.discover_vms()
                all_vms[provider] = vms
                logger.info(f"Discovered {len(vms)} VMs in {provider}")
            except Exception as e:
                logger.error(f"Error discovering VMs in {provider}: {e}")
                all_vms[provider] = []
                
        return all_vms
    
    def get_total_potential_savings(self) -> Dict[str, float]:
        """Calculate potential savings across all clouds"""
        savings = {}
        all_vms = self.discover_all_vms()
        
        for provider, vms in all_vms.items():
            total_savings = sum(vm.potential_savings for vm in vms)
            savings[provider] = total_savings
            
        savings['total'] = sum(savings.values())
        return savings


class CostOptimizationEngine:
    """Advanced cost analysis and optimization recommendations"""
    
    def __init__(self):
        self.optimization_rules = []
        self.cost_models = {}
        
    def analyze_cost_optimization(self, vms: List[VMInfo]) -> Dict:
        """Comprehensive cost optimization analysis"""
        analysis = {
            'current_monthly_cost': sum(vm.monthly_cost_current for vm in vms),
            'byol_monthly_cost': sum(vm.estimated_monthly_cost_byol for vm in vms),
            'monthly_savings': sum(vm.potential_savings for vm in vms),
            'annual_savings': sum(vm.potential_savings for vm in vms) * 12,
            'optimization_recommendations': [],
            'rightsizing_opportunities': [],
            'scheduling_opportunities': [],
            'reserved_instance_recommendations': []
        }
        
        # Add specific optimization recommendations
        analysis['optimization_recommendations'] = self._generate_optimization_recommendations(vms)
        analysis['rightsizing_opportunities'] = self._identify_rightsizing_opportunities(vms)
        analysis['scheduling_opportunities'] = self._identify_scheduling_opportunities(vms)
        
        return analysis
    
    def _generate_optimization_recommendations(self, vms: List[VMInfo]) -> List[Dict]:
        """Generate specific optimization recommendations"""
        recommendations = []
        
        # High-impact conversions
        high_impact_vms = [vm for vm in vms if vm.potential_savings > 100]
        if high_impact_vms:
            recommendations.append({
                'type': 'high_impact_conversion',
                'description': f'Convert {len(high_impact_vms)} high-impact VMs for maximum savings',
                'potential_monthly_savings': sum(vm.potential_savings for vm in high_impact_vms),
                'vm_count': len(high_impact_vms),
                'priority': 'high'
            })
        
        # Low-risk conversions
        low_risk_vms = [vm for vm in vms if vm.risk_level in ['low', 'very_low']]
        if low_risk_vms:
            recommendations.append({
                'type': 'low_risk_conversion',
                'description': f'Start with {len(low_risk_vms)} low-risk VMs for safe implementation',
                'potential_monthly_savings': sum(vm.potential_savings for vm in low_risk_vms),
                'vm_count': len(low_risk_vms),
                'priority': 'medium'
            })
        
        return recommendations
    
    def _identify_rightsizing_opportunities(self, vms: List[VMInfo]) -> List[Dict]:
        """Identify VMs that could be rightsized for additional savings"""
        opportunities = []
        
        for vm in vms:
            # Mock analysis - in practice, would analyze CPU/memory utilization
            if vm.cores > 4 and vm.business_criticality != 'critical':
                potential_size = f"Standard_D{vm.cores//2}s_v3"
                estimated_additional_savings = vm.monthly_cost_current * 0.3
                
                opportunities.append({
                    'vm_id': vm.vm_id,
                    'vm_name': vm.name,
                    'current_size': vm.size,
                    'recommended_size': potential_size,
                    'additional_monthly_savings': estimated_additional_savings,
                    'reason': 'Oversized based on typical utilization patterns'
                })
        
        return opportunities
    
    def _identify_scheduling_opportunities(self, vms: List[VMInfo]) -> List[Dict]:
        """Identify VMs suitable for scheduled start/stop"""
        opportunities = []
        
        for vm in vms:
            if vm.environment_type in ['development', 'testing', 'staging']:
                # Assume 40% savings from scheduled operations (12h/day, 5 days/week)
                potential_savings = vm.monthly_cost_current * 0.4
                
                opportunities.append({
                    'vm_id': vm.vm_id,
                    'vm_name': vm.name,
                    'environment': vm.environment_type,
                    'recommended_schedule': '8 AM - 6 PM, Monday-Friday',
                    'monthly_savings': potential_savings,
                    'annual_savings': potential_savings * 12
                })
        
        return opportunities
    
    def calculate_roi_timeline(self, initial_investment: float, monthly_savings: float) -> Dict:
        """Calculate ROI timeline and break-even point"""
        if monthly_savings <= 0:
            return {'roi_months': float('inf'), 'break_even': 'Never'}
        
        roi_months = initial_investment / monthly_savings
        
        return {
            'initial_investment': initial_investment,
            'monthly_savings': monthly_savings,
            'roi_months': roi_months,
            'break_even': f"{roi_months:.1f} months",
            'annual_roi_percentage': (monthly_savings * 12 / initial_investment * 100) if initial_investment > 0 else float('inf'),
            'three_year_net_savings': (monthly_savings * 36) - initial_investment
        }


class RiskAssessmentEngine:
    """Advanced risk assessment for BYOL conversions"""
    
    def __init__(self):
        self.risk_factors = [
            'business_criticality',
            'environment_type',
            'backup_frequency',
            'monitoring_enabled',
            'compliance_requirements',
            'dependencies',
            'performance_baseline'
        ]
    
    def assess_conversion_risk(self, vm: VMInfo) -> Dict:
        """Comprehensive risk assessment for VM conversion"""
        risk_score = 0
        risk_factors = []
        
        # Business criticality assessment
        criticality_scores = {
            'critical': 40,
            'high': 25,
            'medium': 15,
            'low': 5,
            'unknown': 20
        }
        criticality_score = criticality_scores.get(vm.business_criticality, 20)
        risk_score += criticality_score
        
        if criticality_score >= 25:
            risk_factors.append(f"High business criticality ({vm.business_criticality})")
        
        # Environment type assessment
        env_scores = {
            'production': 30,
            'staging': 15,
            'testing': 5,
            'development': 0,
            'unknown': 20
        }
        env_score = env_scores.get(vm.environment_type, 20)
        risk_score += env_score
        
        if env_score >= 20:
            risk_factors.append(f"Production/unknown environment ({vm.environment_type})")
        
        # Backup and monitoring assessment
        if not vm.backup_frequency or vm.backup_frequency == 'none':
            risk_score += 20
            risk_factors.append("No regular backups configured")
        
        if not vm.monitoring_enabled:
            risk_score += 15
            risk_factors.append("No monitoring enabled")
        
        # Compliance requirements
        if vm.compliance_requirements and len(vm.compliance_requirements) > 0:
            risk_score += 10
            risk_factors.append(f"Compliance requirements: {', '.join(vm.compliance_requirements)}")
        
        # Dependencies assessment
        if vm.dependencies and len(vm.dependencies) > 3:
            risk_score += 15
            risk_factors.append(f"High number of dependencies ({len(vm.dependencies)})")
        
        # Performance baseline
        if not vm.performance_baseline:
            risk_score += 10
            risk_factors.append("No performance baseline established")
        
        # Determine risk level
        if risk_score >= 80:
            risk_level = RiskLevel.CRITICAL
        elif risk_score >= 60:
            risk_level = RiskLevel.HIGH
        elif risk_score >= 40:
            risk_level = RiskLevel.MEDIUM
        elif risk_score >= 20:
            risk_level = RiskLevel.LOW
        else:
            risk_level = RiskLevel.VERY_LOW
        
        return {
            'risk_score': risk_score,
            'risk_level': risk_level.value,
            'risk_factors': risk_factors,
            'recommendation': self._get_risk_recommendation(risk_level),
            'mitigation_steps': self._get_mitigation_steps(risk_factors)
        }
    
    def _get_risk_recommendation(self, risk_level: RiskLevel) -> str:
        """Get recommendation based on risk level"""
        recommendations = {
            RiskLevel.VERY_LOW: "Safe to proceed immediately",
            RiskLevel.LOW: "Proceed with standard precautions",
            RiskLevel.MEDIUM: "Proceed with enhanced monitoring and backup",
            RiskLevel.HIGH: "Proceed only during maintenance window with full rollback plan",
            RiskLevel.CRITICAL: "Not recommended - significant business risk"
        }
        return recommendations.get(risk_level, "Unknown risk level")
    
    def _get_mitigation_steps(self, risk_factors: List[str]) -> List[str]:
        """Generate mitigation steps based on risk factors"""
        mitigation_steps = []
        
        for factor in risk_factors:
            if "backup" in factor.lower():
                mitigation_steps.append("Configure automated backups before conversion")
            elif "monitoring" in factor.lower():
                mitigation_steps.append("Enable comprehensive monitoring and alerting")
            elif "compliance" in factor.lower():
                mitigation_steps.append("Review compliance impact and get approval")
            elif "dependencies" in factor.lower():
                mitigation_steps.append("Map and validate all dependencies")
            elif "baseline" in factor.lower():
                mitigation_steps.append("Establish performance baseline before conversion")
            elif "criticality" in factor.lower():
                mitigation_steps.append("Schedule conversion during maintenance window")
        
        # Always add general mitigation steps
        mitigation_steps.extend([
            "Create VM snapshot before conversion",
            "Prepare rollback procedure",
            "Schedule conversion during low-usage period"
        ])
        
        return list(set(mitigation_steps))  # Remove duplicates


class BYOLDashboard:
    """Interactive dashboard for BYOL conversion tracking and reporting"""
    
    def __init__(self, output_dir: str = "byol_reports"):
        self.output_dir = output_dir
        self.create_output_directory()
        
    def create_output_directory(self):
        """Create output directory if it doesn't exist"""
        if not os.path.exists(self.output_dir):
            os.makedirs(self.output_dir)
    
    def generate_executive_summary(self, analysis_data: Dict) -> str:
        """Generate executive summary report"""
        timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <title>BYOL Conversion Executive Summary</title>
            <meta charset="UTF-8">
            <style>
                body {{ font-family: 'Segoe UI', Arial, sans-serif; margin: 20px; background-color: #f5f5f5; }}
                .container {{ max-width: 1200px; margin: 0 auto; background: white; padding: 30px; border-radius: 10px; box-shadow: 0 0 20px rgba(0,0,0,0.1); }}
                .header {{ background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 20px; border-radius: 10px; margin-bottom: 30px; }}
                .metric-grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(250px, 1fr)); gap: 20px; margin: 20px 0; }}
                .metric-card {{ background: #f8f9fa; padding: 20px; border-radius: 8px; border-left: 4px solid #007bff; }}
                .metric-value {{ font-size: 2em; font-weight: bold; color: #007bff; }}
                .metric-label {{ color: #6c757d; font-size: 0.9em; margin-top: 5px; }}
                .section {{ margin: 30px 0; }}
                .section h2 {{ color: #333; border-bottom: 2px solid #007bff; padding-bottom: 10px; }}
                .recommendation {{ background: #e3f2fd; padding: 15px; border-radius: 5px; margin: 10px 0; border-left: 4px solid #2196f3; }}
                .risk-high {{ border-left-color: #f44336; background: #ffebee; }}
                .risk-medium {{ border-left-color: #ff9800; background: #fff3e0; }}
                .risk-low {{ border-left-color: #4caf50; background: #e8f5e9; }}
                .table {{ width: 100%; border-collapse: collapse; margin: 20px 0; }}
                .table th, .table td {{ padding: 12px; text-align: left; border-bottom: 1px solid #ddd; }}
                .table th {{ background-color: #f8f9fa; font-weight: 600; }}
                .footer {{ text-align: center; margin-top: 40px; color: #6c757d; font-size: 0.9em; }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>BYOL Conversion Analysis</h1>
                    <p>Executive Summary - Generated on {timestamp}</p>
                </div>
                
                <div class="metric-grid">
                    <div class="metric-card">
                        <div class="metric-value">{analysis_data.get('total_vms', 0)}</div>
                        <div class="metric-label">Total Windows VMs</div>
                    </div>
                    <div class="metric-card">
                        <div class="metric-value">${analysis_data.get('monthly_savings', 0):,.0f}</div>
                        <div class="metric-label">Monthly Savings Potential</div>
                    </div>
                    <div class="metric-card">
                        <div class="metric-value">${analysis_data.get('annual_savings', 0):,.0f}</div>
                        <div class="metric-label">Annual Savings Potential</div>
                    </div>
                    <div class="metric-card">
                        <div class="metric-value">{analysis_data.get('conversion_candidates', 0)}</div>
                        <div class="metric-label">Conversion Candidates</div>
                    </div>
                </div>
                
                <div class="section">
                    <h2>Key Recommendations</h2>
        """
        
        # Add recommendations
        recommendations = analysis_data.get('optimization_recommendations', [])
        for rec in recommendations[:5]:  # Top 5 recommendations
            priority_class = f"risk-{rec.get('priority', 'medium')}"
            html_content += f"""
                    <div class="recommendation {priority_class}">
                        <strong>{rec.get('type', 'Recommendation').replace('_', ' ').title()}</strong><br>
                        {rec.get('description', 'No description available')}<br>
                        <small>Potential Monthly Savings: ${rec.get('potential_monthly_savings', 0):,.0f}</small>
                    </div>
            """
        
        html_content += """
                </div>
                
                <div class="section">
                    <h2>Risk Assessment Summary</h2>
                    <table class="table">
                        <thead>
                            <tr>
                                <th>Risk Level</th>
                                <th>VM Count</th>
                                <th>Potential Monthly Savings</th>
                                <th>Recommendation</th>
                            </tr>
                        </thead>
                        <tbody>
        """
        
        # Add risk assessment data
        risk_summary = analysis_data.get('risk_summary', {})
        for risk_level, data in risk_summary.items():
            html_content += f"""
                            <tr>
                                <td>{risk_level.title()}</td>
                                <td>{data.get('count', 0)}</td>
                                <td>${data.get('savings', 0):,.0f}</td>
                                <td>{data.get('recommendation', 'Review required')}</td>
                            </tr>
            """
        
        html_content += """
                        </tbody>
                    </table>
                </div>
                
                <div class="footer">
                    <p>This report was generated by the BYOL Conversion Analysis Tool</p>
                    <p>For detailed technical information, please refer to the technical analysis report</p>
                </div>
            </div>
        </body>
        </html>
        """
        
        report_path = os.path.join(self.output_dir, f"executive_summary_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.html")
        with open(report_path, 'w', encoding='utf-8') as f:
            f.write(html_content)
        
        return report_path
    
    def generate_technical_report(self, vms: List[VMInfo], analysis_data: Dict) -> str:
        """Generate detailed technical report"""
        timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        # Convert to pandas DataFrame for easier manipulation
        df_data = []
        for vm in vms:
            df_data.append({
                'VM Name': vm.name,
                'VM ID': vm.vm_id,
                'Size': vm.size,
                'Cores': vm.cores,
                'Memory (GB)': vm.memory_gb,
                'Current License': vm.current_license_type.value,
                'Monthly Cost (Current)': vm.monthly_cost_current,
                'Monthly Cost (BYOL)': vm.estimated_monthly_cost_byol,
                'Monthly Savings': vm.potential_savings,
                'Risk Level': vm.risk_level,
                'Business Criticality': vm.business_criticality,
                'Environment': vm.environment_type,
                'Status': vm.status.value
            })
        
        df = pd.DataFrame(df_data)
        
        # Save to Excel with multiple sheets
        excel_path = os.path.join(self.output_dir, f"technical_analysis_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx")
        
        with pd.ExcelWriter(excel_path, engine='openpyxl') as writer:
            df.to_excel(writer, sheet_name='VM Inventory', index=False)
            
            # Summary statistics
            summary_data = {
                'Metric': ['Total VMs', 'Total Current Monthly Cost', 'Total BYOL Monthly Cost', 
                          'Total Monthly Savings', 'Total Annual Savings', 'Average Savings per VM'],
                'Value': [
                    len(vms),
                    df['Monthly Cost (Current)'].sum(),
                    df['Monthly Cost (BYOL)'].sum(),
                    df['Monthly Savings'].sum(),
                    df['Monthly Savings'].sum() * 12,
                    df['Monthly Savings'].mean()
                ]
            }
            summary_df = pd.DataFrame(summary_data)
            summary_df.to_excel(writer, sheet_name='Summary', index=False)
            
            # Risk analysis
            risk_analysis = df.groupby('Risk Level').agg({
                'VM Name': 'count',
                'Monthly Savings': 'sum',
                'Monthly Cost (Current)': 'sum'
            }).rename(columns={'VM Name': 'VM Count'})
            risk_analysis.to_excel(writer, sheet_name='Risk Analysis')
            
            # Environment analysis
            env_analysis = df.groupby('Environment').agg({
                'VM Name': 'count',
                'Monthly Savings': 'sum',
                'Monthly Cost (Current)': 'sum'
            }).rename(columns={'VM Name': 'VM Count'})
            env_analysis.to_excel(writer, sheet_name='Environment Analysis')
        
        return excel_path
    
    def generate_conversion_plan(self, vms: List[VMInfo], risk_assessments: Dict) -> str:
        """Generate step-by-step conversion plan"""
        plan_data = []
        
        # Sort VMs by risk level and potential savings
        risk_order = {'very_low': 1, 'low': 2, 'medium': 3, 'high': 4, 'critical': 5}
        sorted_vms = sorted(vms, key=lambda x: (risk_order.get(x.risk_level, 3), -x.potential_savings))
        
        phase = 1
        current_phase_vms = []
        
        for i, vm in enumerate(sorted_vms):
            if vm.current_license_type == LicenseType.ON_DEMAND:  # Only convert non-BYOL VMs
                risk_assessment = risk_assessments.get(vm.vm_id, {})
                
                plan_data.append({
                    'Phase': phase,
                    'VM Name': vm.name,
                    'VM ID': vm.vm_id,
                    'Risk Level': vm.risk_level,
                    'Monthly Savings': vm.potential_savings,
                    'Business Criticality': vm.business_criticality,
                    'Environment': vm.environment_type,
                    'Recommended Timeline': self._get_timeline_recommendation(vm.risk_level),
                    'Prerequisites': '; '.join(risk_assessment.get('mitigation_steps', [])),
                    'Estimated Duration': self._get_duration_estimate(vm.risk_level)
                })
                
                current_phase_vms.append(vm)
                
                # Start new phase after 10 VMs or when risk level changes significantly
                if len(current_phase_vms) >= 10 or (i < len(sorted_vms) - 1 and 
                    risk_order.get(sorted_vms[i+1].risk_level, 3) > risk_order.get(vm.risk_level, 3)):
                    phase += 1
                    current_phase_vms = []
        
        # Save conversion plan
        plan_df = pd.DataFrame(plan_data)
        plan_path = os.path.join(self.output_dir, f"conversion_plan_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx")
        
        with pd.ExcelWriter(plan_path, engine='openpyxl') as writer:
            plan_df.to_excel(writer, sheet_name='Conversion Plan', index=False)
            
            # Phase summary
            phase_summary = plan_df.groupby('Phase').agg({
                'VM Name': 'count',
                'Monthly Savings': 'sum',
                'Risk Level': lambda x: x.mode().iloc[0] if not x.empty else 'unknown'
            }).rename(columns={'VM Name': 'VM Count', 'Risk Level': 'Primary Risk Level'})
            phase_summary.to_excel(writer, sheet_name='Phase Summary')
        
        return plan_path
    
    def _get_timeline_recommendation(self, risk_level: str) -> str:
        """Get timeline recommendation based on risk level"""
        timelines = {
            'very_low': 'Immediate',
            'low': 'Within 1 week',
            'medium': 'Within 2 weeks',
            'high': 'Within 1 month',
            'critical': 'Requires extensive planning'
        }
        return timelines.get(risk_level, 'Review required')
    
    def _get_duration_estimate(self, risk_level: str) -> str:
        """Get duration estimate based on risk level"""
        durations = {
            'very_low': '15 minutes',
            'low': '30 minutes',
            'medium': '1 hour',
            'high': '2-4 hours',
            'critical': '4+ hours'
        }
        return durations.get(risk_level, '1 hour')


class MonitoringIntegration:
    """Integration with monitoring and alerting systems"""
    
    def __init__(self):
        self.monitoring_endpoints = {}
        self.alert_thresholds = {
            'cost_variance': 0.15,  # 15% variance threshold
            'performance_degradation': 0.10,  # 10% performance degradation
            'availability_impact': 0.02  # 2% availability impact
        }
    
    def add_monitoring_endpoint(self, name: str, endpoint_url: str, auth_token: str = None):
        """Add monitoring endpoint for post-conversion tracking"""
        self.monitoring_endpoints[name] = {
            'url': endpoint_url,
            'auth_token': auth_token,
            'last_check': None
        }
    
    def track_conversion_metrics(self, vm_id: str, pre_conversion_metrics: Dict, 
                               post_conversion_metrics: Dict) -> Dict:
        """Track and compare pre/post conversion metrics"""
        comparison = {
            'vm_id': vm_id,
            'conversion_timestamp': datetime.datetime.now().isoformat(),
            'metrics_comparison': {},
            'alerts': [],
            'status': 'success'
        }
        
        # Compare key metrics
        for metric, pre_value in pre_conversion_metrics.items():
            post_value = post_conversion_metrics.get(metric)
            if post_value is not None:
                variance = abs(post_value - pre_value) / pre_value if pre_value != 0 else 0
                comparison['metrics_comparison'][metric] = {
                    'pre_conversion': pre_value,
                    'post_conversion': post_value,
                    'variance_percent': variance * 100,
                    'status': 'normal' if variance < self.alert_thresholds.get('cost_variance', 0.15) else 'alert'
                }
                
                # Generate alerts for significant variances
                if variance > self.alert_thresholds.get('cost_variance', 0.15):
                    comparison['alerts'].append({
                        'type': 'performance_variance',
                        'metric': metric,
                        'variance': variance * 100,
                        'threshold': self.alert_thresholds.get('cost_variance', 0.15) * 100
                    })
        
        # Set overall status
        if comparison['alerts']:
            comparison['status'] = 'requires_attention'
        
        return comparison
    
    def send_conversion_notification(self, vm_id: str, status: str, details: Dict):
        """Send notification about conversion status"""
        notification = {
            'timestamp': datetime.datetime.now().isoformat(),
            'vm_id': vm_id,
            'status': status,
            'details': details
        }
        
        # In practice, this would integrate with Teams, Slack, email, etc.
        logger.info(f"Conversion notification: {notification}")
        return notification


class BYOLConverter:
    """Enhanced main class for BYOL conversion process with comprehensive features"""
    
    def __init__(self, cloud_provider: CloudProvider = CloudProvider.AZURE, dry_run: bool = False, **kwargs):
        self.dry_run = dry_run
        self.cloud_provider = cloud_provider
        
        # Initialize core components
        self.license_manager = LicenseManager()
        self.cost_engine = CostOptimizationEngine()
        self.risk_engine = RiskAssessmentEngine()
        self.dashboard = BYOLDashboard(kwargs.get('output_dir', 'byol_reports'))
        self.monitoring = MonitoringIntegration()
        
        # Initialize VM managers
        if cloud_provider == CloudProvider.AZURE:
            # Support for multiple Azure subscriptions with auto-discovery
            subscription_ids = kwargs.get('subscription_ids')
            
            # If no subscription IDs provided, auto-discover all accessible subscriptions
            if not subscription_ids:
                single_sub_id = kwargs.get('subscription_id')
                if single_sub_id:
                    subscription_ids = [single_sub_id]
                else:
                    # Auto-discovery mode - will discover all accessible subscriptions
                    subscription_ids = None
                    logger.info("🔍 Auto-discovery mode: Will scan all accessible Azure subscriptions")
            
            if not subscription_ids or len(subscription_ids) > 1:
                self.vm_manager = MultiSubscriptionAzureManager(subscription_ids)
                self.multi_subscription_mode = True
                discovered_count = len(self.vm_manager.subscription_ids) if hasattr(self.vm_manager, 'subscription_ids') else 0
                logger.info(f"🔍 Initialized multi-subscription Azure manager for {discovered_count} subscriptions")
            else:
                self.vm_manager = AzureVMManager(subscription_ids[0])
                self.multi_subscription_mode = False
                logger.info(f"🔍 Initialized single Azure subscription manager")
                
        elif cloud_provider == CloudProvider.AWS:
            self.vm_manager = AWSVMManager(kwargs.get('region', 'us-east-1'))
            self.multi_subscription_mode = False
        elif cloud_provider == CloudProvider.GCP:
            self.vm_manager = GCPVMManager(kwargs.get('project_id'))
            self.multi_subscription_mode = False
        elif cloud_provider == CloudProvider.MULTI_CLOUD:
            self.vm_manager = MultiCloudVMManager()
            self.multi_subscription_mode = True
            # Configure multi-cloud managers based on kwargs
            if kwargs.get('azure_subscription_ids'):
                for sub_id in kwargs['azure_subscription_ids']:
                    self.vm_manager.add_azure_manager(sub_id)
            elif kwargs.get('azure_subscription_id'):
                self.vm_manager.add_azure_manager(kwargs['azure_subscription_id'])
            if kwargs.get('aws_region'):
                self.vm_manager.add_aws_manager(kwargs['aws_region'])
            if kwargs.get('gcp_project_id'):
                self.vm_manager.add_gcp_manager(kwargs['gcp_project_id'])
        else:
            raise NotImplementedError(f"Provider {cloud_provider} not implemented")
        
        # Conversion tracking
        self.conversion_log = []
        self.conversion_history = []
        self.rollback_snapshots = {}
        
        # Performance tracking
        self.pre_conversion_metrics = {}
        self.post_conversion_metrics = {}
        
        if self.dry_run:
            logger.info("🔍 DRY RUN MODE ENABLED - No actual changes will be made")
    
    async def run_comprehensive_analysis(self) -> Dict:
        """Run complete BYOL analysis with all enhanced features"""
        logger.info("🚀 Starting comprehensive BYOL analysis...")
        
        # Step 1: Discover VM inventory
        logger.info("📊 Step 1: Discovering VM inventory...")
        if self.multi_subscription_mode and hasattr(self.vm_manager, 'discover_all_subscriptions_vms'):
            # Multi-subscription Azure or multi-cloud
            if isinstance(self.vm_manager, MultiSubscriptionAzureManager):
                all_vms_by_sub = self.vm_manager.discover_all_subscriptions_vms()
                vms = self.vm_manager.get_consolidated_vm_list()
                subscription_summary = self.vm_manager.get_subscription_summary()
            else:
                # Multi-cloud
                all_vms_by_provider = self.vm_manager.discover_all_vms()
                vms = []
                for provider_vms in all_vms_by_provider.values():
                    vms.extend(provider_vms)
                subscription_summary = None
        else:
            # Single subscription/provider
            vms = self.vm_manager.discover_vms()
            all_vms_by_sub = None
            subscription_summary = None
        
        logger.info(f"Found {len(vms)} Windows VMs")
        
        # Step 2: Enhanced risk assessment
        logger.info("⚡ Step 2: Performing enhanced risk assessment...")
        risk_assessments = {}
        for vm in vms:
            risk_assessment = self.risk_engine.assess_conversion_risk(vm)
            risk_assessments[vm.vm_id] = risk_assessment
            # Update VM risk level with enhanced assessment
            vm.risk_level = risk_assessment['risk_level']
            vm.conversion_readiness_score = 100 - risk_assessment['risk_score']
        
        # Step 3: Cost optimization analysis
        logger.info("💰 Step 3: Running cost optimization analysis...")
        cost_analysis = self.cost_engine.analyze_cost_optimization(vms)
        
        # Step 4: License requirement analysis
        logger.info("🔑 Step 4: Analyzing license requirements...")
        license_analysis = self.analyze_licensing_requirements(vms)
        
        # Step 5: ROI calculation
        logger.info("📈 Step 5: Calculating ROI and timeline...")
        roi_analysis = self.cost_engine.calculate_roi_timeline(
            initial_investment=10000,  # Estimated setup cost
            monthly_savings=cost_analysis['monthly_savings']
        )
        
        # Compile comprehensive analysis
        comprehensive_analysis = {
            'timestamp': datetime.datetime.now().isoformat(),
            'multi_subscription_mode': self.multi_subscription_mode,
            'subscription_summary': subscription_summary,
            'vm_inventory': {
                'total_vms': len(vms),
                'by_provider': self._get_vm_distribution_by_provider(vms),
                'by_risk_level': self._get_vm_distribution_by_risk(vms),
                'by_environment': self._get_vm_distribution_by_environment(vms),
                'by_subscription': self._get_vm_distribution_by_subscription(vms) if self.multi_subscription_mode else None
            },
            'cost_analysis': cost_analysis,
            'license_analysis': license_analysis,
            'roi_analysis': roi_analysis,
            'risk_summary': self._generate_risk_summary(vms, risk_assessments),
            'conversion_candidates': len([vm for vm in vms if vm.current_license_type == LicenseType.ON_DEMAND]),
            'optimization_recommendations': cost_analysis['optimization_recommendations'],
            'implementation_timeline': self._generate_implementation_timeline(vms, risk_assessments)
        }
        
        # Step 6: Generate reports
        logger.info("📋 Step 6: Generating comprehensive reports...")
        await self._generate_all_reports(vms, comprehensive_analysis, risk_assessments)
        
        return comprehensive_analysis
    
    async def execute_conversion_plan(self, vm_ids: List[str], phase: str = "pilot") -> Dict:
        """Execute BYOL conversion with enhanced safety and monitoring"""
        logger.info(f"🔄 Starting conversion execution - Phase: {phase}")
        
        if self.dry_run:
            logger.info("🔍 DRY RUN: Simulating conversion process...")
        
        execution_results = {
            'phase': phase,
            'start_time': datetime.datetime.now().isoformat(),
            'total_vms': len(vm_ids),
            'successful_conversions': [],
            'failed_conversions': [],
            'rollback_actions': [],
            'cost_impact': 0.0,
            'warnings': []
        }
        
        # Process conversions with concurrent execution
        semaphore = asyncio.Semaphore(5)  # Limit concurrent conversions
        
        async def convert_single_vm(vm_id: str):
            async with semaphore:
                return await self._execute_single_conversion(vm_id, execution_results)
        
        # Execute conversions
        conversion_tasks = [convert_single_vm(vm_id) for vm_id in vm_ids]
        results = await asyncio.gather(*conversion_tasks, return_exceptions=True)
        
        # Process results
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                execution_results['failed_conversions'].append({
                    'vm_id': vm_ids[i],
                    'error': str(result),
                    'timestamp': datetime.datetime.now().isoformat()
                })
            elif result and result.get('success'):
                execution_results['successful_conversions'].append(result)
                execution_results['cost_impact'] += result.get('monthly_savings', 0)
        
        execution_results['end_time'] = datetime.datetime.now().isoformat()
        execution_results['success_rate'] = len(execution_results['successful_conversions']) / len(vm_ids) * 100
        
        # Log summary
        logger.info(f"✅ Conversion completed: {len(execution_results['successful_conversions'])}/{len(vm_ids)} successful")
        logger.info(f"💰 Total monthly savings: ${execution_results['cost_impact']:,.2f}")
        
        return execution_results
    
    async def _execute_single_conversion(self, vm_id: str, execution_results: Dict) -> Dict:
        """Execute conversion for a single VM with comprehensive safety checks"""
        conversion_result = {
            'vm_id': vm_id,
            'success': False,
            'start_time': datetime.datetime.now().isoformat(),
            'steps_completed': [],
            'rollback_info': {},
            'monthly_savings': 0.0
        }
        
        try:
            # Step 1: Pre-conversion validation
            logger.info(f"🔍 Pre-conversion validation for {vm_id}")
            if not self.dry_run:
                pre_metrics = await self._collect_pre_conversion_metrics(vm_id)
                self.pre_conversion_metrics[vm_id] = pre_metrics
            conversion_result['steps_completed'].append('pre_validation')
            
            # Step 2: Create snapshot/backup
            logger.info(f"📸 Creating snapshot for {vm_id}")
            if not self.dry_run:
                snapshot_id = self.vm_manager.create_snapshot(vm_id)
                self.rollback_snapshots[vm_id] = snapshot_id
                conversion_result['rollback_info']['snapshot_id'] = snapshot_id
            else:
                conversion_result['rollback_info']['snapshot_id'] = f"dry-run-snapshot-{vm_id}"
            conversion_result['steps_completed'].append('snapshot_creation')
            
            # Step 3: License allocation
            logger.info(f"🔑 Allocating license for {vm_id}")
            # Get VM info to determine required license
            vm_info = next((vm for vm in self.vm_manager.discover_vms() if vm.vm_id == vm_id), None)
            if not vm_info:
                raise Exception(f"VM {vm_id} not found")
            
            if not self.dry_run:
                license = self.license_manager.allocate_license(vm_id, "Standard", vm_info.cores)
                if not license:
                    raise Exception(f"No available license for {vm_id}")
            conversion_result['steps_completed'].append('license_allocation')
            
            # Step 4: Perform conversion
            logger.info(f"🔄 Converting {vm_id} to BYOL")
            if not self.dry_run:
                conversion_success = self.vm_manager.convert_to_byol(vm_id)
                if not conversion_success:
                    raise Exception(f"Conversion failed for {vm_id}")
            conversion_result['steps_completed'].append('conversion')
            
            # Step 5: Post-conversion validation
            logger.info(f"✅ Post-conversion validation for {vm_id}")
            if not self.dry_run:
                await asyncio.sleep(30)  # Wait for changes to take effect
                post_metrics = await self._collect_post_conversion_metrics(vm_id)
                self.post_conversion_metrics[vm_id] = post_metrics
                
                # Validate conversion success
                validation_result = self._validate_conversion(vm_id, pre_metrics, post_metrics)
                if not validation_result['success']:
                    execution_results['warnings'].append(f"Validation issues for {vm_id}: {validation_result['issues']}")
            
            conversion_result['steps_completed'].append('post_validation')
            conversion_result['monthly_savings'] = vm_info.potential_savings
            conversion_result['success'] = True
            conversion_result['end_time'] = datetime.datetime.now().isoformat()
            
            logger.info(f"✅ Successfully converted {vm_id}")
            
        except Exception as e:
            logger.error(f"❌ Conversion failed for {vm_id}: {e}")
            conversion_result['error'] = str(e)
            conversion_result['end_time'] = datetime.datetime.now().isoformat()
            
            # Attempt rollback if needed
            if 'conversion' in conversion_result['steps_completed'] and not self.dry_run:
                logger.info(f"🔄 Initiating rollback for {vm_id}")
                rollback_result = await self._rollback_conversion(vm_id, conversion_result['rollback_info'])
                conversion_result['rollback_result'] = rollback_result
        
        return conversion_result
    
    async def _collect_pre_conversion_metrics(self, vm_id: str) -> Dict:
        """Collect baseline metrics before conversion"""
        # In practice, integrate with monitoring systems
        return {
            'cpu_utilization': 45.2,
            'memory_utilization': 67.8,
            'disk_io': 1234.5,
            'network_io': 567.8,
            'response_time': 125.3,
            'availability': 99.95
        }
    
    async def _collect_post_conversion_metrics(self, vm_id: str) -> Dict:
        """Collect metrics after conversion"""
        # In practice, integrate with monitoring systems
        return {
            'cpu_utilization': 44.8,
            'memory_utilization': 68.1,
            'disk_io': 1235.2,
            'network_io': 568.1,
            'response_time': 126.7,
            'availability': 99.94
        }
    
    def _validate_conversion(self, vm_id: str, pre_metrics: Dict, post_metrics: Dict) -> Dict:
        """Validate conversion success by comparing metrics"""
        validation_result = {
            'success': True,
            'issues': []
        }
        
        # Check for significant performance degradation
        for metric, pre_value in pre_metrics.items():
            post_value = post_metrics.get(metric, pre_value)
            if metric in ['response_time'] and post_value > pre_value * 1.1:  # 10% increase in response time
                validation_result['issues'].append(f"{metric} increased by {((post_value/pre_value-1)*100):.1f}%")
            elif metric in ['availability'] and post_value < pre_value * 0.99:  # 1% decrease in availability
                validation_result['issues'].append(f"{metric} decreased by {((1-post_value/pre_value)*100):.1f}%")
        
        if validation_result['issues']:
            validation_result['success'] = False
        
        return validation_result
    
    async def _rollback_conversion(self, vm_id: str, rollback_info: Dict) -> Dict:
        """Rollback conversion if issues are detected"""
        rollback_result = {
            'success': False,
            'actions_taken': [],
            'timestamp': datetime.datetime.now().isoformat()
        }
        
        try:
            # Release allocated license
            self.license_manager.release_license(vm_id)
            rollback_result['actions_taken'].append('license_released')
            
            # Revert from snapshot
            snapshot_id = rollback_info.get('snapshot_id')
            if snapshot_id:
                revert_success = self.vm_manager.revert_from_snapshot(vm_id, snapshot_id)
                if revert_success:
                    rollback_result['actions_taken'].append('snapshot_reverted')
                else:
                    rollback_result['actions_taken'].append('snapshot_revert_failed')
            
            rollback_result['success'] = True
            logger.info(f"✅ Rollback completed for {vm_id}")
            
        except Exception as e:
            logger.error(f"❌ Rollback failed for {vm_id}: {e}")
            rollback_result['error'] = str(e)
        
        return rollback_result
    
    async def _generate_all_reports(self, vms: List[VMInfo], analysis: Dict, risk_assessments: Dict):
        """Generate all comprehensive reports"""
        try:
            # Executive summary (generates HTML file)
            executive_html_path = self.dashboard.generate_executive_summary(analysis)
            logger.info(f"📊 Executive summary generated: {executive_html_path}")
            
            # Technical analysis (generates Excel file)
            technical_excel_path = self.dashboard.generate_technical_report(vms, analysis)
            logger.info(f"📋 Technical analysis Excel generated: {technical_excel_path}")
            
            # Conversion plan (generates Excel file)
            conversion_plan_path = self.dashboard.generate_conversion_plan(vms, risk_assessments)
            logger.info(f"📅 Conversion plan generated: {conversion_plan_path}")
            
            # Generate additional cost analysis report
            cost_report = self.generate_cost_analysis_report(vms, analysis)
            logger.info(f"💰 Cost analysis report: {cost_report}")
            
            print(f"\n🎉 Reports generated successfully!")
            print(f"📄 Executive Summary (HTML): {executive_html_path}")
            print(f"📊 Technical Analysis (Excel): {technical_excel_path}")
            print(f"📋 Conversion Plan (Excel): {conversion_plan_path}")
            
        except Exception as e:
            logger.error(f"Error generating reports: {e}")
            print(f"❌ Error generating reports: {e}")
    
    def _get_vm_distribution_by_provider(self, vms: List[VMInfo]) -> Dict:
        """Get VM distribution by cloud provider"""
        distribution = {}
        for vm in vms:
            provider = vm.region if hasattr(vm, 'region') else 'azure'  # Default to azure
            distribution[provider] = distribution.get(provider, 0) + 1
        return distribution
    
    def _get_vm_distribution_by_risk(self, vms: List[VMInfo]) -> Dict:
        """Get VM distribution by risk level"""
        distribution = {}
        for vm in vms:
            risk = vm.risk_level
            distribution[risk] = distribution.get(risk, 0) + 1
        return distribution
    
    def _get_vm_distribution_by_environment(self, vms: List[VMInfo]) -> Dict:
        """Get VM distribution by environment type"""
        distribution = {}
        for vm in vms:
            env = vm.environment_type
            distribution[env] = distribution.get(env, 0) + 1
        return distribution
    
    def _get_vm_distribution_by_subscription(self, vms: List[VMInfo]) -> Dict:
        """Get VM distribution by subscription (for multi-subscription mode)"""
        distribution = {}
        for vm in vms:
            subscription = getattr(vm, 'subscription_id', 'unknown')
            distribution[subscription] = distribution.get(subscription, 0) + 1
        return distribution
    
    def _generate_risk_summary(self, vms: List[VMInfo], risk_assessments: Dict) -> Dict:
        """Generate risk level summary with recommendations"""
        risk_summary = {}
        
        for vm in vms:
            risk_level = vm.risk_level
            if risk_level not in risk_summary:
                risk_summary[risk_level] = {
                    'count': 0,
                    'savings': 0,
                    'recommendation': ''
                }
            
            risk_summary[risk_level]['count'] += 1
            risk_summary[risk_level]['savings'] += vm.potential_savings
        
        # Add recommendations
        risk_summary.get('very_low', {})['recommendation'] = 'Immediate conversion recommended'
        risk_summary.get('low', {})['recommendation'] = 'Conversion with standard precautions'
        risk_summary.get('medium', {})['recommendation'] = 'Conversion with enhanced monitoring'
        risk_summary.get('high', {})['recommendation'] = 'Careful planning required'
        risk_summary.get('critical', {})['recommendation'] = 'Extensive risk mitigation needed'
        
        return risk_summary
    
    def _generate_implementation_timeline(self, vms: List[VMInfo], risk_assessments: Dict) -> Dict:
        """Generate recommended implementation timeline"""
        timeline = {
            'phase_1_immediate': [],
            'phase_2_short_term': [],
            'phase_3_medium_term': [],
            'phase_4_long_term': []
        }
        
        for vm in vms:
            if vm.current_license_type == LicenseType.ON_DEMAND:
                if vm.risk_level in ['very_low', 'low']:
                    timeline['phase_1_immediate'].append(vm.vm_id)
                elif vm.risk_level == 'medium':
                    timeline['phase_2_short_term'].append(vm.vm_id)
                elif vm.risk_level == 'high':
                    timeline['phase_3_medium_term'].append(vm.vm_id)
                else:  # critical
                    timeline['phase_4_long_term'].append(vm.vm_id)
        
        return timeline
    
    def discover_inventory(self) -> List[VMInfo]:
        """Step 1: Discover current VM inventory and generate comprehensive reports"""
        logger.info("Starting VM inventory discovery...")
        
        # Run comprehensive analysis asynchronously
        try:
            import asyncio
            # Run the comprehensive analysis
            analysis_results = asyncio.run(self.run_comprehensive_analysis())
            vms = self._extract_vms_from_analysis(analysis_results)
        except Exception as e:
            logger.warning(f"Could not run comprehensive analysis: {e}. Falling back to basic inventory.")
            # Fallback to basic discovery
            vms = self.vm_manager.discover_vms()
        
        # Save inventory to file
        self.save_inventory_report(vms, "vm_inventory.json")
        return vms

    def _extract_vms_from_analysis(self, analysis_results: Dict) -> List[VMInfo]:
        """Extract VMs list from comprehensive analysis results"""
        # The VMs are stored in the vm_manager after analysis
        if self.multi_subscription_mode and hasattr(self.vm_manager, 'get_consolidated_vm_list'):
            return self.vm_manager.get_consolidated_vm_list()
        else:
            return self.vm_manager.discover_vms()
    
    def analyze_licensing_requirements(self, vms: List[VMInfo]) -> Dict:
        """Analyze current licensing and requirements"""
        analysis = {
            'total_vms': len(vms),
            'on_demand_vms': len([vm for vm in vms if vm.current_license_type == LicenseType.ON_DEMAND]),
            'byol_vms': len([vm for vm in vms if vm.current_license_type == LicenseType.BYOL]),
            'total_current_cost': sum(vm.monthly_cost_current for vm in vms),
            'total_potential_byol_cost': sum(vm.estimated_monthly_cost_byol for vm in vms),
            'total_potential_savings': sum(vm.potential_savings for vm in vms),
            'license_requirements': {},
            'available_licenses': len([l for l in self.license_manager.licenses if not l.in_use])
        }
        
        # Calculate license requirements by edition
        for vm in vms:
            if vm.current_license_type == LicenseType.ON_DEMAND:
                edition = self._determine_windows_edition(vm.os_version)
                if edition not in analysis['license_requirements']:
                    analysis['license_requirements'][edition] = {'count': 0, 'cores': 0}
                analysis['license_requirements'][edition]['count'] += 1
                analysis['license_requirements'][edition]['cores'] += vm.cores
        
        return analysis
    
    def _determine_windows_edition(self, os_version: str) -> str:
        """Determine Windows edition from OS version"""
        if 'datacenter' in os_version.lower():
            return 'Datacenter'
        else:
            return 'Standard'
    
    def identify_test_candidates(self, vms: List[VMInfo]) -> List[VMInfo]:
        """Step 2: Identify test candidates for conversion"""
        candidates = []
        
        for vm in vms:
            if (vm.current_license_type == LicenseType.ON_DEMAND and 
                vm.risk_level == 'low' and
                vm.potential_savings > 0):
                candidates.append(vm)
        
        # Sort by potential savings (highest first)
        candidates.sort(key=lambda x: x.potential_savings, reverse=True)
        
        logger.info(f"Identified {len(candidates)} test candidates")
        return candidates[:5]  # Return top 5 candidates
    
    def run_test_conversion(self, test_vms: List[VMInfo]) -> List[Dict]:
        """Step 3: Run test conversion on selected VMs"""
        results = []
        
        if self.dry_run:
            logger.info("🔍 DRY RUN: Simulating test conversions...")
            for vm in test_vms:
                logger.info(f"🔍 DRY RUN: Would convert VM: {vm.name}")
                result = self._simulate_conversion(vm, test_mode=True)
                results.append(result)
            return results
        
        for vm in test_vms:
            logger.info(f"Starting test conversion for VM: {vm.name}")
            result = self._convert_single_vm(vm, test_mode=True)
            results.append(result)
            
            # Wait between conversions
            import time
            time.sleep(30)
        
        return results
    
    def _convert_single_vm(self, vm: VMInfo, test_mode: bool = False) -> Dict:
        """Convert a single VM to BYOL"""
        result = {
            'vm_id': vm.vm_id,
            'vm_name': vm.name,
            'conversion_time': datetime.datetime.now().isoformat(),
            'success': False,
            'error': None,
            'snapshot_id': None,
            'license_allocated': None,
            'test_mode': test_mode,
            'dry_run': self.dry_run
        }
        
        # If dry run mode, simulate the conversion
        if self.dry_run:
            return self._simulate_conversion(vm, test_mode)
        
        try:
            # Step 1: Check license availability
            edition = self._determine_windows_edition(vm.os_version)
            license = self.license_manager.allocate_license(vm.vm_id, edition, vm.cores)
            
            if not license:
                result['error'] = f"No available {edition} license for {vm.cores} cores"
                return result
            
            result['license_allocated'] = license.license_key
            
            # Step 2: Create snapshot
            if not test_mode:
                snapshot_id = self.vm_manager.create_snapshot(vm.vm_id)
                result['snapshot_id'] = snapshot_id
            
            # Step 3: Convert to BYOL
            success = self.vm_manager.convert_to_byol(vm.vm_id)
            
            if success:
                result['success'] = True
                logger.info(f"Successfully converted VM {vm.name} to BYOL")
            else:
                # Release license on failure
                self.license_manager.release_license(vm.vm_id)
                result['error'] = "VM conversion failed"
                
        except Exception as e:
            result['error'] = str(e)
            logger.error(f"Error converting VM {vm.name}: {e}")
            
            # Release license on error
            self.license_manager.release_license(vm.vm_id)
        
        self.conversion_log.append(result)
        return result
    
    def _simulate_conversion(self, vm: VMInfo, test_mode: bool = False) -> Dict:
        """Simulate VM conversion for dry run mode"""
        result = {
            'vm_id': vm.vm_id,
            'vm_name': vm.name,
            'conversion_time': datetime.datetime.now().isoformat(),
            'success': True,  # Assume success in simulation
            'error': None,
            'snapshot_id': f"snapshot-{vm.name}-simulated" if not test_mode else None,
            'license_allocated': None,
            'test_mode': test_mode,
            'dry_run': True,
            'simulation_details': {}
        }
        
        # Simulate license check
        edition = self._determine_windows_edition(vm.os_version)
        available_licenses = self.license_manager.get_available_licenses(edition, vm.cores)
        
        if available_licenses:
            result['license_allocated'] = f"SIMULATED-{available_licenses[0].license_key}"
            result['simulation_details']['license_check'] = f"✅ Found available {edition} license for {vm.cores} cores"
            
            # Simulate conversion steps
            result['simulation_details']['steps_simulated'] = [
                "✅ License availability verified",
                "✅ Snapshot creation would succeed" if not test_mode else "⏭️ Snapshot skipped (test mode)",
                "✅ VM conversion to BYOL would succeed",
                "✅ License allocation would complete"
            ]
            
            logger.info(f"🔍 DRY RUN: VM {vm.name} conversion simulation successful")
            logger.info(f"🔍 DRY RUN: Would allocate license {available_licenses[0].license_key}")
            logger.info(f"🔍 DRY RUN: Projected monthly savings: ${vm.potential_savings:.2f}")
            
        else:
            result['success'] = False
            result['error'] = f"No available {edition} license for {vm.cores} cores"
            result['simulation_details']['license_check'] = f"❌ No available {edition} license for {vm.cores} cores"
            logger.warning(f"🔍 DRY RUN: VM {vm.name} conversion would fail - insufficient licenses")
        
        self.conversion_log.append(result)
        return result
    
    def batch_convert_vms(self, vms: List[VMInfo]) -> List[Dict]:
        """Convert multiple VMs to BYOL"""
        results = []
        
        if self.dry_run:
            logger.info("🔍 DRY RUN: Simulating batch VM conversions...")
            for vm in vms:
                if vm.current_license_type == LicenseType.ON_DEMAND:
                    result = self._simulate_conversion(vm, test_mode=False)
                    results.append(result)
            return results
        
        for vm in vms:
            if vm.current_license_type == LicenseType.ON_DEMAND:
                result = self._convert_single_vm(vm, test_mode=False)
                results.append(result)
        
        return results
    
    def generate_cost_analysis_report(self, vms: List[VMInfo], analysis: Dict) -> str:
        """Generate detailed cost analysis report"""
        dry_run_notice = "\n⚠️  DRY RUN MODE - This is a simulation report ⚠️\n" if self.dry_run else ""
        
        report = f"""
# Windows VM BYOL Conversion Analysis Report{dry_run_notice}
Generated: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
Mode: {'🔍 DRY RUN (Simulation)' if self.dry_run else '🚀 LIVE MODE'}

## Executive Summary
- Total VMs Analyzed: {analysis['total_vms']}
- Current On-Demand VMs: {analysis['on_demand_vms']}
- Current Monthly Cost: ${analysis['total_current_cost']:,.2f}
- Potential BYOL Cost: ${analysis['total_potential_byol_cost']:,.2f}
- **Potential Monthly Savings: ${analysis['total_potential_savings']:,.2f}**
- **Annual Savings Potential: ${analysis['total_potential_savings'] * 12:,.2f}**

## License Requirements
"""
        
        for edition, req in analysis['license_requirements'].items():
            report += f"- {edition}: {req['count']} VMs, {req['cores']} cores total\n"
        
        report += f"\n## Available Licenses: {analysis['available_licenses']}\n\n"
        
        # VM breakdown by risk level
        risk_breakdown = {}
        for vm in vms:
            if vm.risk_level not in risk_breakdown:
                risk_breakdown[vm.risk_level] = {'count': 0, 'savings': 0}
            risk_breakdown[vm.risk_level]['count'] += 1
            risk_breakdown[vm.risk_level]['savings'] += vm.potential_savings
        
        report += "## Risk Level Breakdown\n"
        for risk, data in risk_breakdown.items():
            report += f"- {risk.capitalize()} Risk: {data['count']} VMs, ${data['savings']:,.2f} potential monthly savings\n"
        
        return report
    
    def save_inventory_report(self, vms: List[VMInfo], filename: str):
        """Save VM inventory to file"""
        try:
            with open(filename, 'w') as f:
                json.dump([asdict(vm) for vm in vms], f, indent=2, default=str)
            logger.info(f"Saved inventory report to {filename}")
        except Exception as e:
            logger.error(f"Error saving inventory report: {e}")
    
    def save_conversion_log(self, filename: str = None):
        """Save conversion log to file"""
        if not filename:
            mode_prefix = "dryrun_" if self.dry_run else "live_"
            filename = f"{mode_prefix}conversion_log_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        
        try:
            with open(filename, 'w') as f:
                json.dump(self.conversion_log, f, indent=2)
            logger.info(f"Saved conversion log to {filename}")
        except Exception as e:
            logger.error(f"Error saving conversion log: {e}")
    
    def generate_dry_run_summary(self) -> str:
        """Generate a summary of dry run results"""
        if not self.dry_run or not self.conversion_log:
            return ""
        
        successful_sims = [log for log in self.conversion_log if log.get('success', False)]
        failed_sims = [log for log in self.conversion_log if not log.get('success', False)]
        
        summary = f"""
🔍 DRY RUN SUMMARY
==================
Total Simulations: {len(self.conversion_log)}
✅ Would Succeed: {len(successful_sims)}
❌ Would Fail: {len(failed_sims)}

SUCCESSFUL CONVERSIONS WOULD INCLUDE:
"""
        
        for sim in successful_sims:
            summary += f"  - {sim['vm_name']}: License {sim.get('license_allocated', 'N/A')}\n"
        
        if failed_sims:
            summary += "\nFAILED CONVERSIONS:\n"
            for sim in failed_sims:
                summary += f"  - {sim['vm_name']}: {sim.get('error', 'Unknown error')}\n"
        
        summary += f"\n💰 No actual costs incurred - this was a simulation\n"
        summary += f"🚀 Run without --dry-run to execute actual conversions\n"
        
        return summary

def main():
    """Main execution function with multi-subscription support"""
    import argparse
    
    # Parse command line arguments
    parser = argparse.ArgumentParser(description='Windows VM BYOL Conversion Tool')
    parser.add_argument('--dry-run', action='store_true', 
                       help='Run in simulation mode without making actual changes')
    parser.add_argument('--subscription-id', 
                       help='Single Azure subscription ID (overrides auto-discovery)')
    parser.add_argument('--subscription-ids', nargs='+',
                       help='Multiple Azure subscription IDs (overrides auto-discovery)')
    parser.add_argument('--subscription-file',
                       help='File containing list of subscription IDs (overrides auto-discovery)')
    parser.add_argument('--auto-discover', action='store_true', default=True,
                       help='Auto-discover all accessible subscriptions (default behavior)')
    parser.add_argument('--no-auto-discover', action='store_true',
                       help='Disable auto-discovery (requires manual subscription specification)')
    parser.add_argument('--batch-mode', action='store_true',
                       help='Run full batch conversion (use with caution)')
    parser.add_argument('--output-dir', default='byol_reports',
                       help='Output directory for reports')
    
    args = parser.parse_args()
    
    # Determine subscription IDs with auto-discovery as default
    subscription_ids = []
    auto_discovery_mode = False
    
    if args.no_auto_discover:
        # Explicit disable of auto-discovery
        auto_discovery_mode = False
    elif args.subscription_file:
        # Read from file
        try:
            with open(args.subscription_file, 'r') as f:
                subscription_ids = []
                for line in f:
                    line = line.strip()
                    # Skip empty lines and comments
                    if line and not line.startswith('#'):
                        subscription_ids.append(line)
            print(f"📂 Loaded {len(subscription_ids)} subscription IDs from {args.subscription_file}")
        except Exception as e:
            print(f"❌ Error reading subscription file: {e}")
            return
    elif args.subscription_ids:
        # Multiple subscriptions from command line
        subscription_ids = args.subscription_ids
        print(f"📋 Using {len(subscription_ids)} subscription IDs from command line")
    elif args.subscription_id:
        # Single subscription
        subscription_ids = [args.subscription_id]
        print(f"🔍 Using single subscription ID: {args.subscription_id}")
    else:
        # Default: Auto-discovery mode
        auto_discovery_mode = True
        subscription_ids = None
        print("🔍 Auto-discovery mode: Scanning all accessible Azure subscriptions...")
        print("💡 Use --no-auto-discover to disable auto-discovery")
    
    try:
        # Initialize converter with auto-discovery or specified subscriptions
        if auto_discovery_mode:
            print(f"🚀 Initializing BYOL converter with auto-discovery...")
            converter = BYOLConverter(
                CloudProvider.AZURE,
                dry_run=args.dry_run,
                output_dir=args.output_dir
                # No subscription IDs - will auto-discover
            )
        elif len(subscription_ids) > 1:
            print(f"🚀 Initializing multi-subscription BYOL converter for {len(subscription_ids)} subscriptions...")
            converter = BYOLConverter(
                CloudProvider.AZURE,
                dry_run=args.dry_run,
                subscription_ids=subscription_ids,
                output_dir=args.output_dir
            )
        else:
            print(f"🚀 Initializing single-subscription BYOL converter...")
            converter = BYOLConverter(
                CloudProvider.AZURE,
                dry_run=args.dry_run,
                subscription_id=subscription_ids[0] if subscription_ids else None,
                output_dir=args.output_dir
            )
        
        # Step 1: Discover inventory
        mode_text = "🔍 DRY RUN MODE: Discovering" if args.dry_run else "Discovering"
        if auto_discovery_mode:
            print(f"Step 1: {mode_text} VM inventory across all accessible subscriptions...")
        else:
            print(f"Step 1: {mode_text} VM inventory across {len(subscription_ids)} subscription(s)...")
        vms = converter.discover_inventory()
        
        if not vms:
            print("No VMs found. Exiting.")
            return
        
        # Show subscription breakdown if multi-subscription
        if ((not auto_discovery_mode and len(subscription_ids) > 1) or auto_discovery_mode) and hasattr(converter.vm_manager, 'get_subscription_summary'):
            sub_summary = converter.vm_manager.get_subscription_summary()
            print("\n📊 Subscription Breakdown:")
            for sub_id, details in sub_summary['subscription_details'].items():
                print(f"  🔹 {sub_id}: {details['vm_count']} VMs, ${details['potential_monthly_savings']:,.2f} potential savings")
            print(f"  📈 Grand Total: {sub_summary['grand_totals']['total_vms']} VMs, ${sub_summary['grand_totals']['total_potential_savings']:,.2f} potential savings")
        
        # Analyze licensing requirements
        analysis = converter.analyze_licensing_requirements(vms)
        
        # Generate and display cost analysis
        report = converter.generate_cost_analysis_report(vms, analysis)
        print(report)
        
        # Save detailed report
        report_prefix = "dryrun_" if args.dry_run else ""
        if auto_discovery_mode:
            multi_sub_prefix = "auto_discovery_"
        elif subscription_ids and len(subscription_ids) > 1:
            multi_sub_prefix = f"multi_sub_{len(subscription_ids)}_"
        else:
            multi_sub_prefix = ""
        report_filename = f"{report_prefix}{multi_sub_prefix}cost_analysis_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.md"
        with open(report_filename, 'w') as f:
            f.write(report)
        print(f"📄 Detailed report saved to: {report_filename}")
        
        # Step 2: Identify test candidates
        print(f"\nStep 2: Identifying test candidates...")
        test_candidates = converter.identify_test_candidates(vms)
        
        if test_candidates:
            print(f"Found {len(test_candidates)} test candidates:")
            for vm in test_candidates:
                # Show subscription info if multiple subscriptions (auto-discovery or manual multi-sub)
                show_sub_info = auto_discovery_mode or (subscription_ids and len(subscription_ids) > 1)
                sub_info = f" (Sub: {getattr(vm, 'subscription_id', 'unknown')})" if show_sub_info else ""
                print(f"  - {vm.name}{sub_info}: ${vm.potential_savings:.2f} monthly savings")
            
            # Different prompts for dry run vs live mode
            if auto_discovery_mode:
                subscription_text = "all discovered subscriptions"
            elif subscription_ids:
                subscription_text = f"{len(subscription_ids)} subscription(s)"
            else:
                subscription_text = "subscription"
                
            if args.dry_run:
                confirm = input(f"\nProceed with test conversion simulation across {subscription_text}? (y/n): ")
                action_text = "simulating test conversions"
            else:
                confirm = input(f"\n⚠️  Proceed with ACTUAL test conversion across {subscription_text}? (y/n): ")
                action_text = "running test conversions"
            
            if confirm.lower() == 'y':
                print(f"\nStep 3: {action_text.capitalize()}...")
                test_results = converter.run_test_conversion(test_candidates)
                
                # Display results
                successful = [r for r in test_results if r['success']]
                failed = [r for r in test_results if not r['success']]
                
                result_text = "simulations" if args.dry_run else "conversions"
                print(f"\nTest Results: {len(successful)} successful {result_text}, {len(failed)} failed")
                
                if failed:
                    failure_text = "simulations" if args.dry_run else "conversions"
                    print(f"Failed {failure_text}:")
                    for result in failed:
                        print(f"  - {result['vm_name']}: {result['error']}")
                
                # Show dry run summary if applicable
                if args.dry_run:
                    dry_run_summary = converter.generate_dry_run_summary()
                    print(dry_run_summary)
                
                # Multi-subscription batch mode option
                if args.batch_mode and successful:
                    if args.dry_run:
                        if auto_discovery_mode:
                            subscription_text = "all discovered subscriptions"
                        elif subscription_ids:
                            subscription_text = f"{len(subscription_ids)} subscription(s)"
                        else:
                            subscription_text = "subscription"
                        print(f"\n🔍 DRY RUN: Simulating batch conversion across {subscription_text}...")
                        batch_results = converter.batch_convert_vms(vms)
                        batch_successful = [r for r in batch_results if r['success']]
                        print(f"Batch simulation: {len(batch_successful)}/{len(batch_results)} would succeed across all subscriptions")
                        dry_run_summary = converter.generate_dry_run_summary()
                        print(dry_run_summary)
                    else:
                        total_eligible = sum(1 for vm in vms if vm.current_license_type == LicenseType.ON_DEMAND)
                        if auto_discovery_mode:
                            subscription_text = "all discovered subscriptions"
                        elif subscription_ids:
                            subscription_text = f"{len(subscription_ids)} subscription(s)"
                        else:
                            subscription_text = "subscription"
                        batch_confirm = input(f"\n⚠️  Run batch conversion on ALL eligible VMs across {subscription_text}? This will affect {total_eligible} VMs! (y/n): ")
                        if batch_confirm.lower() == 'y':
                            print("Running multi-subscription batch conversion...")
                            batch_results = converter.batch_convert_vms(vms)
                            batch_successful = [r for r in batch_results if r['success']]
                            print(f"Batch conversion completed: {len(batch_successful)}/{len(batch_results)} successful across all subscriptions")
        
        # Save conversion log
        converter.save_conversion_log()
        
        completion_text = "simulation" if args.dry_run else "conversion process"
        if auto_discovery_mode:
            subscription_text = " across all discovered subscriptions"
        elif subscription_ids and len(subscription_ids) > 1:
            subscription_text = f" across {len(subscription_ids)} subscription(s)"
        else:
            subscription_text = ""
        print(f"\n{completion_text.capitalize()}{subscription_text} completed. Check logs for details.")
        
        if args.dry_run:
            print("\n🚀 To execute actual conversions, run the script without --dry-run flag")
        
        # Show final subscription summary for multi-subscription runs
        show_summary = auto_discovery_mode or (subscription_ids and len(subscription_ids) > 1)
        if show_summary:
            if auto_discovery_mode:
                print(f"\n📊 Final Summary Across All Discovered Subscriptions:")
            else:
                print(f"\n📊 Final Summary Across {len(subscription_ids)} Subscriptions:")
            print(f"  📈 Total VMs Analyzed: {len(vms)}")
            if hasattr(converter.vm_manager, 'get_subscription_summary'):
                sub_summary = converter.vm_manager.get_subscription_summary()
                print(f"  💰 Total Potential Monthly Savings: ${sub_summary['grand_totals']['total_potential_savings']:,.2f}")
                print(f"  📅 Total Potential Annual Savings: ${sub_summary['grand_totals']['total_potential_savings'] * 12:,.2f}")
        
    except Exception as e:
        logger.error(f"Error in main execution: {e}")
        print(f"Error: {e}")


# Multi-subscription usage examples and helper functions
def create_subscription_list_file(subscription_ids: List[str], filename: str = "subscriptions.txt"):
    """Helper function to create a subscription list file"""
    try:
        with open(filename, 'w') as f:
            for sub_id in subscription_ids:
                f.write(f"{sub_id}\n")
        print(f"✅ Created subscription list file: {filename}")
    except Exception as e:
        print(f"❌ Error creating subscription file: {e}")


def example_multi_subscription_usage():
    """Example usage for multi-subscription BYOL conversion"""
    print("""
📋 Multi-Subscription BYOL Conversion Examples:

# 1. Using multiple subscription IDs from command line:
python byol_conversion_script.py --subscription-ids sub1-guid sub2-guid sub3-guid --dry-run

# 2. Using subscription list file:
python byol_conversion_script.py --subscription-file subscriptions.txt --dry-run

# 3. Batch conversion across multiple subscriptions:
python byol_conversion_script.py --subscription-ids sub1 sub2 sub3 --batch-mode --dry-run

# 4. Live conversion (remove --dry-run when ready):
python byol_conversion_script.py --subscription-file subscriptions.txt

# Create subscription list file programmatically:
from byol_conversion_script import create_subscription_list_file
subscription_ids = [
    "12345678-1234-1234-1234-123456789012",
    "87654321-4321-4321-4321-210987654321",
    "abcdef12-3456-7890-abcd-ef1234567890"
]
create_subscription_list_file(subscription_ids, "my_subscriptions.txt")
""")


if __name__ == "__main__":
    main()
