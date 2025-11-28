"""Usage metrics analyzer for Azure resources using Azure Monitor APIs"""

import logging
from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta

try:
    from azure.mgmt.monitor import MonitorManagementClient
    MONITOR_AVAILABLE = True
except ImportError:
    MonitorManagementClient = None
    MONITOR_AVAILABLE = False

from ..core.models import UsageAnalysis, AzureResourceType
from ..utils.logger import setup_logger


class UsageMetricsAnalyzer:
    """Analyze actual resource usage patterns using Azure Monitor"""
    
    def __init__(self, credential=None):
        self.logger = setup_logger(self.__class__.__name__)
        self.credential = credential
        self.monitor_client = None
        
        if credential and MONITOR_AVAILABLE:
            try:
                self.monitor_client = MonitorManagementClient(credential, subscription_id="")
                self.logger.info("Azure Monitor client initialized successfully")
            except Exception as e:
                self.logger.warning(f"Failed to initialize Monitor client: {e}")
        else:
            self.logger.warning("Azure Monitor client not available - using basic analysis")
    
    async def analyze_resource_usage(
        self, 
        resource_id: str, 
        subscription_id: str,
        resource_type: AzureResourceType,
        analysis_period_days: int = 30
    ) -> UsageAnalysis:
        """Analyze usage patterns for a specific resource"""
        
        usage_analysis = UsageAnalysis(metrics_period_days=analysis_period_days)
        
        if not self.monitor_client:
            self.logger.warning("Monitor client not available, returning default analysis")
            return usage_analysis
        
        # Update subscription in monitor client
        self.monitor_client.subscription_id = subscription_id
        
        try:
            if resource_type == AzureResourceType.DISK:
                usage_analysis = await self._analyze_disk_usage(resource_id, analysis_period_days)
            elif resource_type == AzureResourceType.STORAGE_ACCOUNT:
                usage_analysis = await self._analyze_storage_usage(resource_id, analysis_period_days)
            elif resource_type == AzureResourceType.PUBLIC_IP:
                usage_analysis = await self._analyze_public_ip_usage(resource_id, analysis_period_days)
            elif resource_type == AzureResourceType.NETWORK_INTERFACE:
                usage_analysis = await self._analyze_network_interface_usage(resource_id, analysis_period_days)
            else:
                self.logger.info(f"Usage analysis not implemented for {resource_type}")
                
        except Exception as e:
            self.logger.error(f"Failed to analyze usage for {resource_id}: {e}")
        
        return usage_analysis
    
    async def _analyze_disk_usage(self, disk_id: str, period_days: int) -> UsageAnalysis:
        """Analyze disk usage patterns"""
        usage_analysis = UsageAnalysis(metrics_period_days=period_days)
        
        try:
            # Define metrics to retrieve
            metric_names = [
                "Disk Read Operations/Sec",
                "Disk Write Operations/Sec", 
                "Disk Read Bytes/Sec",
                "Disk Write Bytes/Sec"
            ]
            
            # Calculate time range
            end_time = datetime.utcnow()
            start_time = end_time - timedelta(days=period_days)
            
            # Get metrics
            metrics_data = self.monitor_client.metrics.list(
                resource_uri=disk_id,
                timespan=f"{start_time.isoformat()}/{end_time.isoformat()}",
                interval="PT1H",  # 1 hour intervals
                metricnames=",".join(metric_names),
                aggregation="Average"
            )
            
            # Analyze the data
            total_read_ops = 0
            total_write_ops = 0
            total_throughput = 0
            data_points = 0
            last_activity = None
            
            for metric in metrics_data.value:
                if metric.timeseries:
                    for timeseries in metric.timeseries:
                        for data_point in timeseries.data:
                            if data_point.average and data_point.average > 0:
                                data_points += 1
                                if not last_activity or data_point.time_stamp > last_activity:
                                    last_activity = data_point.time_stamp
                                
                                if "Read Operations" in metric.name.value:
                                    total_read_ops += data_point.average
                                elif "Write Operations" in metric.name.value:
                                    total_write_ops += data_point.average
                                elif "Bytes/Sec" in metric.name.value:
                                    total_throughput += data_point.average / (1024 * 1024)  # Convert to MB/s
            
            # Calculate analysis results
            if data_points > 0:
                usage_analysis.has_recent_activity = True
                usage_analysis.average_iops = (total_read_ops + total_write_ops) / data_points
                usage_analysis.average_throughput_mbps = total_throughput / data_points
                usage_analysis.last_activity_date = last_activity
                
                # Calculate activity score (0.0 to 1.0)
                # Higher IOPS = higher score
                if usage_analysis.average_iops:
                    usage_analysis.activity_score = min(1.0, usage_analysis.average_iops / 100.0)
                
                # Determine usage trend (simplified)
                if data_points >= period_days:
                    usage_analysis.usage_trend = "stable"
                else:
                    usage_analysis.usage_trend = "decreasing"
            else:
                usage_analysis.has_recent_activity = False
                usage_analysis.activity_score = 0.0
                usage_analysis.usage_trend = "no_activity"
                
        except Exception as e:
            self.logger.error(f"Failed to analyze disk usage: {e}")
        
        return usage_analysis
    
    async def _analyze_storage_usage(self, storage_id: str, period_days: int) -> UsageAnalysis:
        """Analyze storage account usage patterns"""
        usage_analysis = UsageAnalysis(metrics_period_days=period_days)
        
        try:
            metric_names = [
                "Transactions",
                "Ingress", 
                "Egress",
                "UsedCapacity"
            ]
            
            end_time = datetime.utcnow()
            start_time = end_time - timedelta(days=period_days)
            
            metrics_data = self.monitor_client.metrics.list(
                resource_uri=storage_id,
                timespan=f"{start_time.isoformat()}/{end_time.isoformat()}",
                interval="PT1H",
                metricnames=",".join(metric_names),
                aggregation="Total"
            )
            
            total_transactions = 0
            total_ingress = 0
            total_egress = 0
            data_points = 0
            last_activity = None
            
            for metric in metrics_data.value:
                if metric.timeseries:
                    for timeseries in metric.timeseries:
                        for data_point in timeseries.data:
                            if data_point.total and data_point.total > 0:
                                data_points += 1
                                if not last_activity or data_point.time_stamp > last_activity:
                                    last_activity = data_point.time_stamp
                                
                                if "Transactions" in metric.name.value:
                                    total_transactions += data_point.total
                                elif "Ingress" in metric.name.value:
                                    total_ingress += data_point.total
                                elif "Egress" in metric.name.value:
                                    total_egress += data_point.total
            
            if data_points > 0:
                usage_analysis.has_recent_activity = True
                usage_analysis.last_activity_date = last_activity
                usage_analysis.activity_score = min(1.0, total_transactions / 10000.0)
                usage_analysis.usage_trend = "active" if total_transactions > 1000 else "low"
            else:
                usage_analysis.has_recent_activity = False
                usage_analysis.activity_score = 0.0
                usage_analysis.usage_trend = "no_activity"
                
        except Exception as e:
            self.logger.error(f"Failed to analyze storage usage: {e}")
        
        return usage_analysis
    
    async def _analyze_public_ip_usage(self, pip_id: str, period_days: int) -> UsageAnalysis:
        """Analyze public IP usage patterns"""
        usage_analysis = UsageAnalysis(metrics_period_days=period_days)
        
        try:
            metric_names = [
                "ByteCount",
                "PacketCount", 
                "SynCount",
                "VipAvailability"
            ]
            
            end_time = datetime.utcnow()
            start_time = end_time - timedelta(days=period_days)
            
            metrics_data = self.monitor_client.metrics.list(
                resource_uri=pip_id,
                timespan=f"{start_time.isoformat()}/{end_time.isoformat()}",
                interval="PT1H",
                metricnames=",".join(metric_names),
                aggregation="Total"
            )
            
            total_bytes = 0
            total_packets = 0
            data_points = 0
            last_activity = None
            
            for metric in metrics_data.value:
                if metric.timeseries:
                    for timeseries in metric.timeseries:
                        for data_point in timeseries.data:
                            if data_point.total and data_point.total > 0:
                                data_points += 1
                                if not last_activity or data_point.time_stamp > last_activity:
                                    last_activity = data_point.time_stamp
                                
                                if "ByteCount" in metric.name.value:
                                    total_bytes += data_point.total
                                elif "PacketCount" in metric.name.value:
                                    total_packets += data_point.total
            
            if data_points > 0:
                usage_analysis.has_recent_activity = True
                usage_analysis.last_activity_date = last_activity
                usage_analysis.average_throughput_mbps = (total_bytes / data_points) / (1024 * 1024)
                usage_analysis.activity_score = min(1.0, total_packets / 100000.0)
                usage_analysis.usage_trend = "active" if total_packets > 1000 else "low"
            else:
                usage_analysis.has_recent_activity = False
                usage_analysis.activity_score = 0.0
                usage_analysis.usage_trend = "no_activity"
                
        except Exception as e:
            self.logger.error(f"Failed to analyze public IP usage: {e}")
        
        return usage_analysis
    
    async def _analyze_network_interface_usage(self, nic_id: str, period_days: int) -> UsageAnalysis:
        """Analyze network interface usage patterns"""
        usage_analysis = UsageAnalysis(metrics_period_days=period_days)
        
        try:
            metric_names = [
                "Network In Total",
                "Network Out Total",
                "Network In",
                "Network Out"
            ]
            
            end_time = datetime.utcnow()
            start_time = end_time - timedelta(days=period_days)
            
            metrics_data = self.monitor_client.metrics.list(
                resource_uri=nic_id,
                timespan=f"{start_time.isoformat()}/{end_time.isoformat()}",
                interval="PT1H",
                metricnames=",".join(metric_names),
                aggregation="Total"
            )
            
            total_in = 0
            total_out = 0
            data_points = 0
            last_activity = None
            
            for metric in metrics_data.value:
                if metric.timeseries:
                    for timeseries in metric.timeseries:
                        for data_point in timeseries.data:
                            if data_point.total and data_point.total > 0:
                                data_points += 1
                                if not last_activity or data_point.time_stamp > last_activity:
                                    last_activity = data_point.time_stamp
                                
                                if "Network In" in metric.name.value:
                                    total_in += data_point.total
                                elif "Network Out" in metric.name.value:
                                    total_out += data_point.total
            
            if data_points > 0:
                usage_analysis.has_recent_activity = True
                usage_analysis.last_activity_date = last_activity
                usage_analysis.average_throughput_mbps = ((total_in + total_out) / data_points) / (1024 * 1024)
                usage_analysis.activity_score = min(1.0, (total_in + total_out) / 1000000000.0)  # 1GB threshold
                usage_analysis.usage_trend = "active" if (total_in + total_out) > 100000000 else "low"  # 100MB threshold
            else:
                usage_analysis.has_recent_activity = False
                usage_analysis.activity_score = 0.0
                usage_analysis.usage_trend = "no_activity"
                
        except Exception as e:
            self.logger.error(f"Failed to analyze network interface usage: {e}")
        
        return usage_analysis