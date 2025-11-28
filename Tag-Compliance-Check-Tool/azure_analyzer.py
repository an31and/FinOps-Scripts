"""
Azure Analyzer Module

Handles all Azure API interactions, authentication, and resource analysis
for the Azure Tagging Analysis Tool.
"""

import logging
import requests
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Dict, List, Optional, Tuple
from tqdm import tqdm

from azure.core.exceptions import AzureError
from azure.identity import DefaultAzureCredential

from config_manager import Config
from data_models import TagData, ResourceGroupTagData, SubscriptionInfo
from tag_variations import TagVariationMatcher
from constants import TagComplianceStatus
from utils import sanitize_for_excel

logger = logging.getLogger(__name__)


class AzureTagAnalyzer:
    """Enhanced Azure tag analysis with tag variation support"""
    
    def __init__(self, config: Config):
        self.config = config
        self.tag_matcher = TagVariationMatcher(config.tag_variations)
        self.credential = None
        self.access_token = None
        self.session = requests.Session()
        self._setup_session()
        
    def _setup_session(self):
        """Setup requests session with retry strategy"""
        from requests.adapters import HTTPAdapter
        from urllib3.util.retry import Retry
        
        retry_strategy = Retry(
            total=3,
            backoff_factor=1,
            status_forcelist=[429, 500, 502, 503, 504],
        )
        adapter = HTTPAdapter(max_retries=retry_strategy)
        self.session.mount("http://", adapter)
        self.session.mount("https://", adapter)
    
    def get_access_token(self) -> str:
        """Get Azure access token with error handling"""
        try:
            if not self.credential:
                self.credential = DefaultAzureCredential()
            
            token = self.credential.get_token("https://management.azure.com/.default")
            self.access_token = token.token
            logger.info("Successfully obtained Azure access token")
            return self.access_token
            
        except AzureError as e:
            logger.error(f"Failed to get Azure credentials: {e}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error getting credentials: {e}")
            raise
    
    def _make_api_request(self, url: str, timeout: int = None) -> Optional[Dict]:
        """Make authenticated API request with error handling"""
        if not self.access_token:
            self.get_access_token()
            
        headers = {
            "Authorization": f"Bearer {self.access_token}",
            "Content-Type": "application/json",
        }
        
        try:
            response = self.session.get(
                url, 
                headers=headers, 
                timeout=timeout or self.config.timeout
            )
            response.raise_for_status()
            return response.json()
            
        except requests.exceptions.Timeout:
            logger.error(f"Request timeout for URL: {url}")
            return None
        except requests.exceptions.RequestException as e:
            logger.error(f"API request failed for {url}: {e}")
            return None
    
    def get_subscription_info(self, subscription_id: str) -> SubscriptionInfo:
        """Get subscription information"""
        url = f"https://management.azure.com/subscriptions/{subscription_id}"
        params = {"api-version": "2021-01-01"}
        
        response_data = self._make_api_request(f"{url}?{requests.compat.urlencode(params)}")
        
        if response_data:
            return SubscriptionInfo(
                id=subscription_id,
                name=response_data.get("displayName", "Unknown")
            )
        else:
            logger.warning(f"Could not get info for subscription {subscription_id}")
            return SubscriptionInfo(id=subscription_id, name="Unknown")
    
    def get_all_subscriptions(self) -> List[SubscriptionInfo]:
        """Get all available subscriptions (excluding excluded ones)"""
        url = "https://management.azure.com/subscriptions"
        params = {"api-version": "2021-01-01"}
        
        response_data = self._make_api_request(f"{url}?{requests.compat.urlencode(params)}")
        
        if not response_data:
            logger.error("Failed to get subscriptions")
            return []
        
        subscriptions = []
        for sub in response_data.get("value", []):
            sub_id = sub.get("subscriptionId")
            sub_name = sub.get("displayName", "Unknown")
            
            # Skip excluded subscriptions
            if sub_id not in self.config.excluded_subscription_ids:
                subscriptions.append(SubscriptionInfo(id=sub_id, name=sub_name))
            else:
                logger.info(f"Excluding subscription: {sub_name} ({sub_id})")
        
        logger.info(f"Found {len(subscriptions)} subscriptions (after exclusions)")
        return subscriptions
    
    def get_resource_tags(self, subscription_id: str, subscription_name: str) -> Tuple[List[TagData], int, int, int, int]:
        """Get resource tags for a subscription with enhanced compliance tracking, supporting pagination"""
        url = f"https://management.azure.com/subscriptions/{subscription_id}/resources"
        params = {"api-version": self.config.api_version}
        all_resources = []
        next_url = f"{url}?{requests.compat.urlencode(params)}"
        while next_url:
            response_data = self._make_api_request(next_url)
            if not response_data:
                break
            resources = response_data.get("value", [])
            all_resources.extend(resources)
            next_url = response_data.get("nextLink")
        if not all_resources:
            return [], 0, 0, 0, 0
        tag_data = []
        tagged_count = 0
        mandatory_compliant_count = 0
        mandatory_partial_count = 0
        for resource in all_resources:
            resource_name = sanitize_for_excel(resource.get("name", "")).replace(",", " ")
            resource_id = sanitize_for_excel(resource.get("id", ""))
            resource_type = sanitize_for_excel(resource.get("type", ""))
            resource_location = sanitize_for_excel(resource.get("location", ""))
            resource_tags = resource.get("tags", {})
            # Skip excluded resource types
            if resource_type in self.config.exclude_resource_types:
                continue
            # Check if resource has any tags
            has_tags = bool(resource_tags)
            if has_tags:
                tagged_count += 1
            # Check mandatory tag compliance with variations
            full_compliance = True
            partial_compliance = False
            for mandatory_tag in self.config.mandatory_tags:
                if mandatory_tag == "NONE":
                    continue
                compliance_status, variation_matched = self.tag_matcher.is_mandatory_tag_present(
                    resource_tags, mandatory_tag
                )
                if compliance_status == TagComplianceStatus.NON_COMPLIANT:
                    full_compliance = False
                    tag_data.append(TagData(
                        name=sanitize_for_excel(mandatory_tag),
                        value="missing_mandatory_tag",
                        resource_name=resource_name,
                        resource_type=resource_type,
                        resource_id=resource_id,
                        resource_location=resource_location,
                        subscription_name=sanitize_for_excel(subscription_name),
                        subscription_id=subscription_id,
                        is_mandatory_missing=True,
                        compliance_status=TagComplianceStatus.NON_COMPLIANT,
                        canonical_tag_name=sanitize_for_excel(mandatory_tag),
                        all_resource_tags=resource_tags
                    ))
                elif compliance_status == TagComplianceStatus.PARTIAL:
                    full_compliance = False
                    partial_compliance = True
            # Count compliance levels
            if full_compliance and self.config.mandatory_tags != ["NONE"]:
                mandatory_compliant_count += 1
            elif partial_compliance:
                mandatory_partial_count += 1
            # Process existing tags with variation detection
            if resource_tags:
                for tag_name, tag_value in resource_tags.items():
                    clean_value = sanitize_for_excel(str(tag_value)).replace(",", " ").replace('"', " ")
                    canonical_name, compliance_status, variation_matched = self.tag_matcher.match_tag(tag_name)
                    tag_data.append(TagData(
                        name=sanitize_for_excel(tag_name),
                        value=clean_value,
                        resource_name=resource_name,
                        resource_type=resource_type,
                        resource_id=resource_id,
                        resource_location=resource_location,
                        subscription_name=sanitize_for_excel(subscription_name),
                        subscription_id=subscription_id,
                        compliance_status=compliance_status,
                        canonical_tag_name=sanitize_for_excel(canonical_name or tag_name),
                        variation_matched=sanitize_for_excel(variation_matched),
                        all_resource_tags=resource_tags
                    ))
            else:
                tag_data.append(TagData(
                    name="untagged",
                    value="novalue",
                    resource_name=resource_name,
                    resource_type=resource_type,
                    resource_id=resource_id,
                    resource_location=resource_location,
                    subscription_name=sanitize_for_excel(subscription_name),
                    subscription_id=subscription_id,
                    is_untagged=True,
                    compliance_status=TagComplianceStatus.NON_COMPLIANT,
                    all_resource_tags={}
                ))
        return tag_data, len(all_resources), tagged_count, mandatory_compliant_count, mandatory_partial_count
    
    def get_resource_group_tags(self, subscription_id: str, subscription_name: str) -> Tuple[List[ResourceGroupTagData], int, int]:
        """Get resource group tags for a subscription with variation detection"""
        url = f"https://management.azure.com/subscriptions/{subscription_id}/resourcegroups"
        params = {"api-version": self.config.api_version}
        
        response_data = self._make_api_request(f"{url}?{requests.compat.urlencode(params)}")
        
        if not response_data:
            return [], 0, 0
        
        rg_tag_data = []
        resource_groups = response_data.get("value", [])
        tagged_rg_count = 0
        
        for rg in resource_groups:
            rg_name = sanitize_for_excel(rg.get("name", "")).replace(",", " ")
            rg_id = sanitize_for_excel(rg.get("id", ""))
            rg_tags = rg.get("tags", {})
            
            # Check if RG has tags
            if rg_tags:
                tagged_rg_count += 1
                for tag_name, tag_value in rg_tags.items():
                    clean_value = sanitize_for_excel(str(tag_value)).replace(",", " ").replace('"', " ")
                    canonical_name, compliance_status, variation_matched = self.tag_matcher.match_tag(tag_name)
                    
                    rg_tag_data.append(ResourceGroupTagData(
                        name=sanitize_for_excel(tag_name),
                        value=clean_value,
                        resource_name=rg_name,
                        resource_id=rg_id,
                        subscription_name=sanitize_for_excel(subscription_name),
                        subscription_id=subscription_id,
                        compliance_status=compliance_status,
                        canonical_tag_name=sanitize_for_excel(canonical_name or tag_name),
                        variation_matched=sanitize_for_excel(variation_matched)
                    ))
            else:
                rg_tag_data.append(ResourceGroupTagData(
                    name="untagged",
                    value="novalue",
                    resource_name=rg_name,
                    resource_id=rg_id,
                    subscription_name=sanitize_for_excel(subscription_name),
                    subscription_id=subscription_id,
                    is_untagged=True,
                    compliance_status=TagComplianceStatus.NON_COMPLIANT
                ))
        
        return rg_tag_data, len(resource_groups), tagged_rg_count
    
    def process_subscription(self, subscription_info: SubscriptionInfo) -> Tuple[List[TagData], List[ResourceGroupTagData], SubscriptionInfo]:
        """Process a single subscription with enhanced compliance metrics"""
        logger.info(f"Processing subscription: {subscription_info.name} ({subscription_info.id})")
        
        try:
            resource_tags, resource_count, tagged_resources, mandatory_compliant, mandatory_partial = self.get_resource_tags(
                subscription_info.id, subscription_info.name
            )
            rg_tags, rg_count, tagged_rgs = self.get_resource_group_tags(
                subscription_info.id, subscription_info.name
            )
            
            subscription_info.resource_count = resource_count
            subscription_info.rg_count = rg_count
            subscription_info.tagged_resources = tagged_resources
            subscription_info.tagged_rgs = tagged_rgs
            subscription_info.mandatory_compliant_resources = mandatory_compliant
            subscription_info.mandatory_partial_resources = mandatory_partial
            
            logger.info(f"Completed subscription {subscription_info.name}: "
                       f"{resource_count} resources ({subscription_info.resource_tagging_percentage:.1f}% tagged), "
                       f"{rg_count} resource groups ({subscription_info.rg_tagging_percentage:.1f}% tagged), "
                       f"Compliance: {subscription_info.mandatory_compliance_percentage:.1f}% full, "
                       f"{subscription_info.mandatory_partial_percentage:.1f}% partial")
            return resource_tags, rg_tags, subscription_info
            
        except Exception as e:
            logger.error(f"Error processing subscription {subscription_info.id}: {e}")
            return [], [], subscription_info
    
    def analyze_subscriptions(self) -> Tuple[List[TagData], List[ResourceGroupTagData], List[SubscriptionInfo]]:
        """Analyze all subscriptions with parallel processing"""
        # Get subscriptions to process
        if self.config.subscription_ids:
            subscriptions = [self.get_subscription_info(sub_id) for sub_id in self.config.subscription_ids 
                           if sub_id not in self.config.excluded_subscription_ids]
        else:
            subscriptions = self.get_all_subscriptions()
        
        if not subscriptions:
            logger.error("No subscriptions found to process")
            return [], [], []
        
        all_resource_tags = []
        all_rg_tags = []
        processed_subscriptions = []
        
        # Process subscriptions in parallel
        with ThreadPoolExecutor(max_workers=self.config.max_workers) as executor:
            future_to_subscription = {
                executor.submit(self.process_subscription, sub): sub 
                for sub in subscriptions
            }
            
            with tqdm(total=len(subscriptions), desc="Processing subscriptions") as pbar:
                for future in as_completed(future_to_subscription):
                    resource_tags, rg_tags, sub_info = future.result()
                    all_resource_tags.extend(resource_tags)
                    all_rg_tags.extend(rg_tags)
                    processed_subscriptions.append(sub_info)
                    pbar.update(1)
        
        return all_resource_tags, all_rg_tags, processed_subscriptions
