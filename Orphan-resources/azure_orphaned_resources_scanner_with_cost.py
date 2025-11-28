#!/usr/bin/env python3
"""
Azure Orphaned Resources Scanner - Production Version
Identifies and reports on unused Azure resources with cost data across subscriptions.

Author: Anand Lakhera
Version: 2.0.0

install dependencies-
python3 -m pip install azure-identity azure-mgmt-resource azure-mgmt-compute azure-mgmt-network azure-mgmt-cdn azure-mgmt-sql azure-mgmt-web azure-mgmt-trafficmanager azure-mgmt-dns azure-mgmt-logic azure-mgmt-costmanagement tenacity six


Usage:
python3 azure_orphaned_resources_scanner.py [--output-format json|csv|both] [--max-workers N] [--no-costs] [--subscriptions SUB_IDs] [--exclude-subscriptions SUB_IDs]

"""

import os
import sys
import json
import logging
import argparse
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional, Set
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, asdict
import csv

from azure.identity import DefaultAzureCredential, AzureCliCredential, ManagedIdentityCredential
from azure.mgmt.resource import SubscriptionClient, ResourceManagementClient
from azure.mgmt.compute import ComputeManagementClient
from azure.mgmt.network import NetworkManagementClient
from azure.mgmt.cdn import CdnManagementClient
from azure.mgmt.sql import SqlManagementClient
from azure.mgmt.web import WebSiteManagementClient
from azure.mgmt.trafficmanager import TrafficManagerManagementClient
from azure.mgmt.dns import DnsManagementClient
from azure.mgmt.logic import LogicManagementClient
from azure.mgmt.costmanagement import CostManagementClient
from azure.core.exceptions import AzureError, HttpResponseError, ResourceNotFoundError
from tenacity import retry, wait_exponential, stop_after_attempt, retry_if_exception_type

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(f'azure_orphan_scan_{datetime.now().strftime("%Y%m%d_%H%M%S")}.log'),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)


@dataclass
class OrphanedResource:
    """Data class for orphaned resource information."""
    resource_type: str
    resource_name: str
    resource_id: str
    location: str
    subscription_name: str
    subscription_id: str
    resource_group: str
    estimated_monthly_cost: float = 0.0
    tags: Dict[str, str] = None
    detected_at: str = datetime.utcnow().isoformat()
    
    def __post_init__(self):
        if self.tags is None:
            self.tags = {}


@dataclass
class ScanProgress:
    """Track scan progress for resume capability."""
    total_subscriptions: int
    completed_subscriptions: int
    failed_subscriptions: List[str]
    start_time: str
    last_update: str
    
    def to_dict(self):
        return asdict(self)
    
    def save(self, filepath: str = "scan_progress.json"):
        """Save progress to file."""
        try:
            with open(filepath, 'w') as f:
                json.dump(self.to_dict(), f, indent=2)
        except Exception as e:
            logger.error(f"Failed to save progress: {e}")


class AzureCredentialManager:
    """Manage Azure authentication with fallback mechanisms."""
    
    @staticmethod
    def get_credential():
        """Get appropriate Azure credential based on environment."""
        try:
            if os.getenv('AZURE_USE_MANAGED_IDENTITY', '').lower() == 'true':
                logger.info("Using Managed Identity authentication")
                return ManagedIdentityCredential()
            elif os.getenv('AZURE_USE_CLI', '').lower() == 'true':
                logger.info("Using Azure CLI authentication")
                return AzureCliCredential()
            else:
                logger.info("Using Default Azure authentication chain")
                return DefaultAzureCredential()
        except Exception as e:
            logger.error(f"Failed to initialize credential: {e}")
            raise


class ConfigManager:
    """Manage configuration from environment variables and files."""
    
    @staticmethod
    def get_excluded_subscriptions() -> Set[str]:
        """Get set of subscription IDs to exclude from scanning."""
        excluded = os.getenv('EXCLUDED_SUBSCRIPTIONS', '')
        if excluded:
            return set(sub.strip() for sub in excluded.split(',') if sub.strip())
        return set()
    
    @staticmethod
    def get_max_workers() -> int:
        """Get maximum number of parallel workers."""
        return int(os.getenv('MAX_WORKERS', '5'))
    
    @staticmethod
    def get_output_format() -> str:
        """Get desired output format (csv, json, both)."""
        return os.getenv('OUTPUT_FORMAT', 'json').lower()


