# Azure Orphan Detector 🔍

**Enhanced** Azure orphaned resources detection system with comprehensive analysis and intelligent backup policy awareness.

## 🚀 Quick Start
```bash
# 1. Install the tool
pip install -e .

# 2. Login to Azure (required)
az login

# 3. Run basic scan (using Python module syntax)
python -m azure_orphan_detector.cli.main scan

# 4. View results in interactive dashboard
# Opens: orphaned_resources_dashboard.html

# Alternative: Use the installation script
python install.py
```

## 📋 Prerequisites
- **Python 3.8+** installed
- **Azure CLI** installed and configured (`az login`)
- **Azure subscription(s)** with appropriate permissions:
  - `Reader` role on subscriptions/resource groups
  - `Cost Management Reader` (for cost data)
  - `Monitoring Reader` (for usage metrics)
  - `Backup Reader` (for backup policy analysis)

## ✨ Enhanced Features
- 🎯 **Multi-subscription scanning** with parallel processing
- 💰 **Real-time cost analysis** via Azure Cost Management API
- 📊 **Interactive HTML dashboard** with drill-down capabilities
- 🔒 **Security risk assessment** and compliance checking
- 📈 **Actual usage metrics** from Azure Monitor
- 🛡️ **Backup policy awareness** - prevents accidental data loss
- 🚀 **Intelligent confidence scoring** with multiple data sources
- ⚡ **Smart filtering** to reduce false positives

## 🖥️ Azure CLI Integration

This tool works seamlessly with **Azure CLI authentication**:

```bash
# Login to Azure (required first step)
az login

# Select specific subscription (optional)
az account set --subscription "Your-Subscription-ID"

# Check current context
az account show
```

## 📝 Complete Command Reference

### Basic Usage
```bash
# Scan all accessible subscriptions
python -m azure_orphan_detector.cli.main scan

# Scan specific subscriptions
python -m azure_orphan_detector.cli.main scan -s "sub-id-1" -s "sub-id-2"

# Scan specific resource groups
python -m azure_orphan_detector.cli.main scan -g "rg-prod" -g "rg-dev"

# Exclude specific resource groups
python -m azure_orphan_detector.cli.main scan -x "rg-backup" -x "rg-system"
```

### Advanced Configuration
```bash
# Adjust age threshold (more aggressive = lower days)
python -m azure_orphan_detector.cli.main scan --max-age 30        # 30 days (aggressive)
python -m azure_orphan_detector.cli.main scan --max-age 180       # 180 days (conservative)

# Set confidence threshold (higher = more strict)
python -m azure_orphan_detector.cli.main scan --confidence 0.8    # High confidence only
python -m azure_orphan_detector.cli.main scan --confidence 0.5    # Include medium confidence

# Cost-based filtering
python -m azure_orphan_detector.cli.main scan --cost-critical 500 --cost-high 100

# Performance tuning
python -m azure_orphan_detector.cli.main scan --workers 8         # Use 8 parallel workers
```

### Output Formats
```bash
# Interactive dashboard (default)
python -m azure_orphan_detector.cli.main scan

# JSON output for automation
python -m azure_orphan_detector.cli.main scan --format json --output results.json

# CSV for spreadsheet analysis
python -m azure_orphan_detector.cli.main scan --format csv --output results.csv

# Table view in terminal
python -m azure_orphan_detector.cli.main scan --format table

# Custom dashboard location
python -m azure_orphan_detector.cli.main scan --dashboard-output ./reports/dashboard.html
```

### Production Examples
```bash
# Production-safe scan (conservative settings)
python -m azure_orphan_detector.cli.main scan \
  --max-age 180 \
  --confidence 0.8 \
  --cost-critical 1000 \
  --exclude-resource-group "rg-backup" \
  --exclude-resource-group "rg-dr" \
  --verbose

# Development environment cleanup (aggressive)
python -m azure_orphan_detector.cli.main scan \
  --max-age 7 \
  --confidence 0.6 \
  --subscription "dev-subscription-id" \
  --format json \
  --output dev-cleanup.json

# Cost optimization focus
python -m azure_orphan_detector.cli.main scan \
  --cost-critical 100 \
  --cost-high 25 \
  --format csv \
  --output cost-optimization.csv
```

## 🔍 Enhanced Detection Capabilities
- **Unattached disks and snapshots** with usage pattern analysis
- **Unused public IP addresses** with traffic metrics verification
- **Orphaned network interfaces** with bandwidth utilization checks  
- **Empty storage accounts** with transaction history analysis
- **Backup-aware snapshot analysis** - protects critical recovery points
- **Cost-optimized recommendations** using actual billing data

