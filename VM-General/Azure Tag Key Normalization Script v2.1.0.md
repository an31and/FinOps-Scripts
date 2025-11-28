# Azure Tag Key Normalization Script v2.1.0

**Enterprise-grade PowerShell script for normalizing Azure resource tag key variations across 17 Azure subscriptions with advanced resumability and comprehensive logging.**

## 🎯 Overview

This script scans resources across 17 Azure subscriptions and resource groups to normalize common tag key variations to canonical tag keys (e.g., 'env' → 'Environment', 'cost center' → 'Cost_Center'). It's designed for large-scale enterprise environments with robust fault tolerance and Cloud Shell compatibility.

## ✨ Key Features

### 🔄 **Advanced Resumability**
- **Cross-day resumability** in Azure Cloud Shell environments
- **Subscription-level completion tracking** (resumes incomplete subscriptions only)
- **Resource-group and resource-level progress tracking**
- **Automatic periodic uploads** to Azure Storage for fault tolerance
- **Cloud Shell timeout-resistant** with frequent progress saves

### 📊 **Multi-Subscription Processing**
- Process multiple Azure subscriptions in a single run
- **Per-subscription or global tracking modes**
- **Intelligent resume capability** - skips completed subscriptions
- **Subscription isolation** - failures in one subscription don't affect others

### 🔍 **Comprehensive Logging**
- **Dual CSV output system** - master file + optional per-subscription files
- **Automatic Azure Storage upload** for both master and per-subscription CSV files
- **Detailed audit trail** with before/after tag snapshots
- **Color-coded console output** with different log levels
- **Change preview analysis** showing exactly what will be modified
- **Conflict detection** for overlapping tag keys

### 🛡️ **Safety & Performance**
- **Dry-run preview mode** to validate changes before execution
- **Batch processing** with retry logic and throttling protection
- **Error handling** with configurable retry attempts
- **Data loss prevention** through comprehensive logging

## 🏗️ Architecture

```
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│   Azure Cloud   │    │   Azure Storage  │    │  Local Tracking │
│     Shell       │◄──►│   (Resumability) │◄──►│     Files       │
└─────────────────┘    └──────────────────┘    └─────────────────┘
         │                        │                       │
         ▼                        ▼                       ▼
┌─────────────────────────────────────────────────────────────────┐
│                    Tag Normalization Engine                     │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────────┐  │
│  │Subscription │  │ Resource    │  │    Tag Variation        │  │
│  │ Processing  │  │ Group Scan  │  │    Normalization        │  │
│  └─────────────┘  └─────────────┘  └─────────────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
         │
         ▼
┌─────────────────────────────────────────────────────────────────┐
│                      CSV Audit Trail                           │
│  • Before/After Tag Snapshots  • Change Analysis              │
│  • Conflict Detection          • Performance Metrics          │
└─────────────────────────────────────────────────────────────────┘
```

## 🚀 Quick Start

### Prerequisites
- Azure PowerShell module installed
- Appropriate Azure permissions (Contributor role recommended)
- Azure Storage account for resumability (recommended for production)

### Basic Usage

1. **Configure the script variables:**
```powershell
# Basic configuration
$dryRunMode = $true  # Start with preview mode
$targetSubscriptionIds = @('your-subscription-id-1', 'your-subscription-id-2')

# Azure Storage for resumability
$storageAccountName = "yourstorageaccount"
$storageContainerName = "azuretag"
$storageAccountSubscriptionId = "storage-subscription-id"
```

2. **Run in preview mode:**
```powershell
.\Azure-TagKey-Normalization-2.1.0.ps1
```

3. **Review the CSV output** for potential conflicts and changes

4. **Run in live mode:**
```powershell
# Set $dryRunMode = $false in the script
.\Azure-TagKey-Normalization-2.1.0.ps1
```

## ⚙️ Configuration

### Core Settings

