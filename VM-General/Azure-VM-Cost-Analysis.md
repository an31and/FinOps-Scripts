# Azure VM Cost Analysis with Savings Plan Tool

**Author:** Anand Lakhera  
**Email:** [anand.lakhera@ahead.com]
**Version:** 1.3

## Table of Contents
- [Overview](#overview)
- [Features](#features)
- [Prerequisites](#prerequisites)
- [Installation](#installation)
- [Usage](#usage)
- [Output Files](#output-files)
  - [VM_Cost_Analysis_Detail.csv](#vm_cost_analysis_detailcsv)
  - [VM_Cost_Analysis_Summary.csv](#vm_cost_analysis_summarycsv)
- [Technical Details](#technical-details)
  - [RI Coverage Detection](#ri-coverage-detection)
  - [Pricing Calculation](#pricing-calculation)
  - [Cost Calculation](#cost-calculation)
- [Error Handling](#error-handling)
- [Limitations](#limitations)
- [Customization](#customization)
- [Code Structure](#code-structure)

# Azure VM Cost Analysis with Savings Plan Tool

## Overview
This PowerShell script analyzes Azure Virtual Machine (VM) costs in relation to Savings Plans and Reserved Instances (RIs). It provides a comprehensive analysis of your Azure VM fleet, showing which VMs are covered by RIs, what the pay-as-you-go (PAYG) costs are, and how your Savings Plan affects these costs. The script generates detailed reports to help you optimize your Azure costs.

## Features
- Automatically discovers all VMs across all accessible subscriptions
- Retrieves detailed VM information (SKU, region, OS type, power state, etc.)
- Identifies VMs covered by Reserved Instances
- Uses the Azure Retail Prices API to get accurate PAYG pricing
- Calculates costs with and without Savings Plan application
- Generates detailed VM inventory with cost analysis
- Provides summary metrics including savings plan utilization
- Exports results to CSV files for further analysis

## Prerequisites
- PowerShell 5.1 or later
- Azure PowerShell modules:
  - Az.Accounts
  - Az.Compute
  - Az.Reservations
- Azure subscription access with appropriate permissions
- Azure credentials configured for PowerShell

## Installation
Install the required Azure PowerShell modules if not already installed:

```powershell
Install-Module -Name Az.Accounts -Force
Install-Module -Name Az.Compute -Force
Install-Module -Name Az.Reservations -Force
```

Save the script as `Azure-VM-Cost-Analysis.ps1`.

## Usage
Configure your Savings Plan commitment amount in the script:

```powershell
$savingPlanCommitmentPerHour = 180.006  # Modify to match your actual commitment
$savingPlanDiscount = 0.72             # Modify to match your actual discount percentage
```

Run the script:

```powershell
.\Azure-VM-Cost-Analysis.ps1
```

- If not already authenticated, follow the prompts to log in to Azure.
- Wait for the script to complete. The analysis time depends on the number of VMs and subscriptions.
- Review the generated CSV files:
  - `VM_Cost_Analysis_Detail.csv`: Detailed information for each VM
  - `VM_Cost_Analysis_Summary.csv`: Summary statistics of cost analysis

## Output Files

### VM_Cost_Analysis_Detail.csv
Contains detailed information for each VM:

| Column | Description |
|:-------|:------------|
| SubscriptionName | Name of the Azure subscription |
| SubscriptionId | ID of the Azure subscription |
| ResourceGroup | Resource group containing the VM |
| VMName | Name of the virtual machine |
| Location | Azure region where the VM is deployed |
| SKU | VM size/SKU (e.g., Standard_D2s_v3) |
| PowerState | Current power state of the VM |
| OSType | Operating system type (Windows/Linux) |
| Tags | Any tags assigned to the VM |
| RICovered | Whether the VM is covered by a Reserved Instance |
| ApplicableRI | Name of the applicable Reserved Instance if covered |
| PAYGCostPerHour | Pay-as-you-go cost per hour if not covered by RI |
| PAYGCostPerMonth | Pay-as-you-go cost per month if not covered by RI |
| CostAfterSavingsPlanPerHour | Cost after applying savings plan per hour |
| CostAfterSavingsPlanPerMonth | Cost after applying savings plan per month |
| SavingsPerMonth | Monthly savings from the savings plan |

### VM_Cost_Analysis_Summary.csv
Contains summary statistics:

| Metric | Description |
|:-------|:------------|
| TotalVMs | Total number of VMs analyzed |
| RICoveredVMs | Number of VMs covered by Reserved Instances |
| NonRICoveredVMs | Number of VMs not covered by Reserved Instances |
| TotalPAYGCostPerHour | Total hourly cost without RIs or savings plan |
| TotalPAYGCostPerMonth | Total monthly cost without RIs or savings plan |
| TotalCostAfterSavingsPlanPerHour | Total hourly cost after applying savings plan |
| TotalCostAfterSavingsPlanPerMonth | Total monthly cost after applying savings plan |
| TotalSavingsPerHour | Total hourly savings from the savings plan |
| TotalSavingsPerMonth | Total monthly savings from the savings plan |
| SavingsPlanCommitmentPerHour | Hourly commitment for the savings plan |
| SavingsPlanCommitmentPerMonth | Monthly commitment for the savings plan |
| SavingsPlanUtilizationPercentage | Percentage of savings plan commitment utilized |
| RemainingCommitmentPerHour | Unused hourly savings plan commitment |
| RemainingCommitmentPerMonth | Unused monthly savings plan commitment |

## Technical Details

### RI Coverage Detection
The script uses the Azure Reservations API to determine if a VM is covered by a Reserved Instance. It checks:
- If the VM's size matches the reservation's SKU
- If the VM's location matches the reservation's geography
- If the VM's subscription is within the reservation's scope
- If the reservation has instance flexibility enabled

### Pricing Calculation
The script uses the Azure Retail Prices API to get accurate PAYG pricing based on:
- VM size
- Region
- OS type (Windows/Linux)

### Cost Calculation
- **For VMs covered by RIs:** No additional compute cost
- **For VMs not covered by RIs:**
  - PAYG cost calculated using Azure Retail Prices API
  - Savings Plan applied with the configured discount percentage
  - Monthly costs calculated based on 730 hours per month

## Error Handling
The script includes robust error handling for:
- API connectivity issues
- Missing permissions
- Missing modules
- Price retrieval failures

## Limitations
- Pricing accuracy depends on the Azure Retail Prices API
- RI coverage detection requires appropriate permissions
- The script does not account for:
  - Non-standard VM pricing (like Azure Spot Instances)
  - Hybrid Benefit licensing
  - VM usage patterns (assumes 24/7 operation)
  - Other discount programs beyond RIs and Savings Plans

## Customization
You can customize the script by:
- Adjusting the `$savingPlanCommitmentPerHour` to match your actual commitment
- Modifying the `$savingPlanDiscount` to match your discount percentage
- Adding additional region mappings to the `$regionMap` hashtable
- Enhancing the pricing function to account for additional factors

## Code Structure
The script contains two main functions:
- **Get-AzureVMPrice:** Retrieves accurate pricing from the Azure Retail Prices API
- **Test-RICoverage:** Checks if a VM is covered by any Reserved Instance

### The main script flow:
1. Initializes variables and caches
2. Connects to Azure and gets all subscriptions
3. Loops through each subscription and VM
4. Analyzes RI coverage and calculates costs
5. Generates detailed results and summary statistics
6. Exports results to CSV files