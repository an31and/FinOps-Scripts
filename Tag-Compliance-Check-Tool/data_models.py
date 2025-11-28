"""
Data Models Module

Contains all data classes and models used throughout the Azure Tagging Analysis Tool.
"""

from dataclasses import dataclass, field
from typing import Dict, List
from constants import TagComplianceStatus


@dataclass
class TagData:
    """Data structure for tag information with compliance status"""
    name: str
    value: str
    resource_name: str
    resource_type: str
    resource_id: str
    resource_location: str = ""
    subscription_name: str = ""
    subscription_id: str = ""
    is_mandatory_missing: bool = False
    is_untagged: bool = False
    compliance_status: str = TagComplianceStatus.COMPLIANT
    canonical_tag_name: str = ""
    variation_matched: str = ""
    all_resource_tags: Dict[str, str] = field(default_factory=dict)  # Store all tags for the resource


@dataclass
class ResourceGroupTagData:
    """Data structure for resource group tag information"""
    name: str
    value: str
    resource_name: str
    resource_id: str
    subscription_name: str = ""
    subscription_id: str = ""
    is_untagged: bool = False
    compliance_status: str = TagComplianceStatus.COMPLIANT
    canonical_tag_name: str = ""
    variation_matched: str = ""


@dataclass
class SubscriptionInfo:
    """Subscription information with enhanced metrics including partial compliance"""
    id: str
    name: str = ""
    resource_count: int = 0
    rg_count: int = 0
    tagged_resources: int = 0
    tagged_rgs: int = 0
    mandatory_compliant_resources: int = 0
    mandatory_partial_resources: int = 0
    
    @property
    def resource_tagging_percentage(self) -> float:
        """Calculate resource tagging percentage"""
        return (self.tagged_resources / self.resource_count * 100) if self.resource_count > 0 else 0
    
    @property
    def rg_tagging_percentage(self) -> float:
        """Calculate resource group tagging percentage"""
        return (self.tagged_rgs / self.rg_count * 100) if self.rg_count > 0 else 0
    
    @property
    def mandatory_compliance_percentage(self) -> float:
        """Calculate mandatory tag compliance percentage (full compliance only)"""
        return (self.mandatory_compliant_resources / self.resource_count * 100) if self.resource_count > 0 else 0
    
    @property
    def mandatory_partial_percentage(self) -> float:
        """Calculate partial compliance percentage"""
        return (self.mandatory_partial_resources / self.resource_count * 100) if self.resource_count > 0 else 0
    
    @property
    def combined_compliance_percentage(self) -> float:
        """Calculate combined compliance percentage (full + partial)"""
        total_compliant = self.mandatory_compliant_resources + self.mandatory_partial_resources
        return (total_compliant / self.resource_count * 100) if self.resource_count > 0 else 0