## 🛡️ Built-in Safety Features
- **Backup Policy Integration**: Automatically detects Azure Backup dependencies
- **Usage Pattern Analysis**: Verifies resources are truly unused via Azure Monitor
- **Actual Cost Verification**: Uses Azure Cost Management for precise savings calculations
- **Risk-Based Confidence Scoring**: Multi-factor analysis prevents false positives
- **Smart Recommendations**: Context-aware cleanup guidance with risk assessment

## 🔬 How Enhanced Analysis Works

### 1. **Cross-Reference with Azure Cost Management**
- Retrieves actual billing data instead of estimates
- Compares projected vs. actual costs for accuracy
- Identifies cost trends and optimization opportunities

### 2. **Verify Against Actual Usage Patterns**
- **Disk Analysis**: IOPS, throughput, and access patterns from Azure Monitor
- **Storage Analysis**: Transaction counts, ingress/egress patterns
- **Network Analysis**: Bandwidth utilization and traffic flows
- **Activity Scoring**: 0.0-1.0 scale based on recent usage intensity

### 3. **Backup and Disaster Recovery Awareness**
- **Azure Backup Integration**: Checks Recovery Services Vaults and policies
- **Naming Pattern Recognition**: Identifies backup-related resources
- **Retention Policy Analysis**: Respects backup retention requirements
- **Risk Assessment**: Categorizes deletion risk (Low/Medium/High/Critical)

## 🔧 Installation & Setup

### Step 1: Install Dependencies
```bash
# Install the tool in development mode
pip install -e .

# Or install from requirements
pip install -r requirements.txt
```

### Step 2: Azure CLI Setup
```bash
# Install Azure CLI (if not already installed)
# Windows: https://aka.ms/installazurecliwindows
# Linux: curl -sL https://aka.ms/InstallAzureCLIDeb | sudo bash
# macOS: brew install azure-cli

# Login to Azure
az login

# Verify access
az account list --output table
```

### Step 3: Verify Installation
```bash
# Test the tool
python -m azure_orphan_detector.cli.main scan --help

# Quick validation scan (safe, no changes made)
python -m azure_orphan_detector.cli.main scan --max-age 365 --confidence 0.9

# Or use the installation script
python install.py
```

## 🔐 Permissions Required

### ✅ **Minimum Required (Works Great!)**
- **Subscription Reader** or **Reader** role - This is sufficient for core functionality!

### ⚡ **Enhanced Features (Optional)**
For additional insights, these roles provide enhanced capabilities:

| Role | Purpose | Impact Without It |
|------|---------|-------------------|
| **Reader** | Basic resource enumeration | ✅ **REQUIRED** - Core functionality |
| **Cost Management Reader** | Actual billing data | ⚠️ Uses estimated pricing instead |
| **Monitoring Reader** | Detailed usage metrics | ⚠️ Uses basic analysis instead |
| **Backup Reader** | Full backup policy analysis | ⚠️ Uses name-based detection instead |

### 🎯 **For Subscription Reader Users**
If you only have **Subscription Reader** access, the tool will:
- ✅ **Work perfectly** for orphan detection
- ✅ **Generate all reports** and dashboards  
- ⚠️ **Use estimated costs** instead of actual billing
- ⚠️ **Use basic analysis** instead of detailed metrics

```bash
# Check your current permissions
az role assignment list --assignee $(az account show --query user.name -o tsv) --output table

# If you only see "Reader" or "Subscription Reader" - that's perfect for basic usage!
```

### 🎯 **Running with Limited Permissions**

If you have **Subscription Reader** or **Reader** role only:

```bash
# The tool works great with basic permissions!
python -m azure_orphan_detector.cli.main scan

# You'll see messages like:
# ✅ Credential initialized using Azure CLI  
# ⚠️ Cost Management API not available - using estimated pricing
# ⚠️ Usage metrics limited - basic analysis only

# This is normal and expected - the tool still finds orphaned resources!
```

### 📞 **Requesting Additional Permissions (Optional)**

If you want enhanced features, ask your Azure admin for these roles:

```bash
# Example: Request from subscription owner
az role assignment create \
  --assignee "user@domain.com" \
  --role "Cost Management Reader" \
  --scope "/subscriptions/YOUR-SUBSCRIPTION-ID"
```

## 📊 Enhanced Output Examples

```bash
# Resource with backup dependency detected
⚠️  CRITICAL: snapshot-prod-daily-20240925 appears to be part of automated backup system
🚫 DO NOT DELETE without verifying with backup/DR team
💰 Actual cost data available: $45.67/month

# Resource with recent activity
⚠️  Resource shows recent activity (score: 0.73) - verify it's not in use before deletion
📈 Average IOPS: 125.3, Last activity: 2024-09-20 14:23:00

# Safe to delete resource
✅ LOW RISK: No backup dependencies detected
✅ No recent activity detected - safe to delete from usage perspective
💰 Potential savings: $1,234.56/year
```

