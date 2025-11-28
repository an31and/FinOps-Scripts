"""
Dashboard HTML - Styles Module

Handles CSS generation for the dashboard.
"""


class DashboardStylesGenerator:
    """Generates CSS styles for the interactive dashboard"""
    
    def generate_css_styles(self) -> str:
        """Generate complete CSS styles for the dashboard"""
        return """
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }
        
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', 'Roboto', sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            color: #333;
        }
        
        .dashboard-header {
            background: rgba(255, 255, 255, 0.95);
            backdrop-filter: blur(10px);
            padding: 2rem;
            margin: 1rem;
            border-radius: 20px;
            box-shadow: 0 8px 32px rgba(0, 0, 0, 0.1);
            text-align: center;
            border: 1px solid rgba(255, 255, 255, 0.2);
        }
        
        .dashboard-header h1 {
            color: #2c3e50;
            font-size: 2.5rem;
            margin-bottom: 0.5rem;
            font-weight: 700;
        }
        
        .dashboard-header p {
            color: #7f8c8d;
            font-size: 1.1rem;
        }
        
        .metrics-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
            gap: 1.5rem;
            margin: 1rem;
            margin-bottom: 2rem;
        }
        
        .metric-card {
            background: rgba(255, 255, 255, 0.95);
            backdrop-filter: blur(10px);
            padding: 1.5rem;
            border-radius: 15px;
            box-shadow: 0 8px 32px rgba(0, 0, 0, 0.1);
            border: 1px solid rgba(255, 255, 255, 0.2);
            transition: transform 0.3s ease, box-shadow 0.3s ease;
            cursor: pointer;
        }
        
        .metric-card:hover {
            transform: translateY(-5px);
            box-shadow: 0 12px 40px rgba(0, 0, 0, 0.15);
        }
        
        .metric-value {
            font-size: 2.5rem;
            font-weight: 700;
            margin-bottom: 0.5rem;
        }
        
        .metric-label {
            color: #7f8c8d;
            font-size: 0.9rem;
            text-transform: uppercase;
            letter-spacing: 0.5px;
        }
        
        .charts-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(500px, 1fr));
            gap: 2rem;
            margin: 1rem;
        }
        
        .chart-container {
            background: rgba(255, 255, 255, 0.95);
            backdrop-filter: blur(10px);
            padding: 2rem;
            border-radius: 20px;
            box-shadow: 0 8px 32px rgba(0, 0, 0, 0.1);
            border: 1px solid rgba(255, 255, 255, 0.2);
            transition: transform 0.3s ease;
        }
        
        .chart-container:hover {
            transform: translateY(-2px);
        }
        
        .chart-title {
            font-size: 1.3rem;
            font-weight: 600;
            margin-bottom: 1.5rem;
            color: #2c3e50;
            text-align: center;
        }
        
        .chart-canvas {
            position: relative;
            height: 400px;
        }
        
        .full-width {
            grid-column: 1 / -1;
        }
        
        .drill-down-container {
            background: rgba(255, 255, 255, 0.95);
            backdrop-filter: blur(10px);
            padding: 2rem;
            margin: 1rem;
            border-radius: 20px;
            box-shadow: 0 8px 32px rgba(0, 0, 0, 0.1);
            border: 1px solid rgba(255, 255, 255, 0.2);
            display: none;
        }
        
        .drill-down-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 1.5rem;
        }
        
        .drill-down-title {
            font-size: 1.5rem;
            font-weight: 600;
            color: #2c3e50;
        }
        
        .close-btn {
            background: #dc3545;
            color: white;
            border: none;
            padding: 0.5rem 1rem;
            border-radius: 8px;
            cursor: pointer;
            font-size: 1rem;
            transition: background 0.3s ease;
        }
        
        .close-btn:hover {
            background: #c82333;
        }
        
        .search-box {
            width: 100%;
            padding: 0.75rem;
            margin-bottom: 1rem;
            border: 2px solid #e0e0e0;
            border-radius: 8px;
            font-size: 1rem;
            transition: border-color 0.3s ease;
        }
        
        .search-box:focus {
            outline: none;
            border-color: #667eea;
        }
        
        .data-table {
            width: 100%;
            border-collapse: collapse;
            margin-top: 1rem;
        }
        
        .data-table th {
            background: #5D87A1;
            color: white;
            padding: 1rem;
            text-align: left;
            font-weight: 600;
            position: sticky;
            top: 0;
            z-index: 10;
        }
        
        .data-table td {
            padding: 0.75rem;
            border-bottom: 1px solid #e0e0e0;
        }
        
        .data-table tr:nth-child(even) {
            background: rgba(0, 0, 0, 0.02);
        }
        
        .data-table tr:hover {
            background: rgba(102, 126, 234, 0.1);
        }
        
        .table-wrapper {
            max-height: 600px;
            overflow-y: auto;
            border: 1px solid #e0e0e0;
            border-radius: 8px;
        }
        
        .export-btn {
            background: #28a745;
            color: white;
            border: none;
            padding: 0.5rem 1rem;
            border-radius: 8px;
            cursor: pointer;
            font-size: 1rem;
            transition: background 0.3s ease;
            margin-left: 1rem;
        }
        
        .export-btn:hover {
            background: #218838;
        }
        
        .tag-badge {
            display: inline-block;
            padding: 0.25rem 0.5rem;
            margin: 0.125rem;
            border-radius: 4px;
            font-size: 0.85rem;
            background: #e0e0e0;
        }
        
        .compliance-badge {
            padding: 0.25rem 0.5rem;
            border-radius: 4px;
            font-weight: 600;
            text-align: center;
        }
        
        .compliance-compliant {
            background: #D5E8D4;
            color: #2E7D32;
        }
        
        .compliance-partial {
            background: #FFF3E0;
            color: #F57C00;
        }
        
        .compliance-non-compliant {
            background: #FFEBEE;
            color: #C62828;
        }
        
        .footer {
            text-align: center;
            padding: 2rem;
            color: rgba(255, 255, 255, 0.8);
            font-size: 0.9rem;
        }
        
        .excellent { color: #28a745; }
        .good { color: #20c997; }
        .warning { color: #ffc107; }
        .danger { color: #dc3545; }
        
        @media (max-width: 768px) {
            .charts-grid {
                grid-template-columns: 1fr;
            }
            
            .dashboard-header h1 {
                font-size: 2rem;
            }
            
            .metric-value {
                font-size: 2rem;
            }
        }
        """