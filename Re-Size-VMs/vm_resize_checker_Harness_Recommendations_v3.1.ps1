#!/usr/bin/env pwsh
<#
.SYNOPSIS
    Enhanced VM Resize Compatibility Checker v3.0 - With Alternative Recommendations and Cost Analysis
.DESCRIPTION
    This enhanced script performs comprehensive VM resize compatibility checks with:
    - Alternative resize recommendations based on VM capabilities
    - Detection of retiring/retired VM series with migration suggestions
    - Cost analysis comparing current vs. recommended VM sizes
    - Support for both Azure Cloud Shell and Azure Automation
    
.AUTHOR
    Anand Lakhera (Enhanced Version)
.VERSION
    3.0 - Enhanced Edition with Alternatives and Cost Analysis
.PARAMETER InputSource
    Source of input: "File" for local file, "Blob" for Azure Storage blob
.PARAMETER InputPath
    For File: Local file path. For Blob: "StorageAccount/Container/BlobName"
.PARAMETER OutputPath
    Output path (local file or blob path). Auto-generated if not specified.
.PARAMETER StorageAccountKey
    Storage account key (required for blob operations, can use Automation variables)
.PARAMETER ProductionSubscriptionIds
    Array or comma-separated string of production subscription IDs
.PARAMETER ExcludeDtoBResize
    Switch/Boolean to exclude D-series to B-series resizes
.PARAMETER ExcludeResourceGroups
    Array of resource group patterns to exclude
.PARAMETER MaxParallelJobs
    Maximum parallel jobs (ignored in Automation, used in interactive mode)
.PARAMETER DetailedCheck
    Perform detailed compatibility checks
.PARAMETER ShowSavings
    Include savings information in output
.PARAMETER EmailRecipients
    Email addresses for notifications (Automation only)
.PARAMETER UseImportExcel
    Force Excel output in interactive mode (auto-detected)
.PARAMETER IncludeAlternatives
    Include alternative VM size recommendations
.PARAMETER IncludeCostAnalysis
    Include detailed cost analysis with hourly and monthly rates
.PARAMETER MaxAlternatives
    Maximum number of alternative recommendations per VM (default: 3)
.EXAMPLE
    # Cloud Shell with alternatives and cost analysis
    .\Check-VMResizeCompatibility.ps1 -InputSource "File" -InputPath "./recommendations.csv" -IncludeAlternatives $true -IncludeCostAnalysis $true
    
.EXAMPLE
    # Azure Automation with blob storage and all features
    .\Check-VMResizeCompatibility.ps1 -InputSource "Blob" -InputPath "storage/container/input.csv" -StorageAccountKey $key -IncludeAlternatives $true -IncludeCostAnalysis $true
#>

[CmdletBinding()]
param(
    [Parameter(Mandatory=$true)]
    [ValidateSet("File", "Blob")]
    [string]$InputSource,
    
    [Parameter(Mandatory=$true)]
    [string]$InputPath,
    
    [Parameter(Mandatory=$false)]
    [string]$OutputPath = "",
    
    [Parameter(Mandatory=$false)]
    [string]$StorageAccountKey = "",
    
    [Parameter(Mandatory=$false)]
    $ProductionSubscriptionIds = @(),
    
    [Parameter(Mandatory=$false)]
    $ExcludeDtoBResize = $false,
    
    [Parameter(Mandatory=$false)]
    $ExcludeResourceGroups = @('*sap*', '*zerto*', '*paloalto*', '*infoblox*'),
    
    [Parameter(Mandatory=$false)]
    [int]$MaxParallelJobs = 5,
    
    [Parameter(Mandatory=$false)]
    $DetailedCheck = $false,
    
    [Parameter(Mandatory=$false)]
    $ShowSavings = $false,
    
    [Parameter(Mandatory=$false)]
    [string]$EmailRecipients = "",
    
    [Parameter(Mandatory=$false)]
    $UseImportExcel = $null,
    
    # New parameters for enhanced features
    [Parameter(Mandatory=$false)]
    $IncludeAlternatives = $true,
    
    [Parameter(Mandatory=$false)]
    $IncludeCostAnalysis = $true,
    
    [Parameter(Mandatory=$false)]
    [int]$MaxAlternatives = 3,
    
    # Skip parameters
    [Parameter(Mandatory=$false)]
    $SkipDataDiskCheck = $false,
    
    [Parameter(Mandatory=$false)]
    $SkipPremiumStorageCheck = $false,
    
    [Parameter(Mandatory=$false)]
    $SkipAcceleratedNetworkingCheck = $false,
    
    [Parameter(Mandatory=$false)]
    $SkipAvailabilityZoneCheck = $false,
    
    [Parameter(Mandatory=$false)]
    $SkipTrustedLaunchCheck = $false,
    
    [Parameter(Mandatory=$false)]
    $SkipUltraDiskCheck = $false,
    
    [Parameter(Mandatory=$false)]
    $SkipOSCheck = $false
)

# Script initialization
$ErrorActionPreference = 'Continue'
$ProgressPreference = 'SilentlyContinue'
$script:StartTime = Get-Date

# Detect execution environment
$script:IsAutomation = $false
$script:IsCloudShell = $false
$script:CanUseExcel = $false

# Check if running in Azure Automation
try {
    $automationVariable = Get-AutomationVariable -Name "Test" -ErrorAction SilentlyContinue
    $script:IsAutomation = $true
    Write-Output "Detected Azure Automation environment"
} catch {
    $script:IsAutomation = $false
}

# Check if running in Cloud Shell
if ($env:AZUREPS_HOST_ENVIRONMENT -eq 'cloud-shell/1.0' -or $env:ACC_CLOUD -eq 'AzureCloud') {
    $script:IsCloudShell = $true
    Write-Host "Detected Azure Cloud Shell environment" -ForegroundColor Green
}

# Determine if we can use Excel (not in Automation)
if (-not $script:IsAutomation) {
    if ($null -eq $UseImportExcel) {
        $script:CanUseExcel = $null -ne (Get-Module -ListAvailable -Name ImportExcel)
    } else {
        $script:CanUseExcel = $UseImportExcel -and ($null -ne (Get-Module -ListAvailable -Name ImportExcel))
    }
}

Write-Host "`n===== Enhanced VM Resize Compatibility Checker v3.0 =====" -ForegroundColor Cyan
Write-Host "Author: Anand Lakhera (Enhanced Version)" -ForegroundColor Gray
Write-Host "Environment: $(if ($script:IsAutomation) { 'Azure Automation' } elseif ($script:IsCloudShell) { 'Azure Cloud Shell' } else { 'Local PowerShell' })" -ForegroundColor Gray
Write-Host "Start Time: $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')" -ForegroundColor Gray
Write-Host "Features: $(if ($IncludeAlternatives) { '✓ Alternatives' } else { '✗ Alternatives' }) | $(if ($IncludeCostAnalysis) { '✓ Cost Analysis' } else { '✗ Cost Analysis' })" -ForegroundColor Gray

