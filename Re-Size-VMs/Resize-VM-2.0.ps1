param (
    [Parameter(Mandatory=$false)]
    [string]$CsvPath = "/home/x_saransh/test1.csv",  # Cloud Shell friendly path
    
    [Parameter(Mandatory=$false)]
    [bool]$DryRun = $false,
    
    [Parameter(Mandatory=$false)]
    [bool]$UseAzureStorage = $false,
    
    [Parameter(Mandatory=$false)]
    [string]$StorageAccountName = "",
    
    [Parameter(Mandatory=$false)]
    [string]$StorageContainerName = "",
    
    [Parameter(Mandatory=$false)]
    [string]$LogFileName = "ResizeToNewSize_$((Get-Date).ToString('yyyyMMdd-HHmmss')).csv",
    
    [Parameter(Mandatory=$false)]
    [ValidateRange(1,10)]  # Cloud Shell has limited resources
    [int]$MaxParallelJobs = 3,  # Reduced default for Cloud Shell
    
    [Parameter(Mandatory=$false)]
    [int]$TimeoutMinutes = 30,
    
    [Parameter(Mandatory=$false)]
    [ValidateSet("Basic", "Detailed", "Verbose")]
    [string]$LogLevel = "Detailed",
    
    [Parameter(Mandatory=$false)]
    [bool]$EnableEmailNotification = $false,
    
    [Parameter(Mandatory=$false)]
    [string]$EmailTo = "",
    
    [Parameter(Mandatory=$false)]
    [string]$EmailFrom = "",
    
    [Parameter(Mandatory=$false)]
    [string]$SendGridApiKey = "",  # Cloud Shell friendly email option
    
    [Parameter(Mandatory=$false)]
    [bool]$ValidatePreRequisites = $true,
    
    [Parameter(Mandatory=$false)]
    [bool]$CreateBackupSnapshot = $false,
    
    [Parameter(Mandatory=$false)]
    [int]$RetryCount = 3,
    
    [Parameter(Mandatory=$false)]
    [int]$RetryDelaySeconds = 30,
    
    [Parameter(Mandatory=$false)]
    [bool]$UseCloudShellStorage = $true  # Auto-detect and use Cloud Shell storage
)

<#
.SYNOPSIS
    Azure VM Resizing Script - Cloud Shell Optimized Edition

.VERSION
    2.1.0 - Cloud Shell Edition

.DESCRIPTION
    This script resizes Azure VMs with full Azure Cloud Shell compatibility.
    Optimized for Cloud Shell's environment limitations and leverages its built-in features.

.NOTES
    - Automatically detects Cloud Shell environment
    - Uses Cloud Shell's persistent storage
    - Optimized for Cloud Shell's resource constraints
    - Compatible with both Bash and PowerShell Cloud Shell

.EXAMPLE
    # Run in Azure Cloud Shell
    ./Azure-VM-Resize-CloudShell.ps1 -CsvPath "~/vms.csv" -MaxParallelJobs 5

.EXAMPLE
    # Dry run with Cloud Shell storage
    ./Azure-VM-Resize-CloudShell.ps1 -CsvPath "~/vms.csv" -DryRun $true -UseCloudShellStorage $true
#>

# ===================================
# Cloud Shell Detection and Setup
# ===================================
$Global:IsCloudShell = $false
$Global:CloudShellType = ""
$Global:CloudDrive = ""

function Test-CloudShellEnvironment {
    Write-Host "Detecting Cloud Shell environment..." -ForegroundColor Cyan
    
    # Check for Cloud Shell specific environment variables
    if ($env:AZUREPS_HOST_ENVIRONMENT -eq "cloud-shell" -or $env:ACC_CLOUD -eq "AzureCloud") {
        $Global:IsCloudShell = $true
        Write-Host "✓ Running in Azure Cloud Shell" -ForegroundColor Green
        
        # Detect shell type
        if (Test-Path "/usr/bin/pwsh") {
            $Global:CloudShellType = "PowerShell"
        } else {
            $Global:CloudShellType = "Bash"
        }
        
        # Find Cloud Drive mount point
        if (Test-Path "$HOME/clouddrive") {
            $Global:CloudDrive = "$HOME/clouddrive"
            Write-Host "✓ Cloud Drive detected at: $Global:CloudDrive" -ForegroundColor Green
        }
        
        return $true
    }
    
    # Check if running in Azure Cloud Shell by testing Azure CLI availability
    try {
        $azVersion = az version --output json 2>$null | ConvertFrom-Json
        if ($azVersion) {
            # Check if we're in a container (Cloud Shell runs in container)
            if (Test-Path "/.dockerenv" -or (Get-Content /proc/1/cgroup 2>$null | Select-String -Pattern "docker|kubepods" -Quiet)) {
                $Global:IsCloudShell = $true
                Write-Host "✓ Cloud Shell environment detected (container-based)" -ForegroundColor Green
                return $true
            }
        }
    } catch {
        # Not in Cloud Shell
    }
    
    Write-Host "ℹ Running in standard environment (not Cloud Shell)" -ForegroundColor Yellow
    return $false
}