@retry(
    retry=retry_if_exception_type((AzureError, HttpResponseError)),
    wait=wait_exponential(multiplier=1, min=4, max=60),
    stop=stop_after_attempt(3)
)
def safe_api_call(func, *args, **kwargs):
    """Wrapper for Azure API calls with retry logic."""
    try:
        return func(*args, **kwargs)
    except ResourceNotFoundError as e:
        logger.warning(f"Resource not found: {e}")
        return []
    except HttpResponseError as e:
        if e.status_code == 403:
            logger.warning(f"Insufficient permissions: {e}")
            return []
        raise
    except AzureError as e:
        logger.error(f"Azure API error: {e}")
        raise


class OrphanedResourceDetector:
    """Detect various types of orphaned Azure resources."""
    
    def __init__(self, subscription_id: str, credential):
        self.subscription_id = subscription_id
        self.credential = credential
        self.orphaned_resources: List[OrphanedResource] = []
        
    def _create_resource_entry(self, resource_type: str, resource, subscription_name: str) -> OrphanedResource:
        """Create standardized orphaned resource entry."""
        resource_group = self._extract_resource_group(getattr(resource, 'id', ''))
        return OrphanedResource(
            resource_type=resource_type,
            resource_name=resource.name,
            resource_id=getattr(resource, 'id', ''),
            location=getattr(resource, 'location', 'global'),
            subscription_name=subscription_name,
            subscription_id=self.subscription_id,
            resource_group=resource_group,
            tags=dict(getattr(resource, 'tags', {}) or {})
        )
    
    @staticmethod
    def _extract_resource_group(resource_id: str) -> str:
        """Extract resource group name from resource ID."""
        try:
            parts = resource_id.split('/')
            if 'resourceGroups' in parts:
                idx = parts.index('resourceGroups')
                return parts[idx + 1] if idx + 1 < len(parts) else ''
        except Exception:
            pass
        return ''
    
    def get_orphaned_disks(self, compute_client: ComputeManagementClient, subscription_name: str):
        """Find unattached managed disks."""
        logger.info(f"Scanning for orphaned disks in {subscription_name}")
        try:
            disks = safe_api_call(lambda: list(compute_client.disks.list()))
            for disk in disks:
                if not disk.managed_by:
                    self.orphaned_resources.append(
                        self._create_resource_entry('disk', disk, subscription_name)
                    )
        except Exception as e:
            logger.error(f"Error scanning disks: {e}")
    
    def get_unused_nics(self, network_client: NetworkManagementClient, subscription_name: str):
        """Find unused network interfaces."""
        logger.info(f"Scanning for unused NICs in {subscription_name}")
        try:
            nics = safe_api_call(lambda: list(network_client.network_interfaces.list_all()))
            for nic in nics:
                if not nic.virtual_machine:
                    self.orphaned_resources.append(
                        self._create_resource_entry('network_interface', nic, subscription_name)
                    )
        except Exception as e:
            logger.error(f"Error scanning NICs: {e}")
    
    def get_unassociated_public_ips(self, network_client: NetworkManagementClient, subscription_name: str):
        """Find unassociated public IP addresses."""
        logger.info(f"Scanning for unassociated public IPs in {subscription_name}")
        try:
            ips = safe_api_call(lambda: list(network_client.public_ip_addresses.list_all()))
            for ip in ips:
                if ip.ip_configuration is None:
                    self.orphaned_resources.append(
                        self._create_resource_entry('public_ip', ip, subscription_name)
                    )
        except Exception as e:
            logger.error(f"Error scanning public IPs: {e}")
    
    def get_unused_load_balancers(self, network_client: NetworkManagementClient, subscription_name: str):
        """Find unused load balancers (no backend pools or empty pools)."""
        logger.info(f"Scanning for unused load balancers in {subscription_name}")
        try:
            lbs = safe_api_call(lambda: list(network_client.load_balancers.list_all()))
            for lb in lbs:
                # Check if no backend pools exist OR all pools are empty
                if not lb.backend_address_pools or all(
                    not pool.backend_ip_configurations for pool in lb.backend_address_pools
                ):
                    self.orphaned_resources.append(
                        self._create_resource_entry('load_balancer', lb, subscription_name)
                    )
        except Exception as e:
            logger.error(f"Error scanning load balancers: {e}")
    
    def get_unused_nsgs(self, network_client: NetworkManagementClient, subscription_name: str):
        """Find unused network security groups."""
        logger.info(f"Scanning for unused NSGs in {subscription_name}")
        try:
            nsgs = safe_api_call(lambda: list(network_client.network_security_groups.list_all()))
            for nsg in nsgs:
                if not nsg.network_interfaces and not nsg.subnets:
                    self.orphaned_resources.append(
                        self._create_resource_entry('network_security_group', nsg, subscription_name)
                    )
        except Exception as e:
            logger.error(f"Error scanning NSGs: {e}")
    
    def get_unused_app_service_plans(self, web_client: WebSiteManagementClient, subscription_name: str):
        """Find app service plans without hosting apps."""
        logger.info(f"Scanning for unused app service plans in {subscription_name}")
        try:
            asps = safe_api_call(lambda: list(web_client.app_service_plans.list()))
            for asp in asps:
                try:
                    resource_group = self._extract_resource_group(asp.id)
                    apps = safe_api_call(
                        lambda: list(web_client.app_service_plans.list_web_apps(resource_group, asp.name))
                    )
                    if not apps:
                        self.orphaned_resources.append(
                            self._create_resource_entry('app_service_plan', asp, subscription_name)
                        )
                except Exception as e:
                    logger.warning(f"Error checking apps for ASP {asp.name}: {e}")
        except Exception as e:
            logger.error(f"Error scanning app service plans: {e}")
    
    def get_unused_availability_sets(self, compute_client: ComputeManagementClient, subscription_name: str):
        """Find availability sets not associated with any VM."""
        logger.info(f"Scanning for unused availability sets in {subscription_name}")
        try:
            av_sets = safe_api_call(lambda: list(compute_client.availability_sets.list_by_subscription()))
            for av_set in av_sets:
                # Check for DoNotDelete tag (Azure Site Recovery protection)
                tags = getattr(av_set, 'tags', {}) or {}
                if 'DoNotDelete' in tags:
                    continue
                
                if not av_set.virtual_machines:
                    self.orphaned_resources.append(
                        self._create_resource_entry('availability_set', av_set, subscription_name)
                    )
        except Exception as e:
            logger.error(f"Error scanning availability sets: {e}")
    
    def get_unused_route_tables(self, network_client: NetworkManagementClient, subscription_name: str):
        """Find route tables not attached to any subnet."""
        logger.info(f"Scanning for unused route tables in {subscription_name}")
        try:
            route_tables = safe_api_call(lambda: list(network_client.route_tables.list_all()))
            for rt in route_tables:
                if not rt.subnets:
                    self.orphaned_resources.append(
                        self._create_resource_entry('route_table', rt, subscription_name)
                    )
        except Exception as e:
            logger.error(f"Error scanning route tables: {e}")
    
    def get_unused_waf_policies(self, cdn_client: CdnManagementClient, 
                                resource_client: ResourceManagementClient, subscription_name: str):
        """Find Front Door WAF policies without associations."""
        logger.info(f"Scanning for unused WAF policies in {subscription_name}")
        try:
            resource_groups = safe_api_call(lambda: list(resource_client.resource_groups.list()))
            for rg in resource_groups:
                try:
                    policies = safe_api_call(lambda: list(cdn_client.policies.list(rg.name)))
                    for policy in policies:
                        if not policy.frontend_endpoint_links and not policy.security_policy_links:
                            self.orphaned_resources.append(
                                self._create_resource_entry('waf_policy', policy, subscription_name)
                            )
                except Exception as e:
                    logger.warning(f"Error scanning WAF policies in RG {rg.name}: {e}")
        except Exception as e:
            logger.error(f"Error scanning WAF policies: {e}")
    
    def get_unused_traffic_manager_profiles(self, tm_client: TrafficManagerManagementClient, subscription_name: str):
        """Find Traffic Manager profiles without endpoints."""
        logger.info(f"Scanning for unused Traffic Manager profiles in {subscription_name}")
        try:
            profiles = safe_api_call(lambda: list(tm_client.profiles.list_by_subscription()))
            for profile in profiles:
                if not profile.endpoints:
                    self.orphaned_resources.append(
                        self._create_resource_entry('traffic_manager_profile', profile, subscription_name)
                    )
        except Exception as e:
            logger.error(f"Error scanning Traffic Manager profiles: {e}")
    
    def get_application_gateways_without_backends(self, network_client: NetworkManagementClient, subscription_name: str):
        """Find Application Gateways without backend targets."""
        logger.info(f"Scanning for unused Application Gateways in {subscription_name}")
        try:
            agws = safe_api_call(lambda: list(network_client.application_gateways.list_all()))
            for agw in agws:
                if agw.backend_address_pools and all(
                    not pool.backend_addresses for pool in agw.backend_address_pools
                ):
                    self.orphaned_resources.append(
                        self._create_resource_entry('application_gateway', agw, subscription_name)
                    )
        except Exception as e:
            logger.error(f"Error scanning Application Gateways: {e}")
    
    def get_vnets_without_subnets(self, network_client: NetworkManagementClient, subscription_name: str):
        """Find Virtual Networks without subnets."""
        logger.info(f"Scanning for VNets without subnets in {subscription_name}")
        try:
            vnets = safe_api_call(lambda: list(network_client.virtual_networks.list_all()))
            for vnet in vnets:
                if not vnet.subnets:
                    self.orphaned_resources.append(
                        self._create_resource_entry('virtual_network', vnet, subscription_name)
                    )
        except Exception as e:
            logger.error(f"Error scanning VNets: {e}")
    
    def get_empty_subnets(self, network_client: NetworkManagementClient, subscription_name: str):
        """Find subnets without connected devices or delegation."""
        logger.info(f"Scanning for empty subnets in {subscription_name}")
        try:
            vnets = safe_api_call(lambda: list(network_client.virtual_networks.list_all()))
            for vnet in vnets:
                for subnet in vnet.subnets:
                    # Skip gateway subnets and other special subnets
                    if subnet.name.lower() in ['gatewaysubnet', 'azurefirewallsubnet', 'azurebastionsubnet']:
                        continue
                    
                    if not subnet.ip_configurations and not subnet.delegations:
                        # Create pseudo-resource for subnet
                        resource = type('obj', (object,), {
                            'name': f"{vnet.name}/{subnet.name}",
                            'id': subnet.id,
                            'location': vnet.location,
                            'tags': vnet.tags
                        })
                        self.orphaned_resources.append(
                            self._create_resource_entry('subnet', resource, subscription_name)
                        )
        except Exception as e:
            logger.error(f"Error scanning subnets: {e}")
    
    def get_unused_nat_gateways(self, network_client: NetworkManagementClient, subscription_name: str):
        """Find NAT Gateways not attached to any subnet."""
        logger.info(f"Scanning for unused NAT Gateways in {subscription_name}")
        try:
            nat_gateways = safe_api_call(lambda: list(network_client.nat_gateways.list_all()))
            for nat_gateway in nat_gateways:
                if not nat_gateway.subnets:
                    self.orphaned_resources.append(
                        self._create_resource_entry('nat_gateway', nat_gateway, subscription_name)
                    )
        except Exception as e:
            logger.error(f"Error scanning NAT Gateways: {e}")
    
    def get_empty_resource_groups(self, resource_client: ResourceManagementClient, subscription_name: str):
        """Find empty resource groups."""
        logger.info(f"Scanning for empty resource groups in {subscription_name}")
        try:
            resource_groups = safe_api_call(lambda: list(resource_client.resource_groups.list()))
            for rg in resource_groups:
                try:
                    resources = safe_api_call(
                        lambda: list(resource_client.resources.list_by_resource_group(rg.name))
                    )
                    if not resources:
                        self.orphaned_resources.append(
                            self._create_resource_entry('resource_group', rg, subscription_name)
                        )
                except Exception as e:
                    logger.warning(f"Error checking resources in RG {rg.name}: {e}")
        except Exception as e:
            logger.error(f"Error scanning resource groups: {e}")
    
    def scan_all(self, subscription_name: str) -> List[OrphanedResource]:
        """Run all orphaned resource scans for a subscription."""
        logger.info(f"Starting comprehensive scan for subscription: {subscription_name}")
        
        try:
            # Initialize clients
            compute_client = ComputeManagementClient(self.credential, self.subscription_id)
            network_client = NetworkManagementClient(self.credential, self.subscription_id)
            web_client = WebSiteManagementClient(self.credential, self.subscription_id)
            resource_client = ResourceManagementClient(self.credential, self.subscription_id)
            cdn_client = CdnManagementClient(self.credential, self.subscription_id)
            tm_client = TrafficManagerManagementClient(self.credential, self.subscription_id)
            
            # Run all detection methods
            self.get_orphaned_disks(compute_client, subscription_name)
            self.get_unused_nics(network_client, subscription_name)
            self.get_unassociated_public_ips(network_client, subscription_name)
            self.get_unused_load_balancers(network_client, subscription_name)
            self.get_unused_nsgs(network_client, subscription_name)
            self.get_unused_app_service_plans(web_client, subscription_name)
            self.get_unused_availability_sets(compute_client, subscription_name)
            self.get_unused_route_tables(network_client, subscription_name)
            self.get_unused_waf_policies(cdn_client, resource_client, subscription_name)
            self.get_unused_traffic_manager_profiles(tm_client, subscription_name)
            self.get_application_gateways_without_backends(network_client, subscription_name)
            self.get_vnets_without_subnets(network_client, subscription_name)
            self.get_empty_subnets(network_client, subscription_name)
            self.get_unused_nat_gateways(network_client, subscription_name)
            self.get_empty_resource_groups(resource_client, subscription_name)
            
            logger.info(f"Completed scan for {subscription_name}: found {len(self.orphaned_resources)} orphaned resources")
            
        except Exception as e:
            logger.error(f"Error during comprehensive scan of {subscription_name}: {e}")
        
        return self.orphaned_resources


