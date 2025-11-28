<#
.SYNOPSIS
    Azure VM Resizing Script with Logging and CloudShell Support

.VERSION
    1.1.4

.DESCRIPTION
    This script resizes Azure VMs based on a provided CSV input. It includes logging, dry run support,
    CloudShell compatibility, and optional Azure Storage logging.

.PARAMETERS
    -CsvPath: Path to input CSV (Name, SubscriptionId, OldSize, NewSize, ResourceGroup)
    -DryRun: If $true, does not execute actual resizing
    -UseAzureStorage: If $true, uploads logs to Azure Storage
    -StorageAccountName: Name of the Azure Storage account
    -StorageContainerName: Container name in the Azure Storage account
#>
param (
    [string]$CsvPath = "PATH_TO_server.csv",
    [bool]$DryRun = $false,
    [bool]$UseAzureStorage = $false,
    [string]$StorageAccountName = "",
    [string]$StorageContainerName = "",
    [string]$LogFileName = "ResizeToNewSize_$((Get-Date).ToString('yyyyMMdd-HHmmss')).csv"
)

function Write-Log {
    param (
        [string]$Message,
        [string]$Level = "INFO"
    )
    $timestamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
    $entry = "[$timestamp] [$Level] $Message"
    Write-Output $entry
    Add-Content -Path $Global:LogFilePath -Value $entry
}

function Upload-ToAzureStorage {
    param (
        [string]$StorageAccount,
        [string]$ContainerName,
        [string]$FilePath,
        [string]$BlobName
    )
    try {
        $context = (Get-AzStorageAccount -Name $StorageAccount).Context
        Set-AzStorageBlobContent -File $FilePath -Container $ContainerName -Blob $BlobName -Context $context | Out-Null
        Write-Log "Uploaded $FilePath to container '$ContainerName' as blob '$BlobName'" "INFO"
    } catch {
        Write-Log "Failed to upload $FilePath to Azure Storage: $_" "ERROR"
    }
}

# Define paths
$OutputDirectory = "$HOME/VMResizeLogs"
if (!(Test-Path -Path $OutputDirectory)) {
    New-Item -ItemType Directory -Path $OutputDirectory | Out-Null
}
$Global:LogFilePath = Join-Path $OutputDirectory $LogFileName

# Login check (CloudShell safe)
try { Get-AzContext | Out-Null } catch { Connect-AzAccount }

# Import CSV
$servers = Import-Csv -Path $CsvPath
$total = $servers.Count
$counter = 0
$results = @()

foreach ($server in $servers) {
    $counter++
    $progress = [math]::Round(($counter / $total) * 100, 0)
    Write-Progress -Activity "Resizing VMs" -Status "$progress% Complete" -PercentComplete $progress

    $vmName = $server.Name
    $subscriptionId = $server.SubscriptionId
    $newSize = $server.NewSize
    $oldSize = $server.OldSize
    $resourceGroup = $server.ResourceGroup

    try {
        Write-Log "Processing $vmName in subscription $subscriptionId"

        az account set --subscription $subscriptionId

        if ($DryRun) {
            Write-Log "[DRY RUN] Would resize VM '$vmName' from $oldSize to $newSize in $resourceGroup"
            $status = "DryRun"
        } else {
            az vm resize --resource-group $resourceGroup --name $vmName --size $newSize

            # Wait until VM is running under the new size
            $maxAttempts = 20
            $attempt = 0
            $vmRunning = $false
            $skuMatched = $false

            while ($attempt -lt $maxAttempts) {
                Start-Sleep -Seconds 15
                $vmStatus = az vm get-instance-view --resource-group $resourceGroup --name $vmName --query "instanceView.statuses[?starts_with(code, 'PowerState/')].displayStatus" -o tsv
                $vmSize = az vm show --resource-group $resourceGroup --name $vmName --query "hardwareProfile.vmSize" -o tsv

                if ($vmStatus -eq "VM running" -and $vmSize -eq $newSize) {
                    $vmRunning = $true
                    $skuMatched = $true
                    break
                }

                $attempt++
            }

            if (-not $vmRunning -and $vmStatus -ne "VM running") {
                Write-Log "VM '$vmName' is not running after resize. Attempting to start..."
                try {
                    az vm start --resource-group $resourceGroup --name $vmName
                    Start-Sleep -Seconds 30
                    $vmStatus = az vm get-instance-view --resource-group $resourceGroup --name $vmName --query "instanceView.statuses[?starts_with(code, 'PowerState/')].displayStatus" -o tsv
                    if ($vmStatus -eq "VM running") {
                        $vmRunning = $true
                    }
                } catch {
                    Write-Log "Failed to auto-start VM '$vmName': $_" "ERROR"
                }
            }

            if ($vmRunning -and $skuMatched) {
                Write-Log "VM '$vmName' is now running under size '$newSize'"
                $status = "Success"
            } else {
                Write-Log "Validation failed for VM '$vmName': Status='$vmStatus', Size='$vmSize' (expected '$newSize')" "ERROR"
                $status = "ValidationFailed"
            }
        }
    } catch {
        Write-Log "Failed to resize ${vmName}: $_" "ERROR"
        $status = "Failed"
    }

    $results += [PSCustomObject]@{
        VMName = $vmName
        SubscriptionId = $subscriptionId
        ResourceGroup = $resourceGroup
        OldSize = $oldSize
        NewSize = $newSize
        Status = $status
    }
}

# Export results
$csvOutputPath = Join-Path $OutputDirectory $LogFileName
$results | Export-Csv -Path $csvOutputPath -NoTypeInformation
Write-Log "Exported results to $csvOutputPath"

# Upload to Azure Storage if needed
if ($UseAzureStorage -and $StorageAccountName -and $StorageContainerName) {
    Upload-ToAzureStorage -StorageAccount $StorageAccountName -ContainerName $StorageContainerName -FilePath $csvOutputPath -BlobName $LogFileName
}


# -------------------------------
# Final Execution Summary
# -------------------------------
$summary = $results | Group-Object -Property Status | ForEach-Object {
    [PSCustomObject]@{
        Status = $_.Name
        Count = $_.Count
    }
}
Write-Output "`nResize Execution Summary:"
$summary | Format-Table -AutoSize | Out-String | Write-Output
