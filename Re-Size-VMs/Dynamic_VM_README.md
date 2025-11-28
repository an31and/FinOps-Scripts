# Azure VM Resize Script Documentation

This document provides an overview and instructions for a PowerShell script that automates the resizing of Azure Virtual Machines (VMs) based on a schedule defined in a CSV file.

## Overview

The script performs the following tasks:

- **Module Installation & Import:**  
  Checks for the Az module and installs it if necessary, then imports the required Az.Compute and Az.Accounts modules.

- **Azure Authentication:**  
  Authenticates with Azure using `Connect-AzAccount`.

- **CSV File Input:**  
  Reads a CSV file containing details about the VMs, including:
  - VM name
  - Azure subscription ID
  - Resource group
  - New and old VM sizes
  - Scheduled frequencies, days, and times for both downsizing and upsizing

- **Logging:**  
  Logs each resize event to a CSV log file stored in a specified directory. The log file is named based on the current month (e.g., `ResizeLog_2025-02.csv`).

- **Scheduling Logic:**  
  Uses helper functions to determine if the current time matches the scheduled times for either a downsize or an upsize action.

- **Resizing Process:**  
  For each VM listed in the CSV, if the scheduled time is reached:
  - The script stops the VM.
  - Waits for deallocation.
  - Resizes the VM.
  - Restarts the VM.
  - Logs the success or failure of the operation.

## CSV File Format

The CSV file should contain the following columns:

- **Name:** The VM name.
- **SubscriptionId:** The Azure subscription ID.
- **ResourceGroup:** The resource group name.
- **NewSize:** The target VM size for downsizing.
- **OldSize:** The original VM size for upsizing.
- **ResizeDownFrequency:** Frequency of downsizing (Daily, Weekly, Monthly).
- **ResizeDownDay:** The day for downsizing (if applicable).
- **ResizeDownTime:** The time (HH:mm format) for downsizing.
- **ResizeUpFrequency:** Frequency of upsizing.
- **ResizeUpDay:** The day for upsizing (if applicable).
- **ResizeUpTime:** The time (HH:mm format) for upsizing.

## Usage Instructions

1. **Update File Paths:**  
   Modify the `$csvPath` and `$logDir` variables in the script to point to the correct paths on your system.

2. **Prepare the CSV File:**  
   Ensure your CSV file is formatted correctly with the necessary columns as described above.

3. **Run the Script:**  
   Execute the script in PowerShell. Make sure you have the necessary permissions and that your account can authenticate to Azure.

4. **Monitor Logs:**  
   Resize events are logged in the specified log directory. Check the log file (named by month) to review the status of each resize operation.

## Conclusion

This PowerShell script provides an automated solution for managing Azure VM sizes based on a scheduled plan. Adjust the script and scheduling parameters as needed to fit your environment.
