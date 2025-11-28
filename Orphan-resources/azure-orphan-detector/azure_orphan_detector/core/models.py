"""Core data models for Azure Orphan Detector"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Dict, List, Any, Optional


class AzureResourceType(Enum):
    """Azure resource types supported for orphan detection"""
    VIRTUAL_MACHINE = "Microsoft.Compute/virtualMachines"
    DISK = "Microsoft.Compute/disks"
    SNAPSHOT = "Microsoft.Compute/snapshots"
    NETWORK_INTERFACE = "Microsoft.Network/networkInterfaces"
    PUBLIC_IP = "Microsoft.Network/publicIPAddresses"
    NETWORK_SECURITY_GROUP = "Microsoft.Network/networkSecurityGroups"
    LOAD_BALANCER = "Microsoft.Network/loadBalancers"
    APPLICATION_GATEWAY = "Microsoft.Network/applicationGateways"
    STORAGE_ACCOUNT = "Microsoft.Storage/storageAccounts"
    VIRTUAL_NETWORK = "Microsoft.Network/virtualNetworks"


class SeverityLevel(Enum):
    """Severity levels for orphaned resources"""
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    INFO = "info"


class OrphanageReason(Enum):
    """Reasons why a resource is considered orphaned"""
    UNATTACHED = "unattached"
    UNUSED = "unused"
    EMPTY = "empty"
    EXPIRED = "expired"
    REDUNDANT = "redundant"
    MISCONFIGURED = "misconfigured"


@dataclass
class UsageAnalysis:
    """Actual usage patterns from Azure Monitor"""
    has_recent_activity: bool = False
    average_iops: Optional[float] = None
    peak_iops: Optional[float] = None
    average_throughput_mbps: Optional[float] = None
    last_activity_date: Optional[datetime] = None
    usage_trend: str = "unknown"  # increasing, decreasing, stable, unknown
    activity_score: float = 0.0  # 0.0 to 1.0
    metrics_period_days: int = 30


@dataclass
class BackupPolicyAnalysis:
    """Backup and disaster recovery policy analysis"""
    is_automated_backup: bool = False
    has_backup_policy: bool = False
    has_dr_policy: bool = False
    follows_backup_naming: bool = False
    backup_retention_days: Optional[int] = None
    is_part_of_backup_job: bool = False
    risk_level: str = "unknown"  # low, medium, high, critical
    policy_details: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ResourceMetrics:
    """Performance and usage metrics for a resource"""
    cpu_utilization: Optional[float] = None
    memory_utilization: Optional[float] = None
    network_in: Optional[float] = None
    network_out: Optional[float] = None
    last_accessed: Optional[datetime] = None
    storage_usage_gb: Optional[float] = None
    requests_per_day: Optional[float] = None
    disk_iops: Optional[float] = None
    bandwidth_usage: Optional[float] = None
    usage_analysis: Optional[UsageAnalysis] = None


@dataclass
class CostAnalysis:
    """Detailed cost analysis for a resource"""
    current_monthly_cost: float = 0.0
    projected_annual_cost: float = 0.0
    potential_savings: float = 0.0
    cost_trend: str = "stable"
    optimization_suggestions: List[str] = field(default_factory=list)
    cost_breakdown: Dict[str, float] = field(default_factory=dict)
    historical_costs: List[Dict[str, Any]] = field(default_factory=list)
    # Enhanced fields for actual cost data
    actual_costs_available: bool = False
    cost_accuracy: str = "estimated"  # estimated, actual, mixed
    billing_period: str = "current_month"


@dataclass
class SecurityAnalysis:
    """Security implications of orphaned resources"""
    security_risks: List[str] = field(default_factory=list)
    compliance_issues: List[str] = field(default_factory=list)
    network_exposure: str = "none"
    encryption_status: str = "unknown"
    access_permissions: List[str] = field(default_factory=list)
    vulnerability_score: float = 0.0


@dataclass
class EnhancedOrphanedResource:
    """Enhanced orphaned resource with comprehensive analysis"""
    # Basic identification
    resource_id: str
    resource_type: AzureResourceType
    resource_name: str
    resource_group: str
    location: str
    subscription_id: str
    subscription_name: Optional[str] = None
    
    # Timing information
    created_date: Optional[datetime] = None
    last_used: Optional[datetime] = None
    last_modified: Optional[datetime] = None
    
    # Analysis results
    cost_analysis: CostAnalysis = field(default_factory=CostAnalysis)
    metrics: ResourceMetrics = field(default_factory=ResourceMetrics)
    security_analysis: SecurityAnalysis = field(default_factory=SecurityAnalysis)
    backup_analysis: BackupPolicyAnalysis = field(default_factory=BackupPolicyAnalysis)
    
    # Classification
    severity: SeverityLevel = SeverityLevel.MEDIUM
    orphanage_reason: OrphanageReason = OrphanageReason.UNUSED
    confidence_score: float = 0.5
    
    # Metadata
    tags: Dict[str, str] = field(default_factory=dict)
    details: Dict[str, Any] = field(default_factory=dict)
    dependencies: List[str] = field(default_factory=list)
    dependents: List[str] = field(default_factory=list)
    
    # Recommendations
    recommended_actions: List[str] = field(default_factory=list)
    alternative_solutions: List[str] = field(default_factory=list)
    cleanup_priority: int = 5
    estimated_cleanup_time: Optional[int] = None
    
    # Business context
    business_owner: Optional[str] = None
    project_code: Optional[str] = None
    environment: Optional[str] = None
    purpose: Optional[str] = None


@dataclass
class ScanConfiguration:
    """Configuration for orphan detection scans"""
    subscription_ids: List[str] = field(default_factory=list)
    resource_groups: List[str] = field(default_factory=list)
    excluded_resource_groups: List[str] = field(default_factory=list)
    excluded_tags: Dict[str, List[str]] = field(default_factory=dict)
    cost_threshold_critical: float = 100.0
    cost_threshold_high: float = 50.0
    cost_threshold_medium: float = 10.0
    confidence_threshold: float = 0.7
    include_low_confidence: bool = False
    max_age_days: int = 90
    parallel_workers: int = 4
    enable_metrics: bool = True
    enable_security_analysis: bool = True
    enable_compliance_check: bool = True


@dataclass
class ScanResult:
    """Results from an orphan detection scan"""
    scan_id: str
    timestamp: datetime
    configuration: ScanConfiguration
    orphaned_resources: List[EnhancedOrphanedResource] = field(default_factory=list)
    total_monthly_savings: float = 0.0
    total_annual_savings: float = 0.0
    scan_duration_seconds: float = 0.0
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    statistics: Dict[str, Any] = field(default_factory=dict)