# Convert parameters to consistent format
if ($ProductionSubscriptionIds -is [string] -and ![string]::IsNullOrWhiteSpace($ProductionSubscriptionIds)) {
    $ProductionSubscriptionIds = $ProductionSubscriptionIds -split ',' | ForEach-Object { $_.Trim() }
} elseif ($ProductionSubscriptionIds -isnot [array]) {
    $ProductionSubscriptionIds = @()
}

if ($ExcludeResourceGroups -is [string] -and ![string]::IsNullOrWhiteSpace($ExcludeResourceGroups)) {
    $ExcludeResourceGroups = $ExcludeResourceGroups -split ',' | ForEach-Object { $_.Trim() }
}

# Convert switch parameters for Automation compatibility
$ExcludeDtoBResize = [bool]$ExcludeDtoBResize
$DetailedCheck = [bool]$DetailedCheck
$ShowSavings = [bool]$ShowSavings
$IncludeAlternatives = [bool]$IncludeAlternatives
$IncludeCostAnalysis = [bool]$IncludeCostAnalysis

# Define retired and retiring VM series
$script:RetiredVMSeries = @{
    # Retired series (no longer available)
    'Retired' = @{
        'A0-A7' = @{
            'Status' = 'Retired'
            'RetiredDate' = '2024-08-31'
            'Replacements' = @('Dv5', 'Dasv5', 'Ddsv5', 'Dadsv5')
            'Reason' = 'Legacy hardware, limited features'
        }
        'Av1' = @{
            'Status' = 'Retired'
            'RetiredDate' = '2024-08-31'
            'Replacements' = @('Av2', 'Dv5', 'Dasv5')
            'Reason' = 'Previous generation hardware'
        }
        'Dv2' = @{
            'Status' = 'Retired'
            'RetiredDate' = '2024-08-31'
            'Replacements' = @('Dv5', 'Dasv5', 'Ddsv5')
            'Reason' = 'Previous generation, newer versions available'
        }
        'DSv2' = @{
            'Status' = 'Retired'
            'RetiredDate' = '2024-08-31'
            'Replacements' = @('Ddsv5', 'Dadsv5', 'Dsv5', 'Dasv5')
            'Reason' = 'Previous generation with premium storage'
        }
    }
    
    # Series announced for retirement
    'Announced' = @{
        'NCv3' = @{
            'Status' = 'Announced'
            'PlannedRetirement' = '2025-09-30'
            'Replacements' = @('NCasT4_v3', 'NC_A100_v4', 'NVadsA10_v5')
            'Reason' = 'NVIDIA V100 GPUs being replaced with newer models'
        }
        'NV' = @{
            'Status' = 'Announced'
            'PlannedRetirement' = '2025-12-31'
            'Replacements' = @('NVv4', 'NVadsA10_v5')
            'Reason' = 'Legacy GPU series'
        }
        'NC' = @{
            'Status' = 'Announced'
            'PlannedRetirement' = '2025-12-31'
            'Replacements' = @('NCasT4_v3', 'NC_A100_v4')
            'Reason' = 'Legacy GPU compute series'
        }
    }
    
    # Previous generation (capacity limited)
    'PreviousGen' = @{
        'Dv3' = @{
            'Status' = 'PreviousGen'
            'Replacements' = @('Dv5', 'Dasv5')
            'Reason' = 'Newer generation available with better performance'
        }
        'Dsv3' = @{
            'Status' = 'PreviousGen'
            'Replacements' = @('Dsv5', 'Dasv5')
            'Reason' = 'Newer generation available with premium storage'
        }
        'Ev3' = @{
            'Status' = 'PreviousGen'
            'Replacements' = @('Ev5', 'Easv5')
            'Reason' = 'Memory optimized newer generation available'
        }
        'Esv3' = @{
            'Status' = 'PreviousGen'
            'Replacements' = @('Esv5', 'Easv5')
            'Reason' = 'Memory optimized with premium storage newer generation'
        }
        'Fv1' = @{
            'Status' = 'PreviousGen'
            'Replacements' = @('Fv2', 'Fsv2')
            'Reason' = 'Compute optimized newer generation available'
        }
    }
}

# VM Size mapping for alternatives
$script:VMSizeCategories = @{
    'GeneralPurpose' = @{
        'Pattern' = '^Standard_[AD]\d+.*'
        'Series' = @('A', 'Av2', 'D', 'Dv2', 'Dv3', 'Dv4', 'Dv5', 'Dasv4', 'Dasv5', 'Ddsv4', 'Ddsv5', 'Dadsv5')
        'Features' = @('Balanced CPU-Memory', 'General workloads')
    }
    'ComputeOptimized' = @{
        'Pattern' = '^Standard_F\d+.*'
        'Series' = @('F', 'Fv2', 'Fsv2')
        'Features' = @('High CPU-Memory ratio', 'CPU intensive workloads')
    }
    'MemoryOptimized' = @{
        'Pattern' = '^Standard_[EGM]\d+.*'
        'Series' = @('E', 'Ev3', 'Ev4', 'Ev5', 'Easv4', 'Easv5', 'Edsv4', 'Edsv5', 'Eadsv5', 'M', 'Mv2')
        'Features' = @('High Memory-CPU ratio', 'In-memory databases')
    }
    'StorageOptimized' = @{
        'Pattern' = '^Standard_L\d+.*'
        'Series' = @('Lsv2', 'Lsv3', 'Lasv3')
        'Features' = @('High disk throughput', 'Big data workloads')
    }
    'GPU' = @{
        'Pattern' = '^Standard_N[CV]\d+.*'
        'Series' = @('NC', 'NCv2', 'NCv3', 'NCasT4_v3', 'NC_A100_v4', 'NV', 'NVv3', 'NVv4', 'NVadsA10_v5')
        'Features' = @('GPU accelerated', 'AI/ML workloads')
    }
    'HPC' = @{
        'Pattern' = '^Standard_H[BC]\d+.*'
        'Series' = @('H', 'HB', 'HBv2', 'HBv3', 'HC', 'HX')
        'Features' = @('HPC optimized', 'MPI workloads')
    }
}

# Helper Functions