# ===================================
# Global Variables and Configuration
# ===================================
$Global:ScriptVersion = "2.1.0-CloudShell"
$Global:StartTime = Get-Date
$Global:LogEntries = New-Object System.Collections.ArrayList
$Global:Results = New-Object System.Collections.ArrayList

# Detect environment
$isInCloudShell = Test-CloudShellEnvironment

# Setup paths based on environment
if ($Global:IsCloudShell -and $UseCloudShellStorage -and $Global:CloudDrive) {
    $OutputDirectory = "$Global:CloudDrive/VMResizeLogs"
    Write-Host "Using Cloud Drive for persistent storage: $OutputDirectory" -ForegroundColor Green
} else {
    $OutputDirectory = "$HOME/VMResizeLogs"
}

$SessionId = (Get-Date).ToString('yyyyMMdd-HHmmss')
$SessionDirectory = Join-Path $OutputDirectory "Session_$SessionId"

# Create directories
if (!(Test-Path -Path $SessionDirectory)) {
    New-Item -ItemType Directory -Path $SessionDirectory -Force | Out-Null
}

$Global:LogFilePath = Join-Path $SessionDirectory "ResizeLog_$SessionId.log"
$Global:DetailedLogPath = Join-Path $SessionDirectory "DetailedLog_$SessionId.json"
$Global:ResultsCsvPath = Join-Path $SessionDirectory $LogFileName
$Global:ErrorLogPath = Join-Path $SessionDirectory "Errors_$SessionId.log"

# Progress tracking (simplified for Cloud Shell)
$Global:ProgressData = @{
    TotalVMs = 0
    ProcessedVMs = 0
    SuccessfulVMs = 0
    FailedVMs = 0
    SkippedVMs = 0
    Lock = New-Object System.Object
}

# ===================================
# Cloud Shell Optimized Functions
# ===================================
function Write-Log {
    param (
        [string]$Message,
        [ValidateSet("INFO", "WARNING", "ERROR", "SUCCESS", "DEBUG", "VERBOSE")]
        [string]$Level = "INFO",
        [string]$VMName = "",
        [string]$SubscriptionId = ""
    )
    
    $timestamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
    $logEntry = [PSCustomObject]@{
        Timestamp = $timestamp
        Level = $Level
        Message = $Message
        VMName = $VMName
        SubscriptionId = $SubscriptionId
    }
    
    # Thread-safe adding to collection
    [void]$Global:LogEntries.Add($logEntry)
    
    # Console output with color coding
    $color = switch ($Level) {
        "ERROR" { "Red" }
        "WARNING" { "Yellow" }
        "SUCCESS" { "Green" }
        "DEBUG" { "Gray" }
        "VERBOSE" { "Cyan" }
        default { "White" }
    }
    
    $consoleMessage = "[$timestamp] [$Level]"
    if ($VMName) { $consoleMessage += " [$VMName]" }
    $consoleMessage += " $Message"
    
    # Apply log level filtering
    $shouldDisplay = switch ($Global:LogLevel) {
        "Basic" { $Level -in @("INFO", "ERROR", "SUCCESS", "WARNING") }
        "Detailed" { $Level -ne "VERBOSE" }
        "Verbose" { $true }
        default { $true }
    }
    
    if ($shouldDisplay) {
        Write-Host $consoleMessage -ForegroundColor $color
    }
    
    # File logging (simplified for Cloud Shell)
    try {
        $fileEntry = "[$timestamp] [$Level]"
        if ($VMName) { $fileEntry += " [$VMName]" }
        $fileEntry += " $Message"
        
        Add-Content -Path $Global:LogFilePath -Value $fileEntry -ErrorAction SilentlyContinue
        
        if ($Level -eq "ERROR") {
            Add-Content -Path $Global:ErrorLogPath -Value $fileEntry -ErrorAction SilentlyContinue
        }
    } catch {
        # Silently continue if file writing fails in Cloud Shell
    }
}

