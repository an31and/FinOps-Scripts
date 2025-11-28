<#
    Script Name: ResizeResources.ps1
    Version: 1.14
    Last Updated: 2025-03-09
    Author: Patrick Warnke - AHEAD

    Description:
    ------------
    This script reads from a CSV that contains Azure resource IDs (both VMs and Disks),
    along with the desired new size/SKU. It determines which Azure CLI commands to run
    based on whether the resource is a VM or a Disk. Disks attached to a running VM
    are deallocated before re-tiering, and then the VM is started again if it was originally running.
    
    In this version every interaction with Azure (commands executed and their outputs) is logged into a
    DebugLog field, which is written to the CSV for detailed troubleshooting.
    
    **Change:**  
    The VM power state retrieval command was updated to use the displayStatus from the
    statuses array:
      --query "instanceView.statuses[?starts_with(code, 'PowerState/')].displayStatus"
    
    Change Log:
    -----------
    1.13  - Captures and logs all Azure CLI commands and outputs into a DebugLog column in the CSV.
    1.13.2 - Added null/empty checks and clearer error messages for retrieving VM power state.
    1.14  - Updated the VM power state command to use the statuses displayStatus query.
#>

# -------------------------
#   User-Editable Variables
# -------------------------
$UserCSVPathCloudShell = "$HOME/server.csv"   
$UserCSVPathWindows    = "$HOME\NewResizing\server.csv"    
$UserCSVPathMacOS      = "$HOME/NewResizing/server.csv"    
$UserCSVPathLinux      = "$HOME/NewResizing/server.csv"    

$UserLogDirectoryCloudShell = "$HOME"                          
$UserLogDirectoryWindows    = "$HOME\NewResizing\Logs"           
$UserLogDirectoryMacOS      = "$HOME/NewResizing/Logs"           
$UserLogDirectoryLinux      = "$HOME/NewResizing/Logs"           

$UserLogFilePrefix = "ResizeToNewSize_Log_"

# -------------------------
#   Helper Functions: Environment Detection
# -------------------------
function Test-RunningInCloudShell {
    return (Test-Path "$HOME/.Azure")
}

function Get-OSPlatform {
    if ($IsWindows) {
        return "Windows"
    } elseif ($IsMacOS) {
        return "MacOS"
    } elseif ($IsLinux) {
        return "Linux"
    } else {
        throw "Unsupported OS platform"
    }
}

# -------------------------
#   Environment-Specific Path Setup
# -------------------------
if (Test-RunningInCloudShell) {
    Write-Host "Running in Cloud Shell environment."
    $csvPath = $UserCSVPathCloudShell
    $logDirectory = $UserLogDirectoryCloudShell
} else {
    $platform = Get-OSPlatform
    Write-Host "Running on local platform: $platform"
    if ($platform -eq "Windows") {
         $csvPath = $UserCSVPathWindows
         $logDirectory = $UserLogDirectoryWindows
    } elseif ($platform -eq "MacOS") {
         $csvPath = $UserCSVPathMacOS
         $logDirectory = $UserLogDirectoryMacOS
    } elseif ($platform -eq "Linux") {
         $csvPath = $UserCSVPathLinux
         $logDirectory = $UserLogDirectoryLinux
    }
}

# Log in to Azure if not running in Cloud Shell (Cloud Shell is already authenticated)
if (-not (Test-RunningInCloudShell)) {
    Write-Host "Not running in Cloud Shell. Initiating az login..."
    az login | Out-Null
}

# Ensure the log directory exists
if (-not (Test-Path $logDirectory)) {
    New-Item -ItemType Directory -Path $logDirectory -Force | Out-Null
}

# Define log file name using current date
$currentDate   = Get-Date -Format "yyyyMMdd"
$logFilePath = Join-Path $logDirectory ("{0}{1}.csv" -f $UserLogFilePrefix, $currentDate)

# Remove any pre-existing log file for this run
if (Test-Path $logFilePath) {
    Remove-Item $logFilePath -Force
}

