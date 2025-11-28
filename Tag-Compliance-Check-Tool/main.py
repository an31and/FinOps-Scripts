#!/usr/bin/env python3
"""
Azure Resource Tagging Analysis Tool - Main Script

This is the main entry point for the Azure tagging analysis tool.
It coordinates between all modules to provide comprehensive tagging analysis.

Requirements:
    pip install azure-identity requests openpyxl python-dotenv tqdm fuzzywuzzy

Usage:
    python main.py --config config.json
    python main.py --output report.xlsx --debug

Author: Azure Tagging Analysis Tool
Version: 2.0 - Ultra-Modular Edition
"""

import argparse
import logging
import sys
import time
from pathlib import Path

# Import our modules
from config_manager import Config, load_config, generate_sample_config_file
from azure_analyzer import AzureTagAnalyzer
#from excel_generator_core import EnhancedExcelReportGenerator #this is for version 2.0
from updated_excel_generator_core import UltraEnhancedExcelReportGenerator as EnhancedExcelReportGenerator
from dashboard_core import InteractiveDashboardGenerator
#from excel_generator_core import UltraEnhancedExcelReportGenerator as EnhancedExcelReportGenerator
from updated_excel_generator_core import UltraEnhancedExcelReportGenerator as EnhancedExcelReportGenerator
from utils import setup_logging, print_summary_stats

# Import our modules
from config_manager import Config, load_config, generate_sample_config_file
from azure_analyzer import AzureTagAnalyzer
from updated_excel_generator_core import UltraEnhancedExcelReportGenerator as EnhancedExcelReportGenerator  # ← This line changed
from dashboard_core import InteractiveDashboardGenerator
from utils import setup_logging, print_summary_stats