| Variable | Description | Default | Options |
|----------|-------------|---------|---------|
| `$dryRunMode` | Preview mode without making changes | `$true` | `$true`, `$false` |
| `$resetMode` | Clear all tracking and start fresh | `$false` | `$true`, `$false` |
| `$trackingMode` | How to track processed resources | `"global"` | `"global"`, `"per-subscription"` |
| `$targetSubscriptionIds` | Array of subscription IDs to process | Required | Array of GUIDs |
| `$targetResourceGroupNames` | Specific RGs or null for all | `$null` | Array or `$null` |

### Performance Settings

| Variable | Description | Default | Recommended |
|----------|-------------|---------|-------------|
| `$batchSize` | Resources processed per batch | `50` | `25-100` |
| `$maxRetries` | Retry attempts for failed operations | `3` | `2-5` |
| `$retryDelay` | Seconds between retries | `2` | `1-5` |
| `$uploadFrequency` | Upload progress every N resources | `10` | `5-20` |

### Tag Variations

The script normalizes these tag key variations by default:

| Variations | Normalized To |
|------------|---------------|
| `env`, `environmentid`, `enviornment`, `environemnt`, `x_environment` | `Environment` |
| `cc`, `costcenter`, `cost center` | `Cost_Center` |
| `bu`, `businessunit`, `business unit` | `Business_Unit` |
| `app`, `x_app` | `Application` |
| `portfolio group`, `portfoliogroup` | `Portfolio_Group` |
| `project number`, `proj number`, `projectnumber`, `project#` | `Project_Number` |
| `dr tier`, `disaster recovery tier`, `drtier` | `DR_Tier` |
| `data classification`, `dataclassification`, `dataclass` | `Data_Classification` |

## 📋 Usage Scenarios

### Scenario 1: First-Time Large-Scale Normalization
```powershell
# 1. Configure for your environment
$targetSubscriptionIds = @('sub1', 'sub2', 'sub3')
$dryRunMode = $true
$resetMode = $true

# 2. Run preview
.\Azure-TagKey-Normalization-2.1.0.ps1

# 3. Review CSV for conflicts
Import-Csv "dryrun_TagUpdateResults_2.1.0_*.csv" | 
    Where-Object { $_.ChangePreview -like "*REMOVE:*" }

# 4. Run live after validation
$dryRunMode = $false
.\Azure-TagKey-Normalization-2.1.0.ps1
```

### Scenario 2: Resume After Timeout
```powershell
# Script automatically resumes from where it left off
$dryRunMode = $false
$resetMode = $false  # Important: don't reset
.\Azure-TagKey-Normalization-2.1.0.ps1
```

### Scenario 3: Process Specific Resource Groups
```powershell
$targetResourceGroupNames = @('Production-RG', 'Staging-RG')
$targetSubscriptionIds = @('specific-subscription-id')
.\Azure-TagKey-Normalization-2.1.0.ps1
```

## 📊 Output Files

### CSV Audit Trail

#### Master CSV File
**Local:** `dryrun_TagUpdateResults_2.1.0_YYYYMMDD_HHMMSS.csv` (preview) or `TagUpdateResults_2.1.0_YYYYMMDD_HHMMSS.csv` (live)
**Azure Storage:** `output_TagUpdateResults_2.1.0_YYYYMMDD.csv` (automatically uploaded)

Contains comprehensive audit trail for all subscriptions processed.

#### Per-Subscription CSV Files (Optional)
**Local:** `TagUpdateResults_2.1.0_YYYYMMDD_SubscriptionId.csv`
**Azure Storage:** `per_subscription_csv/TagUpdateResults_2.1.0_YYYYMMDD_SubscriptionId.csv`

Individual CSV files for each subscription for targeted analysis. Enable with:
```powershell
$enablePerSubscriptionCsv = $true
```

**CSV Columns:**
- `Timestamp` - When the resource was processed
- `SubscriptionId` - Azure subscription ID
- `ResourceGroupName` - Resource group name
- `ResourceId` - Full Azure resource ID
- `OldTags` - Original tags in JSON format
- `NewTags` - Final tags after normalization
- `Status` - Success, Error, No Changes, Would Change
- `ChangePreview` - Detailed description of changes
- `DryRunMode` - Whether this was a preview run

