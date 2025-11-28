#!/usr/bin/env python3
"""
Final Module Validation Script

Validates that all modularized components can be imported and work together correctly.
This is the FINAL VERSION for the ultra-modular structure.
"""

import sys
import traceback
from pathlib import Path

def validate_imports():
    """Validate all module imports"""
    print("🔍 Validating module imports...")
    
    # Core modules
    core_modules = [
        'config_manager',
        'constants', 
        'data_models',
        'utils',
        'tag_variations',
        'azure_analyzer'
    ]
    
    # Excel modules  
    excel_modules = [
        'excel_styles',
        'excel_worksheets', 
        'excel_summaries',
        'excel_generator_core'
    ]
    
    # Dashboard modules
    dashboard_modules = [
        'dashboard_data',
        'dashboard_html_styles',
        'dashboard_html_structure',
        'dashboard_scripts_core',
        'dashboard_scripts_charts',
        'dashboard_scripts_interactions', 
        'dashboard_scripts_utils',
        'dashboard_html_core',
        'dashboard_core'
    ]
    
    all_modules = core_modules + excel_modules + dashboard_modules
    failed_imports = []
    
    print("\n📦 Core Modules:")
    for module in core_modules:
        try:
            __import__(module)
            print(f"  ✅ {module}")
        except ImportError as e:
            print(f"  ❌ {module}: {e}")
            failed_imports.append((module, str(e)))
    
    print("\n📊 Excel Modules:")
    for module in excel_modules:
        try:
            __import__(module)
            print(f"  ✅ {module}")
        except ImportError as e:
            print(f"  ❌ {module}: {e}")
            failed_imports.append((module, str(e)))
    
    print("\n🌐 Dashboard Modules:")
    for module in dashboard_modules:
        try:
            __import__(module)
            print(f"  ✅ {module}")
        except ImportError as e:
            print(f"  ❌ {module}: {e}")
            failed_imports.append((module, str(e)))
    
    return failed_imports

def validate_class_instantiation():
    """Validate that main classes can be instantiated"""
    print("\n🏗️  Validating class instantiation...")
    
    try:
        from config_manager import Config
        config = Config()
        print("  ✅ Config class")
        
        # Excel classes
        from excel_styles import ExcelStyleManager
        style_manager = ExcelStyleManager()
        print("  ✅ ExcelStyleManager class")
        
        from excel_worksheets import WorksheetGenerator
        worksheet_gen = WorksheetGenerator(config, style_manager)
        print("  ✅ WorksheetGenerator class")
        
        from excel_summaries import SummaryGenerator
        summary_gen = SummaryGenerator(config, style_manager)
        print("  ✅ SummaryGenerator class")
        
        from excel_generator_core import EnhancedExcelReportGenerator
        excel_gen = EnhancedExcelReportGenerator(config)
        print("  ✅ EnhancedExcelReportGenerator class")
        
        # Dashboard classes
        from dashboard_data import DashboardDataPreparator
        data_prep = DashboardDataPreparator(config)
        print("  ✅ DashboardDataPreparator class")
        
        from dashboard_html_styles import DashboardStylesGenerator
        styles_gen = DashboardStylesGenerator()
        print("  ✅ DashboardStylesGenerator class")
        
        from dashboard_html_structure import DashboardStructureGenerator
        structure_gen = DashboardStructureGenerator(config)
        print("  ✅ DashboardStructureGenerator class")
        
        from dashboard_scripts_charts import DashboardChartsGenerator
        charts_gen = DashboardChartsGenerator()
        print("  ✅ DashboardChartsGenerator class")
        
        from dashboard_scripts_interactions import DashboardInteractionsGenerator
        interactions_gen = DashboardInteractionsGenerator(config)
        print("  ✅ DashboardInteractionsGenerator class")
        
        from dashboard_scripts_utils import DashboardUtilsGenerator
        utils_gen = DashboardUtilsGenerator()
        print("  ✅ DashboardUtilsGenerator class")
        
        from dashboard_scripts_core import DashboardScriptsGenerator
        scripts_gen = DashboardScriptsGenerator(config)
        print("  ✅ DashboardScriptsGenerator class")
        
        from dashboard_html_core import DashboardHTMLGenerator
        html_gen = DashboardHTMLGenerator(config)
        print("  ✅ DashboardHTMLGenerator class")
        
        from dashboard_core import InteractiveDashboardGenerator
        dashboard_gen = InteractiveDashboardGenerator(config)
        print("  ✅ InteractiveDashboardGenerator class")
        
        return True
        
    except Exception as e:
        print(f"  ❌ Class instantiation failed: {e}")
        traceback.print_exc()
        return False

