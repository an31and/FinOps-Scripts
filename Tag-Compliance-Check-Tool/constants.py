"""
Constants and Configuration Classes

Contains all constants, thresholds, and enumeration classes used throughout
the Azure Tagging Analysis Tool.
"""

class ColorThresholds:
    """Color thresholds for percentage-based formatting"""
    EXCELLENT = 90  # Dark Green
    GOOD = 70      # Green
    FAIR = 40      # Yellow/Orange
    POOR = 0       # Red


class TagComplianceStatus:
    """Tag compliance status enumeration"""
    COMPLIANT = "compliant"
    PARTIAL = "partial"
    NON_COMPLIANT = "non_compliant"


# Azure resource types that don't support tagging
NON_TAGGABLE_RESOURCE_TYPES = {
    # Compute
    "microsoft.compute/virtualmachines/extensions",
    "microsoft.compute/restorepointcollections/restorepoints",
    
    # Storage
    "microsoft.storage/storageaccounts/blobservices",
    "microsoft.storage/storageaccounts/fileservices",
    "microsoft.storage/storageaccounts/queueservices",
    "microsoft.storage/storageaccounts/tableservices",
    "microsoft.storage/storageaccounts/blobservices/containers",
    
    # Network
    "microsoft.network/virtualnetworks/subnets",
    "microsoft.network/networksecuritygroups/securityrules",
    "microsoft.network/routetables/routes",
    "microsoft.network/virtualnetworkgateways/connections",
    
    # Key Vault
    "microsoft.keyvault/vaults/secrets",
    "microsoft.keyvault/vaults/keys",
    "microsoft.keyvault/vaults/certificates",
    
    # SQL
    "microsoft.sql/servers/databases/transparentdataencryption",
    "microsoft.sql/servers/databases/backupshorttermretentionpolicies",
    "microsoft.sql/servers/databases/geobackuppolicies",
    "microsoft.sql/servers/databases/advisors",
    "microsoft.sql/servers/databases/syncgroups",
    "microsoft.sql/servers/databases/syncmembers",
    
    # App Service
    "microsoft.web/sites/config",
    "microsoft.web/sites/deployments",
    "microsoft.web/sites/sourcecontrols",
    "microsoft.web/sites/hostnamebindings",
    "microsoft.web/serverfarms/virtualnetworkconnections",
    
    # Monitor
    "microsoft.insights/diagnosticsettings",
    "microsoft.insights/metricalerts",
    "microsoft.insights/scheduledqueryrules",
    "microsoft.insights/actiongroups",
    "microsoft.insights/activitylogalerts",
    "microsoft.insights/components/analyticsitems",
    "microsoft.insights/components/myanalyticsitems",
    
    # Authorization
    "microsoft.authorization/roleassignments",
    "microsoft.authorization/roledefinitions",
    "microsoft.authorization/policyassignments",
    "microsoft.authorization/policydefinitions",
    "microsoft.authorization/policysetdefinitions",
    
    # Management
    "microsoft.managementgroups/managementgroups",
    "microsoft.resources/deployments",
    "microsoft.resources/deployments/operations",
    
    # Other
    "microsoft.operationalinsights/workspaces/datasources",
    "microsoft.operationalinsights/workspaces/linkedservices",
    "microsoft.operationalinsights/workspaces/savedSearches",
    "microsoft.automation/automationaccounts/runbooks",
    "microsoft.automation/automationaccounts/jobs",
    "microsoft.automation/automationaccounts/jobschedules",
    "microsoft.servicebus/namespaces/queues",
    "microsoft.servicebus/namespaces/topics",
    "microsoft.servicebus/namespaces/topics/subscriptions",
    "microsoft.eventhub/namespaces/eventhubs",
    "microsoft.eventhub/namespaces/eventhubs/consumergroups",
    "microsoft.containerservice/managedclusters/agentpools",
}