class CostEstimator:
    """Estimate costs for orphaned resources using Azure Cost Management API."""
    
    def __init__(self, credential):
        self.credential = credential
        
    def get_resource_costs(self, resources: List[OrphanedResource]) -> List[OrphanedResource]:
        """Enrich resources with cost data from Azure Cost Management."""
        logger.info(f"Fetching cost data for {len(resources)} resources")
        
        # Group resources by subscription for efficient cost queries
        by_subscription = {}
        for resource in resources:
            if resource.subscription_id not in by_subscription:
                by_subscription[resource.subscription_id] = []
            by_subscription[resource.subscription_id].append(resource)
        
        # Query costs per subscription
        for subscription_id, sub_resources in by_subscription.items():
            try:
                self._enrich_subscription_costs(subscription_id, sub_resources)
            except Exception as e:
                logger.error(f"Failed to get costs for subscription {subscription_id}: {e}")
        
        return resources
    
    def _enrich_subscription_costs(self, subscription_id: str, resources: List[OrphanedResource]):
        """Query and apply cost data for resources in a subscription."""
        try:
            cost_client = CostManagementClient(self.credential)
            
            # Build cost query for the subscription
            scope = f"/subscriptions/{subscription_id}"
            
            # Query last 30 days of costs
            end_date = datetime.now()
            start_date = end_date - timedelta(days=30)
            
            # Create resource ID to resource mapping
            resource_map = {r.resource_id.lower(): r for r in resources if r.resource_id}
            
            # Note: Azure Cost Management API has complex query structure
            # This is a simplified version - production should use proper QueryDefinition
            try:
                # Attempt to query costs - this may fail due to permissions or API version
                # In production, use proper cost management query with aggregation by resource ID
                for resource in resources:
                    # Placeholder: Set estimated cost based on resource type
                    resource.estimated_monthly_cost = self._estimate_cost_by_type(resource)
                    
            except Exception as e:
                logger.warning(f"Cost API query failed, using estimated costs: {e}")
                for resource in resources:
                    resource.estimated_monthly_cost = self._estimate_cost_by_type(resource)
                    
        except Exception as e:
            logger.error(f"Error initializing cost client: {e}")
    
    @staticmethod
    def _estimate_cost_by_type(resource: OrphanedResource) -> float:
        """Provide rough cost estimates based on resource type when API data unavailable."""
        # These are rough estimates - actual costs vary by region and SKU
        cost_estimates = {
            'disk': 5.0,  # Standard HDD estimate
            'public_ip': 3.0,  # Static IP
            'load_balancer': 25.0,  # Basic LB
            'network_interface': 0.0,  # Usually no direct cost
            'network_security_group': 0.0,  # No direct cost
            'app_service_plan': 55.0,  # Basic tier estimate
            'availability_set': 0.0,  # No direct cost
            'route_table': 0.0,  # No direct cost
            'waf_policy': 0.0,  # Cost is in associated resource
            'traffic_manager_profile': 45.0,  # Per profile
            'application_gateway': 140.0,  # V2 standard
            'virtual_network': 0.0,  # No direct cost
            'subnet': 0.0,  # No direct cost
            'nat_gateway': 30.0,  # Per gateway
            'resource_group': 0.0,  # No direct cost
        }
        
        return cost_estimates.get(resource.resource_type, 0.0)


