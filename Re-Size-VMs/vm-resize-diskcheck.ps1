# VM Resize Disk Compatibility Check Script - Multi-Subscription Support
# This script checks if VMs can be resized based on disk attachment limits across multiple subscriptions

param(
    [Parameter(Mandatory=$true)]
    [string]$InputCsvPath,
    
    [Parameter(Mandatory=$false)]
    [string]$OutputCsvPath = "VM_Resize_Analysis.csv"
)

# Function to get maximum data disks for a VM SKU
function Get-MaxDataDisks {
    param([string]$VMSize)
    
    # Comprehensive VM sizes and their max data disk limits
    $vmSizeLimits = @{
        # A-Series (Basic)
        "Basic_A0" = 1
        "Basic_A1" = 2
        "Basic_A2" = 4
        "Basic_A3" = 8
        "Basic_A4" = 16
        
        # A-Series (Standard)
        "Standard_A0" = 1
        "Standard_A1" = 2
        "Standard_A2" = 4
        "Standard_A3" = 8
        "Standard_A4" = 16
        "Standard_A5" = 4
        "Standard_A6" = 8
        "Standard_A7" = 16
        "Standard_A8" = 32
        "Standard_A9" = 64
        "Standard_A10" = 32
        "Standard_A11" = 64
        
        # A-Series v2
        "Standard_A1_v2" = 2
        "Standard_A2_v2" = 4
        "Standard_A4_v2" = 8
        "Standard_A8_v2" = 16
        "Standard_A2m_v2" = 4
        "Standard_A4m_v2" = 8
        "Standard_A8m_v2" = 16
        
        # B-Series (Burstable)
        "Standard_B1ls" = 2
        "Standard_B1s" = 2
        "Standard_B1ms" = 2
        "Standard_B2s" = 4
        "Standard_B2ms" = 4
        "Standard_B4ms" = 8
        "Standard_B8ms" = 16
        "Standard_B12ms" = 16
        "Standard_B16ms" = 32
        "Standard_B20ms" = 32
        
        # D-Series
        "Standard_D1" = 4
        "Standard_D2" = 8
        "Standard_D3" = 16
        "Standard_D4" = 32
        "Standard_D11" = 8
        "Standard_D12" = 16
        "Standard_D13" = 32
        "Standard_D14" = 64
        
        # D-Series v2
        "Standard_D1_v2" = 4
        "Standard_D2_v2" = 8
        "Standard_D3_v2" = 16
        "Standard_D4_v2" = 32
        "Standard_D5_v2" = 64
        "Standard_D11_v2" = 8
        "Standard_D12_v2" = 16
        "Standard_D13_v2" = 32
        "Standard_D14_v2" = 64
        "Standard_D15_v2" = 64
        
        # D-Series v3
        "Standard_D2_v3" = 4
        "Standard_D4_v3" = 8
        "Standard_D8_v3" = 16
        "Standard_D16_v3" = 32
        "Standard_D32_v3" = 32
        "Standard_D48_v3" = 32
        "Standard_D64_v3" = 32
        
        # D-Series v4
        "Standard_D2_v4" = 4
        "Standard_D4_v4" = 8
        "Standard_D8_v4" = 16
        "Standard_D16_v4" = 32
        "Standard_D32_v4" = 32
        "Standard_D48_v4" = 32
        "Standard_D64_v4" = 32
        
        # D-Series v5
        "Standard_D2_v5" = 4
        "Standard_D4_v5" = 8
        "Standard_D8_v5" = 16
        "Standard_D16_v5" = 32
        "Standard_D32_v5" = 32
        "Standard_D48_v5" = 32
        "Standard_D64_v5" = 32
        "Standard_D96_v5" = 32
        
        # DS-Series
        "Standard_DS1" = 4
        "Standard_DS2" = 8
        "Standard_DS3" = 16
        "Standard_DS4" = 32
        "Standard_DS11" = 8
        "Standard_DS12" = 16
        "Standard_DS13" = 32
        "Standard_DS14" = 64
        
        # DS-Series v2
        "Standard_DS1_v2" = 4
        "Standard_DS2_v2" = 8
        "Standard_DS3_v2" = 16
        "Standard_DS4_v2" = 32
        "Standard_DS5_v2" = 64
        "Standard_DS11_v2" = 8
        "Standard_DS12_v2" = 16
        "Standard_DS13_v2" = 32
        "Standard_DS14_v2" = 64
        "Standard_DS15_v2" = 64
        
        # Dsv3-Series
        "Standard_D2s_v3" = 4
        "Standard_D4s_v3" = 8
        "Standard_D8s_v3" = 16
        "Standard_D16s_v3" = 32
        "Standard_D32s_v3" = 32
        "Standard_D48s_v3" = 32
        "Standard_D64s_v3" = 32
        
        # Dsv4-Series
        "Standard_D2s_v4" = 4
        "Standard_D4s_v4" = 8
        "Standard_D8s_v4" = 16
        "Standard_D16s_v4" = 32
        "Standard_D32s_v4" = 32
        "Standard_D48s_v4" = 32
        "Standard_D64s_v4" = 32
        
        # Dsv5-Series
        "Standard_D2s_v5" = 4
        "Standard_D4s_v5" = 8
        "Standard_D8s_v5" = 16
        "Standard_D16s_v5" = 32
        "Standard_D32s_v5" = 32
        "Standard_D48s_v5" = 32
        "Standard_D64s_v5" = 32
        "Standard_D96s_v5" = 32
        
        # E-Series v3
        "Standard_E2_v3" = 4
        "Standard_E4_v3" = 8
        "Standard_E8_v3" = 16
        "Standard_E16_v3" = 32
        "Standard_E20_v3" = 32
        "Standard_E32_v3" = 32
        "Standard_E48_v3" = 32
        "Standard_E64_v3" = 32
        
        # E-Series v4
        "Standard_E2_v4" = 4
        "Standard_E4_v4" = 8
        "Standard_E8_v4" = 16
        "Standard_E16_v4" = 32
        "Standard_E20_v4" = 32
        "Standard_E32_v4" = 32
        "Standard_E48_v4" = 32
        "Standard_E64_v4" = 32
        
        # E-Series v5
        "Standard_E2_v5" = 4
        "Standard_E4_v5" = 8
        "Standard_E8_v5" = 16
        "Standard_E16_v5" = 32
        "Standard_E20_v5" = 32
        "Standard_E32_v5" = 32
        "Standard_E48_v5" = 32
        "Standard_E64_v5" = 32
        "Standard_E96_v5" = 32
        
        # ES-Series v3
        "Standard_E2s_v3" = 4
        "Standard_E4s_v3" = 8
        "Standard_E8s_v3" = 16
        "Standard_E16s_v3" = 32
        "Standard_E20s_v3" = 32
        "Standard_E32s_v3" = 32
        "Standard_E48s_v3" = 32
        "Standard_E64s_v3" = 32
        
        # ES-Series v4
        "Standard_E2s_v4" = 4
        "Standard_E4s_v4" = 8
        "Standard_E8s_v4" = 16
        "Standard_E16s_v4" = 32
        "Standard_E20s_v4" = 32
        "Standard_E32s_v4" = 32
        "Standard_E48s_v4" = 32
        "Standard_E64s_v4" = 32
        
        # ES-Series v5
        "Standard_E2s_v5" = 4
        "Standard_E4s_v5" = 8
        "Standard_E8s_v5" = 16
        "Standard_E16s_v5" = 32
        "Standard_E20s_v5" = 32
        "Standard_E32s_v5" = 32
        "Standard_E48s_v5" = 32
        "Standard_E64s_v5" = 32
        "Standard_E96s_v5" = 32
        
        # F-Series
        "Standard_F1" = 4
        "Standard_F2" = 8
        "Standard_F4" = 16
        "Standard_F8" = 32
        "Standard_F16" = 64
        
        # FS-Series
        "Standard_F1s" = 4
        "Standard_F2s" = 8
        "Standard_F4s" = 16
        "Standard_F8s" = 32
        "Standard_F16s" = 64
        
        # F-Series v2
        "Standard_F2s_v2" = 4
        "Standard_F4s_v2" = 8
        "Standard_F8s_v2" = 16
        "Standard_F16s_v2" = 32
        "Standard_F32s_v2" = 32
        "Standard_F48s_v2" = 32
        "Standard_F64s_v2" = 32
        "Standard_F72s_v2" = 32
        
        # G-Series
        "Standard_G1" = 8
        "Standard_G2" = 16
        "Standard_G3" = 32
        "Standard_G4" = 64
        "Standard_G5" = 64
        
        # GS-Series
        "Standard_GS1" = 8
        "Standard_GS2" = 16
        "Standard_GS3" = 32
        "Standard_GS4" = 64
        "Standard_GS5" = 64
        
        # H-Series
        "Standard_H8" = 32
        "Standard_H16" = 64
        "Standard_H8m" = 32
        "Standard_H16m" = 64
        "Standard_H16r" = 64
        "Standard_H16mr" = 64
        
        # HB-Series
        "Standard_HB60rs" = 4
        "Standard_HB120rs_v2" = 8
        "Standard_HB120rs_v3" = 32
        
        # HC-Series
        "Standard_HC44rs" = 4
        
        # L-Series
        "Standard_L4s" = 16
        "Standard_L8s" = 32
        "Standard_L16s" = 64
        "Standard_L32s" = 64
        
        # L-Series v2
        "Standard_L8s_v2" = 32
        "Standard_L16s_v2" = 64
        "Standard_L32s_v2" = 64
        "Standard_L48s_v2" = 64
        "Standard_L64s_v2" = 64
        "Standard_L80s_v2" = 64
        
        # L-Series v3
        "Standard_L8s_v3" = 32
        "Standard_L16s_v3" = 32
        "Standard_L32s_v3" = 32
        "Standard_L48s_v3" = 32
        "Standard_L64s_v3" = 32
        "Standard_L80s_v3" = 32
        
        # M-Series
        "Standard_M8ms" = 8
        "Standard_M16ms" = 16
        "Standard_M32ms" = 32
        "Standard_M64ms" = 64
        "Standard_M64s" = 64
        "Standard_M128ms" = 64
        "Standard_M128s" = 64
        "Standard_M64" = 64
        "Standard_M64m" = 64
        "Standard_M128" = 64
        "Standard_M128m" = 64
        
        # M-Series v2
        "Standard_M192is_v2" = 64
        "Standard_M192i_v2" = 64
        "Standard_M192ims_v2" = 64
        "Standard_M192im_v2" = 64
        
        # N-Series
        "Standard_NC6" = 24
        "Standard_NC12" = 48
        "Standard_NC24" = 64
        "Standard_NC24r" = 64
        
        # NC-Series v2
        "Standard_NC6s_v2" = 12
        "Standard_NC12s_v2" = 24
        "Standard_NC24s_v2" = 32
        "Standard_NC24rs_v2" = 32
        
        # NC-Series v3
        "Standard_NC6s_v3" = 12
        "Standard_NC12s_v3" = 24
        "Standard_NC24s_v3" = 32
        "Standard_NC24rs_v3" = 32
        
        # ND-Series
        "Standard_ND6s" = 12
        "Standard_ND12s" = 24
        "Standard_ND24s" = 32
        "Standard_ND24rs" = 32
        
        # ND-Series v2
        "Standard_ND40rs_v2" = 32
        
        # NV-Series
        "Standard_NV6" = 24
        "Standard_NV12" = 48
        "Standard_NV24" = 64
        
        # NV-Series v2
        "Standard_NV6s_v2" = 12
        "Standard_NV12s_v2" = 24
        "Standard_NV24s_v2" = 32
        
        # NV-Series v3
        "Standard_NV12s_v3" = 24
        "Standard_NV24s_v3" = 32
        "Standard_NV48s_v3" = 32
        
        # NV-Series v4
        "Standard_NV4as_v4" = 4
        "Standard_NV8as_v4" = 8
        "Standard_NV16as_v4" = 16
        "Standard_NV32as_v4" = 32
        
        # DC-Series
        "Standard_DC1s_v2" = 1
        "Standard_DC2s_v2" = 2
        "Standard_DC4s_v2" = 4
        "Standard_DC8s_v2" = 8
        
        # DC-Series v3
        "Standard_DC1s_v3" = 1
        "Standard_DC2s_v3" = 2
        "Standard_DC4s_v3" = 4
        "Standard_DC8s_v3" = 8
        "Standard_DC16s_v3" = 16
        "Standard_DC32s_v3" = 32
        "Standard_DC48s_v3" = 32
        
        # Additional newer series that might not be widely documented
        # Add more as Azure releases new series
    }
    
    if ($vmSizeLimits.ContainsKey($VMSize)) {
        return $vmSizeLimits[$VMSize]
    } else {
        Write-Warning "VM Size '$VMSize' not found in the predefined list. Please check Azure documentation for this size."
        return -1
    }
}

