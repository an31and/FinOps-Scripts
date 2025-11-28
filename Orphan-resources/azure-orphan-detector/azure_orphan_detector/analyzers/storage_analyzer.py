"""Analyzer for orphaned storage account resources"""

import logging
from typing import Dict, List, Any
from datetime import datetime, timezone, timedelta

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


class StorageAccountAnalyzer(IResourceAnalyzer):
    """Analyzer for orphaned storage account resources"""
    
    def __init__(self):
        self.logger = setup_logger(self.__class__.__name__)
        self.cost_calculator = AzureCostCalculator()
    
    def get_analyzer_name(self) -> str:
        return "StorageAccountAnalyzer"
    
    def get_analyzer_version(self) -> str:
        return "1.0.0"
    
    def get_supported_resource_types(self) -> List[AzureResourceType]:
        return [AzureResourceType.STORAGE_ACCOUNT]
    
    async def analyze(
        self, 
        subscription_id: str, 
        clients: Dict[str, Any], 
        config: ScanConfiguration
    ) -> List[EnhancedOrphanedResource]:
        """Analyze orphaned storage accounts"""
        
        orphaned = []
        self.logger.debug(f"Analyzing storage accounts for subscription {subscription_id}")
        
        try:
            storage_client = clients['storage']
            storage_accounts = list(storage_client.storage_accounts.list())
            
            for storage_account in storage_accounts:
                orphan_analysis = await self._analyze_storage_account(storage_account, config)
                if orphan_analysis['is_orphaned']:
                    orphaned_resource = await self._create_orphaned_storage_resource(
                        storage_account, subscription_id, config, orphan_analysis
                    )
                    if orphaned_resource:
                        orphaned.append(orphaned_resource)
                        
        except Exception as e:
            self.logger.error(f"Error analyzing storage accounts in subscription {subscription_id}: {e}")
        
        return orphaned
    
    async def _analyze_storage_account(self, storage_account: Any, config: ScanConfiguration) -> Dict[str, Any]:
        """Analyze a storage account to determine if it's orphaned"""
        
        analysis = {
            'is_orphaned': False,
            'orphan_reason': OrphanageReason.UNUSED,
            'confidence_factors': [],
            'usage_indicators': []
        }
        
        try:
            # Check creation time - very new accounts might not be orphaned
            if hasattr(storage_account, 'creation_time') and storage_account.creation_time:
                days_old = (datetime.now(timezone.utc) - storage_account.creation_time).days
                if days_old < 7:
                    analysis['confidence_factors'].append(f"Very new account ({days_old} days old)")
                    return analysis
            
            # Check if it's a system/diagnostic storage account
            if self._is_system_storage_account(storage_account):
                analysis['confidence_factors'].append("Appears to be system/diagnostic storage")
                return analysis
            
            # Analyze account properties for usage indicators
            usage_score = 0
            
            # Check account type and access tier
            if hasattr(storage_account, 'access_tier'):
                if storage_account.access_tier == 'Archive':
                    usage_score += 1
                    analysis['usage_indicators'].append("Archive tier indicates infrequent access")
                elif storage_account.access_tier == 'Cool':
                    usage_score += 0.5
                    analysis['usage_indicators'].append("Cool tier indicates lower usage")
            
            # Check if account has any known integrations
            if self._has_known_integrations(storage_account):
                analysis['confidence_factors'].append("Has known Azure service integrations")
                return analysis
            
            # Simple heuristic: if no clear usage indicators and account is old enough
            if days_old > config.max_age_days and usage_score < 2:
                analysis['is_orphaned'] = True
                analysis['confidence_factors'].append(f"Account is {days_old} days old with low usage indicators")
            
            # Additional checks for empty accounts (would require storage client access to containers/blobs)
            # This is a simplified analysis - in production, you'd want to check actual storage usage
            
        except Exception as e:
            self.logger.warning(f"Failed to analyze storage account {storage_account.name}: {e}")
        
        return analysis
    
    def _is_system_storage_account(self, storage_account: Any) -> bool:
        """Check if storage account appears to be system-managed"""
        
        system_indicators = [
            'bootdiag', 'diag', 'diagnostic', 'logs', 'monitor',
            'cloudshell', 'function', 'appservice', 'website'
        ]
        
        account_name = storage_account.name.lower()
        return any(indicator in account_name for indicator in system_indicators)
    
    def _has_known_integrations(self, storage_account: Any) -> bool:
        """Check if storage account has known Azure service integrations"""
        
        # Check tags for service integrations
        if hasattr(storage_account, 'tags') and storage_account.tags:
            integration_tags = [
                'backup', 'function', 'webapp', 'logic', 'datafactory',
                'synapse', 'databricks', 'hdinsight'
            ]
            tag_values = ' '.join(str(v).lower() for v in storage_account.tags.values())
            if any(tag in tag_values for tag in integration_tags):
                return True
        
        # Check account name for service patterns
        service_patterns = [
            'backup', 'function', 'webapp', 'logic', 'data',
            'analytics', 'ml', 'ai', 'synapse'
        ]
        account_name = storage_account.name.lower()
        return any(pattern in account_name for pattern in service_patterns)
    
    async def _create_orphaned_storage_resource(
        self, 
        storage_account: Any, 
        subscription_id: str, 
        config: ScanConfiguration,
        analysis: Dict[str, Any]
    ) -> EnhancedOrphanedResource:
        """Create orphaned resource object for storage account"""
        
        try:
            cost_analysis = self.cost_calculator.calculate_cost(
                storage_account, AzureResourceType.STORAGE_ACCOUNT, storage_account.location
            )
            
            # Storage accounts can have significant security implications
            security_analysis = SecurityAnalysis()
            
            # Check public access settings
            if hasattr(storage_account, 'allow_blob_public_access'):
                if storage_account.allow_blob_public_access:
                    security_analysis.network_exposure = "external"
                    security_analysis.security_risks.append("Public blob access is enabled")
                else:
                    security_analysis.network_exposure = "internal"
            
            # Check for HTTPS only
            if hasattr(storage_account, 'enable_https_traffic_only'):
                if not storage_account.enable_https_traffic_only:
                    security_analysis.security_risks.append("HTTPS-only traffic is not enforced")
            
            # General security risks for unused storage accounts
            security_analysis.security_risks.extend([
                "Unused storage account may contain sensitive data",
                "Account keys may be stored in applications or scripts",
                "Potential for data exfiltration if compromised"
            ])
            
            # Check encryption settings
            if hasattr(storage_account, 'encryption'):
                if storage_account.encryption and hasattr(storage_account.encryption, 'services'):
                    security_analysis.encryption_status = "enabled"
                else:
                    security_analysis.encryption_status = "unknown"
                    security_analysis.security_risks.append("Encryption status unclear")
            
            confidence_score = self._calculate_confidence_score(storage_account, analysis)
            severity = self._determine_severity(cost_analysis, security_analysis, config)
            
            recommendations = [
                "Review storage account contents before deletion",
                "Check for application dependencies and connection strings",
                "Verify no backup or archival data is stored",
                "Consider lifecycle management policies for cost optimization",
                "Ensure proper data retention compliance before cleanup"
            ]
            
            # Add specific recommendations based on analysis
            if analysis['usage_indicators']:
                recommendations.append("Review access tier settings for cost optimization")
            
            # Get storage account details
            details = {
                'account_kind': getattr(storage_account, 'kind', 'Unknown'),
                'sku_name': storage_account.sku.name if hasattr(storage_account, 'sku') and storage_account.sku else 'Unknown',
                'sku_tier': storage_account.sku.tier if hasattr(storage_account, 'sku') and storage_account.sku else 'Unknown',
                'access_tier': getattr(storage_account, 'access_tier', 'Unknown'),
                'provisioning_state': getattr(storage_account, 'provisioning_state', 'Unknown'),
                'primary_location': getattr(storage_account, 'primary_location', 'Unknown'),
                'secondary_location': getattr(storage_account, 'secondary_location', None),
                'allow_blob_public_access': getattr(storage_account, 'allow_blob_public_access', 'Unknown'),
                'enable_https_traffic_only': getattr(storage_account, 'enable_https_traffic_only', 'Unknown'),
                'creation_time': storage_account.creation_time.isoformat() if hasattr(storage_account, 'creation_time') and storage_account.creation_time else None,
                'usage_indicators': analysis['usage_indicators'],
                'confidence_factors': analysis['confidence_factors']
            }
            
            return EnhancedOrphanedResource(
                resource_id=storage_account.id,
                resource_type=AzureResourceType.STORAGE_ACCOUNT,
                resource_name=storage_account.name,
                resource_group=storage_account.id.split('/')[4],
                location=storage_account.location,
                subscription_id=subscription_id,
                created_date=storage_account.creation_time if hasattr(storage_account, 'creation_time') else None,
                cost_analysis=cost_analysis,
                severity=severity,
                orphanage_reason=analysis['orphan_reason'],
                confidence_score=confidence_score,
                security_analysis=security_analysis,
                tags=storage_account.tags or {},
                details=details,
                recommended_actions=recommendations,
                cleanup_priority=self._calculate_cleanup_priority(cost_analysis, severity, confidence_score)
            )
            
        except Exception as e:
            self.logger.warning(f"Failed to create orphaned resource for storage account {storage_account.name}: {e}")
            return None
    
    def _calculate_confidence_score(self, resource: Any, analysis: Dict[str, Any]) -> float:
        """Calculate confidence score for orphaned resource classification"""
        
        score = 0.3  # Lower base score for storage accounts due to complexity
        
        try:
            # Time-based factors
            if hasattr(resource, 'creation_time') and resource.creation_time:
                days_old = (datetime.now(timezone.utc) - resource.creation_time).days
                if days_old > 180:
                    score += 0.3
                elif days_old > 90:
                    score += 0.2
                elif days_old > 30:
                    score += 0.1
            
            # Usage indicators
            if analysis['usage_indicators']:
                score += 0.2
            
            # Tag-based factors
            if hasattr(resource, 'tags') and resource.tags:
                temp_tags = ['temporary', 'test', 'dev', 'poc', 'demo', 'sandbox']
                if any(tag.lower() in str(resource.tags).lower() for tag in temp_tags):
                    score += 0.2
            
            # Reduce confidence if system account
            if self._is_system_storage_account(resource):
                score -= 0.3
            
            score = min(0.9, max(0.1, score))  # Cap at 0.9 for storage accounts
            
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
        
        # High severity if public access is enabled
        if security_analysis.network_exposure == "external":
            return SeverityLevel.HIGH
        
        # Consider cost thresholds
        if monthly_cost > config.cost_threshold_critical:
            return SeverityLevel.CRITICAL
        elif monthly_cost > config.cost_threshold_high:
            return SeverityLevel.HIGH
        elif monthly_cost > config.cost_threshold_medium:
            return SeverityLevel.MEDIUM
        elif len(security_analysis.security_risks) > 3:
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
        
        priority = 6  # Default medium-low priority due to potential data sensitivity
        
        # Adjust based on cost
        monthly_cost = cost_analysis.current_monthly_cost
        if monthly_cost > 100:
            priority -= 2
        elif monthly_cost > 50:
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
        
        # Adjust based on confidence (be more cautious with storage)
        if confidence_score > 0.8:
            priority -= 1
        elif confidence_score < 0.4:
            priority += 2
        
        return max(2, min(10, priority))  # Never highest priority (1) for storage accounts
