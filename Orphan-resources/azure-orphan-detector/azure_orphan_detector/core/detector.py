"""Main orchestrator for Azure Orphan Detection"""

import asyncio
import logging
import uuid
from datetime import datetime, timezone
from typing import Dict, List, Optional, Any
import time
from collections import defaultdict

from .interfaces import IResourceAnalyzer
from .models import (
    ScanConfiguration, 
    ScanResult, 
    EnhancedOrphanedResource,
    AzureResourceType,
    SeverityLevel
)
from ..auth.manager import AuthenticationManager
from ..analyzers.disk_analyzer import DiskAnalyzer
from ..analyzers.public_ip_analyzer import PublicIPAnalyzer
from ..utils.logger import setup_logger


class AnalyzerRegistry:
    """Registry for managing resource analyzers"""
    
    def __init__(self):
        self.logger = setup_logger(self.__class__.__name__)
        self._analyzers: Dict[str, IResourceAnalyzer] = {}
        self._enabled_analyzers: List[str] = []
        # Note: _register_default_analyzers will be called from OrphanDetector
    
    def _register_default_analyzers(self, credential=None):
        """Register default analyzers with enhanced capabilities"""
        default_analyzers = [
            DiskAnalyzer(credential),
            PublicIPAnalyzer(),
        ]
        
        for analyzer in default_analyzers:
            self.register_analyzer(analyzer)
            self.enable_analyzer(analyzer.get_analyzer_name())
    
    def register_analyzer(self, analyzer: IResourceAnalyzer) -> None:
        """Register a new analyzer"""
        name = analyzer.get_analyzer_name()
        self._analyzers[name] = analyzer
        self.logger.debug(f"Registered analyzer: {name}")
    
    def enable_analyzer(self, name: str) -> None:
        """Enable an analyzer"""
        if name in self._analyzers and name not in self._enabled_analyzers:
            self._enabled_analyzers.append(name)
            self.logger.debug(f"Enabled analyzer: {name}")
    
    def get_enabled_analyzers(self) -> List[IResourceAnalyzer]:
        """Get list of enabled analyzers"""
        return [self._analyzers[name] for name in self._enabled_analyzers if name in self._analyzers]


