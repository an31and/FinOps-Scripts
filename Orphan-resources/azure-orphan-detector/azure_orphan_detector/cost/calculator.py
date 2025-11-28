"""Enhanced Azure cost calculator with Azure Cost Management API integration"""

import logging
from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta

try:
    from azure.mgmt.costmanagement import CostManagementClient
    from azure.mgmt.costmanagement.models import (
        QueryDefinition, QueryDataset, QueryTimePeriod, QueryComparisonExpression,
        QueryFilter, QueryGrouping, QueryAggregation
    )
    COST_MANAGEMENT_AVAILABLE = True
except ImportError:
    CostManagementClient = None
    COST_MANAGEMENT_AVAILABLE = False

from ..core.interfaces import ICostCalculator
from ..core.models import AzureResourceType, CostAnalysis
from ..utils.logger import setup_logger


class AzureCostCalculator(ICostCalculator):
    """Enhanced Azure cost calculator with Cost Management API integration"""
    
    def __init__(self, credential=None):
        self.logger = setup_logger(self.__class__.__name__)
        self.credential = credential
        self.cost_client = None
        if credential and COST_MANAGEMENT_AVAILABLE:
            try:
                self.cost_client = CostManagementClient(credential)
                self.logger.info("Azure Cost Management client initialized successfully")
            except Exception as e:
                self.logger.warning(f"Failed to initialize Cost Management client: {e}")
                self.logger.info("Falling back to estimated pricing")
        else:
            self.logger.info("Cost Management API not available - using estimated pricing")
        
        self._load_pricing_data()
    
    def _load_pricing_data(self):
        """Load pricing data from configuration"""
        
        # Simplified pricing data - in production, this would come from Azure Pricing API
        self.pricing_data = {
            AzureResourceType.DISK.value: {
                'Standard_LRS': 0.04,
                'Standard_ZRS': 0.05,
                'Premium_LRS': 0.135,
                'StandardSSD_LRS': 0.075,
                'StandardSSD_ZRS': 0.095,
                'Premium_ZRS': 0.17,
            },
            AzureResourceType.PUBLIC_IP.value: {
                'Basic': 3.65,
                'Standard': 3.65
            },
            AzureResourceType.NETWORK_INTERFACE.value: {
                'default': 0.0  # NICs are generally free
            },
            AzureResourceType.STORAGE_ACCOUNT.value: {
                'Standard_LRS': 0.0208,
                'Standard_GRS': 0.0416,
                'Standard_ZRS': 0.026,
                'Premium_LRS': 0.15
            },
        }
        
        # Regional multipliers
        self.regional_multipliers = {
            'eastus': 1.0,
            'eastus2': 1.0,
            'westus': 1.1,
            'westus2': 1.05,
            'centralus': 1.02,
            'northeurope': 1.05,
            'westeurope': 1.08,
            'uksouth': 1.07,
            'ukwest': 1.07,
            'japaneast': 1.15,
            'australiaeast': 1.2,
            'brazilsouth': 1.25,
        }
    
    def calculate_cost(self, resource: Any, resource_type: AzureResourceType, location: str) -> CostAnalysis:
        """Calculate comprehensive cost analysis for a resource"""
        
        cost_analysis = CostAnalysis()
        
        try:
            if resource_type == AzureResourceType.DISK:
                cost_analysis = self._calculate_disk_cost(resource, location)
            elif resource_type == AzureResourceType.PUBLIC_IP:
                cost_analysis = self._calculate_public_ip_cost(resource, location)
            elif resource_type == AzureResourceType.NETWORK_INTERFACE:
                cost_analysis = self._calculate_nic_cost(resource, location)
            elif resource_type == AzureResourceType.STORAGE_ACCOUNT:
                cost_analysis = self._calculate_storage_cost(resource, location)
            elif resource_type == AzureResourceType.SNAPSHOT:
                cost_analysis = self._calculate_snapshot_cost(resource, location)
            else:
                self.logger.warning(f"Cost calculation not implemented for {resource_type}")
                
        except Exception as e:
            self.logger.error(f"Failed to calculate cost for {resource_type}: {e}")
        
        return cost_analysis

    async def calculate_enhanced_cost(
        self, 
        resource: Any, 
        resource_type: AzureResourceType, 
        location: str, 
        subscription_id: str
    ) -> CostAnalysis:
        """Calculate enhanced cost analysis with actual Azure Cost Management data"""
        
        # Start with estimated costs
        cost_analysis = self.calculate_cost(resource, resource_type, location)
        
        # Try to get actual costs if Cost Management client is available
        if self.cost_client and hasattr(resource, 'id'):
            try:
                actual_costs = await self._get_actual_costs(resource.id, subscription_id)
                if actual_costs:
                    cost_analysis = self._merge_actual_costs(cost_analysis, actual_costs)
                    cost_analysis.actual_costs_available = True
                    cost_analysis.cost_accuracy = "actual"
            except Exception as e:
                self.logger.warning(f"Failed to get actual costs for {resource.id}: {e}")
                cost_analysis.cost_accuracy = "estimated"
        
        return cost_analysis

    async def _get_actual_costs(self, resource_id: str, subscription_id: str) -> Optional[Dict[str, Any]]:
        """Get actual costs from Azure Cost Management API"""
        if not self.cost_client:
            return None
        
        try:
            # Define the scope
            scope = f"/subscriptions/{subscription_id}"
            
            # Define time period (last 30 days)
            end_date = datetime.now()
            start_date = end_date - timedelta(days=30)
            
            # Create query definition
            query_definition = QueryDefinition(
                type="ActualCost",
                timeframe="Custom",
                time_period=QueryTimePeriod(
                    from_property=start_date.strftime('%Y-%m-%dT%H:%M:%S+00:00'),
                    to=end_date.strftime('%Y-%m-%dT%H:%M:%S+00:00')
                ),
                dataset=QueryDataset(
                    granularity="Daily",
                    filter=QueryFilter(
                        dimension=QueryComparisonExpression(
                            name="ResourceId",
                            operator="In",
                            values=[resource_id]
                        )
                    ),
                    aggregation={
                        "totalCost": QueryAggregation(name="PreTaxCost", function="Sum")
                    }
                )
            )
            
            # Execute query
            result = self.cost_client.query.usage(scope, query_definition)
            
            if result.rows:
                total_cost = sum(float(row[0]) for row in result.rows)
                return {
                    'total_cost_30_days': total_cost,
                    'monthly_cost': total_cost,  # Assuming 30 days = 1 month
                    'daily_average': total_cost / 30,
                    'data_points': len(result.rows)
                }
            
        except Exception as e:
            self.logger.error(f"Error querying actual costs: {e}")
        
        return None

    def _merge_actual_costs(self, estimated_analysis: CostAnalysis, actual_costs: Dict[str, Any]) -> CostAnalysis:
        """Merge actual costs with estimated analysis"""
        
        # Update with actual costs
        estimated_analysis.current_monthly_cost = actual_costs['monthly_cost']
        estimated_analysis.projected_annual_cost = actual_costs['monthly_cost'] * 12
        estimated_analysis.potential_savings = estimated_analysis.projected_annual_cost
        
        # Add actual cost breakdown
        estimated_analysis.cost_breakdown.update({
            'actual_monthly_cost': actual_costs['monthly_cost'],
            'daily_average_cost': actual_costs['daily_average'],
            'data_points': actual_costs['data_points']
        })
        
        # Add optimization suggestions based on actual costs
        if actual_costs['monthly_cost'] > 0:
            estimated_analysis.optimization_suggestions.append(
                f"Actual cost: ${actual_costs['monthly_cost']:.2f}/month - Consider deletion to save costs"
            )
        
        return estimated_analysis
    
    def _calculate_disk_cost(self, disk: Any, location: str) -> CostAnalysis:
        """Calculate disk cost"""
        cost_analysis = CostAnalysis()
        
        if not hasattr(disk, 'disk_size_gb') or not disk.disk_size_gb:
            return cost_analysis
        
        sku_name = disk.sku.name if hasattr(disk, 'sku') and disk.sku else 'Standard_LRS'
        base_cost_per_gb = self.pricing_data[AzureResourceType.DISK.value].get(sku_name, 0.04)
        regional_multiplier = self.regional_multipliers.get(location.lower(), 1.1)
        
        monthly_cost = disk.disk_size_gb * base_cost_per_gb * regional_multiplier
        
        cost_analysis.current_monthly_cost = monthly_cost
        cost_analysis.projected_annual_cost = monthly_cost * 12
        cost_analysis.potential_savings = cost_analysis.projected_annual_cost
        cost_analysis.cost_breakdown = {
            'storage': monthly_cost,
            'base_cost_per_gb': base_cost_per_gb,
            'regional_multiplier': regional_multiplier,
            'disk_size_gb': disk.disk_size_gb
        }
        
        if monthly_cost > 50:
            cost_analysis.optimization_suggestions.append("Consider moving to cooler storage tier if access is infrequent")
        
        return cost_analysis
    
    def _calculate_public_ip_cost(self, pip: Any, location: str) -> CostAnalysis:
        """Calculate public IP cost"""
        cost_analysis = CostAnalysis()
        
        sku_name = pip.sku.name if hasattr(pip, 'sku') and pip.sku else 'Basic'
        base_monthly_cost = self.pricing_data[AzureResourceType.PUBLIC_IP.value].get(sku_name, 3.65)
        regional_multiplier = self.regional_multipliers.get(location.lower(), 1.1)
        
        monthly_cost = base_monthly_cost * regional_multiplier
        
        cost_analysis.current_monthly_cost = monthly_cost
        cost_analysis.projected_annual_cost = monthly_cost * 12
        cost_analysis.potential_savings = cost_analysis.projected_annual_cost
        cost_analysis.cost_breakdown = {
            'ip_reservation': monthly_cost,
            'base_monthly_cost': base_monthly_cost,
            'regional_multiplier': regional_multiplier
        }
        
        cost_analysis.optimization_suggestions.append("Release unused public IPs to avoid reservation charges")
        
        return cost_analysis
    
    def _calculate_nic_cost(self, nic: Any, location: str) -> CostAnalysis:
        """Calculate network interface cost"""
        cost_analysis = CostAnalysis()
        
        # NICs are generally free in Azure
        cost_analysis.current_monthly_cost = 0.0
        cost_analysis.projected_annual_cost = 0.0
        cost_analysis.potential_savings = 0.0
        cost_analysis.cost_breakdown = {'nic_base': 0.0}
        
        return cost_analysis
    
    def _calculate_storage_cost(self, storage_account: Any, location: str) -> CostAnalysis:
        """Calculate storage account cost"""
        cost_analysis = CostAnalysis()
        
        sku_name = storage_account.sku.name if hasattr(storage_account, 'sku') and storage_account.sku else 'Standard_LRS'
        base_cost_per_gb = self.pricing_data[AzureResourceType.STORAGE_ACCOUNT.value].get(sku_name, 0.0208)
        regional_multiplier = self.regional_multipliers.get(location.lower(), 1.1)
        
        # Estimate storage usage (this would come from metrics in practice)
        estimated_gb = 100  # Default estimate
        monthly_cost = estimated_gb * base_cost_per_gb * regional_multiplier
        
        cost_analysis.current_monthly_cost = monthly_cost
        cost_analysis.projected_annual_cost = monthly_cost * 12
        cost_analysis.potential_savings = cost_analysis.projected_annual_cost
        cost_analysis.cost_breakdown = {
            'storage': monthly_cost,
            'estimated_gb': estimated_gb,
            'base_cost_per_gb': base_cost_per_gb,
            'regional_multiplier': regional_multiplier
        }
        
        cost_analysis.optimization_suggestions.extend([
            "Implement lifecycle management to move old data to cooler tiers",
            "Review storage redundancy requirements"
        ])
        
        return cost_analysis
    
    def _calculate_snapshot_cost(self, snapshot: Any, location: str) -> CostAnalysis:
        """Calculate snapshot cost"""
        cost_analysis = CostAnalysis()
        
        if not hasattr(snapshot, 'disk_size_gb') or not snapshot.disk_size_gb:
            return cost_analysis
        
        # Snapshots are typically charged at a lower rate than disks
        base_cost_per_gb = 0.02  # Simplified rate
        regional_multiplier = self.regional_multipliers.get(location.lower(), 1.1)
        
        monthly_cost = snapshot.disk_size_gb * base_cost_per_gb * regional_multiplier
        
        cost_analysis.current_monthly_cost = monthly_cost
        cost_analysis.projected_annual_cost = monthly_cost * 12
        cost_analysis.potential_savings = cost_analysis.projected_annual_cost
        cost_analysis.cost_breakdown = {
            'snapshot_storage': monthly_cost,
            'snapshot_size_gb': snapshot.disk_size_gb,
            'base_cost_per_gb': base_cost_per_gb,
            'regional_multiplier': regional_multiplier
        }
        
        cost_analysis.optimization_suggestions.append("Review snapshot retention policy to reduce storage costs")
        
        return cost_analysis
    
    def get_pricing_data(self, resource_type: AzureResourceType, location: str) -> Dict[str, float]:
        """Get pricing data for resource type and location"""
        base_pricing = self.pricing_data.get(resource_type.value, {})
        regional_multiplier = self.regional_multipliers.get(location.lower(), 1.1)
        
        return {
            sku: price * regional_multiplier 
            for sku, price in base_pricing.items()
        }