function Connect-AzureEnvironment {
    if ($script:IsAutomation) {
        try {
            # Try Managed Identity first
            Write-Output "Connecting using Managed Identity..."
            Connect-AzAccount -Identity -ErrorAction Stop
            Write-Output "Connected successfully using Managed Identity"
        }
        catch {
            # Fall back to Run As account
            Write-Output "Trying Run As account..."
            $connection = Get-AutomationConnection -Name AzureRunAsConnection
            Connect-AzAccount `
                -ServicePrincipal `
                -Tenant $connection.TenantID `
                -ApplicationId $connection.ApplicationID `
                -CertificateThumbprint $connection.CertificateThumbprint
            Write-Output "Connected successfully using Run As account"
        }
    } else {
        # Interactive mode - check if already connected
        $context = Get-AzContext -ErrorAction SilentlyContinue
        if (-not $context) {
            Write-Host "Please login to Azure..." -ForegroundColor Yellow
            Connect-AzAccount
        } else {
            Write-Host "Already connected to Azure as $($context.Account.Id)" -ForegroundColor Green
        }
    }
}

function Get-InputData {
    param([string]$Source, [string]$Path, [string]$StorageKey)
    
    if ($Source -eq "File") {
        if (Test-Path $Path) {
            Write-Host "Reading input from local file: $Path" -ForegroundColor Green
            return Import-Csv -Path $Path
        } else {
            throw "Input file not found: $Path"
        }
    }
    elseif ($Source -eq "Blob") {
        # Parse blob path
        $parts = $Path -split '/'
        if ($parts.Count -lt 3) {
            throw "Invalid blob path format. Expected: StorageAccount/Container/BlobName"
        }
        
        $storageAccount = $parts[0]
        $container = $parts[1]
        $blobName = ($parts[2..($parts.Count-1)]) -join '/'
        
        # Get storage key
        if ([string]::IsNullOrWhiteSpace($StorageKey)) {
            if ($script:IsAutomation) {
                # Try to get from Automation variable
                try {
                    $StorageKey = Get-AutomationVariable -Name "${storageAccount}Key" -ErrorAction SilentlyContinue
                    if ([string]::IsNullOrWhiteSpace($StorageKey)) {
                        $StorageKey = Get-AutomationVariable -Name "StorageAccountKey" -ErrorAction SilentlyContinue
                    }
                } catch {}
            }
            
            if ([string]::IsNullOrWhiteSpace($StorageKey)) {
                throw "Storage account key is required for blob operations"
            }
        }
        
        Write-Host "Downloading from blob: $storageAccount/$container/$blobName" -ForegroundColor Green
        
        $ctx = New-AzStorageContext -StorageAccountName $storageAccount -StorageAccountKey $StorageKey
        $tempFile = [System.IO.Path]::GetTempFileName()
        
        Get-AzStorageBlobContent `
            -Container $container `
            -Blob $blobName `
            -Destination $tempFile `
            -Context $ctx `
            -Force | Out-Null
        
        $data = Import-Csv -Path $tempFile
        Remove-Item -Path $tempFile -Force
        
        return $data
    }
}

function Save-OutputData {
    param($Data, [string]$Path, [string]$StorageKey)
    
    # Generate default path if not specified
    if ([string]::IsNullOrWhiteSpace($Path)) {
        $timestamp = Get-Date -Format 'yyyyMMdd_HHmmss'
        if ($InputSource -eq "Blob") {
            $parts = $InputPath -split '/'
            $Path = "$($parts[0])/$($parts[1])/enhanced_resize_report_$timestamp.csv"
        } else {
            $Path = "./enhanced_resize_report_$timestamp$(if ($script:CanUseExcel) { '.xlsx' } else { '.csv' })"
        }
    }
    
    # Determine output type
    $isBlob = $Path -match '^[^/\\]+/[^/\\]+/'
    
    if ($isBlob) {
        # Save to blob
        $parts = $Path -split '/'
        $storageAccount = $parts[0]
        $container = $parts[1]
        $blobName = ($parts[2..($parts.Count-1)]) -join '/'
        
        # Ensure .csv extension for blob
        if ($blobName -notmatch '\.csv$') {
            $blobName = $blobName -replace '\.[^.]+$', '.csv'
        }
        
        # Get storage key
        if ([string]::IsNullOrWhiteSpace($StorageKey)) {
            if ($script:IsAutomation) {
                try {
                    $StorageKey = Get-AutomationVariable -Name "${storageAccount}Key" -ErrorAction SilentlyContinue
                    if ([string]::IsNullOrWhiteSpace($StorageKey)) {
                        $StorageKey = Get-AutomationVariable -Name "StorageAccountKey" -ErrorAction SilentlyContinue
                    }
                } catch {}
            }
            
            if ([string]::IsNullOrWhiteSpace($StorageKey)) {
                throw "Storage account key is required for blob operations"
            }
        }
        
        Write-Host "Uploading to blob: $storageAccount/$container/$blobName" -ForegroundColor Green
        
        $ctx = New-AzStorageContext -StorageAccountName $storageAccount -StorageAccountKey $StorageKey
        $tempFile = [System.IO.Path]::GetTempFileName()
        
        $Data | Export-Csv -Path $tempFile -NoTypeInformation
        
        Set-AzStorageBlobContent `
            -Container $container `
            -Blob $blobName `
            -File $tempFile `
            -Context $ctx `
            -Force | Out-Null
        
        Remove-Item -Path $tempFile -Force
        
        return "$storageAccount/$container/$blobName"
    }
    else {
        # Save to local file
        if ($script:CanUseExcel -and $Path -match '\.xlsx$') {
            # Excel output
            if (-not (Get-Module -Name ImportExcel)) {
                Import-Module ImportExcel
            }
            
            # Create Excel with multiple sheets
            if (Test-Path $Path) { Remove-Item $Path -Force }
            
            # Summary sheet
            $summary = @(
                [PSCustomObject]@{
                    'Metric' = 'Total VMs Processed'
                    'Count' = $Data.Count
                    'Details' = "Processed at $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')"
                }
                [PSCustomObject]@{
                    'Metric' = 'Fully Compatible'
                    'Count' = ($Data | Where-Object { $_.IsFullyCompatible -eq $true }).Count
                    'Details' = "Can be resized without issues"
                }
                [PSCustomObject]@{
                    'Metric' = 'Has Issues'
                    'Count' = ($Data | Where-Object { $_.IsFullyCompatible -eq $false }).Count
                    'Details' = "Require attention before resizing"
                }
                [PSCustomObject]@{
                    'Metric' = 'Retiring VMs'
                    'Count' = ($Data | Where-Object { $_.RetirementStatus -ne 'None' }).Count
                    'Details' = "Running on retiring/retired series"
                }
            )
            
            $summary | Export-Excel -Path $Path -WorksheetName "Summary" -AutoSize -TableStyle Medium1
            $Data | Export-Excel -Path $Path -WorksheetName "All_VMs" -AutoSize -TableStyle Medium2
            
            # Add filtered sheets
            $incompatible = $Data | Where-Object { $_.IsFullyCompatible -eq $false }
            if ($incompatible.Count -gt 0) {
                $incompatible | Export-Excel -Path $Path -WorksheetName "Incompatible_VMs" -AutoSize -TableStyle Medium10
            }
            
            $retiring = $Data | Where-Object { $_.RetirementStatus -ne 'None' }
            if ($retiring.Count -gt 0) {
                $retiring | Export-Excel -Path $Path -WorksheetName "Retiring_VMs" -AutoSize -TableStyle Medium6
            }
            
            Write-Host "Results saved to Excel: $Path" -ForegroundColor Green
        }
        else {
            # CSV output
            $Path = $Path -replace '\.xlsx$', '.csv'
            $Data | Export-Csv -Path $Path -NoTypeInformation
            Write-Host "Results saved to CSV: $Path" -ForegroundColor Green
        }
        
        return $Path
    }
}

