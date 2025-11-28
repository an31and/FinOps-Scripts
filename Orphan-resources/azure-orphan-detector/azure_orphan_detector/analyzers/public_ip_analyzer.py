"""Analyzer for orphaned public IP resources"""

import logging
from typing import Dict, List, Any

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


class PublicIPAnalyzer(IResourceAnalyzer):
    """Analyzer for orphaned public IP resources"""
    
    def __init__(self):
        self.logger = setup_logger(self.__class__.__name__)
        self.cost_calculator = AzureCostCalculator()
    
    def get_analyzer_name(self) -> str:
        return "PublicIPAnalyzer"
    
    def get_analyzer_version(self) -> str:
        return "1.0.0"
    
    def get_supported_resource_types(self) -> List[AzureResourceType]:
        return [AzureResourceType.PUBLIC_IP]
    
    async def analyze(
        self, 
        subscription_id: str, 
        clients: Dict[str, Any], 
        config: ScanConfiguration
    ) -> List[EnhancedOrphanedResource]:
        """Analyze orphaned public IPs"""
        
        orphaned = []
        self.logger.debug(f"Analyzing public IPs for subscription {subscription_id}")
        
        try:
            network_client = clients['network']
            public_ips = list(network_client.public_ip_addresses.list_all())
            
            for pip in public_ips:
                if await self._is_public_ip_orphaned(pip):
                    orphaned_resource = await self._create_orphaned_public_ip_resource(
                        pip, subscription_id, config
                    )
                    if orphaned_resource:
                        orphaned.append(orphaned_resource)
                        
        except Exception as e:
            self.logger.error(f"Error analyzing public IPs in subscription {subscription_id}: {e}")
        
        return orphaned
    
    async def _is_public_ip_orphaned(self, pip: Any) -> bool:
        """Check if public IP is orphaned"""
        return not pip.ip_configuration and not pip.nat_gateway
    
    async def _create_orphaned_public_ip_resource(
        self, 
        pip: Any, 
        subscription_id: str, 
        config: ScanConfiguration
    ) -> EnhancedOrphanedResource:
        """Create orphaned resource object for public IP"""
        
        try:
            cost_analysis = self.cost_calculator.calculate_cost(
                pip, AzureResourceType.PUBLIC_IP, pip.location
            )
            
            # Basic security analysis for public IPs
            security_analysis = SecurityAnalysis()
            security_analysis.network_exposure = "external"
            security_analysis.security_risks.extend([
                "Unused public IP may be discoverable and targeted",
                "IP address may be monitored by threat actors",
                "Potential for DNS hijacking if records exist"
            ])
            
            if hasattr(pip, 'public_ip_allocation_method'):
                if pip.public_ip_allocation_method == 'Static':
                    security_analysis.security_risks.append("Static IP maintains persistent attack surface")
            
            confidence_score = self._calculate_confidence_score(pip)
            severity = self._determine_severity(cost_analysis, security_analysis, config)
            
            recommendations = [
                "Verify no DNS records point to this IP",
                "Check if IP is reserved for future use",
                "Release public IP to avoid charges"
            ]
            
            return EnhancedOrphanedResource(
                resource_id=pip.id,
                resource_type=AzureResourceType.PUBLIC_IP,
                resource_name=pip.name,
                resource_group=pip.id.split('/')[4],
                location=pip.location,
                subscription_id=subscription_id,
                cost_analysis=cost_analysis,
                severity=severity,
                orphanage_reason=OrphanageReason.UNUSED,
                confidence_score=confidence_score,
                security_analysis=security_analysis,
                tags=pip.tags or {},
                details={
                    'ip_address': pip.ip_address,
                    'allocation_method': pip.public_ip_allocation_method,
                    'sku_name': pip.sku.name if pip.sku else 'Basic',
                    'sku_tier': pip.sku.tier if pip.sku else 'Regional',
                    'version': pip.public_ip_address_version,
                    'idle_timeout': pip.idle_timeout_in_minutes
                },
                recommended_actions=recommendations,
                cleanup_priority=self._calculate_cleanup_priority(cost_analysis, severity, confidence_score)
            )
            
        except Exception as e:
            self.logger.warning(f"Failed to create orphaned resource for public IP {pip.name}: {e}")
            return None
    
    def _calculate_confidence_score(self, resource: Any) -> float:
        """Calculate confidence score for orphaned resource classification"""
        
        score = 0.5  # Base score
        
        try:
            # For public IPs, if not associated, high confidence it's orphaned
            if not resource.ip_configuration and not resource.nat_gateway:
                score += 0.3
            
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
        
        monthly_cost = cost_analysis.current_monthly_cost
        
        # Public IPs have security implications, so treat them seriously
        if security_analysis.security_risks:
            return SeverityLevel.HIGH
        elif monthly_cost > config.cost_threshold_medium:
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
        
        priority = 5  # Default medium priority
        
        # Adjust based on cost
        monthly_cost = cost_analysis.current_monthly_cost
        if monthly_cost > 50:
            priority -= 2
        elif monthly_cost > 10:
            priority -= 1
        
        # Adjust based on severity
        severity_adjustments = {
            SeverityLevel.CRITICAL: -2,
            SeverityLevel.HIGH: -1,
            SeverityLevel.MEDIUM: 0,
            SeverityLevel.LOW: 1,
            SeverityLevel.INFO: 2
        }
        priority += severity_adjustments.get(severity, 0)
        
        # Adjust based on confidence
        if confidence_score > 0.8:
            priority -= 1
        elif confidence_score < 0.5:
            priority += 1
        
        return max(1, min(10, priority))