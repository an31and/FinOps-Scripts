# 🚀 Azure BYOL (Bring Your Own License) Conversion Tool

## 📋 Overview

The **Azure BYOL Conversion Tool** is an enterprise-grade automation script that helps organizations save 40-50% on Windows VM licensing costs by converting from Azure's pay-as-you-go licensing to BYOL (using your existing Windows Server licenses).

### 💰 Key Benefits
- **Cost Savings**: Reduce Windows VM licensing costs by 40-50%
- **Enterprise Scale**: Handle hundreds of VMs across multiple subscriptions
- **Risk Management**: Comprehensive assessment before any changes
- **Auto-Discovery**: Automatically finds all accessible Azure subscriptions
- **Professional Reporting**: HTML and Excel reports for management and technical teams
- **Safety First**: Dry-run mode and snapshot creation before changes

---

## 🎯 What This Tool Does

### Core Functionality
1. **🔍 Auto-Discovery**: Automatically discovers all Azure subscriptions and Windows VMs
2. **💰 Cost Analysis**: Calculates current costs and potential savings
3. **⚡ Risk Assessment**: Evaluates conversion readiness for each VM
4. **📊 Professional Reporting**: Generates HTML executive summaries and Excel technical reports
5. **🔄 Safe Conversion**: Converts VMs to BYOL with safety measures (snapshots, rollback)

### Example Savings
```
Typical Results:
- Standard_D4s_v3: $200/month → $100/month (50% savings)
- Standard_E8s_v3: $400/month → $200/month (50% savings)
- Enterprise Scale: $455K+ annual savings potential
```

---

## 🛠️ Installation & Setup

### Prerequisites
- **Python 3.8+** installed
- **Azure CLI** installed and configured (`az login`)
- **Azure Permissions**: Reader access to subscriptions, Contributor access for conversions
- **Windows Server Licenses**: Valid licenses for BYOL conversion

### 1. Install Dependencies

#### Option A: Automatic Installation (Recommended)
```powershell
# Run the automated installer
.\install_dependencies.ps1
```

#### Option B: Manual Installation
```bash
pip install -r requirements.txt
```

#### Option C: Check Dependencies
```bash
python check_dependencies.py
```

### 2. Azure Authentication Setup

#### Method 1: Azure CLI (Recommended)
```bash
# Login to Azure
az login

# Set default subscription (optional)
az account set --subscription "your-subscription-id"
```

#### Method 2: Service Principal (Enterprise)
```bash
# Set environment variables
$env:AZURE_CLIENT_ID = "your-client-id"
$env:AZURE_CLIENT_SECRET = "your-client-secret"
$env:AZURE_TENANT_ID = "your-tenant-id"
```

#### Method 3: Managed Identity (Azure VMs)
No additional setup required when running on Azure VMs with managed identity.

---

## 🚀 Quick Start Guide

### Step 1: Basic Assessment (Start Here!)
```bash
# Run dry-run analysis (safe, no changes made)
python byol_conversion_script.py --dry-run
```

**What this does:**
- Discovers all your Azure subscriptions automatically
- Analyzes all Windows VMs
- Generates cost savings reports
- **No changes made to your environment**

### Step 2: Review Reports
Check the generated files in the `byol_reports/` folder:
- `executive_summary_YYYYMMDD_HHMMSS.html` - Management dashboard
- `technical_analysis_YYYYMMDD_HHMMSS.xlsx` - Detailed technical data

### Step 3: Production Conversion (When Ready)
```bash
# Live conversion (makes actual changes!)
python byol_conversion_script.py
```

---

## 📚 Usage Options

### Auto-Discovery Mode (Default)
```bash
# Automatically discover and analyze all accessible subscriptions
python byol_conversion_script.py --dry-run
```

### Single Subscription
```bash
# Target specific subscription
python byol_conversion_script.py --subscription-id "12345678-1234-1234-1234-123456789012" --dry-run
```

### Multiple Subscriptions
```bash
# Target multiple specific subscriptions
python byol_conversion_script.py --subscription-ids "sub1-id" "sub2-id" "sub3-id" --dry-run
```

### Subscription File
```bash
# Use subscription list from file
python byol_conversion_script.py --subscription-file subscriptions.txt --dry-run
```

#### Example `subscriptions.txt`:
```
# Production subscriptions
12345678-1234-1234-1234-123456789012
87654321-4321-4321-4321-210987654321

# Development subscriptions  
11111111-2222-3333-4444-555555555555
```

### Disable Auto-Discovery
```bash
# Work with specific subscriptions only
python byol_conversion_script.py --no-auto-discover --subscription-id "specific-sub-id"
```

---

## ⚙️ Configuration Options