# SKU Cache
$script:skuCacheByLocation = @{}
$script:pricingCache = @{}

function Get-VMSizeCapabilities {
    param([string]$Location, [string]$VMSize)
    
    try {
        if (-not $script:skuCacheByLocation.ContainsKey($Location)) {
            Write-Verbose "Loading SKU data for location: $Location"
            $locationSkus = Get-AzComputeResourceSku -Location $Location -ErrorAction Stop | 
                Where-Object { $_.ResourceType -eq 'virtualMachines' }
            
            if ($locationSkus) {
                $script:skuCacheByLocation[$Location] = $locationSkus
            }
        }
        
        $capabilities = $script:skuCacheByLocation[$Location] | 
            Where-Object { $_.Name -eq $VMSize }
        
        if ($capabilities) {
            $result = @{
                MaxDataDisks = $null
                PremiumIO = $false
                AcceleratedNetworking = $false
                UltraDisks = $false
                TrustedLaunch = $false
                AvailabilityZones = @()
                vCPUs = $null
                MemoryGB = $null
                MaxNics = $null
                Generation = 'Gen1'
            }
            
            foreach ($cap in $capabilities.Capabilities) {
                switch ($cap.Name) {
                    'MaxDataDiskCount' { $result.MaxDataDisks = [int]$cap.Value }
                    'PremiumIO' { $result.PremiumIO = $cap.Value -eq 'True' }
                    'AcceleratedNetworkingEnabled' { $result.AcceleratedNetworking = $cap.Value -eq 'True' }
                    'UltraSSDAvailable' { $result.UltraDisks = $cap.Value -eq 'True' }
                    'TrustedLaunchDisabled' { $result.TrustedLaunch = $cap.Value -ne 'True' }
                    'vCPUs' { $result.vCPUs = [int]$cap.Value }
                    'MemoryGB' { $result.MemoryGB = [decimal]$cap.Value }
                    'MaxNetworkInterfaces' { $result.MaxNics = [int]$cap.Value }
                    'HyperVGenerations' { 
                        if ($cap.Value -match 'V2') { $result.Generation = 'Gen2' }
                    }
                }
            }
            
            # Enhanced Premium Storage detection
            if ($VMSize -match '^Standard_[A-Z]+\d+[a-z]*s' -or $VMSize -match '^Standard_[A-Z]+S\d+') {
                $result.PremiumIO = $true
            }
            
            # Get availability zones
            if ($capabilities.LocationInfo) {
                foreach ($locInfo in $capabilities.LocationInfo) {
                    if ($locInfo.Location -eq $Location -and $locInfo.Zones) {
                        $result.AvailabilityZones = $locInfo.Zones
                    }
                }
            }
            
            return $result
        }
        
        return $null
    }
    catch {
        Write-Warning "Failed to get capabilities for $VMSize in $Location"
        return $null
    }
}

function Get-VMSeriesInfo {
    param([string]$VMSize)
    
    # Extract series from VM size
    if ($VMSize -match '^Standard_([A-Z]+)(\d+)?([a-z]+)?(_v(\d+))?') {
        $series = $Matches[1]
        $version = if ($Matches[5]) { "v$($Matches[5])" } else { "" }
        $fullSeries = "$series$version"
        
        # Check retired status
        foreach ($category in @('Retired', 'Announced', 'PreviousGen')) {
            if ($script:RetiredVMSeries[$category].ContainsKey($fullSeries)) {
                return @{
                    Series = $fullSeries
                    Category = $category
                    Info = $script:RetiredVMSeries[$category][$fullSeries]
                }
            }
        }
        
        # Check base series without version
        foreach ($category in @('Retired', 'Announced', 'PreviousGen')) {
            if ($script:RetiredVMSeries[$category].ContainsKey($series)) {
                return @{
                    Series = $series
                    Category = $category
                    Info = $script:RetiredVMSeries[$category][$series]
                }
            }
        }
    }
    
    return @{
        Series = $null
        Category = 'None'
        Info = $null
    }
}

function Get-VMCategory {
    param([string]$VMSize)
    
    foreach ($category in $script:VMSizeCategories.GetEnumerator()) {
        if ($VMSize -match $category.Value.Pattern) {
            return $category.Name
        }
    }
    
    return 'Unknown'
}

