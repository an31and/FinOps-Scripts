"""
Dashboard Scripts - Interactions Module

Handles drill-down functionality and user interactions.
"""

from config_manager import Config


class DashboardInteractionsGenerator:
    """Generates interaction-related JavaScript code"""
    
    def __init__(self, config: Config):
        self.config = config
    
    def generate_drill_down_functions(self) -> str:
        """Generate drill-down functionality JavaScript code"""
        return """
        // Drill-down functions
        function showSubscriptionDrillDown() {
            const container = document.getElementById('drillDownContainer');
            const title = document.getElementById('drillDownTitle');
            const tableHeader = document.getElementById('tableHeader');
            const tableBody = document.getElementById('tableBody');
            
            title.textContent = 'Subscription Overview';
            
            tableHeader.innerHTML = `
                <tr>
                    <th>Subscription Name</th>
                    <th>Compliance %</th>
                    <th>Resources</th>
                    <th>Actions</th>
                </tr>
            `;
            
            tableBody.innerHTML = '';
            subscriptionData.labels.forEach((name, index) => {
                const row = document.createElement('tr');
                row.innerHTML = `
                    <td>${name}</td>
                    <td>
                        <span class="compliance-badge ${getComplianceClass(subscriptionData.compliance_data[index])}">${subscriptionData.compliance_data[index]}%</span>
                    </td>
                    <td>${subscriptionData.resource_counts[index]}</td>
                    <td>
                        <button class="export-btn" style="padding: 0.25rem 0.75rem; font-size: 0.9rem;" 
                                onclick="showResourceDrillDown('${name}', '${subscriptionData.ids[index]}')">
                            View Resources
                        </button>
                    </td>
                `;
                tableBody.appendChild(row);
            });
            
            container.style.display = 'block';
            container.scrollIntoView({ behavior: 'smooth' });
        }

        function showResourceDrillDown(subscriptionName, subscriptionId) {
            const container = document.getElementById('drillDownContainer');
            const title = document.getElementById('drillDownTitle');
            const tableHeader = document.getElementById('tableHeader');
            const tableBody = document.getElementById('tableBody');
            
            title.textContent = `Resources in ${subscriptionName}`;
            
            let headerHtml = `
                <tr>
                    <th>Resource Name</th>
                    <th>Resource Type</th>
                    <th>Location</th>
            `;
            
            mandatoryTags.forEach(tag => {
                headerHtml += `<th>${tag}</th>`;
            });
            
            headerHtml += `
                    <th>All Tags</th>
                </tr>
            `;
            
            tableHeader.innerHTML = headerHtml;
            
            const resources = resourcesBySubscription[subscriptionId] || [];
            tableBody.innerHTML = '';
            
            resources.forEach(resource => {
                const row = document.createElement('tr');
                let rowHtml = `
                    <td>${resource.resource_name}</td>
                    <td>${resource.resource_type}</td>
                    <td>${resource.location || 'N/A'}</td>
                `;
                
                mandatoryTags.forEach(tag => {
                    const status = resource.tag_compliance[tag] || '❌';
                    rowHtml += `<td style="text-align: center;">${status}</td>`;
                });
                
                const tagsList = Object.entries(resource.tags || {})
                    .map(([k, v]) => `<span class="tag-badge">${k}: ${v}</span>`)
                    .join(' ');
                rowHtml += `<td>${tagsList || 'No tags'}</td>`;
                
                row.innerHTML = rowHtml;
                tableBody.appendChild(row);
            });
            
            container.style.display = 'block';
            container.scrollIntoView({ behavior: 'smooth' });
        }

        function closeDrillDown() {
            document.getElementById('drillDownContainer').style.display = 'none';
        }

        function filterTable() {
            const searchTerm = document.getElementById('searchBox').value.toLowerCase();
            const rows = document.getElementById('tableBody').getElementsByTagName('tr');
            
            for (let row of rows) {
                const text = row.textContent.toLowerCase();
                row.style.display = text.includes(searchTerm) ? '' : 'none';
            }
        }
        """
