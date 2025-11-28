"""Enhanced analyzer for orphaned disk resources with usage metrics and backup analysis"""

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
    SecurityAnalysis,
    UsageAnalysis,
    BackupPolicyAnalysis
)
from ..cost.calculator import AzureCostCalculator
from ..utils.usage_analyzer import UsageMetricsAnalyzer
from ..utils.backup_analyzer import BackupPolicyAnalyzer
from ..utils.logger import setup_logger


class DiskAnalyzer(IResourceAnalyzer):
    """Enhanced analyzer for orphaned disk resources with comprehensive analysis"""
    
    def __init__(self, credential=None):
        self.logger = setup_logger(self.__class__.__name__)
        self.credential = credential
        self.cost_calculator = AzureCostCalculator(credential)
        self.usage_analyzer = UsageMetricsAnalyzer(credential)
        self.backup_analyzer = BackupPolicyAnalyzer(credential)
    
    def get_analyzer_name(self) -> str:
        return "DiskAnalyzer"
    
    def get_analyzer_version(self) -> str:
        return "1.0.0"
    
    def get_supported_resource_types(self) -> List[AzureResourceType]:
        return [AzureResourceType.DISK, AzureResourceType.SNAPSHOT]
    
    async def analyze(
        self, 
        subscription_id: str, 
        clients: Dict[str, Any], 
        config: ScanConfiguration
    ) -> List[EnhancedOrphanedResource]:
        """Enhanced analysis of orphaned disks with usage metrics and backup policies"""
        
        orphaned = []
        self.logger.debug(f"Performing enhanced analysis of disks for subscription {subscription_id}")
        
        try:
            compute_client = clients['compute']
            disks = list(compute_client.disks.list())
            
            for disk in disks:
                # Step 1: Basic orphan check
                if await self._is_disk_orphaned(disk):
                    # Step 2: Enhanced analysis with usage metrics and backup policies
                    orphaned_resource = await self._create_enhanced_orphaned_disk_resource(
                        disk, subscription_id, config
                    )
                    if orphaned_resource:
                        # Step 3: Apply enhanced confidence filtering
                        if self._should_include_resource(orphaned_resource, config):
                            orphaned.append(orphaned_resource)
                        else:
                            self.logger.debug(f"Excluding disk {disk.name} due to low confidence or backup dependencies")
            
            # Also analyze snapshots with enhanced analysis
            snapshots = list(compute_client.snapshots.list())
            for snapshot in snapshots:
                if await self._is_snapshot_orphaned_enhanced(snapshot, config, subscription_id):
                    orphaned_resource = await self._create_enhanced_orphaned_snapshot_resource(
                        snapshot, subscription_id, config
                    )
                    if orphaned_resource:
                        if self._should_include_resource(orphaned_resource, config):
                            orphaned.append(orphaned_resource)
                        else:
                            self.logger.debug(f"Excluding snapshot {snapshot.name} due to backup dependencies")
                        
        except Exception as e:
            self.logger.error(f"Error analyzing disks in subscription {subscription_id}: {e}")
        
        return orphaned
    
    def _should_include_resource(self, resource: EnhancedOrphanedResource, config: ScanConfiguration) -> bool:
        """Determine if resource should be included based on enhanced analysis"""
        
        # Apply confidence threshold
        if resource.confidence_score < config.confidence_threshold:
            if not config.include_low_confidence:
                return False
        
        # Exclude resources with critical backup dependencies
        if hasattr(resource, 'backup_analysis') and resource.backup_analysis:
            if resource.backup_analysis.risk_level == "critical":
                self.logger.info(f"Excluding {resource.resource_name} due to critical backup dependencies")
                return False
        
        # Include if usage analysis shows no recent activity
        if hasattr(resource, 'metrics') and resource.metrics and resource.metrics.usage_analysis:
            usage = resource.metrics.usage_analysis
            if usage.has_recent_activity and usage.activity_score > 0.3:
                self.logger.info(f"Excluding {resource.resource_name} due to recent activity")
                return False
        
        return True

    async def _is_disk_orphaned(self, disk: Any) -> bool:
        """Check if disk is orphaned"""
        return not disk.managed_by and not disk.managed_by_extended
    
    async def _is_snapshot_orphaned_enhanced(
        self, 
        snapshot: Any, 
        config: ScanConfiguration, 
        subscription_id: str
    ) -> bool:
        """Enhanced snapshot orphan detection with backup policy awareness"""
        
        if not snapshot.time_created:
            return False
        
        # Basic age check
        age_threshold = timedelta(days=config.max_age_days)
        age = datetime.now(timezone.utc) - snapshot.time_created
        basic_age_check = age > age_threshold
        
        if not basic_age_check:
            return False
        
        # Enhanced check: analyze backup policies
        try:
            resource_group = snapshot.id.split('/')[4]
            backup_analysis = await self.backup_analyzer.analyze_backup_policies(
                snapshot, AzureResourceType.SNAPSHOT, subscription_id, resource_group
            )
            
            # Don't flag as orphaned if it's part of critical backup infrastructure
            if backup_analysis.risk_level == "critical":
                self.logger.info(f"Snapshot {snapshot.name} appears to be part of critical backup system")
                return False
                
        except Exception as e:
            self.logger.warning(f"Failed to analyze backup policies for snapshot {snapshot.name}: {e}")
        
        return True

    async def _is_snapshot_orphaned(self, snapshot: Any, config: ScanConfiguration) -> bool:
        """Check if snapshot is orphaned"""
        if not snapshot.time_created:
            return False
        
        age_threshold = timedelta(days=config.max_age_days)
        age = datetime.now(timezone.utc) - snapshot.time_created
        
        return age > age_threshold
    
    async def _create_enhanced_orphaned_disk_resource(
        self, 
        disk: Any, 
        subscription_id: str, 
        config: ScanConfiguration
    ) -> EnhancedOrphanedResource:
        """Create enhanced orphaned resource object for disk with comprehensive analysis"""
        
        try:
            resource_group = disk.id.split('/')[4]
            
            # Step 1: Enhanced cost analysis with actual costs
            cost_analysis = await self.cost_calculator.calculate_enhanced_cost(
                disk, AzureResourceType.DISK, disk.location, subscription_id
            )
            
            # Step 2: Usage metrics analysis
            usage_analysis = await self.usage_analyzer.analyze_resource_usage(
                disk.id, subscription_id, AzureResourceType.DISK, 30
            )
            
            # Step 3: Backup policy analysis
            backup_analysis = await self.backup_analyzer.analyze_backup_policies(
                disk, AzureResourceType.DISK, subscription_id, resource_group
            )
            
            # Step 4: Enhanced metrics
            metrics = ResourceMetrics()
            metrics.usage_analysis = usage_analysis
            
            # Step 5: Security analysis
            security_analysis = SecurityAnalysis()
            security_analysis.security_risks.append("Disk may contain sensitive data")
            security_analysis.compliance_issues.append("Data encryption status should be verified")
            
            # Step 6: Enhanced confidence scoring
            confidence_score = self._calculate_enhanced_confidence_score(
                disk, usage_analysis, backup_analysis
            )
            
            # Step 7: Severity determination
            severity = self._determine_enhanced_severity(cost_analysis, usage_analysis, backup_analysis, config)
            
            # Step 8: Enhanced recommendations
            recommendations = await self._generate_enhanced_recommendations(
                disk, AzureResourceType.DISK, backup_analysis, usage_analysis, cost_analysis
            )
            
            return EnhancedOrphanedResource(
                resource_id=disk.id,
                resource_type=AzureResourceType.DISK,
                resource_name=disk.name,
                resource_group=resource_group,
                location=disk.location,
                subscription_id=subscription_id,
                created_date=disk.time_created,
                cost_analysis=cost_analysis,
                metrics=metrics,
                security_analysis=security_analysis,
                backup_analysis=backup_analysis,
                severity=severity,
                orphanage_reason=OrphanageReason.UNATTACHED,
                confidence_score=confidence_score,
                tags=disk.tags or {},
                details={
                    'disk_size_gb': disk.disk_size_gb,
                    'disk_state': disk.disk_state,
                    'sku_name': disk.sku.name if disk.sku else 'Unknown',
                    'sku_tier': disk.sku.tier if disk.sku else 'Unknown',
                    'os_type': disk.os_type,
                    'usage_activity_score': usage_analysis.activity_score if usage_analysis else 0.0,
                    'backup_risk_level': backup_analysis.risk_level if backup_analysis else 'unknown'
                },
                recommended_actions=recommendations,
                cleanup_priority=self._calculate_cleanup_priority(cost_analysis, severity, confidence_score)
            )
            
        except Exception as e:
            self.logger.warning(f"Failed to create enhanced orphaned resource for disk {disk.name}: {e}")
            # Fallback to basic analysis
            return await self._create_orphaned_disk_resource(disk, subscription_id, config)

    async def _create_enhanced_orphaned_snapshot_resource(
        self, 
        snapshot: Any, 
        subscription_id: str, 
        config: ScanConfiguration
    ) -> EnhancedOrphanedResource:
        """Create enhanced orphaned resource object for snapshot with backup analysis"""
        
        try:
            resource_group = snapshot.id.split('/')[4]
            
            # Enhanced cost analysis
            cost_analysis = await self.cost_calculator.calculate_enhanced_cost(
                snapshot, AzureResourceType.SNAPSHOT, snapshot.location, subscription_id
            )
            
            # Backup policy analysis (critical for snapshots)
            backup_analysis = await self.backup_analyzer.analyze_backup_policies(
                snapshot, AzureResourceType.SNAPSHOT, subscription_id, resource_group
            )
            
            # Enhanced confidence scoring
            confidence_score = self._calculate_enhanced_confidence_score(
                snapshot, None, backup_analysis
            )
            
            # Enhanced severity determination
            severity = self._determine_enhanced_severity(cost_analysis, None, backup_analysis, config)
            
            # Enhanced recommendations
            recommendations = await self._generate_enhanced_recommendations(
                snapshot, AzureResourceType.SNAPSHOT, backup_analysis, None, cost_analysis
            )
            
            return EnhancedOrphanedResource(
                resource_id=snapshot.id,
                resource_type=AzureResourceType.SNAPSHOT,
                resource_name=snapshot.name,
                resource_group=resource_group,
                location=snapshot.location,
                subscription_id=subscription_id,
                created_date=snapshot.time_created,
                cost_analysis=cost_analysis,
                backup_analysis=backup_analysis,
                severity=severity,
                orphanage_reason=OrphanageReason.EXPIRED,
                confidence_score=confidence_score,
                tags=snapshot.tags or {},
                details={
                    'disk_size_gb': snapshot.disk_size_gb,
                    'sku_name': snapshot.sku.name if snapshot.sku else 'Unknown',
                    'os_type': snapshot.os_type,
                    'backup_risk_level': backup_analysis.risk_level if backup_analysis else 'unknown',
                    'is_automated_backup': backup_analysis.is_automated_backup if backup_analysis else False
                },
                recommended_actions=recommendations,
                cleanup_priority=self._calculate_cleanup_priority(cost_analysis, severity, confidence_score)
            )
            
        except Exception as e:
            self.logger.warning(f"Failed to create enhanced orphaned resource for snapshot {snapshot.name}: {e}")
            # Fallback to basic analysis
            return await self._create_orphaned_snapshot_resource(snapshot, subscription_id, config)

    async def _create_orphaned_disk_resource(
        self, 
        disk: Any, 
        subscription_id: str, 
        config: ScanConfiguration
    ) -> EnhancedOrphanedResource:
        """Create orphaned resource object for disk"""
        
        try:
            cost_analysis = self.cost_calculator.calculate_cost(
                disk, AzureResourceType.DISK, disk.location
            )
            
            metrics = ResourceMetrics()
            security_analysis = SecurityAnalysis()
            security_analysis.security_risks.append("Disk may contain sensitive data")
            security_analysis.compliance_issues.append("Data encryption status should be verified")
            
            confidence_score = self._calculate_confidence_score(disk)
            severity = self._determine_severity(cost_analysis, config)
            
            recommendations = [
                "Create snapshot before deletion if data might be needed",
                "Verify no applications are expecting this disk to be available",
                "Delete disk to avoid ongoing storage costs"
            ]
            
            return EnhancedOrphanedResource(
                resource_id=disk.id,
                resource_type=AzureResourceType.DISK,
                resource_name=disk.name,
                resource_group=disk.id.split('/')[4],
                location=disk.location,
                subscription_id=subscription_id,
                created_date=disk.time_created,
                cost_analysis=cost_analysis,
                metrics=metrics,
                severity=severity,
                orphanage_reason=OrphanageReason.UNATTACHED,
                confidence_score=confidence_score,
                security_analysis=security_analysis,
                tags=disk.tags or {},
                details={
                    'disk_size_gb': disk.disk_size_gb,
                    'disk_state': disk.disk_state,
                    'sku_name': disk.sku.name if disk.sku else 'Unknown',
                    'sku_tier': disk.sku.tier if disk.sku else 'Unknown',
                    'os_type': disk.os_type,
                },
                recommended_actions=recommendations,
                cleanup_priority=self._calculate_cleanup_priority(cost_analysis, severity, confidence_score)
            )
            
        except Exception as e:
            self.logger.warning(f"Failed to create orphaned resource for disk {disk.name}: {e}")
            return None
    
    async def _create_orphaned_snapshot_resource(
        self, 
        snapshot: Any, 
        subscription_id: str, 
        config: ScanConfiguration
    ) -> EnhancedOrphanedResource:
        """Create orphaned resource object for snapshot"""
        
        try:
            cost_analysis = self.cost_calculator.calculate_cost(
                snapshot, AzureResourceType.SNAPSHOT, snapshot.location
            )
            
            confidence_score = self._calculate_confidence_score(snapshot)
            severity = self._determine_severity(cost_analysis, config)
            
            recommendations = [
                "Verify snapshot is not part of backup strategy",
                "Check if snapshot data is needed for recovery",
                "Delete old snapshots to reduce storage costs"
            ]
            
            return EnhancedOrphanedResource(
                resource_id=snapshot.id,
                resource_type=AzureResourceType.SNAPSHOT,
                resource_name=snapshot.name,
                resource_group=snapshot.id.split('/')[4],
                location=snapshot.location,
                subscription_id=subscription_id,
                created_date=snapshot.time_created,
                cost_analysis=cost_analysis,
                severity=severity,
                orphanage_reason=OrphanageReason.EXPIRED,
                confidence_score=confidence_score,
                tags=snapshot.tags or {},
                details={
                    'disk_size_gb': snapshot.disk_size_gb,
                    'sku_name': snapshot.sku.name if snapshot.sku else 'Unknown',
                    'os_type': snapshot.os_type,
                },
                recommended_actions=recommendations,
                cleanup_priority=self._calculate_cleanup_priority(cost_analysis, severity, confidence_score)
            )
            
        except Exception as e:
            self.logger.warning(f"Failed to create orphaned resource for snapshot {snapshot.name}: {e}")
            return None
    
    def _calculate_confidence_score(self, resource: Any) -> float:
        """Calculate confidence score for orphaned resource classification"""
        
        score = 0.5  # Base score
        
        try:
            # Time-based factors
            if hasattr(resource, 'time_created') and resource.time_created:
                days_old = (datetime.now(timezone.utc) - resource.time_created).days
                if days_old > 90:
                    score += 0.2
                elif days_old > 30:
                    score += 0.1
            
            # Tag-based factors
            if hasattr(resource, 'tags') and resource.tags:
                temp_tags = ['temporary', 'test', 'dev', 'poc', 'demo']
                if any(tag.lower() in str(resource.tags).lower() for tag in temp_tags):
                    score += 0.1
            
            score = min(1.0, max(0.0, score))
            
        except Exception as e:
            self.logger.warning(f"Failed to calculate confidence score: {e}")
        
        return score
    
    def _determine_severity(self, cost_analysis: CostAnalysis, config: ScanConfiguration) -> SeverityLevel:
        """Determine severity level based on cost analysis"""
        
        monthly_cost = cost_analysis.current_monthly_cost
        
        if monthly_cost > config.cost_threshold_critical:
            return SeverityLevel.CRITICAL
        elif monthly_cost > config.cost_threshold_high:
            return SeverityLevel.HIGH
        elif monthly_cost > config.cost_threshold_medium:
            return SeverityLevel.MEDIUM
        elif monthly_cost > 1.0:
            return SeverityLevel.LOW
        else:
            return SeverityLevel.INFO
    
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
        if monthly_cost > 100:
            priority -= 3
        elif monthly_cost > 50:
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

    def _calculate_enhanced_confidence_score(
        self, 
        resource: Any, 
        usage_analysis: UsageAnalysis = None, 
        backup_analysis: BackupPolicyAnalysis = None
    ) -> float:
        """Calculate enhanced confidence score with usage and backup analysis"""
        
        # Start with basic confidence score
        score = self._calculate_confidence_score(resource)
        
        # Adjust based on usage analysis
        if usage_analysis:
            if not usage_analysis.has_recent_activity:
                score += 0.2  # Higher confidence if no recent activity
            else:
                score -= usage_analysis.activity_score * 0.3  # Lower confidence if active
        
        # Adjust based on backup analysis
        if backup_analysis:
            if backup_analysis.risk_level == "critical":
                score = 0.1  # Very low confidence for critical backup resources
            elif backup_analysis.risk_level == "high":
                score *= 0.5  # Significantly reduce confidence
            elif backup_analysis.risk_level == "medium":
                score *= 0.7  # Moderately reduce confidence
            elif backup_analysis.risk_level == "low":
                score += 0.1  # Slightly increase confidence
        
        return min(1.0, max(0.0, score))

    def _determine_enhanced_severity(
        self, 
        cost_analysis: CostAnalysis, 
        usage_analysis: UsageAnalysis = None, 
        backup_analysis: BackupPolicyAnalysis = None, 
        config: ScanConfiguration = None
    ) -> SeverityLevel:
        """Determine severity with enhanced analysis"""
        
        # Start with cost-based severity
        base_severity = self._determine_severity(cost_analysis, config)
        
        # Upgrade severity if backup risks are involved
        if backup_analysis:
            if backup_analysis.risk_level == "critical":
                return SeverityLevel.CRITICAL
            elif backup_analysis.risk_level == "high" and base_severity.value < SeverityLevel.HIGH.value:
                return SeverityLevel.HIGH
        
        # Downgrade severity if resource is actively used
        if usage_analysis and usage_analysis.has_recent_activity and usage_analysis.activity_score > 0.5:
            severity_order = [SeverityLevel.INFO, SeverityLevel.LOW, SeverityLevel.MEDIUM, SeverityLevel.HIGH, SeverityLevel.CRITICAL]
            current_index = severity_order.index(base_severity)
            if current_index > 0:
                return severity_order[current_index - 1]
        
        return base_severity

    async def _generate_enhanced_recommendations(
        self, 
        resource: Any,
        resource_type: AzureResourceType,
        backup_analysis: BackupPolicyAnalysis = None,
        usage_analysis: UsageAnalysis = None,
        cost_analysis: CostAnalysis = None
    ) -> List[str]:
        """Generate enhanced recommendations based on comprehensive analysis"""
        
        recommendations = []
        
        # Backup-specific recommendations
        if backup_analysis:
            backup_recommendations = await self.backup_analyzer.get_backup_recommendations(
                backup_analysis, resource_type
            )
            recommendations.extend(backup_recommendations)
        
        # Usage-specific recommendations
        if usage_analysis:
            if usage_analysis.has_recent_activity:
                recommendations.append(
                    f"⚠️  Resource shows recent activity (score: {usage_analysis.activity_score:.2f}) - "
                    f"verify it's not in use before deletion"
                )
            else:
                recommendations.append(
                    "✅ No recent activity detected - safe to delete from usage perspective"
                )
        
        # Cost-specific recommendations
        if cost_analysis:
            if cost_analysis.actual_costs_available:
                recommendations.append(
                    f"💰 Actual cost data available: ${cost_analysis.current_monthly_cost:.2f}/month"
                )
            else:
                recommendations.append(
                    f"💰 Estimated cost: ${cost_analysis.current_monthly_cost:.2f}/month "
                    f"(verify with actual billing data)"
                )
        
        # Resource-specific recommendations
        if resource_type == AzureResourceType.DISK:
            recommendations.extend([
                "💾 Create snapshot before deletion if data recovery might be needed",
                "🔍 Verify no applications are expecting this disk to be available",
                "📋 Check if disk is part of any disaster recovery plans"
            ])
        elif resource_type == AzureResourceType.SNAPSHOT:
            recommendations.extend([
                "🕐 Verify snapshot age and retention requirements",
                "🔄 Check if snapshot is part of backup rotation schedule",
                "📊 Review historical importance of the snapshot data"
            ])
        
        # General recommendations
        recommendations.extend([
            "📝 Document deletion in change management system",
            "👥 Notify relevant teams before cleanup",
            "⏰ Consider scheduling deletion during maintenance window"
        ])
        
        return recommendations