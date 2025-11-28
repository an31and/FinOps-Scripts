"""
Tag Variations Module

Handles tag variation definitions, matching, and normalization logic
for the Azure Tagging Analysis Tool.
"""

import re
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple
from constants import TagComplianceStatus

# Optional fuzzy matching import
try:
    from fuzzywuzzy import fuzz
    FUZZY_AVAILABLE = True
except ImportError:
    FUZZY_AVAILABLE = False


@dataclass
class TagVariation:
    """Tag variation configuration"""
    canonical_name: str
    variations: List[str] = field(default_factory=list)
    fuzzy_threshold: int = 85
    case_sensitive: bool = False


class TagVariationMatcher:
    """Handles tag variation matching and normalization"""
    
    def __init__(self, tag_variations: Dict[str, TagVariation]):
        self.tag_variations = tag_variations
        self._build_lookup_table()
    
    def _build_lookup_table(self):
        """Build efficient lookup table for tag matching"""
        self.exact_lookup = {}
        self.case_insensitive_lookup = {}
        
        for canonical, variation_config in self.tag_variations.items():
            # Add canonical name
            if variation_config.case_sensitive:
                self.exact_lookup[canonical] = (canonical, canonical, TagComplianceStatus.COMPLIANT)
            else:
                self.case_insensitive_lookup[canonical.lower()] = (canonical, canonical, TagComplianceStatus.COMPLIANT)
            
            # Add variations
            for variation in variation_config.variations:
                if variation_config.case_sensitive:
                    self.exact_lookup[variation] = (canonical, variation, TagComplianceStatus.PARTIAL)
                else:
                    self.case_insensitive_lookup[variation.lower()] = (canonical, variation, TagComplianceStatus.PARTIAL)
    
    def normalize_tag_name(self, tag_name: str) -> str:
        """Normalize tag name by removing separators and standardizing format"""
        # Remove common separators and normalize
        normalized = re.sub(r'[-_\s]+', '', tag_name.lower())
        return normalized
    
    def match_tag(self, tag_name: str) -> Tuple[Optional[str], str, str]:
        """
        Match a tag name against known variations
        Returns: (canonical_name, compliance_status, variation_matched)
        """
        # Exact match (case-sensitive)
        if tag_name in self.exact_lookup:
            canonical, variation, status = self.exact_lookup[tag_name]
            return canonical, status, variation
        
        # Case-insensitive match
        if tag_name.lower() in self.case_insensitive_lookup:
            canonical, variation, status = self.case_insensitive_lookup[tag_name.lower()]
            return canonical, status, variation
        
        # Normalized separator-insensitive match
        normalized_input = self.normalize_tag_name(tag_name)
        for canonical, variation_config in self.tag_variations.items():
            # Check canonical name
            if self.normalize_tag_name(canonical) == normalized_input:
                return canonical, TagComplianceStatus.PARTIAL, tag_name
            
            # Check variations
            for variation in variation_config.variations:
                if self.normalize_tag_name(variation) == normalized_input:
                    return canonical, TagComplianceStatus.PARTIAL, tag_name
        
        # Fuzzy matching (if available)
        if FUZZY_AVAILABLE:
            best_match = None
            best_score = 0
            best_canonical = None
            
            for canonical, variation_config in self.tag_variations.items():
                # Check against canonical name
                score = fuzz.ratio(tag_name.lower(), canonical.lower())
                if score > best_score and score >= variation_config.fuzzy_threshold:
                    best_score = score
                    best_match = canonical
                    best_canonical = canonical
                
                # Check against variations
                for variation in variation_config.variations:
                    score = fuzz.ratio(tag_name.lower(), variation.lower())
                    if score > best_score and score >= variation_config.fuzzy_threshold:
                        best_score = score
                        best_match = variation
                        best_canonical = canonical
            
            if best_match:
                return best_canonical, TagComplianceStatus.PARTIAL, tag_name
        
        return None, TagComplianceStatus.NON_COMPLIANT, tag_name
    
    def is_mandatory_tag_present(self, resource_tags: Dict[str, str], mandatory_tag: str) -> Tuple[str, str]:
        """
        Check if a mandatory tag is present (including variations)
        Returns: (compliance_status, variation_matched)
        """
        for tag_name in resource_tags.keys():
            canonical, status, variation = self.match_tag(tag_name)
            if canonical == mandatory_tag:
                return status, variation
        
        return TagComplianceStatus.NON_COMPLIANT, ""


def create_default_tag_variations() -> Dict[str, TagVariation]:
    """Create default tag variations for common scenarios"""
    default_variations = {
        "Environment": TagVariation(
            canonical_name="Environment",
            variations=["Env", "env", "environment", "ENVIRONMENT", "Stage", "stage"],
            fuzzy_threshold=80,
            case_sensitive=False
        ),
        "CostCenter": TagVariation(
            canonical_name="CostCenter",
            variations=["Cost_Center", "cost-center", "costcenter", "COSTCENTER", "CC", "BillingCenter"],
            fuzzy_threshold=80,
            case_sensitive=False
        ),
        "Owner": TagVariation(
            canonical_name="Owner",
            variations=["owner", "OWNER", "ResourceOwner", "resource-owner", "CreatedBy"],
            fuzzy_threshold=80,
            case_sensitive=False
        ),
        "Project": TagVariation(
            canonical_name="Project",
            variations=["project", "PROJECT", "ProjectName", "project-name", "Application"],
            fuzzy_threshold=80,
            case_sensitive=False
        )
    }
    return default_variations
