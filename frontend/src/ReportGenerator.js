/**
 * ReportGenerator.js
 *
 * Generates HTML reports from graph data
 * Light theme, printable, English language
 */

/**
 * Generate and open HTML report in new tab
 *
 * @param {Object} reportData - Report data
 * @param {Object} reportData.mainNode - Main node information
 * @param {Array} reportData.nodes - All visible nodes
 * @param {Array} reportData.edges - All visible edges
 * @param {string} reportData.graphImage - Base64 PNG image
 */
export function generateReport(reportData) {
  const { mainNode, nodes, edges, graphImage } = reportData;

  const html = buildHTMLReport(mainNode, nodes, edges, graphImage);

  // Open in new window
  const reportWindow = window.open("", "_blank");
  reportWindow.document.write(html);
  reportWindow.document.close();

  // Optional: Print dialog after short delay
  // reportWindow.onload = () => {
  //   setTimeout(() => reportWindow.print(), 500);
  // };
}

/**
 * Build complete HTML report
 */
function buildHTMLReport(mainNode, nodes, edges, graphImage) {
  const metadata = {
    generatedDate: new Date().toLocaleString("en-US", {
      year: "numeric",
      month: "long",
      day: "numeric",
      hour: "2-digit",
      minute: "2-digit",
    }),
    nodeCount: nodes.length,
    edgeCount: edges.length,
    mainEntityName: mainNode.name || "Unknown",
    mainEntityType: mainNode.type || "Unknown",
  };

  return `<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Threat Intelligence Report - ${escapeHtml(metadata.mainEntityName)}</title>
  <style>
    ${getReportStyles()}
  </style>
</head>
<body>
  <div class="report-container">
    ${buildReportHeader(metadata)}
    ${buildMetadataSection(metadata)}
    ${buildMainNodeSection(mainNode)}
    ${buildGraphVisualizationSection(graphImage)}
    ${buildConnectionsSection(nodes, edges, mainNode)}
    ${buildFooter()}
  </div>
  
  <script>
    // Add print button functionality
    function printReport() {
      window.print();
    }
  </script>
</body>
</html>`;
}

/**
 * Report CSS Styles - Light theme, print-friendly
 */
