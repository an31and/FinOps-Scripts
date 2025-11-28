# How to Set Up an Azure Automation Runbook for Business Hours VM Management

This guide explains how to create a single Azure Automation runbook that checks the current day and time to ensure your Azure VM is running during business hours on weekdays and is shut down outside those hours (or during weekends).

---

## Step 1: Create an Azure Automation Account

1. In the [Azure portal](https://portal.azure.com/), search for and select **Automation Accounts**.
2. Click **+ Create** and fill in the required details (name, resource group, location, etc.).
3. Once created, open your Automation Account.

---

## Step 2: Create a New PowerShell Runbook

1. In your Automation Account, under **Process Automation**, select **Runbooks**.
2. Click **+ Create a runbook**.
3. Provide a name (e.g., `ManageVMBusinessHours`), select **PowerShell** as the runbook type, and click **Create**.

---

## Step 3: Write the Runbook Script

Copy and paste the script into your runbook editor. Update the user-defined variables and business hours as needed.


## Script Explanation

- **User-Defined Variables:**  
  At the top, set your target resource group and VM name. Also, define your business hours with `$BusinessStartHour` and `$BusinessEndHour`.

- **Current Date and Time:**  
  The script retrieves the current day and hour using `Get-Date`.

- **VM Status Check:**  
  It gets the current status of the VM to determine if it’s already running or stopped.

- **Conditional Logic:**  
  - On weekdays (Monday to Friday) during business hours (between the start and end hours), the script ensures the VM is running.
  - Outside business hours (or on weekends), it ensures the VM is stopped.
  - The script only performs an action if the current VM state does not match the desired state.

- **Authentication:**  
  If your Automation account isn’t using a Managed Identity, uncomment the `Connect-AzAccount` line to authenticate.

---

## Step 4: Publish the Runbook

1. After pasting the script into the editor, click **Save**.
2. Then click **Publish** to make the runbook available for scheduling.

---

## Step 5: Schedule the Runbook

1. In the runbook’s overview page, click **Schedules** under the **Resources** section.
2. Click **+ Add a schedule**.
3. Either create a new schedule or link an existing one:
   - **New Schedule:** Click **+ New**, name your schedule (e.g., `BusinessHoursSchedule`), and set it to run every 15 or 30 minutes (or as needed) to frequently check the current state and enforce your desired VM status.
   - **Existing Schedule:** Link an existing schedule if it meets your desired recurrence.
4. Configure the recurrence settings (start time, recurrence interval, etc.) ensuring the schedule covers all days since the runbook itself handles weekday vs. weekend logic.

---

## Step 6: Monitor and Test

- **Test the Runbook:**  
  Use the **Test pane** in the Automation Account to run the script manually and review the output logs. Confirm that it correctly identifies the current day, time, and VM state, and takes the appropriate action.

- **Monitor Execution:**  
  After scheduling, you can monitor runbook job history in the **Jobs** section of your Automation Account to ensure it runs successfully and your VM is being managed as expected.

---

By following these steps, you will have a single runbook that uses both the day of the week and the time of day to automatically manage your Azure VM—keeping it on during business hours on weekdays and off outside those hours.