### Command Line Arguments

| Argument | Description | Example |
|----------|-------------|---------|
| `--dry-run` | Run simulation without making changes (recommended) | `--dry-run` |
| `--subscription-id` | Target single subscription | `--subscription-id "12345678-..."` |
| `--subscription-ids` | Target multiple subscriptions | `--subscription-ids "sub1" "sub2"` |
| `--subscription-file` | Load subscriptions from file | `--subscription-file subs.txt` |
| `--auto-discover` | Auto-discover subscriptions (default) | `--auto-discover` |
| `--no-auto-discover` | Disable auto-discovery | `--no-auto-discover` |
| `--batch-mode` | Enterprise batch processing | `--batch-mode` |
| `--output-dir` | Custom output directory | `--output-dir "custom_reports"` |

### Environment Variables

| Variable | Purpose | Example |
|----------|---------|---------|
| `AZURE_SUBSCRIPTION_ID` | Default subscription | `12345678-1234-1234-1234-123456789012` |
| `AZURE_CLIENT_ID` | Service principal ID | `11111111-2222-3333-4444-555555555555` |
| `AZURE_CLIENT_SECRET` | Service principal secret | `your-client-secret` |
| `AZURE_TENANT_ID` | Azure tenant ID | `22222222-3333-4444-5555-666666666666` |

---

## 🔍 Operating Modes

### 🛡️ Dry-Run Mode (Recommended First Step)
```bash
python byol_conversion_script.py --dry-run
```

**What happens:**
- ✅ Scans all VMs and analyzes costs
- ✅ Generates comprehensive reports
- ✅ Shows potential savings
- ✅ **No changes made to Azure environment**
- ✅ Zero risk assessment

**Use for:**
- Initial cost assessment
- Management presentations
- Planning and approval process

### ⚠️ Live Conversion Mode
```bash
python byol_conversion_script.py
```

**What happens:**
- ⚠️ **Makes actual changes to VMs**
- ⚠️ Converts license type to BYOL
- ✅ Creates safety snapshots first
- ✅ Immediate cost savings
- ✅ Detailed conversion logging

**Requirements:**
- Valid Windows Server licenses
- Azure Contributor permissions
- Management approval

### 🏭 Batch Mode (Enterprise Scale)
```bash
python byol_conversion_script.py --batch-mode
```

**Features:**
- Concurrent processing for speed
- Enterprise-grade error handling
- Real-time progress monitoring
- Handles thousands of VMs

---

## 📊 Understanding Reports

### Executive Summary (HTML)
**File:** `executive_summary_YYYYMMDD_HHMMSS.html`

**Contains:**
- High-level cost savings overview
- Visual charts and metrics
- Business case for BYOL conversion
- Risk summary

**Audience:** Management, decision-makers

### Technical Analysis (Excel)
**File:** `technical_analysis_YYYYMMDD_HHMMSS.xlsx`

**Sheets:**
- **VM Inventory**: Complete VM list with specifications
- **Summary**: Aggregated statistics
- **Risk Analysis**: Risk breakdown by category
- **Environment Analysis**: By environment type

**Audience:** Technical teams, engineers

### Conversion Plan (Excel)
**File:** `conversion_plan_YYYYMMDD_HHMMSS.xlsx`

**Contains:**
- Phase-by-phase implementation timeline
- Risk-based prioritization
- Detailed conversion steps

---

## 🛡️ Safety & Risk Management

### Risk Assessment
The tool automatically categorizes VMs by risk level:

- 🔴 **High Risk**: Production VMs, critical systems
- 🟡 **Medium Risk**: QA, staging environments
- 🟢 **Low Risk**: Development, test VMs

### Safety Measures
- **Snapshots**: Automatic creation before conversion
- **Rollback**: Ability to revert changes
- **Dry-run**: Test everything before live conversion
- **Logging**: Comprehensive audit trail

### Best Practices
1. **Always start with dry-run mode**
2. **Review all reports thoroughly**
3. **Get management approval**
4. **Start with low-risk VMs**
5. **Monitor post-conversion**

---

## 🔧 Advanced Configuration

### Custom Output Directory
```bash
python byol_conversion_script.py --output-dir "custom_reports" --dry-run
```

### Enterprise Service Principal Setup
```powershell
# Create service principal
az ad sp create-for-rbac --name "BYOL-Converter" --role "Contributor" --scopes "/subscriptions/your-sub-id"

# Set environment variables
$env:AZURE_CLIENT_ID = "output-appId"
$env:AZURE_CLIENT_SECRET = "output-password"
$env:AZURE_TENANT_ID = "output-tenant"
```

### Multi-Cloud Support (Future)
The script architecture supports extension to other cloud providers:
- AWS EC2 instances
- Google Cloud Platform VMs