# Function to find VM across all subscriptions
function Find-VMInSubscriptions {
    param(
        [string]$VMName,
        [string]$ResourceGroup
    )
    
    $subscriptions = Get-AzSubscription
    
    foreach ($subscription in $subscriptions) {
        try {
            Set-AzContext -SubscriptionId $subscription.Id -ErrorAction SilentlyContinue | Out-Null
            
            # Try to find the VM in this subscription
            $vm = Get-AzVM -ResourceGroupName $ResourceGroup -Name $VMName -ErrorAction SilentlyContinue
            
            if ($vm) {
                return @{
                    VM = $vm
                    Subscription = $subscription
                }
            }
        } catch {
            # Continue to next subscription if this one fails
            continue
        }
    }
    
    return $null
}

# Check if Azure PowerShell module is installed
$requiredModules = @('Az.Accounts', 'Az.Compute', 'Az.Profile')
foreach ($module in $requiredModules) {
    if (-not (Get-Module -ListAvailable -Name $module)) {
        Write-Error "Azure PowerShell module ($module) is not installed. Please install it using: Install-Module -Name Az"
        exit 1
    }
}

# Import required modules
foreach ($module in $requiredModules) {
    Import-Module $module -Force
}

# Check if user is logged in to Azure
$context = Get-AzContext
if (-not $context) {
    Write-Host "Please log in to Azure..." -ForegroundColor Yellow
    Connect-AzAccount
}