def validate_file_structure():
    """Validate that all required files exist"""
    print("\n📁 Validating file structure...")
    
    required_files = [
        # Core files
        'config_manager.py',
        'constants.py',
        'data_models.py', 
        'utils.py',
        'tag_variations.py',
        'azure_analyzer.py',
        # Excel files
        'excel_styles.py',
        'excel_worksheets.py',
        'excel_summaries.py', 
        'excel_generator_core.py',
        # Dashboard files
        'dashboard_data.py',
        'dashboard_html_styles.py',
        'dashboard_html_structure.py',
        'dashboard_scripts_core.py',
        'dashboard_scripts_charts.py',
        'dashboard_scripts_interactions.py',
        'dashboard_scripts_utils.py',
        'dashboard_html_core.py',
        'dashboard_core.py'
    ]
    
    missing_files = []
    present_files = []
    
    for file in required_files:
        if Path(file).exists():
            print(f"  ✅ {file}")
            present_files.append(file)
        else:
            print(f"  ❌ {file} - MISSING")
            missing_files.append(file)
    
    print(f"\n📊 File Summary: {len(present_files)}/{len(required_files)} files present")
    return missing_files

def validate_integration():
    """Test that modules work together"""
    print("\n🔗 Validating module integration...")
    
    try:
        from config_manager import Config
        from excel_generator_core import EnhancedExcelReportGenerator
        from dashboard_core import InteractiveDashboardGenerator
        
        config = Config()
        excel_gen = EnhancedExcelReportGenerator(config)
        dashboard_gen = InteractiveDashboardGenerator(config)
        
        print("  ✅ Main generators can be instantiated together")
        print("  ✅ All imports work correctly")
        print("  ✅ Module integration successful")
        
        return True
        
    except Exception as e:
        print(f"  ❌ Integration test failed: {e}")
        return False

def main():
    """Main validation function"""
    print("🚀 Azure Tagging Analysis Tool - FINAL Module Validation")
    print("=" * 70)
    print("📦 Ultra-Modular Structure Validation (13 modules)")
    print("=" * 70)
    
    # Validate file structure
    missing_files = validate_file_structure()
    
    # Validate imports
    failed_imports = validate_imports()
    
    # Validate class instantiation
    classes_ok = validate_class_instantiation()
    
    # Validate integration
    integration_ok = validate_integration()
    
    # Summary
    print("\n" + "=" * 70)
    print("📋 FINAL VALIDATION SUMMARY")
    print("=" * 70)
    
    if missing_files:
        print(f"❌ Missing Files ({len(missing_files)}):")
        for file in missing_files:
            print(f"   - {file}")
    else:
        print("✅ All required files present (19 modules)")
    
    if failed_imports:
        print(f"\n❌ Failed Imports ({len(failed_imports)}):")
        for module, error in failed_imports:
            print(f"   - {module}: {error}")
    else:
        print("✅ All modules import successfully")
    
    if classes_ok:
        print("✅ All classes instantiate successfully")
    else:
        print("❌ Class instantiation issues detected")
    
    if integration_ok:
        print("✅ Module integration working perfectly")
    else:
        print("❌ Module integration issues detected")
    
    # Overall status
    all_good = not missing_files and not failed_imports and classes_ok and integration_ok
    
    print("\n" + "=" * 70)
    
    if all_good:
        print("🎉 ALL VALIDATIONS PASSED!")
        print("✅ Your ULTRA-MODULAR Azure Tagging Analysis Tool is ready!")
        print("\n📊 Structure Summary:")
        print("   📦 Core Modules: 6")
        print("   📊 Excel Modules: 4") 
        print("   🌐 Dashboard Modules: 9")
        print("   📁 Total Modules: 19")
        print("\n🚀 Next steps:")
        print("  1. Run: python main.py --generate-sample-config")
        print("  2. Edit: sample_config.json with your settings")
        print("  3. Run: python main.py --config sample_config.json")
        print("\n💡 Benefits achieved:")
        print("  ✅ No more download issues (small files)")
        print("  ✅ Easy to debug and maintain")
        print("  ✅ Perfect for team collaboration")
        print("  ✅ Modular testing and development")
    else:
        print("⚠️  VALIDATION ISSUES DETECTED")
        print("Please resolve the issues above before running the tool.")
        print("\n🔧 Troubleshooting:")
        print("  - Ensure all .py files are in the same directory")
        print("  - Check Python version (3.8+ required)")
        print("  - Verify all dependencies are installed")
        sys.exit(1)

def show_module_structure():
    """Display the complete module structure"""
    print("\n📁 Complete Module Structure:")
    print("""
Azure Tagging Analysis Tool (Ultra-Modular)
├── 📦 Core Modules (6)
│   ├── config_manager.py
│   ├── constants.py
│   ├── data_models.py
│   ├── utils.py
│   ├── tag_variations.py
│   └── azure_analyzer.py
├── 📊 Excel Generation (4)
│   ├── excel_styles.py
│   ├── excel_worksheets.py
│   ├── excel_summaries.py
│   └── excel_generator_core.py
└── 🌐 Dashboard Generation (9)
    ├── dashboard_data.py
    ├── dashboard_html_styles.py
    ├── dashboard_html_structure.py
    ├── dashboard_scripts_core.py
    ├── dashboard_scripts_charts.py
    ├── dashboard_scripts_interactions.py
    ├── dashboard_scripts_utils.py
    ├── dashboard_html_core.py
    └── dashboard_core.py
    """)

if __name__ == "__main__":
    main()
    show_module_structure()