function Update-ProgressBar {
    param (
        [string]$Activity = "Resizing Azure VMs",
        [string]$CurrentOperation = ""
    )
    
    $processed = $Global:ProgressData.ProcessedVMs
    $total = $Global:ProgressData.TotalVMs
    
    if ($total -gt 0) {
        $percentComplete = [math]::Round(($processed / $total) * 100, 0)
        
        $status = "[$processed/$total] Success: $($Global:ProgressData.SuccessfulVMs) | " +
                  "Failed: $($Global:ProgressData.FailedVMs) | " +
                  "Skipped: $($Global:ProgressData.SkippedVMs)"
        
        Write-Progress -Activity $Activity `
                       -Status $status `
                       -CurrentOperation $CurrentOperation `
                       -PercentComplete $percentComplete
    }
}

function Test-Prerequisites {
    Write-Log "Starting Cloud Shell optimized prerequisites validation..." "INFO"
    
    $issues = @()
    
    # Check if we're authenticated (Cloud Shell is always authenticated)
    if ($Global:IsCloudShell) {
        Write-Log "Cloud Shell authentication detected (always authenticated)" "SUCCESS"
    } else {
        try {
            $context = Get-AzContext -ErrorAction SilentlyContinue
            if (-not $context) {
                Write-Log "No Azure context found. Attempting to authenticate..." "WARNING"
                Connect-AzAccount
            } else {
                Write-Log "Authenticated as: $($context.Account.Id)" "INFO"
            }
        } catch {
            $issues += "Authentication check failed: $_"
        }
    }
    
    # Check Azure CLI (always available in Cloud Shell)
    try {
        $azVersion = az version --query '"azure-cli"' -o tsv 2>$null
        if ($azVersion) {
            Write-Log "Azure CLI found: v$azVersion" "INFO"
        } else {
            $issues += "Azure CLI not found or not configured"
        }
    } catch {
        $issues += "Failed to check Azure CLI: $_"
    }
    
    # Check CSV file
    $expandedPath = [System.Environment]::ExpandEnvironmentVariables($CsvPath)
    $expandedPath = $expandedPath.Replace("~", $HOME)
    
    if (!(Test-Path -Path $expandedPath)) {
        $issues += "CSV file not found: $expandedPath"
    } else {
        try {
            $testImport = Import-Csv -Path $expandedPath -ErrorAction Stop
            $requiredColumns = @("Name", "SubscriptionId", "OldSize", "NewSize", "ResourceGroup")
            $csvColumns = $testImport[0].PSObject.Properties.Name
            
            foreach ($col in $requiredColumns) {
                if ($col -notin $csvColumns) {
                    $issues += "Required column missing in CSV: $col"
                }
            }
            Write-Log "CSV validation successful. Found $($testImport.Count) VMs to process" "INFO"
        } catch {
            $issues += "Failed to validate CSV: $_"
        }
    }
    
    # Check Cloud Shell resource limits
    if ($Global:IsCloudShell) {
        Write-Log "Cloud Shell resource limits:" "INFO"
        Write-Log "  - Recommended max parallel jobs: 3-5" "INFO"
        Write-Log "  - Session timeout: 20 minutes (interactive)" "INFO"
        Write-Log "  - Storage: Using $($Global:CloudDrive ? 'Cloud Drive' : 'local storage')" "INFO"
        
        if ($MaxParallelJobs -gt 10) {
            Write-Log "Warning: MaxParallelJobs ($MaxParallelJobs) may be too high for Cloud Shell" "WARNING"
        }
    }
    
    if ($issues.Count -gt 0) {
        Write-Log "Prerequisites validation failed:" "ERROR"
        foreach ($issue in $issues) {
            Write-Log "  - $issue" "ERROR"
        }
        return $false
    }
    
    Write-Log "Prerequisites validation completed successfully" "SUCCESS"
    return $true
}

function Test-VMSizeAvailability {
    param (
        [string]$Location,
        [string]$VMSize,
        [string]$SubscriptionId
    )
    
    try {
        # Use Azure CLI for better Cloud Shell compatibility
        az account set --subscription $SubscriptionId 2>$null
        
        $availableSizes = az vm list-sizes --location $Location --query "[].name" -o tsv 2>$null
        
        if ($availableSizes -contains $VMSize) {
            return @{
                Available = $true
                Message = "VM size '$VMSize' is available in location '$Location'"
            }
        } else {
            return @{
                Available = $false
                Message = "VM size '$VMSize' is not available in location '$Location'"
            }
        }
    } catch {
        return @{
            Available = $false
            Message = "Failed to check VM size availability: $_"
        }
    }
}

function New-VMDiskSnapshot {
    param (
        [string]$VMName,
        [string]$ResourceGroup,
        [string]$SubscriptionId
    )
    
    Write-Log "Creating disk snapshots for VM: $VMName" "INFO" -VMName $VMName
    
    try {
        az account set --subscription $SubscriptionId 2>$null
        
        # Get VM details
        $vmJson = az vm show --name $VMName --resource-group $ResourceGroup 2>$null | ConvertFrom-Json
        $snapshots = @()
        
        # OS Disk snapshot
        if ($vmJson.storageProfile.osDisk) {
            $snapshotName = "$VMName-osdisk-snapshot-$SessionId"
            
            $snapshot = az snapshot create `
                --resource-group $ResourceGroup `
                --name $snapshotName `
                --source $vmJson.storageProfile.osDisk.managedDisk.id `
                --location $vmJson.location 2>$null
            
            if ($?) {
                $snapshots += $snapshotName
                Write-Log "Created OS disk snapshot: $snapshotName" "SUCCESS" -VMName $VMName
            }
        }
        
        # Data Disks snapshots
        foreach ($dataDisk in $vmJson.storageProfile.dataDisks) {
            $snapshotName = "$VMName-datadisk-$($dataDisk.lun)-snapshot-$SessionId"
            
            $snapshot = az snapshot create `
                --resource-group $ResourceGroup `
                --name $snapshotName `
                --source $dataDisk.managedDisk.id `
                --location $vmJson.location 2>$null
            
            if ($?) {
                $snapshots += $snapshotName
                Write-Log "Created data disk snapshot: $snapshotName" "SUCCESS" -VMName $VMName
            }
        }
        
        return @{
            Success = $true
            Snapshots = $snapshots
        }
    } catch {
        Write-Log "Failed to create snapshots for VM $VMName : $_" "ERROR" -VMName $VMName
        return @{
            Success = $false
            Error = $_.Exception.Message
        }
    }
}

# ===================================
# Simplified Parallel Processing for Cloud Shell
# ===================================
function Resize-AzureVMBatch {
    param (
        [array]$Servers,
        [bool]$DryRun,
        [bool]$CreateBackup,
        [int]$RetryCount,
        [int]$RetryDelaySeconds,
        [int]$TimeoutMinutes,
        [int]$MaxParallel
    )
    
    $results = @()
    
    # Use ForEach-Object -Parallel if available (PowerShell 7+)
    $PSVersion = $PSVersionTable.PSVersion
    $useModernParallel = ($PSVersion.Major -ge 7)
    
    if ($useModernParallel -and -not $Global:IsCloudShell) {
        Write-Log "Using PowerShell 7+ parallel processing" "INFO"
        
        $results = $Servers | ForEach-Object -Parallel {
            $server = $_
            . $using:PWD/Azure-VM-Resize-CloudShell.ps1
            Resize-SingleVM -Server $server `
                          -DryRun $using:DryRun `
                          -CreateBackup $using:CreateBackup `
                          -RetryCount $using:RetryCount `
                          -RetryDelaySeconds $using:RetryDelaySeconds `
                          -TimeoutMinutes $using:TimeoutMinutes
        } -ThrottleLimit $MaxParallel
    } else {
        # Use Jobs for Cloud Shell and older PowerShell versions
        Write-Log "Using background jobs for parallel processing (Cloud Shell compatible)" "INFO"
        
        $jobs = @()
        $jobQueue = [System.Collections.Queue]::new()
        
        foreach ($server in $Servers) {
            $jobQueue.Enqueue($server)
        }
        
        while ($jobQueue.Count -gt 0 -or $jobs.Count -gt 0) {
            # Start new jobs if under the limit
            while ($jobs.Count -lt $MaxParallel -and $jobQueue.Count -gt 0) {
                $server = $jobQueue.Dequeue()
                
                $job = Start-Job -ScriptBlock {
                    param($Server, $DryRun, $CreateBackup, $RetryCount, $RetryDelaySeconds, $TimeoutMinutes)
                    
                    # Simplified resize logic for job execution
                    $result = [PSCustomObject]@{
                        VMName = $Server.Name
                        SubscriptionId = $Server.SubscriptionId
                        ResourceGroup = $Server.ResourceGroup
                        OldSize = $Server.OldSize
                        NewSize = $Server.NewSize
                        Status = "Unknown"
                        StartTime = Get-Date
                        EndTime = $null
                        Duration = $null
                        Error = ""
                    }
                    
                    try {
                        # Set subscription
                        az account set --subscription $Server.SubscriptionId 2>$null
                        
                        if ($DryRun) {
                            $result.Status = "DryRun"
                        } else {
                            # Execute resize
                            $resizeOutput = az vm resize `
                                --resource-group $Server.ResourceGroup `
                                --name $Server.Name `
                                --size $Server.NewSize 2>&1
                            
                            if ($LASTEXITCODE -eq 0) {
                                # Verify resize
                                Start-Sleep -Seconds 10
                                $currentSize = az vm show `
                                    --resource-group $Server.ResourceGroup `
                                    --name $Server.Name `
                                    --query "hardwareProfile.vmSize" `
                                    -o tsv 2>$null
                                
                                if ($currentSize -eq $Server.NewSize) {
                                    $result.Status = "Success"
                                } else {
                                    $result.Status = "ValidationFailed"
                                    $result.Error = "Size mismatch after resize"
                                }
                            } else {
                                $result.Status = "Failed"
                                $result.Error = $resizeOutput
                            }
                        }
                    } catch {
                        $result.Status = "Failed"
                        $result.Error = $_.Exception.Message
                    } finally {
                        $result.EndTime = Get-Date
                        $result.Duration = ($result.EndTime - $result.StartTime).TotalMinutes
                    }
                    
                    return $result
                    
                } -ArgumentList $server, $DryRun, $CreateBackup, $RetryCount, $RetryDelaySeconds, $TimeoutMinutes
                
                $jobs += [PSCustomObject]@{
                    Job = $job
                    Server = $server
                    StartTime = Get-Date
                }
                
                Write-Log "Started resize job for VM: $($server.Name)" "INFO" -VMName $server.Name
            }
            
            # Check for completed jobs
            $completedJobs = @()
            foreach ($jobInfo in $jobs) {
                if ($jobInfo.Job.State -eq 'Completed' -or $jobInfo.Job.State -eq 'Failed') {
                    try {
                        $result = Receive-Job -Job $jobInfo.Job -ErrorAction Stop
                        $results += $result
                        
                        # Update progress
                        [System.Threading.Monitor]::Enter($Global:ProgressData.Lock)
                        try {
                            $Global:ProgressData.ProcessedVMs++
                            switch ($result.Status) {
                                "Success" { $Global:ProgressData.SuccessfulVMs++ }
                                "Failed" { $Global:ProgressData.FailedVMs++ }
                                "ValidationFailed" { $Global:ProgressData.FailedVMs++ }
                                default { $Global:ProgressData.SkippedVMs++ }
                            }
                        } finally {
                            [System.Threading.Monitor]::Exit($Global:ProgressData.Lock)
                        }
                        
                        Write-Log "Completed: $($jobInfo.Server.Name) - Status: $($result.Status)" "INFO" -VMName $jobInfo.Server.Name
                    } catch {
                        Write-Log "Error processing job for $($jobInfo.Server.Name): $_" "ERROR" -VMName $jobInfo.Server.Name
                    } finally {
                        Remove-Job -Job $jobInfo.Job -Force
                        $completedJobs += $jobInfo
                    }
                } elseif ((Get-Date) - $jobInfo.StartTime -gt [TimeSpan]::FromMinutes($TimeoutMinutes)) {
                    # Timeout handling
                    Stop-Job -Job $jobInfo.Job -Force
                    Remove-Job -Job $jobInfo.Job -Force
                    
                    $result = [PSCustomObject]@{
                        VMName = $jobInfo.Server.Name
                        SubscriptionId = $jobInfo.Server.SubscriptionId
                        ResourceGroup = $jobInfo.Server.ResourceGroup
                        OldSize = $jobInfo.Server.OldSize
                        NewSize = $jobInfo.Server.NewSize
                        Status = "Timeout"
                        Error = "Operation timed out after $TimeoutMinutes minutes"
                    }
                    $results += $result
                    $completedJobs += $jobInfo
                    
                    Write-Log "Timeout: $($jobInfo.Server.Name)" "ERROR" -VMName $jobInfo.Server.Name
                }
            }
            
            # Remove completed jobs from tracking
            foreach ($completed in $completedJobs) {
                $jobs = $jobs | Where-Object { $_.Job.Id -ne $completed.Job.Id }
            }
            
            # Update progress bar
            Update-ProgressBar -CurrentOperation "Processing VMs..."
            
            # Small delay to prevent CPU spinning
            Start-Sleep -Milliseconds 500
        }
    }
    
    return $results
}

# ===================================
# Storage Functions (Cloud Shell Optimized)
# ===================================
function Upload-ToAzureStorage {
    param (
        [string]$StorageAccount,
        [string]$ContainerName,
        [string]$FilePath,
        [string]$BlobName
    )
    
    try {
        # Use Azure CLI for Cloud Shell compatibility
        $accountKey = az storage account keys list `
            --account-name $StorageAccount `
            --query "[0].value" `
            -o tsv 2>$null
        
        if (-not $accountKey) {
            throw "Could not retrieve storage account key"
        }
        
        # Create container if it doesn't exist
        az storage container create `
            --name $ContainerName `
            --account-name $StorageAccount `
            --account-key $accountKey 2>$null | Out-Null
        
        # Upload file
        $uploadResult = az storage blob upload `
            --file $FilePath `
            --container-name $ContainerName `
            --name $BlobName `
            --account-name $StorageAccount `
            --account-key $accountKey `
            --overwrite 2>$null
        
        if ($?) {
            Write-Log "Successfully uploaded $FilePath to Azure Storage as $BlobName" "SUCCESS"
            return $true
        } else {
            throw "Upload command failed"
        }
    } catch {
        Write-Log "Failed to upload $FilePath to Azure Storage: $_" "ERROR"
        return $false
    }
}

# ===================================
# Email Function (SendGrid for Cloud Shell)
# ===================================
function Send-CompletionNotification {
    param (
        [array]$Results,
        [string]$EmailTo,
        [string]$EmailFrom,
        [string]$SendGridApiKey
    )
    
    if (-not $EnableEmailNotification -or -not $EmailTo -or -not $SendGridApiKey) {
        return
    }
    
    try {
        $summary = $Results | Group-Object -Property Status | ForEach-Object {
            "$($_.Name): $($_.Count)"
        }
        
        $duration = (Get-Date) - $Global:StartTime
        
        $bodyHtml = @"
<html>
<body>
<h2>Azure VM Resize Operation Completed</h2>
<p><strong>Session ID:</strong> $SessionId</p>
<p><strong>Environment:</strong> $($Global:IsCloudShell ? 'Azure Cloud Shell' : 'Standard')</p>
<p><strong>Start Time:</strong> $($Global:StartTime)</p>
<p><strong>End Time:</strong> $(Get-Date)</p>
<p><strong>Duration:</strong> $($duration.ToString("hh\:mm\:ss"))</p>
<h3>Summary:</h3>
<ul>
$(($summary | ForEach-Object { "<li>$_</li>" }) -join "`n")
</ul>
<p><strong>Total VMs Processed:</strong> $($Results.Count)</p>
<p>Log files are available at: $SessionDirectory</p>
<hr>
<p><em>This is an automated notification from Azure VM Resize Script v$Global:ScriptVersion</em></p>
</body>
</html>
"@
        
        $body = @{
            personalizations = @(
                @{
                    to = @(
                        @{
                            email = $EmailTo
                        }
                    )
                }
            )
            from = @{
                email = $EmailFrom
            }
            subject = "Azure VM Resize Completed - Session $SessionId"
            content = @(
                @{
                    type = "text/html"
                    value = $bodyHtml
                }
            )
        } | ConvertTo-Json -Depth 10
        
        $headers = @{
            "Authorization" = "Bearer $SendGridApiKey"
            "Content-Type" = "application/json"
        }
        
        Invoke-RestMethod -Uri "https://api.sendgrid.com/v3/mail/send" `
                         -Method Post `
                         -Headers $headers `
                         -Body $body
        
        Write-Log "Email notification sent to $EmailTo" "SUCCESS"
    } catch {
        Write-Log "Failed to send email notification: $_" "ERROR"
    }
}

# ===================================
# Main Execution Block
# ===================================
try {
    Write-Host "`n========================================" -ForegroundColor Cyan
    Write-Host "Azure VM Resize Script v$Global:ScriptVersion" -ForegroundColor Cyan
    Write-Host "Environment: $($Global:IsCloudShell ? 'Azure Cloud Shell' : 'Standard')" -ForegroundColor Yellow
    Write-Host "========================================`n" -ForegroundColor Cyan
    
    Write-Log "Starting Azure VM Resize Script v$Global:ScriptVersion" "INFO"
    Write-Log "Session ID: $SessionId" "INFO"
    Write-Log "Environment: $($Global:IsCloudShell ? 'Azure Cloud Shell' : 'Standard')" "INFO"
    Write-Log "Parameters: MaxParallelJobs=$MaxParallelJobs, DryRun=$DryRun, LogLevel=$LogLevel" "INFO"
    
    # Cloud Shell specific warnings
    if ($Global:IsCloudShell) {
        Write-Log "Cloud Shell Limitations:" "WARNING"
        Write-Log "  - Session timeout: 20 minutes for interactive sessions" "WARNING"
        Write-Log "  - Limited compute resources - using $MaxParallelJobs parallel jobs" "WARNING"
        Write-Log "  - Files saved to: $($UseCloudShellStorage ? 'Cloud Drive (persistent)' : 'Local (temporary)')" "INFO"
    }
    
    # Validate prerequisites
    if ($ValidatePreRequisites) {
        if (-not (Test-Prerequisites)) {
            Write-Log "Prerequisites validation failed. Exiting script." "ERROR"
            exit 1
        }
    }
    
    # Import CSV (handle ~ in path for Cloud Shell)
    $expandedCsvPath = [System.Environment]::ExpandEnvironmentVariables($CsvPath)
    $expandedCsvPath = $expandedCsvPath.Replace("~", $HOME)
    
    Write-Log "Importing CSV from: $expandedCsvPath" "INFO"
    $servers = Import-Csv -Path $expandedCsvPath
    $Global:ProgressData.TotalVMs = $servers.Count
    
    Write-Log "Found $($servers.Count) VMs to process" "INFO"
    
    # Process VMs in batches (Cloud Shell optimized)
    $results = Resize-AzureVMBatch -Servers $servers `
                                   -DryRun $DryRun `
                                   -CreateBackup $CreateBackupSnapshot `
                                   -RetryCount $RetryCount `
                                   -RetryDelaySeconds $RetryDelaySeconds `
                                   -TimeoutMinutes $TimeoutMinutes `
                                   -MaxParallel $MaxParallelJobs
    
    Write-Progress -Activity "Resizing Azure VMs" -Completed
    
    # ===================================
    # Generate Reports
    # ===================================
    Write-Log "`nGenerating reports..." "INFO"
    
    # Export results to CSV
    $results | Export-Csv -Path $Global:ResultsCsvPath -NoTypeInformation
    Write-Log "Exported results to: $Global:ResultsCsvPath" "SUCCESS"
    
    # Export detailed JSON log
    $Global:LogEntries | ConvertTo-Json -Depth 3 | Out-File -FilePath $Global:DetailedLogPath
    Write-Log "Exported detailed log to: $Global:DetailedLogPath" "SUCCESS"
    
    # Generate summary
    $duration = (Get-Date) - $Global:StartTime
    $summaryPath = Join-Path $SessionDirectory "Summary_$SessionId.txt"
    
    $summaryContent = @"
=====================================
Azure VM Resize Operation Summary
=====================================
Session ID: $SessionId
Script Version: $Global:ScriptVersion
Environment: $($Global:IsCloudShell ? 'Azure Cloud Shell' : 'Standard Environment')
Start Time: $($Global:StartTime)
End Time: $(Get-Date)
Total Duration: $($duration.ToString("hh\:mm\:ss"))

Cloud Shell Details:
- Type: $($Global:CloudShellType)
- Cloud Drive: $($Global:CloudDrive ? $Global:CloudDrive : 'Not Available')

Parameters:
- CSV Path: $CsvPath
- Max Parallel Jobs: $MaxParallelJobs
- Dry Run: $DryRun
- Create Backup: $CreateBackupSnapshot

Results:
- Total VMs: $($Global:ProgressData.TotalVMs)
- Successful: $($Global:ProgressData.SuccessfulVMs)
- Failed: $($Global:ProgressData.FailedVMs)
- Skipped: $($Global:ProgressData.SkippedVMs)

Success Rate: $(if ($Global:ProgressData.ProcessedVMs -gt 0) { [math]::Round(($Global:ProgressData.SuccessfulVMs / $Global:ProgressData.ProcessedVMs) * 100, 2) } else { 0 })%

Status Breakdown:
$($results | Group-Object -Property Status | ForEach-Object { "  - $($_.Name): $($_.Count)" } | Out-String)

Log Files:
- Results CSV: $Global:ResultsCsvPath
- Detailed Log: $Global:DetailedLogPath
- Error Log: $Global:ErrorLogPath

=====================================
"@
    
    $summaryContent | Out-File -FilePath $summaryPath
    Write-Host "`n$summaryContent" -ForegroundColor Cyan
    
    # Upload to Azure Storage if configured
    if ($UseAzureStorage -and $StorageAccountName -and $StorageContainerName) {
        Write-Log "Uploading logs to Azure Storage..." "INFO"
        
        $filesToUpload = @(
            @{ Path = $Global:ResultsCsvPath; Name = "Results_$SessionId.csv" }
            @{ Path = $Global:LogFilePath; Name = "Log_$SessionId.log" }
            @{ Path = $summaryPath; Name = "Summary_$SessionId.txt" }
        )
        
        foreach ($file in $filesToUpload) {
            if (Test-Path $file.Path) {
                Upload-ToAzureStorage -StorageAccount $StorageAccountName `
                                    -ContainerName $StorageContainerName `
                                    -FilePath $file.Path `
                                    -BlobName "VMResize/$SessionId/$($file.Name)"
            }
        }
    }
    
    # Send notification
    if ($EnableEmailNotification -and $SendGridApiKey) {
        Send-CompletionNotification -Results $results `
                                  -EmailTo $EmailTo `
                                  -EmailFrom $EmailFrom `
                                  -SendGridApiKey $SendGridApiKey
    }
    
    Write-Log "Script execution completed successfully" "SUCCESS"
    
    # Cloud Shell specific completion message
    if ($Global:IsCloudShell) {
        Write-Host "`n⚠ Cloud Shell Note:" -ForegroundColor Yellow
        Write-Host "  Your session will timeout after 20 minutes of inactivity." -ForegroundColor Yellow
        if ($UseCloudShellStorage -and $Global:CloudDrive) {
            Write-Host "  ✓ Results saved to Cloud Drive (persistent): $SessionDirectory" -ForegroundColor Green
        } else {
            Write-Host "  ⚠ Results saved to local storage (temporary): $SessionDirectory" -ForegroundColor Yellow
            Write-Host "  Consider using -UseCloudShellStorage `$true for persistent storage" -ForegroundColor Yellow
        }
    }
    
} catch {
    Write-Log "Critical error: $_" "ERROR"
    Write-Host "`nScript execution failed. Check logs at: $SessionDirectory" -ForegroundColor Red
    exit 1
} finally {
    Write-Host "`n========================================" -ForegroundColor Green
    Write-Host "Execution completed" -ForegroundColor Green
    Write-Host "Logs: $SessionDirectory" -ForegroundColor Yellow
    Write-Host "========================================`n" -ForegroundColor Green
}

# Return results
return $results
