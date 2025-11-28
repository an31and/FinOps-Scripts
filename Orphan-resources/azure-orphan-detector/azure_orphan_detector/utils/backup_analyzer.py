"""Backup policy analyzer for Azure resources"""

import logging
from typing import Dict, Any, Optional, List
try:
    from azure.mgmt.recoveryservicesbackup import RecoveryServicesBackupClient
except ImportError:
    RecoveryServicesBackupClient = None

from ..core.models import BackupPolicyAnalysis, AzureResourceType
from ..utils.logger import setup_logger


class BackupPolicyAnalyzer:
    """Analyze backup and disaster recovery policies for Azure resources"""
    
    def __init__(self, credential=None):
        self.logger = setup_logger(self.__class__.__name__)
        self.credential = credential
        self.backup_client = None
        
        if credential and RecoveryServicesBackupClient:
            try:
                self.backup_client = RecoveryServicesBackupClient(credential, subscription_id="")
                self.logger.info("Recovery Services Backup client initialized successfully")
            except Exception as e:
                self.logger.warning(f"Failed to initialize Backup client: {e}")
        else:
            self.logger.warning("Recovery Services Backup client not available - using basic analysis")
    
    async def analyze_backup_policies(
        self, 
        resource: Any,
        resource_type: AzureResourceType,
        subscription_id: str,
        resource_group: str
    ) -> BackupPolicyAnalysis:
        """Analyze backup and DR policies for a resource"""
        
        analysis = BackupPolicyAnalysis()
        
        if not self.backup_client:
            self.logger.warning("Backup client not available, returning default analysis")
            return analysis
        
        # Update subscription in backup client
        self.backup_client.subscription_id = subscription_id
        
        try:
            # Check for automated backup tags and naming patterns
            analysis.follows_backup_naming = self._check_backup_naming_patterns(resource)
            analysis.is_automated_backup = self._check_automated_backup_tags(resource)
            
            # Check for backup policies in the resource group
            backup_policies = await self._get_backup_policies(resource_group)
            analysis.has_backup_policy = len(backup_policies) > 0
            
            if backup_policies:
                analysis.policy_details = {
                    'policies_found': len(backup_policies),
                    'policy_names': [policy.name for policy in backup_policies]
                }
            
            # For snapshots, perform additional analysis
            if resource_type == AzureResourceType.SNAPSHOT:
                snapshot_analysis = await self._analyze_snapshot_backup_importance(resource, backup_policies)
                analysis = self._merge_snapshot_analysis(analysis, snapshot_analysis)
            
            # Calculate risk level
            analysis.risk_level = self._calculate_deletion_risk(analysis, resource_type)
            
        except Exception as e:
            self.logger.error(f"Failed to analyze backup policies: {e}")
            analysis.risk_level = "unknown"
        
        return analysis
    
    def _check_backup_naming_patterns(self, resource: Any) -> bool:
        """Check if resource follows backup naming conventions"""
        if not hasattr(resource, 'name') or not resource.name:
            return False
        
        backup_patterns = [
            'backup', 'bkp', 'snap', 'snapshot', 'restore', 'dr-', 'disaster',
            'prod-backup', 'daily-backup', 'weekly-backup', 'monthly-backup',
            'archive', 'recovery', 'checkpoint'
        ]
        
        resource_name_lower = resource.name.lower()
        return any(pattern in resource_name_lower for pattern in backup_patterns)
    
    def _check_automated_backup_tags(self, resource: Any) -> bool:
        """Check for automated backup tags"""
        if not hasattr(resource, 'tags') or not resource.tags:
            return False
        
        backup_tags = [
            'backup', 'automated-backup', 'backup-policy', 'backup-schedule',
            'retention', 'backup-type', 'backup-job', 'recovery-services'
        ]
        
        tags_lower = {k.lower(): v.lower() for k, v in resource.tags.items()}
        
        # Check tag keys
        has_backup_tags = any(tag in str(tags_lower.keys()).lower() for tag in backup_tags)
        
        # Check tag values
        has_backup_values = any(tag in str(tags_lower.values()).lower() for tag in backup_tags)
        
        return has_backup_tags or has_backup_values
    
    async def _get_backup_policies(self, resource_group: str) -> List[Any]:
        """Get backup policies for a resource group"""
        policies = []
        
        try:
            # List Recovery Services Vaults in the resource group
            vaults = self.backup_client.recovery_services_vaults.list_by_resource_group(resource_group)
            
            for vault in vaults:
                try:
                    # List backup policies in each vault
                    vault_policies = self.backup_client.backup_policies.list(
                        vault_name=vault.name,
                        resource_group_name=resource_group
                    )
                    policies.extend(vault_policies)
                except Exception as e:
                    self.logger.warning(f"Failed to get policies from vault {vault.name}: {e}")
                    
        except Exception as e:
            self.logger.warning(f"Failed to list Recovery Services Vaults: {e}")
        
        return policies
    
    async def _analyze_snapshot_backup_importance(
        self, 
        snapshot: Any, 
        backup_policies: List[Any]
    ) -> Dict[str, Any]:
        """Analyze if a snapshot is part of backup strategy"""
        
        analysis = {
            'is_part_of_backup_job': False,
            'backup_retention_days': None,
            'backup_job_correlation': False
        }
        
        try:
            # Check if snapshot creation time correlates with backup schedules
            if hasattr(snapshot, 'time_created') and backup_policies:
                # Simplified check - in real implementation, would check backup job logs
                analysis['backup_job_correlation'] = len(backup_policies) > 0
            
            # Check snapshot properties for backup indicators
            if hasattr(snapshot, 'tags') and snapshot.tags:
                backup_related_tags = ['backup-job-id', 'backup-policy', 'retention-days']
                for tag_key, tag_value in snapshot.tags.items():
                    if any(backup_tag in tag_key.lower() for backup_tag in backup_related_tags):
                        analysis['is_part_of_backup_job'] = True
                        if 'retention' in tag_key.lower():
                            try:
                                analysis['backup_retention_days'] = int(tag_value)
                            except ValueError:
                                pass
            
            # Check if snapshot name indicates it's part of automated backup
            if hasattr(snapshot, 'name'):
                automated_indicators = [
                    'microsoft.azure.backup', 'azurebackup', 'backup-', 'automated-'
                ]
                if any(indicator in snapshot.name.lower() for indicator in automated_indicators):
                    analysis['is_part_of_backup_job'] = True
                    
        except Exception as e:
            self.logger.warning(f"Failed to analyze snapshot backup importance: {e}")
        
        return analysis
    
    def _merge_snapshot_analysis(
        self, 
        base_analysis: BackupPolicyAnalysis, 
        snapshot_analysis: Dict[str, Any]
    ) -> BackupPolicyAnalysis:
        """Merge snapshot-specific analysis"""
        
        base_analysis.is_part_of_backup_job = snapshot_analysis['is_part_of_backup_job']
        base_analysis.backup_retention_days = snapshot_analysis['backup_retention_days']
        
        base_analysis.policy_details.update({
            'backup_job_correlation': snapshot_analysis['backup_job_correlation'],
            'automated_backup_detected': snapshot_analysis['is_part_of_backup_job']
        })
        
        return base_analysis
    
    def _calculate_deletion_risk(
        self, 
        analysis: BackupPolicyAnalysis, 
        resource_type: AzureResourceType
    ) -> str:
        """Calculate risk level for deleting the resource"""
        
        risk_score = 0
        
        # High risk factors
        if analysis.is_automated_backup:
            risk_score += 3
        if analysis.has_backup_policy:
            risk_score += 2
        if analysis.is_part_of_backup_job:
            risk_score += 3
        if analysis.follows_backup_naming:
            risk_score += 1
        
        # Resource type specific risks
        if resource_type == AzureResourceType.SNAPSHOT:
            risk_score += 1  # Snapshots are often critical for recovery
        
        # Calculate retention impact
        if analysis.backup_retention_days:
            if analysis.backup_retention_days > 365:
                risk_score += 2  # Long retention = important data
            elif analysis.backup_retention_days > 90:
                risk_score += 1
        
        # Determine risk level
        if risk_score >= 6:
            return "critical"
        elif risk_score >= 4:
            return "high"
        elif risk_score >= 2:
            return "medium"
        else:
            return "low"
    
    async def get_backup_recommendations(
        self, 
        analysis: BackupPolicyAnalysis, 
        resource_type: AzureResourceType
    ) -> List[str]:
        """Get recommendations based on backup analysis"""
        
        recommendations = []
        
        if analysis.risk_level == "critical":
            recommendations.extend([
                "⚠️  CRITICAL: This resource appears to be part of automated backup system",
                "🚫 DO NOT DELETE without verifying with backup/DR team",
                "📋 Check backup job dependencies before any action"
            ])
        elif analysis.risk_level == "high":
            recommendations.extend([
                "⚠️  HIGH RISK: Resource may be important for backup/recovery",
                "🔍 Verify with backup team before deletion",
                "📊 Check recent backup job logs"
            ])
        elif analysis.risk_level == "medium":
            recommendations.extend([
                "⚠️  MEDIUM RISK: Some backup indicators found",
                "✅ Safe to delete after verification",
                "📝 Document deletion in change management"
            ])
        else:
            recommendations.extend([
                "✅ LOW RISK: No backup dependencies detected",
                "🗑️  Safe to delete",
                "💡 Consider cleanup to reduce costs"
            ])
        
        # Add specific recommendations based on analysis
        if analysis.is_part_of_backup_job:
            recommendations.append("📋 Resource is part of backup job - check job impact")
        
        if analysis.backup_retention_days:
            recommendations.append(
                f"⏰ Backup retention: {analysis.backup_retention_days} days - "
                f"consider impact on compliance"
            )
        
        if not analysis.has_backup_policy and resource_type == AzureResourceType.SNAPSHOT:
            recommendations.append("💡 No backup policies found - may be safe to cleanup old snapshots")
        
        return recommendations