function getReportStyles() {
  return `
    /* Base Styles */
    * {
      margin: 0;
      padding: 0;
      box-sizing: border-box;
    }
    
    body {
      font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
      line-height: 1.6;
      color: #333;
      background: #f5f5f5;
    }
    
    .report-container {
      max-width: 1200px;
      margin: 2rem auto;
      background: white;
      box-shadow: 0 0 20px rgba(0,0,0,0.1);
    }
    
    /* Header */
    .report-header {
      background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
      color: white;
      padding: 3rem 2rem;
      text-align: center;
    }
    
    .report-header h1 {
      font-size: 2.5rem;
      margin-bottom: 0.5rem;
      font-weight: 300;
    }
    
    .report-header .entity-name {
      font-size: 3rem;
      font-weight: 700;
      margin: 1rem 0;
      text-shadow: 2px 2px 4px rgba(0,0,0,0.2);
    }
    
    .report-header .entity-type {
      display: inline-block;
      background: rgba(255,255,255,0.2);
      padding: 0.5rem 1.5rem;
      border-radius: 25px;
      font-size: 1.1rem;
      font-weight: 500;
      backdrop-filter: blur(10px);
    }
    
    /* Print Button */
    .print-button {
      position: fixed;
      top: 20px;
      right: 20px;
      background: #667eea;
      color: white;
      border: none;
      padding: 1rem 2rem;
      border-radius: 8px;
      cursor: pointer;
      font-size: 1rem;
      font-weight: 600;
      box-shadow: 0 4px 12px rgba(102, 126, 234, 0.3);
      transition: all 0.3s ease;
      z-index: 1000;
    }
    
    .print-button:hover {
      background: #5568d3;
      transform: translateY(-2px);
      box-shadow: 0 6px 16px rgba(102, 126, 234, 0.4);
    }
    
    /* Section Styles */
    section {
      padding: 2rem;
      border-bottom: 1px solid #e0e0e0;
    }
    
    section:last-of-type {
      border-bottom: none;
    }
    
    section h2 {
      color: #667eea;
      font-size: 1.8rem;
      margin-bottom: 1.5rem;
      padding-bottom: 0.5rem;
      border-bottom: 3px solid #667eea;
    }
    
    section h3 {
      color: #555;
      font-size: 1.3rem;
      margin-top: 1.5rem;
      margin-bottom: 1rem;
    }
    
    /* Metadata Grid */
    .metadata-grid {
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
      gap: 1.5rem;
      margin-top: 1rem;
    }
    
    .metadata-item {
      background: #f8f9fa;
      padding: 1.5rem;
      border-radius: 8px;
      border-left: 4px solid #667eea;
    }
    
    .metadata-item .label {
      font-size: 0.85rem;
      color: #666;
      text-transform: uppercase;
      letter-spacing: 0.5px;
      margin-bottom: 0.5rem;
      font-weight: 600;
    }
    
    .metadata-item .value {
      font-size: 1.5rem;
      color: #333;
      font-weight: 700;
    }
    
    /* Properties Table */
    .properties-table {
      width: 100%;
      border-collapse: collapse;
      margin-top: 1rem;
      background: white;
      box-shadow: 0 2px 8px rgba(0,0,0,0.05);
    }
    
    .properties-table th {
      background: #667eea;
      color: white;
      padding: 1rem;
      text-align: left;
      font-weight: 600;
      text-transform: uppercase;
      font-size: 0.9rem;
      letter-spacing: 0.5px;
    }
    
    .properties-table td {
      padding: 1rem;
      border-bottom: 1px solid #e0e0e0;
    }
    
    .properties-table tr:last-child td {
      border-bottom: none;
    }
    
    .properties-table tr:hover {
      background: #f8f9fa;
    }
    
    .properties-table .property-key {
      font-weight: 600;
      color: #667eea;
      width: 200px;
    }
    
    .properties-table .property-value {
      color: #333;
      word-break: break-word;
    }
    
    /* Graph Visualization */
    .graph-visualization {
      text-align: center;
      background: #f8f9fa;
      padding: 2rem;
      border-radius: 8px;
      margin-top: 1rem;
    }
    
    .graph-visualization img {
      max-width: 100%;
      height: auto;
      border-radius: 8px;
      box-shadow: 0 4px 12px rgba(0,0,0,0.1);
    }
    
    /* Node Cards */
    .node-cards {
      display: grid;
      grid-template-columns: repeat(auto-fill, minmax(350px, 1fr));
      gap: 1.5rem;
      margin-top: 1.5rem;
    }
    
    .node-card {
      background: white;
      border: 2px solid #e0e0e0;
      border-radius: 8px;
      padding: 1.5rem;
      transition: all 0.3s ease;
    }
    
    .node-card:hover {
      border-color: #667eea;
      box-shadow: 0 4px 12px rgba(102, 126, 234, 0.1);
      transform: translateY(-2px);
    }
    
    .node-card.main-node {
      border-color: #667eea;
      background: linear-gradient(135deg, rgba(102, 126, 234, 0.05) 0%, rgba(118, 75, 162, 0.05) 100%);
    }
    
    .node-card-header {
      display: flex;
      justify-content: space-between;
      align-items: center;
      margin-bottom: 1rem;
      padding-bottom: 1rem;
      border-bottom: 2px solid #e0e0e0;
    }
    
    .node-card-title {
      font-size: 1.2rem;
      font-weight: 700;
      color: #333;
    }
    
    .node-type-badge {
      display: inline-block;
      padding: 0.4rem 1rem;
      border-radius: 20px;
      font-size: 0.85rem;
      font-weight: 600;
      text-transform: uppercase;
      letter-spacing: 0.5px;
    }
    
    /* Node type colors */
    .type-ThreatActor { background: #ef4444; color: white; }
    .type-Malware { background: #dc2626; color: white; }
    .type-Tool { background: #10b981; color: white; }
    .type-Vulnerability { background: #f97316; color: white; }
    .type-Campaign { background: #f59e0b; color: white; }
    .type-Identity { background: #8b5cf6; color: white; }
    .type-Indicator { background: #14b8a6; color: white; }
    .type-Observable { background: #06b6d4; color: white; }
    .type-Organization { background: #3b82f6; color: white; }
    .type-Report { background: #6366f1; color: white; }
    .type-default { background: #6b7280; color: white; }
    
    .node-card-body {
      font-size: 0.95rem;
    }
    
    .node-property {
      margin-bottom: 0.75rem;
    }
    
    .node-property-label {
      font-weight: 600;
      color: #667eea;
      margin-right: 0.5rem;
    }
    
    .node-property-value {
      color: #555;
    }
    
    /* Relationships Section */
    .relationships-list {
      margin-top: 1.5rem;
    }
    
    .relationship-item {
      background: #f8f9fa;
      padding: 1.5rem;
      border-radius: 8px;
      margin-bottom: 1rem;
      border-left: 4px solid #667eea;
    }
    
    .relationship-header {
      font-size: 1.1rem;
      font-weight: 700;
      color: #333;
      margin-bottom: 0.75rem;
    }
    
    .relationship-type {
      display: inline-block;
      background: #667eea;
      color: white;
      padding: 0.3rem 0.8rem;
      border-radius: 4px;
      font-size: 0.85rem;
      font-weight: 600;
      margin-left: 0.5rem;
    }
    
    .relationship-nodes {
      color: #666;
      margin-top: 0.5rem;
    }
    
    /* Footer */
    .report-footer {
      background: #2d3748;
      color: white;
      padding: 2rem;
      text-align: center;
    }
    
    .report-footer p {
      margin: 0.5rem 0;
      opacity: 0.8;
    }
    
    /* Print Styles */
    @media print {
      body {
        background: white;
      }
      
      .report-container {
        box-shadow: none;
        margin: 0;
      }
      
      .print-button {
        display: none;
      }
      
      .node-card {
        break-inside: avoid;
        page-break-inside: avoid;
      }
      
      section {
        page-break-inside: avoid;
      }
      
      .report-header {
        background: #667eea !important;
        -webkit-print-color-adjust: exact;
        print-color-adjust: exact;
      }
    }
    
    /* Utility Classes */
    .text-center {
      text-align: center;
    }
    
    .mt-2 {
      margin-top: 2rem;
    }
    
    .mb-2 {
      margin-bottom: 2rem;
    }
  `;
}