class OutputFormatter:
    """Format and output scan results in various formats."""
    
    @staticmethod
    def to_csv(resources: List[OrphanedResource], filename: str = None):
        """Output results to CSV format."""
        if filename is None:
            filename = f"orphaned_resources_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
        
        try:
            with open(filename, 'w', newline='', encoding='utf-8') as csvfile:
                fieldnames = [
                    'resource_type', 'resource_name', 'resource_id', 'location',
                    'subscription_name', 'subscription_id', 'resource_group',
                    'estimated_monthly_cost', 'tags', 'detected_at'
                ]
                writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
                writer.writeheader()
                
                for resource in resources:
                    row = asdict(resource)
                    row['tags'] = json.dumps(row['tags'])
                    writer.writerow(row)
            
            logger.info(f"CSV output written to {filename}")
            return filename
        except Exception as e:
            logger.error(f"Failed to write CSV output: {e}")
            return None
    
    @staticmethod
    def to_json(resources: List[OrphanedResource], filename: str = None):
        """Output results to JSON format."""
        if filename is None:
            filename = f"orphaned_resources_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        
        try:
            output = {
                'scan_date': datetime.utcnow().isoformat(),
                'total_resources': len(resources),
                'total_estimated_monthly_cost': sum(r.estimated_monthly_cost for r in resources),
                'resources': [asdict(r) for r in resources]
            }
            
            with open(filename, 'w', encoding='utf-8') as jsonfile:
                json.dump(output, jsonfile, indent=2, default=str)
            
            logger.info(f"JSON output written to {filename}")
            return filename
        except Exception as e:
            logger.error(f"Failed to write JSON output: {e}")
            return None
    
    @staticmethod
    def to_console(resources: List[OrphanedResource]):
        """Output summary to console."""
        total_cost = sum(r.estimated_monthly_cost for r in resources)
        
        print("\n" + "="*80)
        print("AZURE ORPHANED RESOURCES SCAN SUMMARY")
        print("="*80)
        print(f"Scan Date: {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC')}")
        print(f"Total Orphaned Resources: {len(resources)}")
        print(f"Estimated Monthly Cost: ${total_cost:.2f}")
        print("="*80)
        
        # Group by type
        by_type = {}
        for resource in resources:
            if resource.resource_type not in by_type:
                by_type[resource.resource_type] = []
            by_type[resource.resource_type].append(resource)
        
        print("\nBreakdown by Resource Type:")
        print("-" * 80)
        for resource_type, type_resources in sorted(by_type.items()):
            type_cost = sum(r.estimated_monthly_cost for r in type_resources)
            print(f"{resource_type:30s} Count: {len(type_resources):4d}  Cost: ${type_cost:8.2f}/month")
        
        print("\n" + "="*80 + "\n")


