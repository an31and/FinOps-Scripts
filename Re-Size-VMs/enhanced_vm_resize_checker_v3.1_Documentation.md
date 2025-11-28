# Enhanced VM Resize Compatibility Checker v3.1

## Overview
This PowerShell script provides a comprehensive solution for Azure VM resize compatibility checks, alternative recommendations, and cost analysis. It is designed for use in Azure Cloud Shell, Azure Automation, or local PowerShell environments.

## Key Features
- **Compatibility Checks:** Evaluates if VMs can be resized to recommended sizes, considering disk, storage, networking, and security requirements.
- **Alternative Recommendations:** Suggests up to 3 alternative VM sizes per VM, based on similarity and Azure best practices.
- **Retiring/Retired Series Detection:** Identifies VMs running on series that are retired or announced for retirement, with migration suggestions.
- **Cost Analysis:** Compares current and recommended VM sizes for hourly and monthly costs, including potential savings.
- **Flexible Input/Output:** Supports input from local files or Azure Storage blobs, and outputs results to CSV or Excel (with ImportExcel module).
- **Parallel Processing:** Supports parallel batch processing for large datasets (except in Automation/Cloud Shell).
- **Cloud Shell & Automation Ready:** Detects environment and adapts behavior for compatibility.
- **Robust Error Handling:** Handles API errors, missing data, and logs warnings for failed operations.

## Parameters
- `InputSource` (File/Blob): Source of input data (CSV of recommendations).
- `InputPath`: Path to input file or blob.
- `OutputPath`: Path for output file or blob (auto-generated if not specified).
- `StorageAccountKey`: Key for blob operations (optional if using Automation variables).
- `ProductionSubscriptionIds`: List of production subscription IDs for tagging.
- `ExcludeDtoBResize`: Exclude D-series to B-series resize recommendations.
- `ExcludeResourceGroups`: Patterns for resource groups to exclude.
- `MaxParallelJobs`: Number of parallel jobs (interactive mode only).
- `DetailedCheck`: Enable detailed compatibility checks.
- `ShowSavings`: Include savings columns from input.
- `EmailRecipients`: For Automation email notifications.
- `UseImportExcel`: Force Excel output (if ImportExcel module is available).
- `IncludeAlternatives`: Include alternative VM size recommendations.
- `IncludeCostAnalysis`: Include cost analysis columns.
- `MaxAlternatives`: Number of alternative recommendations per VM.
- `Skip*Check`: Skip specific compatibility checks (data disk, premium storage, etc.).

## How It Works
1. **Initialization:** Detects environment, parses parameters, and sets up caches.
2. **Input Loading:** Reads recommendations from file or blob.
3. **Processing:** For each VM:
   - Retrieves VM details and capabilities.
   - Checks compatibility with recommended size.
   - Suggests alternatives and calculates costs.
   - Detects if VM is on a retiring/retired series.
4. **Output:** Results are saved to CSV or Excel, with summary and cost analysis.
5. **Summary:** Prints a summary of results, including compatibility, errors, and cost savings.

## Output Columns
- SubscriptionId, SubscriptionName, IsProduction
- ResourceGroup, VMName
- CurrentVMSize, CurrentVMCategory
- RecommendedVMSize, RecommendedVMCategory
- DataDisks, TotalDisks, MaxDataDisksSupported
- PremiumStorageSupported, IsFullyCompatible, Issues, Warnings
- RetirementStatus, RetirementInfo, RecommendedReplacements
- CurrentHourlyRate, CurrentMonthlyRate, RecommendedHourlyRate, RecommendedMonthlyRate, MonthlySavings, Currency
- Alternative1/2/3_Size, _vCPUs, _Memory, _Score, _MonthlyRate
- CheckedAt

## Usage Examples
**Cloud Shell:**
```
./Check-VMResizeCompatibility.ps1 -InputSource "File" -InputPath "./recommendations.csv" -IncludeAlternatives $true -IncludeCostAnalysis $true
```
**Azure Automation:**
```
./Check-VMResizeCompatibility.ps1 -InputSource "Blob" -InputPath "storage/container/input.csv" -StorageAccountKey $key -IncludeAlternatives $true -IncludeCostAnalysis $true
```

## Best Practices
- Ensure you have the necessary Azure permissions to read VM and pricing data.
- For large datasets, use parallel processing in local PowerShell for better performance.
- Use the ImportExcel module for Excel output if available.
- Regularly update the script to keep up with Azure VM series retirements and pricing API changes.

## Troubleshooting
- **API Errors:** The script logs warnings for failed API calls and continues processing other VMs.
- **Missing Pricing:** If pricing is not found, the script sets rates to 0 and logs a warning.
- **Invalid Input:** The script checks for valid input formats and throws errors if not met.

## Author
Anand Lakhera (Enhanced Version)

---
_Last updated: July 2, 2025_