# -------------------------
#   Import CSV
# -------------------------
$resources = Import-Csv -Path $csvPath

# -------------------------
#   Helper Function: Convert-ResourceId
# -------------------------
function Convert-ResourceId {
    param(
        [string]$ResourceId
    )
    $parts = $ResourceId -split '/'
    $subscriptionId = $parts[2]
    $resourceGroup  = $parts[4]
    $provider       = $parts[6]
    $resourceType   = $parts[7]
    $resourceName   = $parts[8]
    return [PSCustomObject]@{
        SubscriptionId = $subscriptionId
        ResourceGroup  = $resourceGroup
        Provider       = $provider
        ResourceType   = $resourceType
        ResourceName   = $resourceName
    }
}

# -------------------------
#   Main Loop: Process Each Resource
# -------------------------
foreach ($item in $resources) {
    $debugLog = ""

    $resourceId = $item.ResourceId
    $oldSize    = $item.OldSize
    $newSize    = $item.NewSize

    $parsed = Convert-ResourceId -ResourceId $resourceId
    $subscriptionId = $parsed.SubscriptionId
    $resourceGroup  = $parsed.ResourceGroup
    $resourceType   = $parsed.ResourceType
    $resourceName   = $parsed.ResourceName

    $originalPowerState = $null
    $status       = "Success"
    $errorMessage = ""

    try {
        # Switch subscription
        $debugLog += "Setting subscription context to $subscriptionId`n"
        az account set --subscription $subscriptionId
        $debugLog += "Subscription set.`n"

        if ($resourceType -eq "virtualMachines") {
            # VM Resize Logic
            $debugLog += "Getting power state for VM $resourceName in RG $resourceGroup.`n"
            $azOutput = az vm get-instance-view --name $resourceName --resource-group $resourceGroup --query "instanceView.statuses[?starts_with(code, 'PowerState/')].displayStatus" -o tsv
            $debugLog += "Get VM power state output: $azOutput`n"
            if (-not $azOutput) {
                throw "Unable to retrieve power state for VM $resourceName in RG $resourceGroup. Possibly VM not found or insufficient permissions."
            }
            $originalPowerState = $azOutput.Trim()

            if ($originalPowerState -match "running")    { $originalPowerState = "VM running" }
            elseif ($originalPowerState -match "stopped") { $originalPowerState = "VM stopped" }
            elseif ($originalPowerState -match "deallocated") { $originalPowerState = "VM deallocated" }

            if ($originalPowerState -eq "VM running") {
                $debugLog += "VM $resourceName is running. Deallocating...`n"
                $azOutput = az vm deallocate --resource-group $resourceGroup --name $resourceName
                $debugLog += "Deallocate VM output: $azOutput`n"
            }

            $debugLog += "Resizing VM $resourceName to size $newSize.`n"
            $azOutput = az vm resize --resource-group $resourceGroup --name $resourceName --size $newSize
            $debugLog += "Resize VM output: $azOutput`n"

            if ($originalPowerState -eq "VM running") {
                $debugLog += "Starting VM $resourceName.`n"
                $azOutput = az vm start --resource-group $resourceGroup --name $resourceName
                $debugLog += "Start VM output: $azOutput`n"
            }
        }
        elseif ($resourceType -eq "disks") {
            # Disk Resize/Re-tier Logic
            $debugLog += "Re-tiering Disk $resourceName to SKU $newSize.`n"
            $azOutput = az disk show --ids $resourceId --query "managedBy" -o tsv
            $debugLog += "Disk show output for ${resourceName}: $azOutput`n"
            $vmAttached = $azOutput

            if (-not [string]::IsNullOrEmpty($vmAttached)) {
                $debugLog += "Disk $resourceName is attached to VM: $vmAttached`n"
                $attachedVm = Convert-ResourceId -ResourceId $vmAttached
                $vmRG   = $attachedVm.ResourceGroup
                $vmName = $attachedVm.ResourceName

                $debugLog += "Getting power state for attached VM $vmName in RG $vmRG.`n"
                $azOutput = az vm get-instance-view --name $vmName --resource-group $vmRG --query "instanceView.statuses[?starts_with(code, 'PowerState/')].displayStatus" -o tsv
                $debugLog += "Get VM power state output for ${vmName}: $azOutput`n"
                if (-not $azOutput) {
                    throw "Unable to retrieve power state for VM $vmName in RG $vmRG. Possibly VM not found or insufficient permissions."
                }
                $originalPowerState = $azOutput.Trim()

                if ($originalPowerState -match "running")       { $originalPowerState = "VM running" }
                elseif ($originalPowerState -match "deallocated") { $originalPowerState = "VM deallocated" }
                elseif ($originalPowerState -match "stopped")   { $originalPowerState = "VM stopped" }

                if ($originalPowerState -eq "VM running") {
                    $debugLog += "Attached VM $vmName is running. Deallocating before disk re-tier...`n"
                    $azOutput = az vm deallocate --resource-group $vmRG --name $vmName
                    $debugLog += "Deallocate VM output for ${vmName}: $azOutput`n"

                    $maxWaitTime  = 300
                    $waitInterval = 10
                    $elapsed      = 0

                    do {
                        $azOutput = az vm get-instance-view --name $vmName --resource-group $vmRG --query "instanceView.statuses[?starts_with(code, 'PowerState/')].displayStatus" -o tsv
                        $currentState = $azOutput.Trim()
                        $debugLog += "Polling VM $vmName, current state: $currentState`n"
                        if ($currentState -match "deallocated") { break }
                        Start-Sleep -Seconds $waitInterval
                        $elapsed += $waitInterval
                    } while ($elapsed -lt $maxWaitTime)

                    if (-not ($currentState -match "deallocated")) {
                        throw "VM $vmName did not reach a deallocated state after waiting $maxWaitTime seconds. Current state: $currentState"
                    }
                }

                $debugLog += "Updating disk $resourceName SKU to $newSize.`n"
                $azOutput = az disk update --ids $resourceId --set sku.name=$newSize
                $debugLog += "Disk update output for ${resourceName}: $azOutput`n"

                if ($originalPowerState -eq "VM running") {
                    $debugLog += "Starting attached VM $vmName.`n"
                    $azOutput = az vm start --resource-group $vmRG --name $vmName
                    $debugLog += "Start VM output for ${vmName}: $azOutput`n"
                }
            }
            else {
                $debugLog += "Disk $resourceName is not attached to any VM. Re-tiering directly.`n"
                $azOutput = az disk update --ids $resourceId --set sku.name=$newSize
                $debugLog += "Disk update output for ${resourceName}: $azOutput`n"
            }
        }
        else {
            $status = "Skipped"
            $errorMessage = "Unknown resource type: $resourceType"
            $debugLog += "Skipping unknown resource type in Resource ID: $resourceId`n"
            Write-Host "Skipping unknown resource type in Resource ID: $resourceId"
        }
    }
    catch {
        $status = "Failed"
        $errorMessage = $_.Exception.Message
        $debugLog += "Error occurred on resource ${resourceName}: $errorMessage`n"
        Write-Host "Error occurred on resource '$resourceName': $errorMessage"
    }

    $logRecord = [PSCustomObject]@{
        ResourceId     = $resourceId
        ResourceType   = $resourceType
        SubscriptionId = $subscriptionId
        ResourceGroup  = $resourceGroup
        ResourceName   = $resourceName
        OldSize        = $oldSize
        NewSize        = $newSize
        Status         = $status
        ErrorMessage   = $errorMessage
        Timestamp      = (Get-Date).ToString("yyyy-MM-dd HH:mm:ss")
        DebugLog       = $debugLog
    }

    if (-not (Test-Path $logFilePath)) {
        $logRecord | Export-Csv -Path $logFilePath -NoTypeInformation -Encoding UTF8
    }
    else {
        $logRecord | Export-Csv -Path $logFilePath -Append -NoTypeInformation -Encoding UTF8
    }
}

Write-Host "`nAll done! Log file saved to: $logFilePath"
