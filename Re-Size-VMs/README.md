
# Azure VM Rightsizing Script

This script dynamically resizes Azure VMs based on a specified schedule in a CSV file. It can resize VMs up or down based on flexible scheduling options like "3rd Saturday" or "Last Sunday." The script also includes logging to track resizing events.

## Prerequisites
- PowerShell 7.0 or higher (or Azure Automation).
- Azure PowerShell Az module.
- CSV file with VM configuration and schedules (`ResizeDownFrequency`, `ResizeDownDay`, `ResizeDownTime`, `ResizeUpFrequency`, `ResizeUpDay`, `ResizeUpTime`).
- Access to an Azure account with permissions to start/stop and resize VMs.

## CSV File Structure
The CSV file should include the following columns:
| Column               | Description |
|----------------------|-------------|
| `Name`               | Name of the VM |
| `SubscriptionId`     | Azure Subscription ID for the VM |
| `ResourceGroup`      | Azure Resource Group containing the VM |
| `NewSize`            | The VM size to resize to during a scheduled downsize |
| `OldSize`            | The VM size to resize back to during a scheduled upsize |
| `ResizeDownFrequency`| Frequency of downsizing (Daily, Weekly, Monthly) |
| `ResizeDownDay`      | Specific day of the week or month (e.g., "3rd Saturday" for Monthly or "Friday" for Weekly) |
| `ResizeDownTime`     | Specific time for downsizing in HH:MM format |
| `ResizeUpFrequency`  | Frequency of upsizing (Daily, Weekly, Monthly) |
| `ResizeUpDay`        | Specific day of the week or month (e.g., "3rd Sunday" for Monthly or "Monday" for Weekly) |
| `ResizeUpTime`       | Specific time for upsizing in HH:MM format |

You can find a sample CSV [here](Sample_VM_Schedule_With_RG.csv).

## Logging
The script generates a log file in CSV format to record each resizing event, capturing details such as timestamp, VM name, action (resize up or down), old size, new size, and status. Each month, a new log file is created to archive the previous month's logs.

Sample log file available for download [here](Sample_VM_Resize_Log.csv).

## Script Setup
1. **Clone or download the script file** to your local environment.
2. **Install the Az Module** (if not installed):
   ```powershell
   Install-Module -Name Az -Scope CurrentUser -Force -AllowClobber
   ```
3. **Connect to your Azure account**:
   ```powershell
   Connect-AzAccount
   ```

## Manual Execution Instructions
1. Open PowerShell and navigate to the directory containing the script and CSV file.
2. Update the `$csvPath` variable in the script to point to your CSV file path:
   ```powershell
   $csvPath = "C:\path\to\Server.csv"
   ```
3. Run the script manually:
   ```powershell
   .\YourScriptName.ps1
   ```
   The script will:
   - Parse the CSV file.
   - Check today’s date and match it to any scheduled resize events in `ResizeDownFrequency`, `ResizeDownDay`, `ResizeDownTime`, etc.
   - Perform resizing operations if the schedule matches today’s date and time.
   - Log each resizing event to a monthly CSV file.

## Automating the Script in Azure Cloud (Azure Automation Account)
1. **Create an Azure Automation Account**:
   - In the Azure portal, go to **Automation Accounts** and click **Create**.
   - Enter the required details (Subscription, Resource Group, Name, and Region) and click **Create**.

2. **Add Az Modules to the Automation Account**:
   - Open the Automation Account you created, go to **Modules gallery**.
   - Search for `Az.Accounts` and `Az.Compute`, then **Import** both modules.

3. **Upload the CSV to Azure Storage**:
   - In the Azure portal, create a **Storage Account** (or use an existing one).
   - In the Storage Account, create a **Container** and upload the CSV file.
   - Get the **URL** for the CSV file and generate a **SAS token** with read permissions to access the file securely.

4. **Create a Runbook for the Script**:
   - Go back to the Automation Account, and under **Process Automation**, select **Runbooks**.
   - Click **Create a Runbook**, name it (e.g., `VMResizeRunbook`), and set **Runbook Type** to `PowerShell`.
   - Paste the PowerShell script into the Runbook editor.
   - Replace `$csvPath` with the URL to your CSV file, using the SAS token for access (e.g., `https://mystorageaccount.blob.core.windows.net/mycontainer/Server.csv?<sas_token>`).
   - Save and **Publish** the Runbook.

5. **Schedule the Runbook**:
   - In the Runbook, select **Schedules** and click **Link to a new schedule**.
   - Create a schedule with the desired frequency (e.g., Daily) and save it.

### Testing the Azure Automation
- Run the Runbook manually to verify functionality by selecting **Start** from the Runbook overview.
- Check the **Output** and **Logs** to confirm successful execution.

---
