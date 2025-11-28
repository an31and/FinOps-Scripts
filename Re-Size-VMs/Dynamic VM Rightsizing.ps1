# Import the Az module if not already installed
if (!(Get-Module -ListAvailable -Name Az)) {
    Write-Output "Installing Az module..."
    Install-Module -Name Az -Scope CurrentUser -Force -AllowClobber
}

Import-Module Az.Compute
Import-Module Az.Accounts

# Authenticate with Azure
Connect-AzAccount

# Path to the CSV file
$csvPath = "C:\path\to\Server.csv"

# Directory for log files (modify path as needed)
$logDir = "C:\path\to\logs"

# Ensure log directory exists
if (!(Test-Path -Path $logDir)) {
    New-Item -ItemType Directory -Path $logDir | Out-Null
}

# Get the log file path for the current month
$logFilePath = Join-Path -Path $logDir -ChildPath ("ResizeLog_" + (Get-Date -Format "yyyy-MM") + ".csv")

# Function to log resize events
function Log-ResizeEvent {
    param (
        [string]$vmName,
        [string]$action,
        [string]$oldSize,
        [string]$newSize,
        [string]$status
    )

    $timestamp = (Get-Date).ToString("yyyy-MM-dd HH:mm:ss")
    $logEntry = "$timestamp,$vmName,$action,$oldSize,$newSize,$status"

    # If log file does not exist, add headers
    if (!(Test-Path -Path $logFilePath)) {
        "Timestamp,VM Name,Action,Old Size,New Size,Status" | Out-File -FilePath $logFilePath -Encoding UTF8 -Append
    }

    # Append log entry
    $logEntry | Out-File -FilePath $logFilePath -Encoding UTF8 -Append
}

# Function to parse the time window
function Is-ScheduledTime {
    param (
        [string]$frequency,
        [string]$day,
        [string]$time
    )

    $currentDate = Get-Date
    $currentTime = $currentDate.ToString("HH:mm")

    switch ($frequency) {
        "Daily" { return $currentTime -eq $time }
        "Weekly" {
            return ($currentDate.DayOfWeek -eq $day) -and ($currentTime -eq $time)
        }
        "Monthly" {
            $scheduledDate = Get-ScheduledDate -day $day
            return ($currentDate.Date -eq $scheduledDate) -and ($currentTime -eq $time)
        }
        default { return $false }
    }
}

# Helper function to parse monthly schedules like "3rd Saturday"
function Get-ScheduledDate {
    param (
        [string]$day
    )

    $dayParts = $day.Split(' ')
    $occurrence = $dayParts[0]
    $dayOfWeek = $dayParts[1]

    $days = @("Sunday", "Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday")
    $dayNumber = $days.IndexOf($dayOfWeek)

    $today = Get-Date
    $dates = 1..31 | ForEach-Object {
        $date = Get-Date -Year $today.Year -Month $today.Month -Day $_ -ErrorAction SilentlyContinue
        if ($date -and $date.DayOfWeek -eq $dayNumber) { $date }
    }

    switch ($occurrence) {
        '1st' { return $dates[0] }
        '2nd' { return $dates[1] }
        '3rd' { return $dates[2] }
        '4th' { return $dates[3] }
        'Last' { return $dates[-1] }
        default { return $null }
    }
}

# Function to resize a VM
function Resize-VM {
    param (
        [string]$SubscriptionId,
        [string]$ResourceGroupName,
        [string]$VMName,
        [string]$NewSize,
        [string]$OldSize,
        [string]$Action
    )

    try {
        # Set the Azure subscription context
        Set-AzContext -SubscriptionId $SubscriptionId

        # Stop the VM before resizing
        Stop-AzVM -ResourceGroupName $ResourceGroupName -Name $VMName -NoWait -Force
        if ($LASTEXITCODE -ne 0) {
            Write-Output "The Stop-AzVM command failed with exit code $LASTEXITCODE."
            Exit 1
        }

        # Wait for VM to deallocate
        Write-Output "Waiting for VM $VMName to deallocate..."
        while ((Get-AzVM -ResourceGroupName $ResourceGroupName -Name $VMName).ProvisioningState -ne 'Succeeded') {
            Start-Sleep -Seconds 10
        }

        # Update the VM size
        Update-AzVM -ResourceGroupName $ResourceGroupName -VMName $VMName -VMSize $NewSize
        # Check the return code
        if ($LASTEXITCODE -ne 0) {
            Write-Output "The Update-AzVM command failed with exit code $LASTEXITCODE."
            Exit 1
        }

        # Start the VM after resizing
        Start-AzVM -ResourceGroupName $ResourceGroupName -Name $VMName
        # Check the return code
        if ($LASTEXITCODE -ne 0) {
            Write-Output "The Start-AzVM command failed with exit code $LASTEXITCODE."
            Exit 1
        }

        # Log the successful resizing action
        Log-ResizeEvent -vmName $VMName -action $Action -oldSize $OldSize -newSize $NewSize -status "Success"
    }
    catch {
        # Log failure
        Log-ResizeEvent -vmName $VMName -action $Action -oldSize $OldSize -newSize $NewSize -status "Failed"
    }
}

# Load CSV and loop through each row
Import-Csv -Path $csvPath | ForEach-Object {
    $vmName = $_.Name
    $subscriptionId = $_.SubscriptionId
    $resourceGroupName = $_.ResourceGroup
    $newSize = $_.NewSize
    $oldSize = $_.OldSize
    $resizeDownFrequency = $_.ResizeDownFrequency
    $resizeDownDay = $_.ResizeDownDay
    $resizeDownTime = $_.ResizeDownTime
    $resizeUpFrequency = $_.ResizeUpFrequency
    $resizeUpDay = $_.ResizeUpDay
    $resizeUpTime = $_.ResizeUpTime

    # Check if it's time to downsize
    if (Is-ScheduledTime -frequency $resizeDownFrequency -day $resizeDownDay -time $resizeDownTime) {
        Write-Output "Resizing VM $vmName to $newSize."
        Resize-VM -SubscriptionId $subscriptionId -ResourceGroupName $resourceGroupName -VMName $vmName -NewSize $newSize -OldSize $oldSize -Action "Downsize"
    }

    # Check if it's time to upsize
    if (Is-ScheduledTime -frequency $resizeUpFrequency -day $resizeUpDay -time $resizeUpTime) {
        Write-Output "Resizing VM $vmName to $oldSize."
        Resize-VM -SubscriptionId $subscriptionId -ResourceGroupName $resourceGroupName -VMName $vmName -NewSize $oldSize -OldSize $newSize -Action "Upsize"
    }
}
