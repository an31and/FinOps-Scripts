# User-defined variables
$ResourceGroupName = "YourResourceGroup"  # Replace with your resource group name
$VMName = "YourVM"                        # Replace with your virtual machine name

# Define business hours (24-hour format)
$BusinessStartHour = 8    # 8 AM
$BusinessEndHour   = 18   # 6 PM

# Optional: Uncomment the following line if not using a Managed Identity
# Connect-AzAccount

# Retrieve current date and time
$CurrentDate = Get-Date
$CurrentHour = $CurrentDate.Hour
$CurrentDay = $CurrentDate.DayOfWeek.ToString()

Write-Output "Today is $CurrentDay at hour $CurrentHour (24h format)."

# Retrieve the current status of the VM
$vm = Get-AzVM -ResourceGroupName $ResourceGroupName -Name $VMName -Status
$vmStatus = ($vm.Statuses | Where-Object { $_.Code -like "PowerState/*" }).Code
Write-Output "Current VM status is: $vmStatus"

# Define desired action based on day and time
if ($CurrentDay -in @("Monday", "Tuesday", "Wednesday", "Thursday", "Friday")) {
    if (($CurrentHour -ge $BusinessStartHour) -and ($CurrentHour -lt $BusinessEndHour)) {
        Write-Output "Business hours detected. Desired state: Running."
        if ($vmStatus -ne "PowerState/running") {
            Write-Output "VM is not running. Starting the VM..."
            Start-AzVM -ResourceGroupName $ResourceGroupName -Name $VMName -NoWait
        }
        else {
            Write-Output "VM is already running. No action needed."
        }
    }
    else {
        Write-Output "Outside business hours. Desired state: Stopped."
        if ($vmStatus -eq "PowerState/running") {
            Write-Output "VM is running. Stopping the VM..."
            Stop-AzVM -ResourceGroupName $ResourceGroupName -Name $VMName -Force -NoWait
        }
        else {
            Write-Output "VM is already stopped. No action needed."
        }
    }
}
else {
    Write-Output "Weekend detected. Desired state: Stopped."
    if ($vmStatus -eq "PowerState/running") {
        Write-Output "VM is running. Stopping the VM..."
        Stop-AzVM -ResourceGroupName $ResourceGroupName -Name $VMName -Force -NoWait
    }
    else {
        Write-Output "VM is already stopped. No action needed."
    }
}