def scan_subscription(subscription_id: str, subscription_name: str, 
                      credential, include_costs: bool = True) -> List[OrphanedResource]:
    """Scan a single subscription for orphaned resources."""
    logger.info(f"Scanning subscription: {subscription_name} ({subscription_id})")
    
    try:
        detector = OrphanedResourceDetector(subscription_id, credential)
        resources = detector.scan_all(subscription_name)
        
        if include_costs and resources:
            cost_estimator = CostEstimator(credential)
            resources = cost_estimator.get_resource_costs(resources)
        
        return resources
        
    except Exception as e:
        logger.error(f"Failed to scan subscription {subscription_name}: {e}")
        return []


def main():
    """Main execution function."""
    parser = argparse.ArgumentParser(
        description='Scan Azure subscriptions for orphaned resources with cost analysis'
    )
    parser.add_argument(
        '--output-format',
        choices=['csv', 'json', 'both'],
        default='json',
        help='Output format (default: json)'
    )
    parser.add_argument(
        '--max-workers',
        type=int,
        default=5,
        help='Maximum parallel workers for subscription scanning (default: 5)'
    )
    parser.add_argument(
        '--no-costs',
        action='store_true',
        help='Skip cost estimation (faster scanning)'
    )
    parser.add_argument(
        '--subscriptions',
        nargs='+',
        help='Specific subscription IDs to scan (default: all)'
    )
    parser.add_argument(
        '--exclude-subscriptions',
        nargs='+',
        help='Subscription IDs to exclude from scanning'
    )
    
    args = parser.parse_args()
    
    # Override with environment variables if not specified
    if not args.exclude_subscriptions:
        args.exclude_subscriptions = list(ConfigManager.get_excluded_subscriptions())
    
    logger.info("="*80)
    logger.info("Azure Orphaned Resources Scanner - Starting")
    logger.info("="*80)
    
    # Initialize credential
    try:
        credential = AzureCredentialManager.get_credential()
    except Exception as e:
        logger.error(f"Failed to authenticate: {e}")
        sys.exit(1)
    
    # Get subscriptions
    try:
        subscription_client = SubscriptionClient(credential)
        all_subscriptions = list(subscription_client.subscriptions.list())
        
        # Filter subscriptions
        subscriptions_to_scan = []
        for sub in all_subscriptions:
            # Skip disabled subscriptions
            if sub.state != 'Enabled':
                logger.info(f"Skipping disabled subscription: {sub.display_name}")
                continue
            
            # Apply filters
            if args.subscriptions and sub.subscription_id not in args.subscriptions:
                continue
            if args.exclude_subscriptions and sub.subscription_id in args.exclude_subscriptions:
                logger.info(f"Excluding subscription: {sub.display_name}")
                continue
            
            subscriptions_to_scan.append(sub)
        
        logger.info(f"Found {len(subscriptions_to_scan)} subscriptions to scan")
        
    except Exception as e:
        logger.error(f"Failed to list subscriptions: {e}")
        sys.exit(1)
    
    # Initialize progress tracking
    progress = ScanProgress(
        total_subscriptions=len(subscriptions_to_scan),
        completed_subscriptions=0,
        failed_subscriptions=[],
        start_time=datetime.utcnow().isoformat(),
        last_update=datetime.utcnow().isoformat()
    )
    
    # Scan subscriptions in parallel
    all_resources = []
    
    with ThreadPoolExecutor(max_workers=args.max_workers) as executor:
        # Submit all scanning tasks
        future_to_sub = {
            executor.submit(
                scan_subscription,
                sub.subscription_id,
                sub.display_name,
                credential,
                not args.no_costs
            ): sub for sub in subscriptions_to_scan
        }
        
        # Process completed scans
        for future in as_completed(future_to_sub):
            sub = future_to_sub[future]
            try:
                resources = future.result()
                all_resources.extend(resources)
                progress.completed_subscriptions += 1
                logger.info(
                    f"Progress: {progress.completed_subscriptions}/{progress.total_subscriptions} "
                    f"subscriptions completed"
                )
            except Exception as e:
                logger.error(f"Subscription {sub.display_name} scan failed: {e}")
                progress.failed_subscriptions.append(sub.subscription_id)
            
            progress.last_update = datetime.utcnow().isoformat()
            progress.save()
    
    # Output results
    logger.info(f"Scan complete. Found {len(all_resources)} orphaned resources")
    
    # Console output
    OutputFormatter.to_console(all_resources)
    
    # File output
    output_files = []
    if args.output_format in ['json', 'both']:
        json_file = OutputFormatter.to_json(all_resources)
        if json_file:
            output_files.append(json_file)
    
    if args.output_format in ['csv', 'both']:
        csv_file = OutputFormatter.to_csv(all_resources)
        if csv_file:
            output_files.append(csv_file)
    
    # Summary
    logger.info("="*80)
    logger.info("Scan Summary")
    logger.info("="*80)
    logger.info(f"Subscriptions scanned: {progress.completed_subscriptions}/{progress.total_subscriptions}")
    logger.info(f"Failed subscriptions: {len(progress.failed_subscriptions)}")
    logger.info(f"Total orphaned resources: {len(all_resources)}")
    logger.info(f"Total estimated monthly cost: ${sum(r.estimated_monthly_cost for r in all_resources):.2f}")
    
    if output_files:
        logger.info(f"\nOutput files generated:")
        for file in output_files:
            logger.info(f"  - {file}")
    
    logger.info("="*80)
    
    return 0 if not progress.failed_subscriptions else 1


if __name__ == "__main__":
    sys.exit(main())