# Read the input CSV file
if (-not (Test-Path $InputCsvPath)) {
    Write-Error "Input CSV file '$InputCsvPath' not found."
    exit 1
}

$inputData = Import-Csv $InputCsvPath

# Validate required columns
$requiredColumns = @('VMName', 'ResourceGroup', 'CurrentSize', 'NewSize')
$csvColumns = $inputData | Get-Member -MemberType NoteProperty | Select-Object -ExpandProperty Name

foreach ($column in $requiredColumns) {
    if ($column -notin $csvColumns) {
        Write-Error "Required column '$column' not found in CSV. Required columns: $($requiredColumns -join ', ')"
        exit 1
    }
}

# Get all accessible subscriptions
Write-Host "Getting list of accessible subscriptions..." -ForegroundColor Green
$allSubscriptions = Get-AzSubscription
Write-Host "Found $($allSubscriptions.Count) accessible subscriptions" -ForegroundColor Green

# Initialize results array
$results = @()

Write-Host "`nProcessing VMs across all subscriptions..." -ForegroundColor Green

foreach ($vmInfo in $inputData) {
    Write-Host "Processing VM: $($vmInfo.VMName) in RG: $($vmInfo.ResourceGroup)" -ForegroundColor Yellow
    
    try {
        # Find the VM across all subscriptions
        $vmResult = Find-VMInSubscriptions -VMName $vmInfo.VMName -ResourceGroup $vmInfo.ResourceGroup
        
        if ($vmResult) {
            $azVM = $vmResult.VM
            $subscription = $vmResult.Subscription
            
            Write-Host "  Found in subscription: $($subscription.Name) ($($subscription.Id))" -ForegroundColor Cyan
            
            # Count attached data disks (excluding OS disk)
            $currentDataDiskCount = $azVM.StorageProfile.DataDisks.Count
            
            # Get max disks for current and new sizes
            $currentMaxDisks = Get-MaxDataDisks -VMSize $vmInfo.CurrentSize
            $newMaxDisks = Get-MaxDataDisks -VMSize $vmInfo.NewSize
            
            # Determine compatibility
            $isCompatible = ($currentDataDiskCount -le $newMaxDisks) -and ($newMaxDisks -ne -1)
            $resizeRecommendation = if ($newMaxDisks -eq -1) { 
                "REVIEW REQUIRED - UNKNOWN VM SIZE" 
            } elseif ($isCompatible) { 
                "SAFE TO RESIZE" 
            } else { 
                "RESIZE BLOCKED - TOO MANY DISKS" 
            }
            
            # Create result object
            $result = [PSCustomObject]@{
                VMName = $vmInfo.VMName
                ResourceGroup = $vmInfo.ResourceGroup
                SubscriptionId = $subscription.Id
                SubscriptionName = $subscription.Name
                CurrentSize = $vmInfo.CurrentSize
                NewSize = $vmInfo.NewSize
                CurrentDataDiskCount = $currentDataDiskCount
                CurrentSizeMaxDisks = $currentMaxDisks
                NewSizeMaxDisks = $newMaxDisks
                IsResizeCompatible = $isCompatible
                ResizeRecommendation = $resizeRecommendation
                Notes = if ($newMaxDisks -eq -1) { 
                    "New VM size '$($vmInfo.NewSize)' not found in predefined list - manual verification required" 
                } elseif (-not $isCompatible) { 
                    "Current VM has $currentDataDiskCount data disks, but new size only supports $newMaxDisks" 
                } else { 
                    "Resize is safe from disk perspective" 
                }
            }
            
            $results += $result
            
            Write-Host "  ✓ Current disks: $currentDataDiskCount, New max: $newMaxDisks, Compatible: $isCompatible" -ForegroundColor $(if($isCompatible){"Green"}else{"Red"})
            
        } else {
            Write-Warning "VM '$($vmInfo.VMName)' not found in any accessible subscription"
            
            # Add not found result
            $result = [PSCustomObject]@{
                VMName = $vmInfo.VMName
                ResourceGroup = $vmInfo.ResourceGroup
                SubscriptionId = "NOT FOUND"
                SubscriptionName = "NOT FOUND"
                CurrentSize = $vmInfo.CurrentSize
                NewSize = $vmInfo.NewSize
                CurrentDataDiskCount = "NOT FOUND"
                CurrentSizeMaxDisks = Get-MaxDataDisks -VMSize $vmInfo.CurrentSize
                NewSizeMaxDisks = Get-MaxDataDisks -VMSize $vmInfo.NewSize
                IsResizeCompatible = "NOT FOUND"
                ResizeRecommendation = "VM NOT FOUND"
                Notes = "VM not found in any accessible subscription or insufficient permissions"
            }
            
            $results += $result
        }
        
    } catch {
        Write-Warning "Failed to process VM '$($vmInfo.VMName)': $($_.Exception.Message)"
        
        # Add error result
        $result = [PSCustomObject]@{
            VMName = $vmInfo.VMName
            ResourceGroup = $vmInfo.ResourceGroup
            SubscriptionId = "ERROR"
            SubscriptionName = "ERROR"
            CurrentSize = $vmInfo.CurrentSize
            NewSize = $vmInfo.NewSize
            CurrentDataDiskCount = "ERROR"
            CurrentSizeMaxDisks = Get-MaxDataDisks -VMSize $vmInfo.CurrentSize
            NewSizeMaxDisks = Get-MaxDataDisks -VMSize $vmInfo.NewSize
            IsResizeCompatible = "ERROR"
            ResizeRecommendation = "ERROR - COULD NOT ANALYZE"
            Notes = "Error: $($_.Exception.Message)"
        }
        
        $results += $result
    }
}

