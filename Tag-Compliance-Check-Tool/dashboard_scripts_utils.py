"""
Dashboard Scripts - Utils Module

Handles utility functions for the dashboard.
"""


class DashboardUtilsGenerator:
    """Generates utility JavaScript functions"""
    
    def generate_utility_functions(self) -> str:
        """Generate utility JavaScript functions"""
        return """
        function exportTableData() {
            const table = document.getElementById('dataTable');
            const rows = table.querySelectorAll('tr');
            let csv = [];
            
            rows.forEach(row => {
                const cols = row.querySelectorAll('td, th');
                const rowData = Array.from(cols).map(col => {
                    let text = col.textContent.trim();
                    if (text.includes(',') || text.includes('"')) {
                        text = '"' + text.replace(/"/g, '""') + '"';
                    }
                    return text;
                });
                csv.push(rowData.join(','));
            });
            
            const csvContent = csv.join('\\n');
            const blob = new Blob([csvContent], { type: 'text/csv' });
            const url = window.URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = 'azure_tagging_export_' + new Date().toISOString().slice(0, 10) + '.csv';
            document.body.appendChild(a);
            a.click();
            document.body.removeChild(a);
            window.URL.revokeObjectURL(url);
        }

        function getComplianceClass(percentage) {
            if (percentage >= 90) return 'compliance-compliant';
            if (percentage >= 70) return 'compliance-partial';
            return 'compliance-non-compliant';
        }

        function formatNumber(num) {
            return num.toLocaleString();
        }

        function formatPercentage(num) {
            return num.toFixed(1) + '%';
        }

        function escapeHtml(text) {
            const map = {
                '&': '&amp;',
                '<': '&lt;',
                '>': '&gt;',
                '"': '&quot;',
                "'": '&#039;'
            };
            return text.replace(/[&<>"']/g, function(m) { return map[m]; });
        }

        function debounce(func, wait) {
            let timeout;
            return function executedFunction(...args) {
                const later = () => {
                    clearTimeout(timeout);
                    func(...args);
                };
                clearTimeout(timeout);
                timeout = setTimeout(later, wait);
            };
        }

        // Enhanced table filtering with debounce
        const debouncedFilter = debounce(filterTable, 300);
        
        // Add event listener for search box with debounced filtering
        document.addEventListener('DOMContentLoaded', function() {
            const searchBox = document.getElementById('searchBox');
            if (searchBox) {
                searchBox.addEventListener('input', debouncedFilter);
            }
        });
        """