class OrphanDetector:
    """Main orchestrator for orphan detection"""
    
    def __init__(self, config: Optional[ScanConfiguration] = None):
        self.config = config or ScanConfiguration()
        self.logger = setup_logger(self.__class__.__name__)
        self.auth_manager = AuthenticationManager()
        
        # Initialize registry with credentials for enhanced analysis
        credential = self.auth_manager.get_credential()
        self.analyzer_registry = AnalyzerRegistry()
        self.analyzer_registry._register_default_analyzers(credential)
        
        self.scan_results: List[ScanResult] = []
        
    async def scan_subscriptions(
        self, 
        subscription_ids: Optional[List[str]] = None
    ) -> ScanResult:
        """Scan multiple subscriptions for orphaned resources"""
        
        scan_id = str(uuid.uuid4())
        start_time = time.time()
        
        self.logger.info(f"Starting scan {scan_id}")
        
        # Use provided subscription IDs or get from config
        subs_to_scan = subscription_ids or self.config.subscription_ids
        if not subs_to_scan:
            subs_to_scan = await self.auth_manager.get_accessible_subscriptions()
        
        scan_result = ScanResult(
            scan_id=scan_id,
            timestamp=datetime.now(timezone.utc),
            configuration=self.config
        )
        
        all_orphaned_resources = []
        
        # Process subscriptions in parallel
        semaphore = asyncio.Semaphore(self.config.parallel_workers)
        
        async def scan_subscription(subscription_id: str):
            async with semaphore:
                try:
                    return await self._scan_single_subscription(subscription_id)
                except Exception as e:
                    self.logger.error(f"Error scanning subscription {subscription_id}: {e}")
                    scan_result.errors.append(f"Subscription {subscription_id}: {str(e)}")
                    return []
        
        # Execute scans
        tasks = [scan_subscription(sub_id) for sub_id in subs_to_scan]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Collect results
        for result in results:
            if isinstance(result, list):
                all_orphaned_resources.extend(result)
            elif isinstance(result, Exception):
                scan_result.errors.append(str(result))
        
        # Calculate totals
        scan_result.orphaned_resources = all_orphaned_resources
        scan_result.total_monthly_savings = sum(
            r.cost_analysis.current_monthly_cost for r in all_orphaned_resources
        )
        scan_result.total_annual_savings = scan_result.total_monthly_savings * 12
        scan_result.scan_duration_seconds = time.time() - start_time
        
        # Generate statistics
        scan_result.statistics = self._generate_statistics(all_orphaned_resources)
        
        self.scan_results.append(scan_result)
        
        self.logger.info(
            f"Scan {scan_id} completed: {len(all_orphaned_resources)} resources found, "
            f"${scan_result.total_monthly_savings:.2f} monthly savings potential"
        )
        
        return scan_result
    
    async def _scan_single_subscription(self, subscription_id: str) -> List[EnhancedOrphanedResource]:
        """Scan a single subscription"""
        
        self.logger.debug(f"Scanning subscription: {subscription_id}")
        
        try:
            # Get Azure clients
            clients = await self.auth_manager.get_clients_for_subscription(subscription_id)
            
            # Get enabled analyzers
            analyzers = self.analyzer_registry.get_enabled_analyzers()
            
            all_resources = []
            
            # Run analyzers
            for analyzer in analyzers:
                try:
                    self.logger.debug(f"Running {analyzer.get_analyzer_name()} for {subscription_id}")
                    resources = await analyzer.analyze(subscription_id, clients, self.config)
                    all_resources.extend(resources)
                except Exception as e:
                    self.logger.error(f"Analyzer {analyzer.get_analyzer_name()} failed: {e}")
            
            # Apply post-processing
            processed_resources = await self._post_process_resources(all_resources, subscription_id)
            
            return processed_resources
            
        except Exception as e:
            self.logger.error(f"Failed to scan subscription {subscription_id}: {e}")
            raise
    
    async def _post_process_resources(
        self, 
        resources: List[EnhancedOrphanedResource],
        subscription_id: str
    ) -> List[EnhancedOrphanedResource]:
        """Apply post-processing to resources"""
        
        processed = []
        
        for resource in resources:
            # Apply filters
            if not self._should_include_resource(resource):
                continue
            
            # Enrich with additional data
            await self._enrich_resource_data(resource, subscription_id)
            
            processed.append(resource)
        
        # Sort by cleanup priority
        processed.sort(key=lambda x: (x.cleanup_priority, -x.cost_analysis.current_monthly_cost))
        
        return processed
    
    def _should_include_resource(self, resource: EnhancedOrphanedResource) -> bool:
        """Apply inclusion filters"""
        
        # Check confidence threshold
        if (not self.config.include_low_confidence and 
            resource.confidence_score < self.config.confidence_threshold):
            return False
        
        # Check excluded resource groups
        if resource.resource_group in self.config.excluded_resource_groups:
            return False
        
        # Check excluded tags
        for tag_key, tag_values in self.config.excluded_tags.items():
            if (tag_key in resource.tags and 
                (not tag_values or resource.tags[tag_key] in tag_values)):
                return False
        
        return True
    
    async def _enrich_resource_data(
        self, 
        resource: EnhancedOrphanedResource, 
        subscription_id: str
    ) -> None:
        """Enrich resource with additional data"""
        
        try:
            # Add subscription name if available
            if not resource.subscription_name:
                resource.subscription_name = await self.auth_manager.get_subscription_name(subscription_id)
            
            # Extract business context from tags
            if 'owner' in resource.tags:
                resource.business_owner = resource.tags['owner']
            if 'project' in resource.tags:
                resource.project_code = resource.tags['project']
            if 'environment' in resource.tags:
                resource.environment = resource.tags['environment']
                
        except Exception as e:
            self.logger.warning(f"Failed to enrich resource {resource.resource_name}: {e}")
    
    def _generate_statistics(self, resources: List[EnhancedOrphanedResource]) -> Dict[str, Any]:
        """Generate scan statistics"""
        
        stats = {
            'total_resources': len(resources),
            'by_severity': {},
            'by_type': {},
            'by_subscription': {},
        }
        
        if not resources:
            return stats
        
        for resource in resources:
            # Severity distribution
            severity = resource.severity.value
            stats['by_severity'][severity] = stats['by_severity'].get(severity, 0) + 1
            
            # Type distribution
            resource_type = resource.resource_type.value.split('/')[-1]
            stats['by_type'][resource_type] = stats['by_type'].get(resource_type, 0) + 1
            
            # Subscription distribution
            sub_id = resource.subscription_id[:8] + "..."
            stats['by_subscription'][sub_id] = stats['by_subscription'].get(sub_id, 0) + 1
        
        return stats