# Export results to CSV
$results | Export-Csv -Path $OutputCsvPath -NoTypeInformation

Write-Host "`nAnalysis complete!" -ForegroundColor Green
Write-Host "Results saved to: $OutputCsvPath" -ForegroundColor Green

# Display summary
$totalVMs = $results.Count
$compatibleVMs = ($results | Where-Object { $_.IsResizeCompatible -eq $true }).Count
$incompatibleVMs = ($results | Where-Object { $_.IsResizeCompatible -eq $false }).Count
$errorVMs = ($results | Where-Object { $_.IsResizeCompatible -eq "ERROR" }).Count
$notFoundVMs = ($results | Where-Object { $_.IsResizeCompatible -eq "NOT FOUND" }).Count
$reviewRequiredVMs = ($results | Where-Object { $_.ResizeRecommendation -like "*REVIEW REQUIRED*" }).Count

Write-Host "`n=== SUMMARY ===" -ForegroundColor Cyan
Write-Host "Total VMs analyzed: $totalVMs" -ForegroundColor White
Write-Host "Compatible for resize: $compatibleVMs" -ForegroundColor Green
Write-Host "Incompatible for resize: $incompatibleVMs" -ForegroundColor Red
Write-Host "Require manual review: $reviewRequiredVMs" -ForegroundColor Yellow
Write-Host "VMs not found: $notFoundVMs" -ForegroundColor Magenta
Write-Host "Errors during analysis: $errorVMs" -ForegroundColor Red