function Get-AzureVMPricing {
    param(
        [string]$VMSize,
        [string]$Location,
        [string]$OS = 'Linux'
    )
    
    $cacheKey = "$VMSize-$Location-$OS"
    
    if ($script:pricingCache.ContainsKey($cacheKey)) {
        return $script:pricingCache[$cacheKey]
    }
    
    try {
        # Convert location to API format (lowercase, no spaces/dashes)
        $apiLocation = $Location.ToLower() -replace '\s+', '' -replace '-', ''

        # Build the filter - only use supported OData operators
        $filters = @()
        $filters += "serviceName eq 'Virtual Machines'"
        $filters += "armRegionName eq '$apiLocation'"
        $filters += "armSkuName eq '$VMSize'"
        $filters += "priceType eq 'Consumption'"

        $filterString = $filters -join ' and '
        $baseUri = "https://prices.azure.com/api/retail/prices"
        $encodedFilter = [System.Web.HttpUtility]::UrlEncode($filterString)
        $uri = "${baseUri}?`$filter=${encodedFilter}"

        Write-Verbose "Fetching pricing from: $uri"

        $headers = @{
            'Accept' = 'application/json'
            'User-Agent' = 'PowerShell-VMResizeChecker/1.0'
        }

        $response = Invoke-RestMethod -Uri $uri -Method Get -Headers $headers -ErrorAction Stop

        $items = $response.Items
        if ($OS -eq 'Windows') {
            $items = $items | Where-Object { $_.productName -like '*Windows*' }
        } else {
            $items = $items | Where-Object { $_.productName -notlike '*Windows*' }
        }

        if ($items -and $items.Count -gt 0) {
            $price = $items[0]
            $result = @{
                HourlyRate = [decimal]$price.retailPrice
                MonthlyRate = [decimal]$price.retailPrice * 730  # Average hours per month
                Currency = $price.currencyCode
                Unit = $price.unitOfMeasure
                Found = $true
                MeterName = $price.meterName
                ProductName = $price.productName
            }
            $script:pricingCache[$cacheKey] = $result
            Write-Verbose "Found pricing for $VMSize in $Location`: `$$($result.HourlyRate)/hour"
            return $result
        } else {
            Write-Verbose "No pricing data found for $VMSize in $Location"
        }
    }
    catch {
        Write-Warning "Failed to get pricing for $VMSize in $Location : $($_.Exception.Message)"
    }

    # Return default result if all attempts fail
    $defaultResult = @{
        HourlyRate = 0
        MonthlyRate = 0
        Currency = 'USD'
        Unit = 'Unknown'
        Found = $false
        MeterName = 'Not Found'
        ProductName = 'Not Found'
    }
    $script:pricingCache[$cacheKey] = $defaultResult
    return $defaultResult
}

function Get-AlternativeVMSizes {
    param(
        [string]$CurrentSize,
        [hashtable]$CurrentCapabilities,
        [string]$Location,
        [string]$Category,
        [int]$MaxResults = 3
    )
    
    $alternatives = @()
    
    # Get current size info
    $currentCPUs = $CurrentCapabilities.vCPUs
    $currentMemory = $CurrentCapabilities.MemoryGB
    $currentPremium = $CurrentCapabilities.PremiumIO
    
    if (-not $currentCPUs -or -not $currentMemory) {
        Write-Verbose "Missing CPU/Memory info for $CurrentSize"
        return $alternatives
    }
    
    # Get all available sizes in location
    $availableSizes = $script:skuCacheByLocation[$Location] | 
        Where-Object { $_.ResourceType -eq 'virtualMachines' } |
        Select-Object -ExpandProperty Name -Unique
    
    # Score and rank alternatives
    $scoredSizes = @()
    
    foreach ($size in $availableSizes) {
        # Skip current size
        if ($size -eq $CurrentSize) { continue }
        
        # Get capabilities
        $caps = Get-VMSizeCapabilities -Location $Location -VMSize $size
        if (-not $caps -or -not $caps.vCPUs -or -not $caps.MemoryGB) { continue }
        
        # Check if it's a retiring series
        $seriesInfo = Get-VMSeriesInfo -VMSize $size
        if ($seriesInfo.Category -in @('Retired', 'Announced')) { continue }
        
        # Calculate similarity score
        $cpuDiff = [Math]::Abs($caps.vCPUs - $currentCPUs) / $currentCPUs
        $memDiff = [Math]::Abs($caps.MemoryGB - $currentMemory) / $currentMemory
        $score = 100 - (($cpuDiff + $memDiff) * 50)
        
        # Bonus for matching features
        if ($caps.PremiumIO -eq $currentPremium) { $score += 10 }
        if ($caps.AcceleratedNetworking -eq $CurrentCapabilities.AcceleratedNetworking) { $score += 5 }
        
        # Bonus for newer generation
        if ($size -match 'v5') { $score += 15 }
        elseif ($size -match 'v4') { $score += 10 }
        elseif ($size -match 'v3') { $score += 5 }

        # Penalty for previous gen
        if ($seriesInfo.Category -eq 'PreviousGen') { $score -= 20 }
        
        $scoredSizes += [PSCustomObject]@{
            Size = $size
            Score = $score
            CPUs = $caps.vCPUs
            Memory = $caps.MemoryGB
            PremiumIO = $caps.PremiumIO
            Category = Get-VMCategory -VMSize $size
        }
    }
    
    # Sort by score and get top results
    $topSizes = $scoredSizes | Sort-Object -Property Score -Descending | Select-Object -First $MaxResults
    
    foreach ($alt in $topSizes) {
        $alternatives += [PSCustomObject]@{
            VMSize = $alt.Size
            vCPUs = $alt.CPUs
            MemoryGB = $alt.Memory
            PremiumIO = $alt.PremiumIO
            Category = $alt.Category
            Score = [Math]::Round($alt.Score, 2)
        }
    }
    
    return $alternatives
}