def main():
    """Main function with interactive dashboard support"""
    parser = argparse.ArgumentParser(
        description="Enhanced Azure Resource Tagging Analysis Tool with Interactive Drill-Down Dashboard",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python main.py --config config.json
  python main.py --output report.xlsx
  python main.py --mandatory-tags "Environment,CostCenter,Owner"
  python main.py --subscriptions "sub1,sub2" --exclude-subscriptions "sub3"
  python main.py --tag-variations-file variations.json --max-workers 10
  python main.py --use-default-variations --debug

Compliance Status:
  - COMPLIANT (Green): Tag name matches exactly (e.g., "Environment" = "Environment")
  - PARTIAL (Yellow): Tag matches variation (e.g., "env" matches "Environment")
  - NON_COMPLIANT (Red): Tag is missing or doesn't match any variations
        """
    )
    parser.add_argument("--config", help="Configuration file path")
    parser.add_argument("--output", help="Output Excel file path")
    parser.add_argument("--subscriptions", help="Comma-separated subscription IDs")
    parser.add_argument("--exclude-subscriptions", help="Comma-separated subscription IDs to exclude")
    parser.add_argument("--mandatory-tags", help="Comma-separated mandatory tags")
    parser.add_argument("--max-workers", type=int, help="Number of parallel workers")
    parser.add_argument("--exclude-types", help="Comma-separated resource types to exclude (in addition to non-taggable)")
    parser.add_argument("--tag-variations-file", help="JSON file containing tag variations configuration")
    parser.add_argument("--use-default-variations", action="store_true", help="Use default tag variations")
    parser.add_argument("--fuzzy-threshold", type=int, help="Fuzzy matching threshold (0-100)")
    parser.add_argument("--debug", action="store_true", help="Enable debug mode with verbose logging")
    parser.add_argument("--generate-sample-config", action="store_true", help="Generate sample configuration file and exit")
    
    args = parser.parse_args()
    
    # Setup logging with debug mode if requested
    setup_logging(debug_mode=args.debug)
    logger = logging.getLogger(__name__)
    
    # Generate sample config if requested
    if args.generate_sample_config:
        logger.info("🔧 Generating sample configuration files...")
        generate_sample_config_file(Config())
        logger.info("✅ Sample files generated: sample_config.json")
        return
    
    # Load configuration
    logger.debug("📋 Loading configuration...")
    config = load_config()
    
    # Override with command line arguments
    if args.output:
        config.output_file = args.output
        logger.debug(f"Output file set to: {config.output_file}")
    if args.subscriptions:
        config.subscription_ids = [s.strip() for s in args.subscriptions.split(",")]
        logger.debug(f"Subscription IDs set to: {config.subscription_ids}")
    if args.exclude_subscriptions:
        config.excluded_subscription_ids = [s.strip() for s in args.exclude_subscriptions.split(",")]
        logger.debug(f"Excluded subscription IDs: {config.excluded_subscription_ids}")
    if args.mandatory_tags:
        config.mandatory_tags = [t.strip() for t in args.mandatory_tags.split(",")]
        logger.debug(f"Mandatory tags set to: {config.mandatory_tags}")
    if args.max_workers:
        config.max_workers = args.max_workers
        logger.debug(f"Max workers set to: {config.max_workers}")
    if args.exclude_types:
        for t in args.exclude_types.split(","):
            if t.strip():
                config.exclude_resource_types.add(t.strip())
        logger.debug(f"Additional excluded resource types: {args.exclude_types}")
    if args.fuzzy_threshold:
        config.fuzzy_matching_threshold = args.fuzzy_threshold
        logger.debug(f"Fuzzy threshold set to: {config.fuzzy_matching_threshold}")
    
    # Load tag variations
    from tag_variations import create_default_tag_variations, TagVariation
    
    if args.use_default_variations:
        logger.debug("🔄 Loading default tag variations...")
        config.tag_variations.update(create_default_tag_variations())
        logger.info("Loaded default tag variations")
    
    if args.tag_variations_file and Path(args.tag_variations_file).exists():
        logger.debug(f"📂 Loading tag variations from file: {args.tag_variations_file}")
        try:
            import json
            with open(args.tag_variations_file, 'r') as f:
                variations_data = json.load(f)
                for canonical, variation_config in variations_data.items():
                    config.tag_variations[canonical] = TagVariation(
                        canonical_name=canonical,
                        variations=variation_config.get("variations", []),
                        fuzzy_threshold=variation_config.get("fuzzy_threshold", config.fuzzy_matching_threshold),
                        case_sensitive=variation_config.get("case_sensitive", False)
                    )
            logger.info(f"Loaded tag variations from {args.tag_variations_file}")
            logger.debug(f"Loaded {len(config.tag_variations)} tag variation configurations")
        except Exception as e:
            logger.error(f"Error loading tag variations file: {e}")
            if args.debug:
                logger.exception("Full traceback:")
    
    # Load main config file if provided
    if args.config and Path(args.config).exists():
        logger.debug(f"📂 Loading main config file: {args.config}")
        try:
            import json
            with open(args.config, 'r') as f:
                file_config = json.load(f)
                
                # Process each configuration item
                for key, value in file_config.items():
                    # Skip comment fields
                    if key.startswith('_comment') or key.startswith('//'):
                        continue
                    
                    if hasattr(config, key) and key != 'tag_variations':
                        setattr(config, key, value)
                        logger.debug(f"Config {key} set to: {value}")
                
                # Handle tag variations from config file
                if 'tag_variations' in file_config:
                    logger.debug("Processing tag variations from config file...")
                    for canonical, variation_config in file_config['tag_variations'].items():
                        config.tag_variations[canonical] = TagVariation(
                            canonical_name=variation_config.get("canonical_name", canonical),
                            variations=variation_config.get("variations", []),
                            fuzzy_threshold=variation_config.get("fuzzy_threshold", config.fuzzy_matching_threshold),
                            case_sensitive=variation_config.get("case_sensitive", False)
                        )
                
                # Handle dashboard options
                if 'dashboard_options' in file_config:
                    config.dashboard_options.update(file_config['dashboard_options'])
                    
        except Exception as e:
            logger.error(f"Error loading config file: {e}")
            if args.debug:
                logger.exception("Full traceback:")
    
    logger.info("🚀 Starting Enhanced Azure Tagging Analysis with Interactive Dashboard...")
    logger.info(f"📋 Mandatory tags: {config.mandatory_tags}")
    logger.info(f"🔄 Tag variations configured: {len(config.tag_variations)}")
    logger.info(f"📄 Output file: {config.output_file}")
    logger.info(f"⚡ Max workers: {config.max_workers}")
    
    if config.excluded_subscription_ids:
        logger.info(f"🚫 Excluded subscriptions: {len(config.excluded_subscription_ids)}")
    
    logger.info("\n📌 Compliance Status Definitions:")
    logger.info("   ✅ COMPLIANT: Tag matches exactly (e.g., 'Environment' = 'Environment')")
    logger.info("   ⚠️  PARTIAL: Tag matches variation (e.g., 'env' matches 'Environment')")
    logger.info("   ❌ NON_COMPLIANT: Tag is missing or doesn't match any variations\n")
    
    start_time = time.time()
    
    try:
        # Initialize analyzer
        logger.debug("🔧 Initializing Azure Tag Analyzer...")
        analyzer = AzureTagAnalyzer(config)
        analyzer.get_access_token()
        
        # Analyze subscriptions
        logger.debug("🔍 Starting subscription analysis...")
        resource_tags, rg_tags, subscriptions = analyzer.analyze_subscriptions()
        
        if not resource_tags and not rg_tags:
            logger.warning("⚠️  No data collected. Check your subscriptions and permissions.")
            return
        
        logger.debug(f"📊 Analysis complete: {len(resource_tags)} resource tags, {len(rg_tags)} RG tags, {len(subscriptions)} subscriptions")
        
        # Generate enhanced report (Excel)
        logger.debug("📄 Generating Excel report...")
        report_generator = EnhancedExcelReportGenerator(config)
        report_generator.generate_report(resource_tags, rg_tags, subscriptions)
        report_generator.save(config.output_file)
        logger.debug("✅ Excel report generation complete")
        
        # Generate interactive HTML dashboard with drill-down
        logger.debug("🌐 Generating interactive HTML dashboard...")
        dashboard_generator = InteractiveDashboardGenerator(config)
        dashboard_file = dashboard_generator.generate_dashboard(resource_tags, rg_tags, subscriptions, config.output_file)
        logger.debug("✅ HTML dashboard generation complete")
        
        # Generate CSV export for detailed data
        logger.debug("📊 Generating CSV export...")
        csv_file = config.output_file.replace('.xlsx', '_detailed_data.csv')
        
        import csv
        with open(csv_file, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            
            # Write header
            writer.writerow([
                'Subscription', 'Tag Name', 'Tag Value', 'Resource Name', 'Resource Type', 
                'Resource ID', 'Location', 'Compliance Status', 'Canonical Tag', 'Variation Matched'
            ])
            
            # Write data
            for tag in resource_tags:
                writer.writerow([
                    tag.subscription_name, tag.name, tag.value, tag.resource_name, 
                    tag.resource_type, tag.resource_id, tag.resource_location,
                    tag.compliance_status, tag.canonical_tag_name, tag.variation_matched
                ])
        
        logger.info(f"📊 CSV export generated: {csv_file}")
        
        # Print summary statistics
        logger.debug("📈 Generating summary statistics...")
        print_summary_stats(subscriptions, config)
        
        # Final summary
        end_time = time.time()
        elapsed_time = end_time - start_time
        minutes, seconds = divmod(elapsed_time, 60)
        
        logger.info("✅ Analysis Complete!")
        logger.info(f"⏱️  Execution time: {int(minutes)} minutes and {int(seconds)} seconds")
        logger.info(f"📊 Enhanced Excel report generated: {config.output_file}")
        logger.info(f"📊 CSV export generated: {csv_file}")
        logger.info(f"🌐 Interactive HTML dashboard generated: {dashboard_file}")
        logger.info(f"📈 Open the HTML dashboard in your browser for interactive drill-down analysis!")
        
        # Generate sample configuration files if they don't exist
        if not Path("sample_config.json").exists():
            logger.debug("📝 Generating sample configuration files...")
            generate_sample_config_file(config)
        
    except KeyboardInterrupt:
        logger.info("⏹️  Script interrupted by user")
    except Exception as e:
        logger.error(f"❌ Script failed: {e}")
        if args.debug:
            logger.exception("Full traceback:")
        else:
            logger.error("Use --debug flag for detailed error information")
        sys.exit(1)


if __name__ == "__main__":
    main()
