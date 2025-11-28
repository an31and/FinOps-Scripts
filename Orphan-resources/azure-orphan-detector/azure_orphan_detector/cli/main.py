#!/usr/bin/env python3
"""Command-line interface for Azure Orphan Detector"""

import asyncio
import sys
import typer
from pathlib import Path
from typing import List, Optional
from rich.console import Console
from rich.table import Table
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.panel import Panel
from rich import print as rprint

from ..core.detector import OrphanDetector
from ..core.models import ScanConfiguration
from ..dashboard.generator import DashboardGenerator
from ..utils.logger import setup_logger

app = typer.Typer(
    name="azure-orphan-detector",
    help="🔍 Azure Orphaned Resources Detection System",
    add_completion=False
)

console = Console()


@app.command()
def scan(
    subscription_ids: Optional[List[str]] = typer.Option(
        None, "--subscription", "-s",
        help="Subscription IDs to scan (if not specified, scans all accessible)"
    ),
    resource_groups: Optional[List[str]] = typer.Option(
        None, "--resource-group", "-g",
        help="Specific resource groups to scan"
    ),
    exclude_resource_groups: Optional[List[str]] = typer.Option(
        None, "--exclude-resource-group", "-x",
        help="Resource groups to exclude from scan"
    ),
    cost_threshold_critical: float = typer.Option(
        100.0, "--cost-critical",
        help="Cost threshold for critical severity ($)"
    ),
    cost_threshold_high: float = typer.Option(
        50.0, "--cost-high",
        help="Cost threshold for high severity ($)"
    ),
    cost_threshold_medium: float = typer.Option(
        10.0, "--cost-medium",
        help="Cost threshold for medium severity ($)"
    ),
    confidence_threshold: float = typer.Option(
        0.7, "--confidence",
        help="Minimum confidence score (0.0-1.0)"
    ),
    include_low_confidence: bool = typer.Option(
        False, "--include-low-confidence",
        help="Include resources with low confidence scores"
    ),
    max_age_days: int = typer.Option(
        90, "--max-age",
        help="Maximum age in days for considering resources orphaned"
    ),
    parallel_workers: int = typer.Option(
        4, "--workers",
        help="Number of parallel workers"
    ),
    output_format: str = typer.Option(
        "dashboard", "--format", "-f",
        help="Output format: dashboard, json, csv, table"
    ),
    output_file: Optional[str] = typer.Option(
        None, "--output", "-o",
        help="Output file path"
    ),
    generate_dashboard: bool = typer.Option(
        True, "--dashboard/--no-dashboard",
        help="Generate interactive dashboard"
    ),
    dashboard_output: Optional[str] = typer.Option(
        None, "--dashboard-output",
        help="Dashboard output path (defaults to orphaned_resources_dashboard.html)"
    ),
    verbose: bool = typer.Option(
        False, "--verbose", "-v",
        help="Enable verbose logging"
    )
):
    """🔍 Scan Azure subscriptions for orphaned resources"""
    
    # Setup logging
    log_level = "DEBUG" if verbose else "INFO"
    logger = setup_logger("AzureOrphanDetector", log_level)
    
    # Create scan configuration
    config = ScanConfiguration(
        subscription_ids=subscription_ids or [],
        resource_groups=resource_groups or [],
        excluded_resource_groups=exclude_resource_groups or [],
        cost_threshold_critical=cost_threshold_critical,
        cost_threshold_high=cost_threshold_high,
        cost_threshold_medium=cost_threshold_medium,
        confidence_threshold=confidence_threshold,
        include_low_confidence=include_low_confidence,
        max_age_days=max_age_days,
        parallel_workers=parallel_workers
    )
    
    try:
        # Run the scan
        console.print("\n🚀 Starting Azure Orphan Detection Scan...\n")
        
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console
        ) as progress:
            
            scan_task = progress.add_task("Scanning Azure resources...", total=None)
            
            async def run_scan():
                detector = OrphanDetector(config)
                return await detector.scan_subscriptions(subscription_ids)
            
            # Run async scan
            scan_result = asyncio.run(run_scan())
        
        # Display results summary
        display_scan_summary(scan_result)
        
        # Generate outputs
        if output_file or output_format != "dashboard":
            export_results(scan_result, output_format, output_file)
        
        if generate_dashboard:
            dashboard_path = dashboard_output or "orphaned_resources_dashboard.html"
            generate_interactive_dashboard(scan_result, dashboard_path)
        
        # Exit with appropriate code
        if scan_result.errors:
            console.print("\n⚠️  Scan completed with errors. Check logs for details.", style="yellow")
            sys.exit(1)
        else:
            console.print(f"\n✅ Scan completed successfully! Found {len(scan_result.orphaned_resources)} orphaned resources.", style="green")
            sys.exit(0)
            
    except KeyboardInterrupt:
        console.print("\n❌ Scan cancelled by user.", style="red")
        sys.exit(130)
    except Exception as e:
        console.print(f"\n❌ Scan failed: {e}", style="red")
        if verbose:
            console.print_exception()
        sys.exit(1)