function Test-VMCompatibility {
    param(
        [object]$VM,
        [string]$TargetVMSize,
        [hashtable]$TargetCapabilities
    )
    
    $compatibility = @{
        IsFullyCompatible = $true
        Issues = @()
        Warnings = @()
    }
    
    # Data disk check
    if (-not $SkipDataDiskCheck) {
        $dataDisks = if ($VM.StorageProfile.DataDisks) { $VM.StorageProfile.DataDisks.Count } else { 0 }
        
        if ($TargetCapabilities.MaxDataDisks -and $dataDisks -gt $TargetCapabilities.MaxDataDisks) {
            $compatibility.IsFullyCompatible = $false
            $compatibility.Issues += "Target supports only $($TargetCapabilities.MaxDataDisks) data disks, VM has $dataDisks"
        }
    }
    
    # Premium storage check
    if (-not $SkipPremiumStorageCheck) {
        $usesPremium = $VM.StorageProfile.OsDisk.ManagedDisk.StorageAccountType -match 'Premium'
        if (-not $usesPremium) {
            foreach ($disk in $VM.StorageProfile.DataDisks) {
                if ($disk.ManagedDisk.StorageAccountType -match 'Premium') {
                    $usesPremium = $true
                    break
                }
            }
        }
        
        if ($usesPremium -and $TargetCapabilities -and -not $TargetCapabilities.PremiumIO) {
            $compatibility.IsFullyCompatible = $false
            $compatibility.Issues += "VM uses Premium Storage but target doesn't support it"
        }
    }
    
    # Accelerated networking check
    if (-not $SkipAcceleratedNetworkingCheck) {
        $usesAccelNet = $false
        foreach ($nic in $VM.NetworkProfile.NetworkInterfaces) {
            $nicResource = Get-AzNetworkInterface -ResourceId $nic.Id -ErrorAction SilentlyContinue
            if ($nicResource -and $nicResource.EnableAcceleratedNetworking) {
                $usesAccelNet = $true
                break
            }
        }
        
        if ($usesAccelNet -and $TargetCapabilities -and -not $TargetCapabilities.AcceleratedNetworking) {
            $compatibility.Warnings += "VM uses Accelerated Networking but target doesn't support it"
        }
    }
    
    # Availability zone check
    if (-not $SkipAvailabilityZoneCheck) {
        if ($VM.Zones -and $VM.Zones.Count -gt 0) {
            if ($TargetCapabilities -and $TargetCapabilities.AvailabilityZones) {
                $vmZone = $VM.Zones[0]
                if ($vmZone -notin $TargetCapabilities.AvailabilityZones) {
                    $compatibility.Warnings += "VM is in zone $vmZone but target doesn't support this zone"
                }
            } else {
                $compatibility.Warnings += "VM uses Availability Zones but target availability unknown"
            }
        }
    }
    
    # Ultra disk check
    if (-not $SkipUltraDiskCheck) {
        $usesUltra = $false
        foreach ($disk in $VM.StorageProfile.DataDisks) {
            if ($disk.ManagedDisk.StorageAccountType -eq 'UltraSSD_LRS') {
                $usesUltra = $true
                break
            }
        }
        
        if ($usesUltra -and $TargetCapabilities -and -not $TargetCapabilities.UltraDisks) {
            $compatibility.IsFullyCompatible = $false
            $compatibility.Issues += "VM uses Ultra Disks but target doesn't support them"
        }
    }
    
    # Trusted launch check
    if (-not $SkipTrustedLaunchCheck) {
        if ($VM.SecurityProfile -and $VM.SecurityProfile.SecurityType -eq 'TrustedLaunch') {
            if ($TargetCapabilities -and -not $TargetCapabilities.TrustedLaunch) {
                $compatibility.IsFullyCompatible = $false
                $compatibility.Issues += "VM uses Trusted Launch but target doesn't support it"
            }
        }
    }
    
    # Check if target is retiring
    $targetSeriesInfo = Get-VMSeriesInfo -VMSize $TargetVMSize
    if ($targetSeriesInfo.Category -in @('Retired', 'Announced')) {
        $compatibility.IsFullyCompatible = $false
        $compatibility.Issues += "Target VM series is $($targetSeriesInfo.Category) for retirement"
    }
    
    return $compatibility
}

