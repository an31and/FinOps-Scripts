"""Analyzer for orphaned network interface resources"""

import logging
from typing import Dict, List, Any
from datetime import datetime, timezone

from ..core.interfaces import IResourceAnalyzer
from ..core.models import (
    EnhancedOrphanedResource, 
    AzureResourceType, 
    OrphanageReason,
    ScanConfiguration,
    SeverityLevel,
    CostAnalysis,
    ResourceMetrics,
    SecurityAnalysis
)
from ..cost.calculator import AzureCostCalculator
from ..utils.logger import setup_logger


class NetworkInterfaceAnalyzer(IResourceAnalyzer):
    """Analyzer for orphaned network interface resources"""
    
    def __init__(self):
        self.logger = setup_logger(self.__class__.__name__)
        self.cost_calculator = AzureCostCalculator()
    
    def get_analyzer_name(self) -> str:
        return "NetworkInterfaceAnalyzer"
    
    def get_analyzer_version(self) -> str:
        return "1.0.0"
    
    def get_supported_resource_types(self) -> List[AzureResourceType]:
        return [AzureResourceType.NETWORK_INTERFACE]
    
    async def analyze(
        self, 
        subscription_id: str, 
        clients: Dict[str, Any], 
        config: ScanConfiguration
    ) -> List[EnhancedOrphanedResource]:
        """Analyze orphaned network interfaces"""
        
        orphaned = []
        self.logger.debug(f"Analyzing network interfaces for subscription {subscription_id}")
        
        try:
            network_client = clients['network']
            network_interfaces = list(network_client.network_interfaces.list_all())
            
            for nic in network_interfaces:
                if await self._is_network_interface_orphaned(nic):
                    orphaned_resource = await self._create_orphaned_nic_resource(
                        nic, subscription_id, config
                    )
                    if orphaned_resource:
                        orphaned.append(orphaned_resource)
                        
        except Exception as e:
            self.logger.error(f"Error analyzing network interfaces in subscription {subscription_id}: {e}")
        
        return orphaned
    
    async def _is_network_interface_orphaned(self, nic: Any) -> bool:
        """Check if network interface is orphaned"""
        
        # Check if NIC is attached to a VM
        if hasattr(nic, 'virtual_machine') and nic.virtual_machine:
            return False
        
        # Check if NIC has active IP configurations that might be in use
        if hasattr(nic, 'ip_configurations') and nic.ip_configurations:
            for ip_config in nic.ip_configurations:
                # If any IP config has a load balancer backend or application gateway, it's not orphaned
                if (hasattr(ip_config, 'load_balancer_backend_address_pools') and 
                    ip_config.load_balancer_backend_address_pools):
                    return False
                
                if (hasattr(ip_config, 'application_gateway_backend_address_pools') and 
                    ip_config.application_gateway_backend_address_pools):
                    return False
        
        # If we reach here, the NIC is likely orphaned
        return True
    
    async def _create_orphaned_nic_resource(
        self, 
        nic: Any, 
        subscription_id: str, 
        config: ScanConfiguration
    ) -> EnhancedOrphanedResource:
        """Create orphaned resource object for network interface"""
        
        try:
            cost_analysis = self.cost_calculator.calculate_cost(
                nic, AzureResourceType.NETWORK_INTERFACE, nic.location
            )
            
            # Network interfaces generally don't have significant costs, but they can have security implications
            security_analysis = SecurityAnalysis()
            security_analysis.network_exposure = "internal"
            
            # Check for public IP associations
            if hasattr(nic, 'ip_configurations') and nic.ip_configurations:
                for ip_config in nic.ip_configurations:
                    if hasattr(ip_config, 'public_ip_address') and ip_config.public_ip_address:
                        security_analysis.network_exposure = "external"
                        security_analysis.security_risks.append("NIC has public IP address association")
                        break
            
            security_analysis.security_risks.extend([
                "Unused network interface may be misconfigured",
                "May have outdated security group associations",
                "Potential for unauthorized network access if reactivated"
            ])
            
            if hasattr(nic, 'network_security_group') and nic.network_security_group:
                security_analysis.security_risks.append("Has network security group that may contain outdated rules")
            
            confidence_score = self._calculate_confidence_score(nic)
            severity = self._determine_severity(cost_analysis, security_analysis, config)
            
            recommendations = [
                "Verify the NIC is not needed for future VM deployments",
                "Check if NIC is part of infrastructure-as-code templates",
                "Remove unused network interface to reduce management overhead",
                "Review associated network security group rules if present"
            ]
            
            # Get additional NIC details
            details = {
                'mac_address': getattr(nic, 'mac_address', 'Unknown'),
                'enable_accelerated_networking': getattr(nic, 'enable_accelerated_networking', False),
                'enable_ip_forwarding': getattr(nic, 'enable_ip_forwarding', False),
                'primary': getattr(nic, 'primary', False),
                'provisioning_state': getattr(nic, 'provisioning_state', 'Unknown'),
                'ip_configurations_count': len(nic.ip_configurations) if hasattr(nic, 'ip_configurations') and nic.ip_configurations else 0
            }
            
            # Check for private IP addresses
            private_ips = []
            public_ips = []
            if hasattr(nic, 'ip_configurations') and nic.ip_configurations:
                for ip_config in nic.ip_configurations:
                    if hasattr(ip_config, 'private_ip_address') and ip_config.private_ip_address:
                        private_ips.append(ip_config.private_ip_address)
                    if hasattr(ip_config, 'public_ip_address') and ip_config.public_ip_address:
                        public_ips.append(ip_config.public_ip_address.ip_address if hasattr(ip_config.public_ip_address, 'ip_address') else 'Unknown')
            
            details['private_ip_addresses'] = private_ips
            details['public_ip_addresses'] = public_ips
            
            return EnhancedOrphanedResource(
                resource_id=nic.id,
                resource_type=AzureResourceType.NETWORK_INTERFACE,
                resource_name=nic.name,
                resource_group=nic.id.split('/')[4],
                location=nic.location,
                subscription_id=subscription_id,
                cost_analysis=cost_analysis,
                severity=severity,
                orphanage_reason=OrphanageReason.UNATTACHED,
                confidence_score=confidence_score,
                security_analysis=security_analysis,
                tags=nic.tags or {},
                details=details,
                recommended_actions=recommendations,
                cleanup_priority=self._calculate_cleanup_priority(cost_analysis, severity, confidence_score)
            )
            
        except Exception as e:
            self.logger.warning(f"Failed to create orphaned resource for network interface {nic.name}: {e}")
            return None
    
    def _calculate_confidence_score(self, resource: Any) -> float:
        """Calculate confidence score for orphaned resource classification"""
        
        score = 0.5  # Base score
        
        try:
            # If not attached to any VM, high confidence it's orphaned
            if not hasattr(resource, 'virtual_machine') or not resource.virtual_machine:
                score += 0.3
            
            # Check provisioning state
            if hasattr(resource, 'provisioning_state'):
                if resource.provisioning_state == 'Succeeded':
                    score += 0.1  # Successfully provisioned but not attached
                elif resource.provisioning_state == 'Failed':
                    score += 0.2  # Failed provisioning, likely orphaned
            
            # Tag-based factors
            if hasattr(resource, 'tags') and resource.tags:
                temp_tags = ['temporary', 'test', 'dev', 'poc', 'demo']
                if any(tag.lower() in str(resource.tags).lower() for tag in temp_tags):
                    score += 0.1
            
            score = min(1.0, max(0.0, score))
            
        except Exception as e:
            self.logger.warning(f"Failed to calculate confidence score: {e}")
        
        return score
    
    def _determine_severity(
        self, 
        cost_analysis: CostAnalysis, 
        security_analysis: SecurityAnalysis,
        config: ScanConfiguration
    ) -> SeverityLevel:
        """Determine severity level based on cost and security analysis"""
        
        # NICs generally have minimal cost, so focus on security and management aspects
        if security_analysis.network_exposure == "external":
            return SeverityLevel.HIGH  # External exposure is a security concern
        elif len(security_analysis.security_risks) > 2:
            return SeverityLevel.MEDIUM
        else:
            return SeverityLevel.LOW
    
    def _calculate_cleanup_priority(
        self, 
        cost_analysis: CostAnalysis, 
        severity: SeverityLevel, 
        confidence_score: float
    ) -> int:
        """Calculate cleanup priority (1-10, where 1 is highest priority)"""
        
        priority = 7  # Default low priority since NICs have minimal cost
        
        # Adjust based on severity (security concerns)
        severity_adjustments = {
            SeverityLevel.CRITICAL: -3,
            SeverityLevel.HIGH: -2,
            SeverityLevel.MEDIUM: -1,
            SeverityLevel.LOW: 0,
            SeverityLevel.INFO: 1
        }
        priority += severity_adjustments.get(severity, 0)
        
        # Adjust based on confidence
        if confidence_score > 0.8:
            priority -= 1
        elif confidence_score < 0.5:
            priority += 1
        
        return max(1, min(10, priority))
                