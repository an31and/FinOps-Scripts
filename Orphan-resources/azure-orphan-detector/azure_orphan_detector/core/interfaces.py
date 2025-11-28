"""Core interfaces for the Azure Orphan Detector system"""

from abc import ABC, abstractmethod
from typing import Dict, List, Any, Optional
from .models import (
    EnhancedOrphanedResource, 
    AzureResourceType, 
    ResourceMetrics, 
    CostAnalysis,
    SecurityAnalysis,
    ScanConfiguration
)


class IResourceAnalyzer(ABC):
    """Interface for resource analyzers"""
    
    @abstractmethod
    async def analyze(
        self, 
        subscription_id: str, 
        clients: Dict[str, Any], 
        config: ScanConfiguration
    ) -> List[EnhancedOrphanedResource]:
        """Analyze resources and return orphaned ones"""
        pass
    
    @abstractmethod
    def get_supported_resource_types(self) -> List[AzureResourceType]:
        """Return list of supported resource types"""
        pass
    
    @abstractmethod
    def get_analyzer_name(self) -> str:
        """Return analyzer name"""
        pass
    
    @abstractmethod
    def get_analyzer_version(self) -> str:
        """Return analyzer version"""
        pass


class ICostCalculator(ABC):
    """Interface for cost calculators"""
    
    @abstractmethod
    def calculate_cost(
        self, 
        resource: Any, 
        resource_type: AzureResourceType,
        location: str
    ) -> CostAnalysis:
        """Calculate cost analysis for a resource"""
        pass
    
    @abstractmethod
    def get_pricing_data(self, resource_type: AzureResourceType, location: str) -> Dict[str, float]:
        """Get pricing data for resource type and location"""
        pass


class IDashboardGenerator(ABC):
    """Interface for dashboard generators"""
    
    @abstractmethod
    def generate_dashboard(
        self, 
        resources: List[EnhancedOrphanedResource], 
        output_path: str,
        config: Optional[Dict[str, Any]] = None
    ) -> str:
        """Generate dashboard and return path"""
        pass