## 🎯 Common Use Cases

### 1. Monthly Cost Optimization Review
```bash
# Generate comprehensive cost report
python -m azure_orphan_detector.cli.main scan \
  --max-age 90 \
  --confidence 0.7 \
  --format csv \
  --output monthly-optimization-2025-09.csv \
  --verbose
```

### 2. Pre-Production Cleanup
```bash
# Clean up dev/test environments aggressively
python -m azure_orphan_detector.cli.main scan \
  --subscription "dev-sub-id" \
  --max-age 14 \
  --confidence 0.6 \
  --exclude-resource-group "rg-shared"
```

### 3. Compliance & Audit Reporting
```bash
# Conservative scan for compliance review
python -m azure_orphan_detector.cli.main scan \
  --max-age 365 \
  --confidence 0.9 \
  --cost-critical 500 \
  --format json \
  --output audit-report-20250925.json
```

### 4. Emergency Cost Reduction
```bash
# Find high-impact savings quickly
python -m azure_orphan_detector.cli.main scan \
  --cost-critical 50 \
  --confidence 0.6 \
  --max-age 30 \
  --format table
```

## 🔧 Troubleshooting

### Common Issues & Solutions

#### "No Azure credentials found"
```bash
# Solution: Login to Azure CLI
az login
az account show  # Verify login worked
```

#### "Insufficient permissions"
```bash
# Check your roles
az role assignment list --assignee $(az account show --query user.name -o tsv)

# Request additional roles from subscription owner:
# - Cost Management Reader
# - Monitoring Reader  
# - Backup Reader
```

#### "ModuleNotFoundError" for Azure packages
```bash
# Reinstall dependencies
pip install --upgrade -r requirements.txt

# Or install individual packages
pip install azure-mgmt-costmanagement azure-mgmt-monitor
```

#### "Rate limiting" or timeout errors
```bash
# Reduce parallel workers
azure-orphan-detector scan --workers 2

# Scan specific resource groups instead of entire subscription
azure-orphan-detector scan -g "specific-rg"
```

#### Dashboard not opening automatically
```bash
# Generate dashboard to specific location
azure-orphan-detector scan --dashboard-output ./dashboard.html

# Then open manually in browser
start ./dashboard.html  # Windows
open ./dashboard.html   # macOS
xdg-open ./dashboard.html  # Linux
```

### Debug Mode
```bash
# Enable detailed logging
python -m azure_orphan_detector.cli.main scan --verbose

# Save logs to file (PowerShell)
python -m azure_orphan_detector.cli.main scan --verbose 2> debug.log

# Save logs to file (Command Prompt)
python -m azure_orphan_detector.cli.main scan --verbose 2> debug.log
```

## 🏗️ Project Structure
```
azure-orphan-detector/
├── azure_orphan_detector/     # Main package
│   ├── core/                  # Core detection engine
│   │   ├── detector.py        # Main orchestrator
│   │   ├── models.py          # Data models
│   │   └── interfaces.py      # Abstract interfaces
│   ├── auth/                  # Azure authentication
│   │   └── manager.py         # Credential management
│   ├── analyzers/             # Resource-specific analyzers
│   │   ├── disk_analyzer.py   # Disks & snapshots
│   │   ├── storage_analyzer.py # Storage accounts
│   │   ├── network_interface_analyzer.py # NICs
│   │   └── public_ip_analyzer.py # Public IPs
│   ├── cost/                  # Cost calculation & optimization
│   │   └── calculator.py      # Azure Cost Management integration
│   ├── utils/                 # Enhanced analysis utilities
│   │   ├── usage_analyzer.py  # Azure Monitor integration
│   │   ├── backup_analyzer.py # Backup policy awareness
│   │   ├── config.py          # Configuration management
│   │   └── logger.py          # Logging setup
│   ├── dashboard/             # Interactive reporting
│   │   └── generator.py       # HTML dashboard generator
│   └── cli/                   # Command-line interface
│       └── main.py            # Typer-based CLI
├── requirements.txt           # Python dependencies
├── setup.py                   # Package installation
└── README.md                  # This file
```

## 🤝 Contributing & Support

### Getting Help
1. Check the [Troubleshooting](#troubleshooting) section
2. Review command help: `azure-orphan-detector scan --help`
3. Enable verbose logging: `--verbose`
4. Check Azure CLI connectivity: `az account show`

### Feature Requests
- Enhanced resource type support
- Additional cloud provider integrations
- Custom analysis rules
- Advanced reporting formats