### Azure Storage Organization
```
your-storage-container/
├── output_TagUpdateResults_2.1.0_YYYYMMDD.csv          # Master CSV
├── per_subscription_csv/                               # Per-subscription CSVs
│   ├── TagUpdateResults_2.1.0_YYYYMMDD_sub1.csv
│   ├── TagUpdateResults_2.1.0_YYYYMMDD_sub2.csv
│   └── ...
├── processed_subscriptions.txt                         # Tracking files
├── processed_resources_*.txt
└── processed_resource_groups_*.txt
```

### Tracking Files (Azure Storage)
- `processed_subscriptions.txt` - Completed subscriptions
- `processed_resources_*.txt` - Processed resources (per subscription or global)
- `processed_resource_groups_*.txt` - Processed resource groups

## 🔍 Monitoring & Troubleshooting

### Real-time Monitoring
The script provides color-coded console output:

- 🔴 **ERROR** - Critical errors requiring attention
- 🟡 **WARNING** - Non-critical issues or warnings
- 🟢 **SUCCESS** - Successful operations and completions
- 🟦 **STORAGE** - Azure Storage upload/download operations
- 🟣 **RESUME** - Resume and tracking operations
- 🔵 **PROGRESS** - Processing progress and status updates
- ⚪ **INFO** - General information and configuration details

### Common Issues

#### "Storage account not found"
```powershell
# Verify storage account details
$storageAccountName = "correct-storage-account-name"
$storageAccountSubscriptionId = "correct-subscription-id"
$resourceGroupForStorage = "correct-resource-group"
```

#### "Subscription not accessible"
```powershell
# Check Azure context and permissions
Get-AzContext
Get-AzSubscription
```

#### "Tag conflicts detected"
Review the CSV output for `REMOVE:` entries indicating potential data loss:
```powershell
Import-Csv "output.csv" | Where-Object { $_.ChangePreview -like "*REMOVE:*" }
```

### Performance Optimization

#### For Large Environments (>10k resources)
```powershell
$trackingMode = "per-subscription"  # Better isolation
$batchSize = 25                     # Smaller batches
$uploadFrequency = 5                # More frequent saves
```

#### For Small Environments (<1k resources)
```powershell
$trackingMode = "global"     # Simpler tracking
$batchSize = 100             # Larger batches
$uploadFrequency = 20        # Less frequent saves
```

## 🛡️ Data Safety & Conflict Resolution

### Conflict Scenarios

**What happens with conflicting tags:**
```
Original: { "Cost Center": "123456", "Cost_Center": "987654" }
Result:   { "Cost_Center": "987654" }  // Last processed wins
CSV Log:  "REMOVE: 'Cost Center' = '123456'"
```

### Prevention Strategies

1. **Always run in dry-run mode first**
2. **Review CSV output for REMOVE entries**
3. **Manually resolve conflicts before live run**
4. **Use specific resource group targeting for testing**

### Audit Trail Analysis
```powershell
# Find all conflicts
$conflicts = Import-Csv "output.csv" | 
    Where-Object { $_.ChangePreview -like "*REMOVE:*" }

# Analyze by tag type
$conflicts | Group-Object { 
    ($_.ChangePreview -split "REMOVE: '")[1] -split "'" | Select-Object -First 1 
} | Select-Object Name, Count
```

## 🔧 Customization

### Adding New Tag Variations
```powershell
$tagVariations += @{
    Variations = @("dept", "department", "dpt")
    NormalizedTagKey = "Department"
}
```

### Custom Storage Configuration
```powershell
# Use different storage account per environment
$storageAccountName = if ($env -eq "prod") { "prodtagstorage" } else { "devtagstorage" }
```

### Environment-Specific Settings
```powershell
# Different settings based on environment
$maxRetries = if ($targetSubscriptionIds.Count -gt 5) { 5 } else { 3 }
$batchSize = if ($totalResources -gt 10000) { 25 } else { 50 }
```

## 📈 Performance Metrics

Expected performance for 17-subscription enterprise environment:

