"""Authentication manager for Azure services"""

import os
import logging
import subprocess
from typing import Dict, List, Optional, Any

try:
    from azure.identity import (
        DefaultAzureCredential, 
        AzureCliCredential, 
        ClientSecretCredential,
        EnvironmentCredential
    )
    from azure.mgmt.resource import ResourceManagementClient
    from azure.mgmt.compute import ComputeManagementClient
    from azure.mgmt.network import NetworkManagementClient
    from azure.mgmt.storage import StorageManagementClient
    from azure.mgmt.monitor import MonitorManagementClient
    from azure.mgmt.subscription import SubscriptionClient
    from azure.core.exceptions import ClientAuthenticationError
except ImportError as e:
    raise ImportError(f"Required Azure SDK packages not installed: {e}")

from ..utils.logger import setup_logger


class AuthenticationManager:
    """Manages Azure authentication and client creation"""
    
    def __init__(self):
        self.logger = setup_logger(self.__class__.__name__)
        self.credential = None
        self._subscription_cache = {}
        self._client_cache = {}
    
    async def authenticate(self, **kwargs) -> bool:
        """Authenticate with Azure using various methods"""
        
        # Try environment variables first
        if all(os.getenv(var) for var in ['AZURE_TENANT_ID', 'AZURE_CLIENT_ID', 'AZURE_CLIENT_SECRET']):
            try:
                self.credential = EnvironmentCredential()
                await self._test_credential()
                self.logger.info("Authenticated using environment variables")
                return True
            except Exception as e:
                self.logger.debug(f"Environment credential failed: {e}")
        
        # Try Azure CLI
        try:
            self.credential = AzureCliCredential()
            await self._test_credential()
            self.logger.info("Authenticated using Azure CLI")
            return True
        except Exception as e:
            self.logger.debug(f"Azure CLI authentication failed: {e}")
        
        # Try default credential chain
        try:
            self.credential = DefaultAzureCredential()
            await self._test_credential()
            self.logger.info("Authenticated using default credential chain")
            return True
        except Exception as e:
            self.logger.error(f"Default authentication failed: {e}")
        
        raise ClientAuthenticationError("Unable to authenticate with Azure")
    
    def get_credential(self):
        """Get the current credential, initializing if needed"""
        if not self.credential:
            try:
                # Try Azure CLI first as it's most commonly used
                self.credential = AzureCliCredential()
                # Quick test to ensure it works
                subscription_client = SubscriptionClient(self.credential)
                list(subscription_client.subscriptions.list())
                self.logger.info("Credential initialized using Azure CLI")
            except Exception as e:
                self.logger.debug(f"Azure CLI credential failed: {e}")
                try:
                    # Fallback to default credential chain
                    self.credential = DefaultAzureCredential()
                    subscription_client = SubscriptionClient(self.credential)
                    list(subscription_client.subscriptions.list())
                    self.logger.info("Credential initialized using default credential chain")
                except Exception as e2:
                    self.logger.error(f"Failed to initialize credential: {e2}")
                    self.credential = None
        
        return self.credential
    
    async def _test_credential(self):
        """Test the credential by listing subscriptions"""
        subscription_client = SubscriptionClient(self.credential)
        list(subscription_client.subscriptions.list())
    
    async def get_accessible_subscriptions(self) -> List[str]:
        """Get list of accessible subscription IDs"""
        
        if not self.credential:
            await self.authenticate()
        
        try:
            subscription_client = SubscriptionClient(self.credential)
            subscriptions = list(subscription_client.subscriptions.list())
            
            subscription_ids = []
            for sub in subscriptions:
                if sub.state == 'Enabled':
                    subscription_ids.append(sub.subscription_id)
                    self._subscription_cache[sub.subscription_id] = sub.display_name
                    self.logger.debug(f"Found subscription: {sub.display_name} ({sub.subscription_id})")
            
            self.logger.info(f"Found {len(subscription_ids)} enabled subscriptions")
            return subscription_ids
            
        except Exception as e:
            self.logger.error(f"Failed to list subscriptions: {e}")
            return await self._get_subscriptions_from_cli()
    
    async def _get_subscriptions_from_cli(self) -> List[str]:
        """Fallback: Get subscriptions using Azure CLI"""
        
        try:
            result = subprocess.run(
                ['az', 'account', 'list', '--query', '[?state==`Enabled`].id', '-o', 'tsv'],
                capture_output=True, text=True, check=True
            )
            
            subscription_ids = [sub.strip() for sub in result.stdout.strip().split('\n') if sub.strip()]
            
            if subscription_ids:
                self.logger.info(f"Found {len(subscription_ids)} subscriptions via Azure CLI")
                return subscription_ids
            else:
                current_result = subprocess.run(
                    ['az', 'account', 'show', '--query', 'id', '-o', 'tsv'],
                    capture_output=True, text=True, check=True
                )
                current_sub = current_result.stdout.strip()
                self.logger.info(f"Using current subscription: {current_sub}")
                return [current_sub]
                
        except subprocess.CalledProcessError as e:
            self.logger.error(f"Azure CLI failed: {e}")
            raise Exception("Unable to determine subscriptions. Please ensure Azure CLI is installed and you're logged in.")
        except Exception as e:
            self.logger.error(f"Failed to get subscriptions: {e}")
            raise
    
    async def get_clients_for_subscription(self, subscription_id: str) -> Dict[str, Any]:
        """Get Azure service clients for a subscription"""
        
        if not self.credential:
            await self.authenticate()
        
        cache_key = subscription_id
        if cache_key in self._client_cache:
            return self._client_cache[cache_key]
        
        try:
            clients = {
                'resource': ResourceManagementClient(self.credential, subscription_id),
                'compute': ComputeManagementClient(self.credential, subscription_id),
                'network': NetworkManagementClient(self.credential, subscription_id),
                'storage': StorageManagementClient(self.credential, subscription_id),
                'monitor': MonitorManagementClient(self.credential, subscription_id),
            }
            
            # Test access by listing resource groups
            list(clients['resource'].resource_groups.list())
            
            self._client_cache[cache_key] = clients
            self.logger.debug(f"Created clients for subscription {subscription_id}")
            
            return clients
            
        except Exception as e:
            self.logger.error(f"Failed to create clients for subscription {subscription_id}: {e}")
            raise
    
    async def get_subscription_name(self, subscription_id: str) -> str:
        """Get subscription display name"""
        return self._subscription_cache.get(subscription_id, subscription_id[:8] + "...")