@app.command()
def list_subscriptions():
    """📋 List accessible Azure subscriptions"""
    
    try:
        from ..auth.manager import AuthenticationManager
        
        console.print("🔍 Discovering accessible Azure subscriptions...\n")
        
        async def get_subscriptions():
            auth_manager = AuthenticationManager()
            return await auth_manager.get_accessible_subscriptions()
        
        subscription_ids = asyncio.run(get_subscriptions())
        
        if subscription_ids:
            table = Table(title="Accessible Azure Subscriptions")
            table.add_column("Subscription ID", style="cyan")
            table.add_column("Status", style="green")
            
            for sub_id in subscription_ids:
                table.add_row(sub_id, "✅ Accessible")
            
            console.print(table)
            console.print(f"\n📊 Total: {len(subscription_ids)} accessible subscriptions")
        else:
            console.print("❌ No accessible subscriptions found.", style="red")
            
    except Exception as e:
        console.print(f"❌ Failed to list subscriptions: {e}", style="red")
        sys.exit(1)


@app.command()
def version():
    """📝 Show version information"""
    
    version_info = {
        "Azure Orphan Detector": "2.0.0",
        "Python": sys.version.split()[0],
        "Platform": sys.platform
    }
    
    panel_content = "\n".join([f"{k}: {v}" for k, v in version_info.items()])
    console.print(Panel(panel_content, title="Version Information", expand=False))


def display_scan_summary(scan_result):
    """Display scan results summary"""
    
    # Summary panel
    summary_content = f"""
🔍 Scan ID: {scan_result.scan_id}
⏱️  Duration: {scan_result.scan_duration_seconds:.2f} seconds
📊 Resources Found: {len(scan_result.orphaned_resources)}
💰 Monthly Savings: ${scan_result.total_monthly_savings:.2f}
📈 Annual Savings: ${scan_result.total_annual_savings:.2f}
"""
    
    if scan_result.errors:
        summary_content += f"⚠️  Errors: {len(scan_result.errors)}"
    
    console.print(Panel(summary_content, title="📋 Scan Summary", expand=False))
    
    if scan_result.orphaned_resources:
        # Resources table
        table = Table(title="🎯 Top Orphaned Resources (by cost)")
        table.add_column("Resource Name", style="cyan")
        table.add_column("Type", style="blue")
        table.add_column("Monthly Cost", style="red")
        table.add_column("Severity", style="yellow")
        table.add_column("Confidence", style="green")
        
        # Show top 10 resources by cost
        top_resources = sorted(
            scan_result.orphaned_resources,
            key=lambda x: x.cost_analysis.current_monthly_cost,
            reverse=True
        )[:10]
        
        for resource in top_resources:
            severity_color = {
                'critical': 'red',
                'high': 'orange3',
                'medium': 'yellow',
                'low': 'green',
                'info': 'blue'
            }.get(resource.severity.value, 'white')
            
            table.add_row(
                resource.resource_name,
                resource.resource_type.value.split('/')[-1],
                f"${resource.cost_analysis.current_monthly_cost:.2f}",
                f"[{severity_color}]{resource.severity.value.upper()}[/{severity_color}]",
                f"{resource.confidence_score:.1%}"
            )
        
        console.print(table)
        
        if len(scan_result.orphaned_resources) > 10:
            console.print(f"\n... and {len(scan_result.orphaned_resources) - 10} more resources")
    
    # Show errors if any
    if scan_result.errors:
        console.print("\n⚠️  Errors encountered during scan:", style="yellow")
        for error in scan_result.errors[:5]:  # Show first 5 errors
            console.print(f"  • {error}", style="red")
        if len(scan_result.errors) > 5:
            console.print(f"  ... and {len(scan_result.errors) - 5} more errors")