| Environment Scale | Resources/Minute | Estimated Total Time | Per Subscription |
|------------------|------------------|---------------------|------------------|
| Small Environment (< 5k total resources) | 150-200 | 25-35 minutes | 1-2 minutes |
| Medium Environment (5k-50k total resources) | 100-150 | 45-90 minutes | 3-5 minutes |
| Large Environment (50k+ total resources) | 75-100 | 2-6 hours | 7-20 minutes |

**17-Subscription Enterprise Estimates:**
- **Conservative**: ~3,000 resources per subscription = 51k total resources = ~4-6 hours
- **Typical**: ~1,500 resources per subscription = 25k total resources = ~2-3 hours  
- **Light**: ~500 resources per subscription = 8.5k total resources = ~45-60 minutes

**Factors affecting performance:**
- Azure region latency
- Network connectivity
- Resource types and tag complexity
- Batch size and retry settings
- Cloud Shell session stability

## 🔒 Security Considerations

### Required Permissions
- **Contributor** role on target subscriptions (for tag modifications)
- **Storage Blob Data Contributor** on storage account (for resumability)

### Best Practices
- Use **Managed Identity** in production environments
- **Limit subscription scope** to minimize blast radius
- **Test in non-production** environments first
- **Review audit logs** regularly

## 📚 Advanced Features

### Multi-Tenancy Support
```powershell
# Process subscriptions across different tenants
foreach ($tenant in $tenants) {
    Connect-AzAccount -Tenant $tenant.Id
    # Run script for tenant-specific subscriptions
}
```

### Integration with Azure DevOps
```yaml
# Azure DevOps Pipeline example
- task: AzurePowerShell@5
  inputs:
    azureSubscription: 'service-connection'
    ScriptType: 'FilePath'
    ScriptPath: 'Azure-TagKey-Normalization-2.1.0.ps1'
    azurePowerShellVersion: 'LatestVersion'
```

### Scheduled Execution
```powershell
# Azure Automation Runbook
# Schedule for monthly tag normalization
param(
    [string]$SubscriptionList,
    [bool]$DryRun = $true
)
```

## 🆘 Support & Troubleshooting

### Log Analysis
```powershell
# Check detailed logs
Get-Content "$HOME/tag_normalization.log" | Select-String "ERROR"

# Monitor progress
Get-Content "$HOME/processed_resources_*.txt" | Measure-Object
```

### Common Error Resolutions

| Error | Solution |
|-------|----------|
| "Insufficient permissions" | Verify Contributor role on subscription |
| "Storage blob not found" | Check storage account configuration |
| "Resource not found" | Resource may have been deleted during processing |
| "Throttling detected" | Reduce batch size or increase retry delay |

## 📄 Version History

- **v2.1.0** - Enhanced dual CSV output system with Azure Storage uploads, expanded to 17 subscriptions, added per-subscription CSV files with configurable output options
- **v2.0.0** - Major update: Multi-subscription tracking, detailed logging, cross-day resumability, enhanced Cloud Shell support
- **v1.2.0** - Added batch processing and improved performance
- **v1.1.0** - Added basic resumability
- **v1.0.0** - Initial basic version

## 📝 License

This script is provided as-is for educational and enterprise use. Please review and test thoroughly before production deployment.

## 👤 Author

**Patrick Warnke**
**Anand Lakhera** 

---

## 🚀 Quick Reference

### Essential Commands
```powershell
# Preview run
$dryRunMode = $true; .\Azure-TagKey-Normalization-2.1.0.ps1

# Live run
$dryRunMode = $false; .\Azure-TagKey-Normalization-2.1.0.ps1

# Reset and start fresh
$resetMode = $true; .\Azure-TagKey-Normalization-2.1.0.ps1

# Check progress
Get-Content "$HOME/processed_subscriptions.txt"
```

### File Locations
- **Script:** `Azure-TagKey-Normalization-2.1.0.ps1`
- **Output CSV:** `$HOME/dryrun_TagUpdateResults_2.1.0_YYYYMMDD.csv`
- **Tracking Files:** `$HOME/processed_*.txt`
- **Storage Blobs:** Azure Storage Container specified in configuration

---
*For additional support or feature requests, please refer to the script documentation or contact the development team.*