/**
 * Build report header
 */
function buildReportHeader(metadata) {
  return `
    <button class="print-button" onclick="printReport()">
      🖨️ Print / Save as PDF
    </button>
    
    <header class="report-header">
      <h1>Threat Intelligence Report</h1>
      <div class="entity-name">${escapeHtml(metadata.mainEntityName)}</div>
      <span class="entity-type">${escapeHtml(metadata.mainEntityType)}</span>
    </header>
  `;
}

/**
 * Build metadata section
 */
function buildMetadataSection(metadata) {
  return `
    <section class="metadata-section">
      <h2>Report Metadata</h2>
      <div class="metadata-grid">
        <div class="metadata-item">
          <div class="label">Generated</div>
          <div class="value">${escapeHtml(metadata.generatedDate)}</div>
        </div>
        <div class="metadata-item">
          <div class="label">Main Entity</div>
          <div class="value">${escapeHtml(metadata.mainEntityName)}</div>
        </div>
        <div class="metadata-item">
          <div class="label">Total Nodes</div>
          <div class="value">${metadata.nodeCount}</div>
        </div>
        <div class="metadata-item">
          <div class="label">Total Relationships</div>
          <div class="value">${metadata.edgeCount}</div>
        </div>
      </div>
    </section>
  `;
}

/**
 * Build main node section
 */
function buildMainNodeSection(mainNode) {
  const properties = mainNode.properties || mainNode;
  const propertyEntries = Object.entries(properties).filter(
    ([key]) => key !== "name" && key !== "label",
  );

  return `
    <section class="main-node-section">
      <h2>Main Entity Information</h2>
      <p><strong>Name:</strong> ${escapeHtml(mainNode.name || "Unknown")}</p>
      <p><strong>Type:</strong> ${escapeHtml(mainNode.type || "Unknown")}</p>
      
      ${
        propertyEntries.length > 0
          ? `
        <h3>Properties</h3>
        <table class="properties-table">
          <thead>
            <tr>
              <th>Property</th>
              <th>Value</th>
            </tr>
          </thead>
          <tbody>
            ${propertyEntries
              .map(
                ([key, value]) => `
              <tr>
                <td class="property-key">${escapeHtml(key)}</td>
                <td class="property-value">${escapeHtml(String(value))}</td>
              </tr>
            `,
              )
              .join("")}
          </tbody>
        </table>
      `
          : "<p><em>No additional properties</em></p>"
      }
    </section>
  `;
}

