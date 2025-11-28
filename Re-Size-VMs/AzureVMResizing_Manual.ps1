# Define the current date in YYYYMMdd format
$currentDate = Get-Date -Format "yyyyMMdd"

# Define the path for the CSV log file with the date appended
$logFilePath = "/home/<username>/ResizeToNewSize_Log_$currentDate.csv"  # Change <username> to your Cloud Shell username

# Import the server list from the CSV file
$servers = Import-Csv -Path "/home/<username>/New resizing/server.csv"  # Update the path as needed

# Initialize an array to store log entries
$logEntries = @()

foreach ($server in $servers) {
    # Initialize variable to track original power state
    $originalPowerState = $null
    
    try {
        # Set the subscription context for each server
        $subscriptionId = $server.SubscriptionId
        az account set --subscription $subscriptionId

        # Resize the VM to NewSize
        $vmName = $server.Name
        $newSize = $server.NewSize
        $resourceGroup = $server.ResourceGroup  # Get the resource group from the CSV

        # Get the current power state of the VM
        $originalPowerState = az vm show --name $vmName --resource-group $resourceGroup --query "powerState" -o tsv

        # Stop and deallocate the VM if it is powered on
        if ($originalPowerState -ne "VM deallocated" -and $originalPowerState -ne "VM stopped") {
            Write-Host "Stopping and deallocating VM: $vmName in Resource Group: $resourceGroup"
            az vm stop --resource-group $resourceGroup --name $vmName
            az vm deallocate --resource-group $resourceGroup --name $vmName
        }

        # Resize the VM using Azure CLI
        Write-Host "Resizing VM: $vmName to Size: $newSize"
        az vm resize --resource-group $resourceGroup --name $vmName --size $newSize

        # Start the VM if it was originally powered on
        if ($originalPowerState -ne "VM deallocated" -and $originalPowerState -ne "VM stopped") {
            Write-Host "Starting VM: $vmName"
            az vm start --resource-group $resourceGroup --name $vmName
        }

        # Log the successful operation
        $logEntries += [PSCustomObject]@{
            VMName          = $vmName
            SubscriptionId  = $subscriptionId
            OldSize         = $server.OldSize
            NewSize         = $newSize
            Status          = "Success"
            Timestamp       = (Get-Date).ToString("yyyy-MM-dd HH:mm:ss")
        }
    } catch {
        # Log any errors and leave the VM in its original power state
        Write-Host "Error occurred: $_.Exception.Message"
        $logEntries += [PSCustomObject]@{
            VMName          = $vmName
            SubscriptionId  = $subscriptionId
            OldSize         = $server.OldSize
            NewSize         = $newSize
            Status          = "Failed"
            ErrorMessage    = $_.Exception.Message
            Timestamp       = (Get-Date).ToString("yyyy-MM-dd HH:mm:ss")
        }

        # Log the original power state
        if ($originalPowerState -eq "VM deallocated") {
            Write-Host "VM '$vmName' remains deallocated."
        } elseif ($originalPowerState -eq "VM stopped") {
            Write-Host "VM '$vmName' remains stopped."
        } else {
            Write-Host "VM '$vmName' remains powered on."
        }
    }
}

# Export log entries to CSV
$logEntries | Export-Csv -Path $logFilePath -NoTypeInformation -Encoding UTF8