if ($incompatibleVMs -gt 0) {
    Write-Host "`nVMs with disk compatibility issues:" -ForegroundColor Red
    $results | Where-Object { $_.IsResizeCompatible -eq $false } | ForEach-Object {
        Write-Host "  - $($_.VMName) [$($_.SubscriptionName)]: $($_.CurrentDataDiskCount) disks, new size supports max $($_.NewSizeMaxDisks)" -ForegroundColor Red
    }
}

if ($reviewRequiredVMs -gt 0) {
    Write-Host "`nVMs requiring manual review (unknown VM sizes):" -ForegroundColor Yellow
    $results | Where-Object { $_.ResizeRecommendation -like "*REVIEW REQUIRED*" } | ForEach-Object {
        Write-Host "  - $($_.VMName) [$($_.SubscriptionName)]: New size '$($_.NewSize)' needs verification" -ForegroundColor Yellow
    }
}

if ($notFoundVMs -gt 0) {
    Write-Host "`nVMs not found in any subscription:" -ForegroundColor Magenta
    $results | Where-Object { $_.IsResizeCompatible -eq "NOT FOUND" } | ForEach-Object {
        Write-Host "  - $($_.VMName) in RG: $($_.ResourceGroup)" -ForegroundColor Magenta
    }
}

Write-Host "`nSubscriptions processed:" -ForegroundColor Cyan
$allSubscriptions | ForEach-Object {
    Write-Host "  - $($_.Name) ($($_.Id))" -ForegroundColor White
}