function Process-VMBatch {
    param([array]$Recommendations)
    
    $results = @()
    $total = $Recommendations.Count
    $current = 0
    
    foreach ($rec in $Recommendations) {
        $current++
        
        if ($script:IsAutomation) {
            Write-Output "Processing VM $current of $total"
        } else {
            Write-Progress -Activity "Processing VMs" -Status "VM $current of $total" -PercentComplete (($current / $total) * 100)
        }
        
        try {
            # Parse resource name
            $parts = $rec.'Resource Name' -split '/'
            if ($parts.Count -lt 3) {
                Write-Warning "Invalid resource name format: $($rec.'Resource Name')"
                continue
            }
            
            $resourceGroup = $parts[0]
            $subscriptionId = $parts[1]
            $vmName = $parts[2]
            
            # Apply filters
            $rgExcluded = $false
            foreach ($pattern in $ExcludeResourceGroups) {
                if ($resourceGroup -like $pattern) {
                    $rgExcluded = $true
                    break
                }
            }
            
            if ($rgExcluded) {
                Write-Verbose "Skipping VM in excluded resource group: $resourceGroup"
                continue
            }
            
            if ($ExcludeDtoBResize -and 
                $rec.'Current VM Size' -match '^Standard_D\d+' -and 
                $rec.'Recommended VM Size' -match '^Standard_B\d+') {
                Write-Verbose "Skipping D to B resize: $vmName"
                continue
            }
            
            # Get VM details
            Set-AzContext -SubscriptionId $subscriptionId -ErrorAction Stop | Out-Null
            $vm = Get-AzVM -ResourceGroupName $resourceGroup -Name $vmName -ErrorAction Stop
            
            # Get current VM capabilities
            $currentCaps = Get-VMSizeCapabilities -Location $vm.Location -VMSize $rec.'Current VM Size'
            
            # Get target capabilities
            $targetCaps = Get-VMSizeCapabilities -Location $vm.Location -VMSize $rec.'Recommended VM Size'
            
            # Check compatibility
            $compatCheck = Test-VMCompatibility -VM $vm -TargetVMSize $rec.'Recommended VM Size' -TargetCapabilities $targetCaps
            
            # Check retirement status
            $currentSeriesInfo = Get-VMSeriesInfo -VMSize $rec.'Current VM Size'
            
            # Count disks
            $dataDisks = if ($vm.StorageProfile.DataDisks) { $vm.StorageProfile.DataDisks.Count } else { 0 }
            $totalDisks = $dataDisks + 1
            
            # Determine OS type
            $osType = if ($vm.StorageProfile.OsDisk.OsType) { $vm.StorageProfile.OsDisk.OsType } else { 'Linux' }
            
            # Build base result - using ordered hashtable to avoid duplicate property issues
            $resultProps = [ordered]@{
                SubscriptionId = $subscriptionId
                SubscriptionName = (Get-AzSubscription -SubscriptionId $subscriptionId).Name
                IsProduction = $subscriptionId -in $ProductionSubscriptionIds
                ResourceGroup = $resourceGroup
                VMName = $vmName
                CurrentVMSize = $rec.'Current VM Size'
                CurrentVMCategory = Get-VMCategory -VMSize $rec.'Current VM Size'
                RecommendedVMSize = $rec.'Recommended VM Size'
                RecommendedVMCategory = Get-VMCategory -VMSize $rec.'Recommended VM Size'
                DataDisks = $dataDisks
                TotalDisks = $totalDisks
                MaxDataDisksSupported = if ($targetCaps) { $targetCaps.MaxDataDisks } else { "Unknown" }
                PremiumStorageSupported = if ($targetCaps) { $targetCaps.PremiumIO } else { "Unknown" }
                IsFullyCompatible = $compatCheck.IsFullyCompatible
                Issues = $compatCheck.Issues -join "; "
                Warnings = $compatCheck.Warnings -join "; "
                RetirementStatus = $currentSeriesInfo.Category
                RetirementInfo = if ($currentSeriesInfo.Info) { $currentSeriesInfo.Info.Reason } else { "" }
                CheckedAt = Get-Date -Format 'yyyy-MM-dd HH:mm:ss'
            }
            
            if ($ShowSavings) {
                # Check if these properties exist in the input data
                if ($rec.PSObject.Properties['Potential Savings']) {
                    $resultProps['PotentialSavings'] = $rec.'Potential Savings'
                }
                if ($rec.PSObject.Properties['Savings Percentage']) {
                    $resultProps['SavingsPercentage'] = $rec.'Savings Percentage'
                }
            }
            
            # Add cost analysis
            if ($IncludeCostAnalysis) {
                $currentPricing = Get-AzureVMPricing -VMSize $rec.'Current VM Size' -Location $vm.Location -OS $osType
                $recommendedPricing = Get-AzureVMPricing -VMSize $rec.'Recommended VM Size' -Location $vm.Location -OS $osType
                
                $resultProps['CurrentHourlyRate'] = $currentPricing.HourlyRate
                $resultProps['CurrentMonthlyRate'] = $currentPricing.MonthlyRate
                $resultProps['RecommendedHourlyRate'] = $recommendedPricing.HourlyRate
                $resultProps['RecommendedMonthlyRate'] = $recommendedPricing.MonthlyRate
                $resultProps['MonthlySavings'] = ($currentPricing.MonthlyRate - $recommendedPricing.MonthlyRate)
                $resultProps['Currency'] = $currentPricing.Currency
            }
            
            # Add alternatives
            if ($IncludeAlternatives) {
                $alternatives = Get-AlternativeVMSizes `
                    -CurrentSize $rec.'Current VM Size' `
                    -CurrentCapabilities $currentCaps `
                    -Location $vm.Location `
                    -Category (Get-VMCategory -VMSize $rec.'Current VM Size') `
                    -MaxResults $MaxAlternatives
                
                for ($i = 0; $i -lt $MaxAlternatives; $i++) {
                    if ($i -lt $alternatives.Count) {
                        $alt = $alternatives[$i]
                        $resultProps["Alternative$($i+1)_Size"] = $alt.VMSize
                        $resultProps["Alternative$($i+1)_vCPUs"] = $alt.vCPUs
                        $resultProps["Alternative$($i+1)_Memory"] = $alt.MemoryGB
                        $resultProps["Alternative$($i+1)_Score"] = $alt.Score
                        
                        if ($IncludeCostAnalysis) {
                            $altPricing = Get-AzureVMPricing -VMSize $alt.VMSize -Location $vm.Location -OS $osType
                            $resultProps["Alternative$($i+1)_MonthlyRate"] = $altPricing.MonthlyRate
                        }
                    } else {
                        $resultProps["Alternative$($i+1)_Size"] = ""
                        $resultProps["Alternative$($i+1)_vCPUs"] = ""
                        $resultProps["Alternative$($i+1)_Memory"] = ""
                        $resultProps["Alternative$($i+1)_Score"] = ""
                        if ($IncludeCostAnalysis) {
                            $resultProps["Alternative$($i+1)_MonthlyRate"] = ""
                        }
                    }
                }
            }
            
            # Add retirement recommendations
            if ($currentSeriesInfo.Category -ne 'None' -and $currentSeriesInfo.Info.Replacements) {
                $replacements = $currentSeriesInfo.Info.Replacements -join ", "
                $resultProps['RecommendedReplacements'] = $replacements
            } else {
                $resultProps['RecommendedReplacements'] = ""
            }
            
            # Create the final result object
            $result = [PSCustomObject]$resultProps
            $results += $result
            
        }
        catch {
            Write-Warning "Failed to process ${vmName}: $_"
            
            $results += [PSCustomObject]@{
                SubscriptionId = $subscriptionId
                SubscriptionName = "Unknown"
                IsProduction = $subscriptionId -in $ProductionSubscriptionIds
                ResourceGroup = $resourceGroup
                VMName = $vmName
                CurrentVMSize = $rec.'Current VM Size'
                CurrentVMCategory = "Unknown"
                RecommendedVMSize = $rec.'Recommended VM Size'
                RecommendedVMCategory = "Unknown"
                DataDisks = "Error"
                TotalDisks = "Error"
                MaxDataDisksSupported = "Error"
                PremiumStorageSupported = "Error"
                IsFullyCompatible = $false
                Issues = "Error: $($_.Exception.Message)"
                Warnings = ""
                RetirementStatus = "Unknown"
                RetirementInfo = ""
                CheckedAt = Get-Date -Format 'yyyy-MM-dd HH:mm:ss'
            }
        }
    }
    
    if (-not $script:IsAutomation) {
        Write-Progress -Activity "Processing VMs" -Completed
    }
    
    return $results
}

# Main execution
try {
    # Connect to Azure
    Connect-AzureEnvironment
    
    # Get input data
    Write-Host "`nLoading input data..." -ForegroundColor Yellow
    $recommendations = Get-InputData -Source $InputSource -Path $InputPath -StorageKey $StorageAccountKey
    $validRecommendations = $recommendations | Where-Object { ![string]::IsNullOrWhiteSpace($_.'Resource Name') }
    Write-Host "Loaded $($validRecommendations.Count) valid recommendations" -ForegroundColor Green
    
    # Process VMs
    Write-Host "`nProcessing VMs..." -ForegroundColor Yellow
    
    if ($script:IsAutomation -or $MaxParallelJobs -le 1) {
        # Sequential processing
        $results = Process-VMBatch -Recommendations $validRecommendations
    }
    else {
        # For Cloud Shell or when having issues with parallel processing, use sequential
        if ($script:IsCloudShell -or $validRecommendations.Count -gt 100) {
            Write-Host "Using sequential processing for stability (Cloud Shell or large dataset)..." -ForegroundColor Yellow
            $results = Process-VMBatch -Recommendations $validRecommendations
        }
        else {
            # Parallel processing for interactive mode
            $batches = @()
            $batchSize = [Math]::Ceiling($validRecommendations.Count / $MaxParallelJobs)
            
            for ($i = 0; $i -lt $validRecommendations.Count; $i += $batchSize) {
                $end = [Math]::Min($i + $batchSize - 1, $validRecommendations.Count - 1)
                $batches += ,@($validRecommendations[$i..$end])
            }
            
            Write-Host "Processing in $($batches.Count) parallel batches..." -ForegroundColor Cyan
            
            $jobs = @()
            foreach ($batch in $batches) {
                $jobs += Start-Job -ScriptBlock {
                    param($batch, $functions, $params, $retiredSeries, $sizeCategories)
                    
                    # Import functions
                    foreach ($func in $functions.GetEnumerator()) {
                        New-Item -Path "Function:\$($func.Key)" -Value $func.Value -Force | Out-Null
                    }
                    
                    # Set parameters
                    foreach ($param in $params.GetEnumerator()) {
                        Set-Variable -Name $param.Key -Value $param.Value -Scope Script
                    }
                    
                    # Set script variables
                    $script:RetiredVMSeries = $retiredSeries
                    $script:VMSizeCategories = $sizeCategories
                    $script:skuCacheByLocation = @{}
                    $script:pricingCache = @{}
                    
                    Process-VMBatch -Recommendations $batch
                } -ArgumentList $batch, @{
                    'Process-VMBatch' = ${function:Process-VMBatch}
                    'Get-VMSizeCapabilities' = ${function:Get-VMSizeCapabilities}
                    'Test-VMCompatibility' = ${function:Test-VMCompatibility}
                    'Get-VMSeriesInfo' = ${function:Get-VMSeriesInfo}
                    'Get-VMCategory' = ${function:Get-VMCategory}
                    'Get-AzureVMPricing' = ${function:Get-AzureVMPricing}
                    'Get-AlternativeVMSizes' = ${function:Get-AlternativeVMSizes}
                }, @{
                    'ProductionSubscriptionIds' = $ProductionSubscriptionIds
                    'ExcludeResourceGroups' = $ExcludeResourceGroups
                    'ExcludeDtoBResize' = $ExcludeDtoBResize
                    'ShowSavings' = $ShowSavings
                    'IncludeAlternatives' = $IncludeAlternatives
                    'IncludeCostAnalysis' = $IncludeCostAnalysis
                    'MaxAlternatives' = $MaxAlternatives
                    'SkipDataDiskCheck' = $SkipDataDiskCheck
                    'SkipPremiumStorageCheck' = $SkipPremiumStorageCheck
                    'SkipAcceleratedNetworkingCheck' = $SkipAcceleratedNetworkingCheck
                    'SkipAvailabilityZoneCheck' = $SkipAvailabilityZoneCheck
                    'SkipTrustedLaunchCheck' = $SkipTrustedLaunchCheck
                    'SkipUltraDiskCheck' = $SkipUltraDiskCheck
                    'SkipOSCheck' = $SkipOSCheck
                }, $script:RetiredVMSeries, $script:VMSizeCategories
            }
            
            Write-Host "Waiting for jobs to complete..." -ForegroundColor Gray
            
            # Wait for jobs with timeout
            $timeout = New-TimeSpan -Minutes 10
            $stopwatch = [System.Diagnostics.Stopwatch]::StartNew()
            $results = @()
            
            while ($jobs.Count -gt 0 -and $stopwatch.Elapsed -lt $timeout) {
                $completedJobs = $jobs | Where-Object { $_.State -eq 'Completed' -or $_.State -eq 'Failed' }
                
                foreach ($job in $completedJobs) {
                    if ($job.State -eq 'Completed') {
                        $results += Receive-Job -Job $job
                    } else {
                        Write-Warning "Job $($job.Id) failed: $($job.ChildJobs[0].JobStateInfo.Reason)"
                    }
                    Remove-Job -Job $job
                    $jobs = $jobs | Where-Object { $_.Id -ne $job.Id }
                }
                
                if ($jobs.Count -gt 0) {
                    Write-Host "Waiting for $($jobs.Count) jobs to complete... ($([int]$stopwatch.Elapsed.TotalSeconds)s elapsed)" -ForegroundColor Gray
                    Start-Sleep -Seconds 2
                }
            }
            
            # Handle timeout
            if ($jobs.Count -gt 0) {
                Write-Warning "Timeout reached. Stopping remaining jobs..."
                $jobs | Stop-Job
                $jobs | Remove-Job -Force
            }
            
            $stopwatch.Stop()
        }
    }
    
    # Save results
    Write-Host "`nSaving results..." -ForegroundColor Yellow
    $outputLocation = Save-OutputData -Data $results -Path $OutputPath -StorageKey $StorageAccountKey
    
    # Display summary
    $summary = @{
        Total = $results.Count
        Compatible = ($results | Where-Object { $_.IsFullyCompatible -eq $true }).Count
        Incompatible = ($results | Where-Object { $_.IsFullyCompatible -eq $false }).Count
        Errors = ($results | Where-Object { $_.Issues -match "Error:" }).Count
        Retiring = ($results | Where-Object { $_.RetirementStatus -ne 'None' }).Count
    }
    
    Write-Host "`n========== SUMMARY ==========" -ForegroundColor Cyan
    Write-Host "Total VMs Processed: $($summary.Total)" -ForegroundColor White
    Write-Host "Fully Compatible: $($summary.Compatible)" -ForegroundColor Green
    Write-Host "Has Issues: $($summary.Incompatible)" -ForegroundColor Red
    Write-Host "Errors: $($summary.Errors)" -ForegroundColor Yellow
    Write-Host "Retiring VMs: $($summary.Retiring)" -ForegroundColor Magenta
    Write-Host "Output Location: $outputLocation" -ForegroundColor Green
    
    # Show cost summary if enabled
    if ($IncludeCostAnalysis) {
        $totalCurrentCost = ($results | Measure-Object -Property CurrentMonthlyRate -Sum).Sum
        $totalRecommendedCost = ($results | Measure-Object -Property RecommendedMonthlyRate -Sum).Sum
        $totalSavings = $totalCurrentCost - $totalRecommendedCost
        
        Write-Host "`n========== COST ANALYSIS ==========" -ForegroundColor Cyan
        Write-Host "Current Monthly Cost: `$([Math]::Round($totalCurrentCost, 2))" -ForegroundColor White
        Write-Host "Recommended Monthly Cost: `$([Math]::Round($totalRecommendedCost, 2))" -ForegroundColor White
        Write-Host "Potential Monthly Savings: `$([Math]::Round($totalSavings, 2))" -ForegroundColor Green
        Write-Host "Savings Percentage: $([Math]::Round(($totalSavings / $totalCurrentCost) * 100, 2))%" -ForegroundColor Green
    }
    
    # Show retiring VMs summary
    if ($summary.Retiring -gt 0) {
        Write-Host "`n========== RETIRING VMs ==========" -ForegroundColor Magenta
        $retiringVMs = $results | Where-Object { $_.RetirementStatus -ne 'None' }
        $retiringGroups = $retiringVMs | Group-Object -Property RetirementStatus
        
        foreach ($group in $retiringGroups) {
            Write-Host "$($group.Name): $($group.Count) VMs" -ForegroundColor Yellow
        }
    }
    
    # Email notification (Automation only)
    if ($script:IsAutomation -and ![string]::IsNullOrWhiteSpace($EmailRecipients)) {
        Write-Output "`nSending email notification..."
        # Add email logic here based on your email service
    }
    
    Write-Host "`nExecution completed successfully!" -ForegroundColor Green
    Write-Host "Total Time: $([Math]::Round(((Get-Date) - $script:StartTime).TotalMinutes, 2)) minutes" -ForegroundColor Gray
    
}
catch {
    Write-Error "Script failed: $_"
    throw
} 