def export_results(scan_result, output_format: str, output_file: Optional[str]):
    """Export scan results to specified format"""
    
    if not output_file:
        output_file = f"orphaned_resources.{output_format}"
    
    try:
        if output_format.lower() == "json":
            export_to_json(scan_result, output_file)
        elif output_format.lower() == "csv":
            export_to_csv(scan_result, output_file)
        elif output_format.lower() == "table":
            export_to_table(scan_result)
        else:
            console.print(f"❌ Unsupported output format: {output_format}", style="red")
            return
        
        if output_format.lower() != "table":
            console.print(f"📁 Results exported to: {output_file}", style="green")
            
    except Exception as e:
        console.print(f"❌ Failed to export results: {e}", style="red")


def export_to_json(scan_result, output_file: str):
    """Export results to JSON"""
    import json
    from datetime import datetime
    
    def json_serializer(obj):
        if isinstance(obj, datetime):
            return obj.isoformat()
        elif hasattr(obj, '__dict__'):
            return obj.__dict__
        elif hasattr(obj, 'value'):
            return obj.value
        return str(obj)
    
    with open(output_file, 'w') as f:
        json.dump(scan_result, f, default=json_serializer, indent=2)


def export_to_csv(scan_result, output_file: str):
    """Export results to CSV"""
    import csv
    
    with open(output_file, 'w', newline='') as f:
        writer = csv.writer(f)
        
        # Headers
        writer.writerow([
            'Resource Name', 'Resource Type', 'Subscription', 'Resource Group',
            'Location', 'Monthly Cost', 'Annual Cost', 'Severity', 'Confidence',
            'Orphan Reason', 'Cleanup Priority', 'Created Date'
        ])
        
        # Data
        for resource in scan_result.orphaned_resources:
            writer.writerow([
                resource.resource_name,
                resource.resource_type.value,
                resource.subscription_id,
                resource.resource_group,
                resource.location,
                f"{resource.cost_analysis.current_monthly_cost:.2f}",
                f"{resource.cost_analysis.projected_annual_cost:.2f}",
                resource.severity.value,
                f"{resource.confidence_score:.2f}",
                resource.orphanage_reason.value,
                resource.cleanup_priority,
                resource.created_date.isoformat() if resource.created_date else ''
            ])


def export_to_table(scan_result):
    """Display results as a table"""
    
    if not scan_result.orphaned_resources:
        console.print("No orphaned resources found.", style="yellow")
        return
    
    table = Table(title="All Orphaned Resources")
    table.add_column("Resource Name", style="cyan")
    table.add_column("Type", style="blue")
    table.add_column("Subscription", style="magenta")
    table.add_column("Monthly Cost", style="red")
    table.add_column("Severity", style="yellow")
    
    for resource in scan_result.orphaned_resources:
        severity_color = {
            'critical': 'red',
            'high': 'orange3',
            'medium': 'yellow',
            'low': 'green',
            'info': 'blue'
        }.get(resource.severity.value, 'white')
        
        table.add_row(
            resource.resource_name,
            resource.resource_type.value.split('/')[-1],
            resource.subscription_id[:8] + "...",
            f"${resource.cost_analysis.current_monthly_cost:.2f}",
            f"[{severity_color}]{resource.severity.value.upper()}[/{severity_color}]"
        )
    
    console.print(table)


def generate_interactive_dashboard(scan_result, dashboard_path: str):
    """Generate interactive HTML dashboard"""
    
    try:
        console.print(f"🎨 Generating interactive dashboard...")
        
        dashboard_generator = DashboardGenerator()
        output_path = dashboard_generator.generate_dashboard(
            scan_result.orphaned_resources,
            dashboard_path
        )
        
        console.print(f"📊 Interactive dashboard generated: {output_path}", style="green")
        console.print(f"🌐 Open in browser: file://{Path(output_path).absolute()}", style="blue")
        
    except Exception as e:
        console.print(f"❌ Failed to generate dashboard: {e}", style="red")


def main():
    """Main entry point"""
    try:
        app()
    except KeyboardInterrupt:
        console.print("\n❌ Interrupted by user.", style="red")
        sys.exit(130)
    except Exception as e:
        console.print(f"\n❌ Unexpected error: {e}", style="red")
        sys.exit(1)


if __name__ == "__main__":
    main()