---

## 📈 Expected Results

### Typical Savings by VM Size

| VM Size | Current Cost/Month | BYOL Cost/Month | Savings/Month | Savings/Year |
|---------|-------------------|-----------------|---------------|--------------|
| Standard_B2s | $73 | $29 | $44 | $528 |
| Standard_D2s_v3 | $100 | $50 | $50 | $600 |
| Standard_D4s_v3 | $200 | $100 | $100 | $1,200 |
| Standard_E8s_v3 | $400 | $200 | $200 | $2,400 |

### Enterprise Example
```
Large Organization Results:
- Total VMs: 695
- Conversion Candidates: 11
- Monthly Savings: $37,979
- Annual Savings: $455,747
- ROI Period: 2-3 months
```

---

## 🚨 Troubleshooting

### Common Issues

#### 1. Authentication Errors
```bash
# Error: Authentication failed
# Solution: Login to Azure CLI
az login
az account show  # Verify login
```

#### 2. Permission Errors
```bash
# Error: Insufficient permissions
# Solution: Ensure proper Azure roles
az role assignment list --assignee your-user@domain.com
```

#### 3. No VMs Found
```bash
# Issue: Script reports 0 VMs
# Check: Verify subscription access and Windows VMs exist
az vm list --query "[?storageProfile.osDisk.osType=='Windows']"
```

#### 4. Unicode Errors (Windows Console)
```bash
# Issue: Emoji character errors in console
# Solution: These are cosmetic only, reports still generate correctly
# Use PowerShell or set console encoding to UTF-8
```

### Getting Help
1. Check log files in the output directory
2. Run with `--dry-run` first to isolate issues
3. Verify Azure CLI authentication: `az account show`
4. Check subscription permissions
5. Review generated reports for detailed error information

---

## 📋 Requirements File Contents

### `requirements.txt`
```txt
# Azure SDK dependencies
azure-identity>=1.12.0
azure-mgmt-compute>=29.0.0
azure-mgmt-resource>=21.0.0
azure-core>=1.26.0

# Multi-cloud support
boto3>=1.26.0

# Data processing
pandas>=1.5.0
openpyxl>=3.0.0

# Utilities
requests>=2.28.0
```

---

## 🎯 Implementation Strategy

### Phase 1: Assessment (Week 1)
1. Install and configure the tool
2. Run dry-run analysis across all subscriptions
3. Review reports and identify savings opportunities
4. Present business case to management

### Phase 2: Pilot (Week 2-3)
1. Select low-risk development/test VMs
2. Perform pilot conversions
3. Validate savings and functionality
4. Refine conversion strategy

### Phase 3: Production (Week 4+)
1. Convert medium-risk VMs
2. Convert high-risk VMs with careful planning
3. Monitor and validate savings
4. Document results and lessons learned

---

## 📞 Support Information

### Prerequisites Checklist
- [ ] Python 3.8+ installed
- [ ] Azure CLI installed and configured
- [ ] Required Azure permissions (Reader minimum, Contributor for conversions)
- [ ] Valid Windows Server licenses for BYOL
- [ ] Management approval for conversions

### Quick Validation
```bash
# Verify setup
python --version          # Should be 3.8+
az --version              # Should be installed
az account show           # Should show current subscription
python check_dependencies.py  # All dependencies OK
```

---

## 🏆 Success Metrics

### Key Performance Indicators
- **Cost Reduction**: Target 40-50% savings on Windows licensing
- **ROI Achievement**: Typically 2-3 months payback period
- **Risk Management**: Zero production incidents during conversion
- **Automation**: 90%+ reduction in manual effort vs manual conversion

### Monitoring Post-Conversion
- Monitor Azure billing for cost reductions
- Validate VM functionality post-conversion
- Track any licensing compliance requirements
- Document total savings achieved

---

## 📄 License & Compliance

### Tool Usage
This tool is designed to help with legitimate BYOL conversions where you own valid Windows Server licenses. Ensure compliance with Microsoft licensing terms.

### Audit Trail
The tool maintains comprehensive logs for:
- All VMs discovered and analyzed
- Conversion decisions and rationale
- Actual changes made to Azure resources
- Cost savings achieved

---

## 🔄 Version History

### v2.0 (Current)
- Auto-discovery of Azure subscriptions
- Multi-subscription support
- Enhanced risk assessment
- Professional reporting
- Enterprise-grade safety features

### Previous Versions
- v1.x: Single subscription support
- v0.x: Basic conversion functionality

---

**🎉 Ready to save money on your Azure Windows VMs? Start with a dry-run analysis today!**

```bash
python byol_conversion_script.py --dry-run
```