/**
 * Build graph visualization section
 */
function buildGraphVisualizationSection(graphImage) {
  return `
    <section class="graph-section">
      <h2>Graph Visualization</h2>
      <p>Visual representation of the threat intelligence relationships</p>
      <div class="graph-visualization">
        <img src="${graphImage}" alt="Threat Intelligence Graph" />
      </div>
    </section>
  `;
}

/**
 * Build connections section (all nodes and edges)
 */
function buildConnectionsSection(nodes, edges, mainNode) {
  // Separate main node from others
  const mainNodeId = mainNode.name || mainNode.id;
  const otherNodes = nodes.filter((n) => n.data.id !== mainNodeId);

  return `
    <section class="connections-section">
      <h2>Connected Entities (${otherNodes.length})</h2>
      <p>All entities and their relationships visible in the graph</p>
      
      <div class="node-cards">
        ${otherNodes.map((node) => buildNodeCard(node, edges)).join("")}
      </div>
      
      <h2 class="mt-2">Relationships Overview (${edges.length})</h2>
      <div class="relationships-list">
        ${edges.map((edge) => buildRelationshipItem(edge, nodes)).join("")}
      </div>
    </section>
  `;
}

/**
 * Build individual node card
 */
function buildNodeCard(node, edges) {
  const nodeData = node.data;
  const properties = nodeData.properties || {};
  const propertyEntries = Object.entries(properties)
    .filter(([key]) => key !== "name" && key !== "label")
    .slice(0, 5); // Limit to 5 properties for cards

  // Count connections
  const connectionCount = edges.filter(
    (e) => e.data.source === nodeData.id || e.data.target === nodeData.id,
  ).length;

  return `
    <div class="node-card ${nodeData.isMainNode ? "main-node" : ""}">
      <div class="node-card-header">
        <div class="node-card-title">${escapeHtml(nodeData.label)}</div>
        <span class="node-type-badge type-${nodeData.type}">${escapeHtml(nodeData.type)}</span>
      </div>
      <div class="node-card-body">
        <div class="node-property">
          <span class="node-property-label">Connections:</span>
          <span class="node-property-value">${connectionCount}</span>
        </div>
        ${propertyEntries
          .map(
            ([key, value]) => `
          <div class="node-property">
            <span class="node-property-label">${escapeHtml(key)}:</span>
            <span class="node-property-value">${escapeHtml(String(value).substring(0, 100))}${String(value).length > 100 ? "..." : ""}</span>
          </div>
        `,
          )
          .join("")}
        ${propertyEntries.length === 0 ? "<p><em>No additional properties</em></p>" : ""}
      </div>
    </div>
  `;
}

/**
 * Build relationship item
 */
function buildRelationshipItem(edge, nodes) {
  const edgeData = edge.data;
  const sourceNode = nodes.find((n) => n.data.id === edgeData.source);
  const targetNode = nodes.find((n) => n.data.id === edgeData.target);

  const sourceName = sourceNode ? sourceNode.data.label : edgeData.source;
  const targetName = targetNode ? targetNode.data.label : edgeData.target;

  return `
    <div class="relationship-item">
      <div class="relationship-header">
        ${escapeHtml(sourceName)} 
        <span class="relationship-type">${escapeHtml(edgeData.relationshipType || edgeData.label)}</span> 
        ${escapeHtml(targetName)}
      </div>
      <div class="relationship-nodes">
        From: <strong>${escapeHtml(sourceName)}</strong> → 
        To: <strong>${escapeHtml(targetName)}</strong>
      </div>
    </div>
  `;
}

/**
 * Build footer
 */
function buildFooter() {
  return `
    <footer class="report-footer">
      <p><strong>Threat Intelligence Platform</strong></p>
      <p>Generated automatically from graph data</p>
      <p>© 2025 - For internal use only</p>
    </footer>
  `;
}

/**
 * Escape HTML to prevent XSS
 */
function escapeHtml(text) {
  const map = {
    "&": "&amp;",
    "<": "&lt;",
    ">": "&gt;",
    '"': "&quot;",
    "'": "&#039;",
  };
  return String(text).replace(/[&<>"']/g, (m) => map[m]);
}
