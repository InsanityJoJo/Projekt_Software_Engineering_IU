<!-- GraphView.svelte -->
<script>
  import { onMount, onDestroy } from 'svelte';
  import cytoscape from 'cytoscape';
  import { getNodeByName } from './api.js';
  import ContextMenu from './ContextMenu.svelte';
  import { generateReport } from './ReportGenerator.js';

  // ============================================
  // DEBUG CONFIGURATION
  // ============================================
  const DEBUG = true;

  function debugLog(...args) {
    if (DEBUG) {
      console.log(...args);
    }
  }

  /**
  * @type {{ n: any, connections: any[], edges?: any[], nodes?: any[] } | null}
  */
  export let node = null;

  let cy;
  let containerElement;
  
  // ============================================
  // STATE FOR INTERACTIVE FEATURES
  // ============================================
  
  // Context menu state
  let contextMenuVisible = false;
  let contextMenuPosition = null;
  let contextMenuTargetNode = null;
  
  // Selected node for info display
  let selectedNodeData = null;
  
  // Main node reference (protected from deletion)
  let mainNodeId = null;
  
  // Loading state for extend operation
  let isExtending = false;

  // ============================================
  // COLOR HELPERS
  // ============================================
  
  /**
   * Get computed CSS variable value from :root
   */
  function getCSSVariable(varName) {
    return getComputedStyle(document.documentElement).getPropertyValue(varName).trim();
  }

  /**
   * Get color for a node type from CSS variables
   */
  function getNodeColor(type) {
    const color = getCSSVariable(`--node-${type}`);
    return color || getCSSVariable('--node-default');
  }
  
  /**
   * Get color for an edge/relationship type from CSS variables
   */
  function getEdgeColor(relType) {
    const color = getCSSVariable(`--edge-${relType}`);
    return color || getCSSVariable('--edge-default');
  }

  // ============================================
  // HELPER FUNCTIONS
  // ============================================

  /**
   * Extract relationship type as string from various formats
   */
  function getRelationshipString(rel) {
    if (typeof rel === 'string') return rel;
    if (rel && rel.type) return rel.type;
    if (rel && typeof rel === 'object') return String(rel);
    return 'CONNECTED';
  }

  /**
   * Create style data object for a node
   */
  function createNodeStyleData(nodeData, isMainNode = false) {
    return {
      color: getNodeColor(nodeData.label),
      size: isMainNode ? 80 : 60,
      fontSize: isMainNode ? 14 : 12,
      fontWeight: isMainNode ? 'bold' : 'normal',
      borderWidth: isMainNode ? 3 : 0,
      borderColor: '#f8fafc'
    };
  }

  /**
   * Create style data object for an edge
   */
  function createEdgeStyleData(relType) {
    return {
      color: getEdgeColor(relType),
      width: 2,
      arrowShape: 'triangle'
    };
  }

  /**
   * Create a Cytoscape node object
   */
  function createCytoscapeNode(id, label, properties, type, isMainNode = false) {
    const styleData = createNodeStyleData(properties, isMainNode);
    
    return {
      data: {
        id,
        label,
        properties,
        type,
        isMainNode,
        ...styleData
      }
    };
  }

  /**
   * Create a Cytoscape edge object
   */
  function createCytoscapeEdge(id, source, target, relType, properties = {}) {
    const styleData = createEdgeStyleData(relType);
    
    return {
      data: {
        id,
        source,
        target,
        label: relType,
        relationshipType: relType,
        properties,
        ...styleData
      }
    };
  }

  // ============================================
  // DATA CONVERSION
  // ============================================

  /**
   * Convert backend node data to Cytoscape format with pre-computed colors
   */
  function nodeDataToCytoscape(nodeData) {
    if (!nodeData || !nodeData.n) {
      debugLog('No node data provided to GraphView');
      return { nodes: [], edges: [] };
    }

    debugLog('=== nodeDataToCytoscape called ===');
    debugLog('Input nodeData:', nodeData);

    // Create the main node with PRE-COMPUTED styling data
    const mainNode = createCytoscapeNode(
      nodeData.n.name || 'unknown',
      nodeData.n.name || 'Unknown',
      nodeData.n,
      nodeData.n.label || 'Unknown',
      true
    );
    
    // Store main node ID for protection
    mainNodeId = mainNode.data.id;
    
    debugLog('Main node created:', mainNode.data.id, 'Color:', mainNode.data.color);
    
    const nodes = [mainNode];
    const edges = [];
    const processedNodes = new Set([mainNode.data.id]);

    // Process the nodes and edges arrays from backend
    if (!nodeData.edges || !nodeData.nodes) {
      console.error('Missing edges or nodes array in data - cannot display graph');
      return { nodes: [mainNode], edges: [] };
    }
    
    debugLog('Processing path information');
    debugLog(`Found ${nodeData.nodes.length} nodes and ${nodeData.edges.length} edges`);
    
    // Add all nodes with pre-computed styling
    nodeData.nodes.forEach(nodeInfo => {
      debugLog('Processing node:', nodeInfo.data?.name);
      
      const nodeId = nodeInfo.id || nodeInfo.data.name;
      
      if (!processedNodes.has(nodeId)) {
        const isMain = nodeInfo.isMainNode || false;
        
        const cytoscapeNode = createCytoscapeNode(
          nodeId,
          nodeInfo.data.name || nodeId,
          nodeInfo.data,
          nodeInfo.data.label || 'Unknown',
          isMain
        );
        
        nodes.push(cytoscapeNode);
        processedNodes.add(nodeId);
      }
    });
    
    // Add all edges with pre-computed styling
    nodeData.edges.forEach((edge, idx) => {
      const relType = getRelationshipString(edge.relationship);
      
      const cytoscapeEdge = createCytoscapeEdge(
        edge.id || `edge-${idx}`,
        edge.source,
        edge.target,
        relType,
        edge.properties || {}
      );
      
      edges.push(cytoscapeEdge);
    });
    
    debugLog(`Created ${nodes.length} nodes and ${edges.length} edges`);
    debugLog('Graph will show ACTUAL relationships, not artificial star topology');

    return { nodes, edges };
  }

  // ============================================
  // INTERACTIVE FEATURES
  // ============================================

  /**
   * Show context menu at position
   */
  function showContextMenu(x, y, node) {
    contextMenuPosition = { x, y };
    contextMenuTargetNode = node;
    contextMenuVisible = true;
  }

  /**
   * Handle context menu action
   */
  async function handleContextMenuAction(event) {
    const { action, node } = event.detail;
    debugLog(`Context menu action: ${action}`, node);

    switch (action) {
      case 'info':
        showNodeInfo(node);
        break;
      case 'extend':
        await extendNode(node);
        break;
      case 'collapse':
        collapseNode(node);
        break;
      case 'delete':
        deleteNode(node);
        break;
    }
  }

  /**
   * Show node information in the info panel
   */
  function showNodeInfo(node) {
    selectedNodeData = {
      name: node.data('label'),
      type: node.data('type'),
      properties: node.data('properties'),
      isMainNode: node.data('isMainNode')
    };
    debugLog('Showing info for node:', selectedNodeData);
  }

  /**
   * Clear selected node (return to main node display)
   */
  function clearSelectedNode() {
    selectedNodeData = null;
    debugLog('Cleared selected node, showing main node');
  }

  /**
   * Extend node - fetch and add its connections
   */
  async function extendNode(node) {
    const nodeName = node.data('label');
    const nodeType = node.data('type');
    
    debugLog(`Extending node: ${nodeName} (${nodeType})`);
    
    isExtending = true;
    
    try {
      // Fetch node data with hops=1 (immediate connections)
      const response = await getNodeByName(nodeName, nodeType, 1);
      
      if (!response.success || !response.data || response.data.length === 0) {
        console.error('Failed to fetch node connections');
        return;
      }
      
      const fetchedData = response.data[0];
      debugLog('Fetched data for extend:', fetchedData);
      
      // Convert to Cytoscape format
      const newGraphData = nodeDataToCytoscape(fetchedData);
      
      // Merge into existing graph (avoiding duplicates)
      mergeGraphData(newGraphData);
      
      // Re-run layout to position new nodes
      runLayout(true);
      
    } catch (error) {
      console.error('Error extending node:', error);
    } finally {
      isExtending = false;
    }
  }

  /**
   * Merge new graph data into existing graph
   * Avoids duplicates by checking if nodes/edges already exist
   */
  function mergeGraphData(newGraphData) {
    let addedNodes = 0;
    let addedEdges = 0;
    
    // Add new nodes (if they don't exist)
    newGraphData.nodes.forEach(nodeObj => {
      const existingNode = cy.getElementById(nodeObj.data.id);
      if (existingNode.length === 0) {
        cy.add(nodeObj);
        addedNodes++;
      }
    });
    
    // Add new edges (if they don't exist)
    newGraphData.edges.forEach(edgeObj => {
      const existingEdge = cy.getElementById(edgeObj.data.id);
      if (existingEdge.length === 0) {
        // Check if edge between same nodes exists (even with different ID)
        const duplicateEdge = cy.edges().filter(e => 
          e.data('source') === edgeObj.data.source &&
          e.data('target') === edgeObj.data.target &&
          e.data('relationshipType') === edgeObj.data.relationshipType
        );
        
        if (duplicateEdge.length === 0) {
          cy.add(edgeObj);
          addedEdges++;
        }
      }
    });
    
    debugLog(`Merged: ${addedNodes} new nodes, ${addedEdges} new edges`);
  }

  /**
   * Collapse node - remove leaf nodes connected only to this node
   */
  function collapseNode(node) {
    const nodeId = node.id();
    debugLog(`Collapsing node: ${nodeId}`);
    
    // Find all directly connected nodes
    const connectedEdges = node.connectedEdges();
    const connectedNodes = node.neighborhood('node');
    
    let removedCount = 0;
    
    // Check each connected node
    connectedNodes.forEach(connectedNode => {
      // Skip if it's the main node (protected)
      if (connectedNode.data('isMainNode')) {
        return;
      }
      
      // Check if this node is only connected to our target node
      const allEdges = connectedNode.connectedEdges();
      const isLeaf = allEdges.every(edge => 
        edge.data('source') === nodeId || edge.data('target') === nodeId
      );
      
      if (isLeaf) {
        // Remove the leaf node (edges will be removed automatically)
        cy.remove(connectedNode);
        removedCount++;
      }
    });
    
    debugLog(`Collapsed: removed ${removedCount} leaf nodes`);
    
    // Re-run layout to adjust positions
    if (removedCount > 0) {
      runLayout(true);
    }
  }

  /**
   * Delete node and its connected edges
   */
  function deleteNode(node) {
    const nodeId = node.id();
    
    // Protect main node from deletion
    if (node.data('isMainNode')) {
      debugLog('Cannot delete main node (protected)');
      console.warn('Main node is protected and cannot be deleted');
      return;
    }
    
    debugLog(`Deleting node: ${nodeId}`);
    
    // If this node is currently selected, clear selection
    if (selectedNodeData && selectedNodeData.name === node.data('label')) {
      clearSelectedNode();
    }
    
    // Remove node (edges will be removed automatically by Cytoscape)
    cy.remove(node);
    
    // Re-run layout
    runLayout(true);
  }

  /**
   * Run layout algorithm
   */
  function runLayout(animate = false) {
    const layoutConfig = getCoseLayoutConfig();
    layoutConfig.animate = animate;
    cy.layout(layoutConfig).run();
  }

  // ============================================
  // GRAPH INITIALIZATION
  // ============================================

  /**
   * Initialize or update the graph
   */
  function initializeGraph() {
    if (!containerElement) {
      debugLog('Container element not ready');
      return;
    }

    const bgColor = getCSSVariable('--graph-background') || '#0f172a';
    const nodeTextColor = getCSSVariable('--graph-node-text') || '#f8fafc';

    const graphData = nodeDataToCytoscape(node);

    if (graphData.nodes.length === 0) {
      console.error('No nodes to display');
      return;
    }

    // If graph instance exists, update it
    if (cy) {
      debugLog('Updating existing graph');
      cy.elements().remove();
      cy.add(graphData.nodes);
      cy.add(graphData.edges);
      
      runLayout(true);
      return;
    }

    debugLog('Creating new Cytoscape instance');

    // Create new Cytoscape instance
    cy = cytoscape({
      container: containerElement,
      elements: [...graphData.nodes, ...graphData.edges],
      
      style: [
        {
          selector: 'node',
          style: {
            'label': 'data(label)',
            'background-color': 'data(color)',
            'width': 'data(size)',
            'height': 'data(size)',
            'font-size': 'data(fontSize)',
            'font-weight': 'data(fontWeight)',
            'border-width': 'data(borderWidth)',
            'border-color': 'data(borderColor)',
            'color': nodeTextColor,
            'text-valign': 'center',
            'text-halign': 'center',
            'text-wrap': 'wrap',
            'text-max-width': 80,
          }
        },
        {
          selector: 'edge',
          style: {
            'width': 'data(width)',
            'line-color': 'data(color)',
            'target-arrow-color': 'data(color)',
            'target-arrow-shape': 'data(arrowShape)',
            'curve-style': 'bezier',
            'label': 'data(label)',
            'font-size': 10,
            'text-rotation': 'autorotate',
            'color': nodeTextColor,
            'text-background-color': bgColor,
            'text-background-opacity': 0.8,
            'text-background-padding': '3px',
          }
        },
        {
          selector: 'node:selected',
          style: {
            'border-width': 3,
            'border-color': '#fff',
            'overlay-color': '#fff',
            'overlay-padding': 5,
            'overlay-opacity': 0.3,
          }
        },
        {
          selector: 'edge:selected',
          style: {
            'width': 4,
            'line-color': '#fff',
            'target-arrow-color': '#fff',
          }
        }
      ],
      
      layout: getCoseLayoutConfig()
    });

    containerElement.style.backgroundColor = bgColor;

    // ============================================
    // EVENT HANDLERS
    // ============================================

    // Single click on node - show info
    cy.on('tap', 'node', function(evt) {
      const clickedNode = evt.target;
      showNodeInfo(clickedNode);
    });

    // Double click on node - extend
    cy.on('dbltap', 'node', function(evt) {
      const clickedNode = evt.target;
      extendNode(clickedNode);
    });

    // Right click on node - context menu
    cy.on('cxttap', 'node', function(evt) {
      const clickedNode = evt.target;
      const position = evt.renderedPosition || evt.position;
      
      // Convert Cytoscape position to screen coordinates
      const container = containerElement.getBoundingClientRect();
      showContextMenu(
        container.left + position.x,
        container.top + position.y,
        clickedNode
      );
    });

    // Click on edge - show edge info
    cy.on('tap', 'edge', function(evt) {
      const clickedEdge = evt.target;
      showEdgeInfo(clickedEdge);
    });

    // Click on background - deselect
    cy.on('tap', function(evt) {
      if (evt.target === cy) {
        clearSelectedNode();
      }
    });

    cy.fit(null, 50);
  }

  /**
   * Show edge information
   */
  function showEdgeInfo(edge) {
    selectedNodeData = {
      name: edge.data('label'),
      type: 'Relationship',
      properties: edge.data('properties'),
      isEdge: true,
      source: edge.source().data('label'),
      target: edge.target().data('label')
    };
    debugLog('Showing info for edge:', selectedNodeData);
  }

  /**
   * Get CoSE layout configuration
   */
  function getCoseLayoutConfig() {
    return {
      name: 'cose',
      idealEdgeLength: 100,
      nodeOverlap: 20,
      refresh: 20,
      fit: true,
      padding: 50,
      randomize: false,
      nodeRepulsion: 400000,
      edgeElasticity: 100,
      nestingFactor: 5,
      gravity: 80,
      numIter: 1000,
      initialTemp: 200,
      coolingFactor: 0.95,
      minTemp: 1.0,
      animate: true,
      animationDuration: 500
    };
  }

  // ============================================
  // REPORT GENERATION
  // ============================================

  /**
   * Generate HTML report of current graph state
   * Called from parent component (App.svelte)
   * 
   * @public
   */
  export function generateReportFromGraph() {
    if (!cy) {
      console.error('Cannot generate report: Cytoscape instance not initialized');
      return;
    }

    debugLog('=== Generating Report ===');

    // Get current main node info
    const mainNodeInfo = selectedNodeData || {
      name: node.n.name,
      type: node.n.label,
      properties: node.n
    };

    // Get all visible nodes
    const visibleNodes = cy.nodes().jsons();
    debugLog(`Report includes ${visibleNodes.length} nodes`);

    // Get all visible edges
    const visibleEdges = cy.edges().jsons();
    debugLog(`Report includes ${visibleEdges.length} edges`);

    // Export graph as PNG image
    const graphImage = cy.png({
      output: 'base64uri',
      bg: '#0f172a',  // dark background
      full: true,      // Full graph, not just viewport
      scale: 2,        // 2x for better quality
      maxWidth: 2000,  // Limit width for performance
      maxHeight: 2000
    });
    debugLog('Graph image exported as PNG');

    // Prepare report data
    const reportData = {
      mainNode: mainNodeInfo,
      nodes: visibleNodes,
      edges: visibleEdges,
      graphImage: graphImage
    };

    // Generate and open report
    generateReport(reportData);
    debugLog('Report generated and opened in new tab');
  }

  // ============================================
  // LIFECYCLE HOOKS
  // ============================================

  onMount(() => {
    debugLog('=== GraphView MOUNTED ===');
    debugLog('Node prop on mount:', node);
    initializeGraph();
  });

  onDestroy(() => {
    debugLog('GraphView destroyed');
    if (cy) {
      cy.destroy();
      cy = null;
    }
  });

  $: {
    debugLog('=== Reactive: node prop changed ===');
    debugLog('New node value:', node);
    
    if (cy && node) {
      debugLog('Updating graph because node changed');
      initializeGraph();
    }
  }
</script>

<div class="graph-wrapper">
  <div bind:this={containerElement} id="cy" class="graph-canvas"></div>
  
  <!-- Loading indicator for extend operation -->
  {#if isExtending}
    <div class="loading-overlay">
      <div class="loading-spinner"></div>
      <p>Loading connections...</p>
    </div>
  {/if}
  
  <!-- Node/Edge Info Panel -->
  <div class="node-info">
    {#if selectedNodeData}
      <!-- Showing selected node/edge info -->
      <h3>{selectedNodeData.name}</h3>
      <span class="node-type label-{selectedNodeData.type}">
        {selectedNodeData.type}
      </span>
      
      {#if selectedNodeData.isEdge}
        <div class="edge-connection">
          <strong>From:</strong> {selectedNodeData.source}<br>
          <strong>To:</strong> {selectedNodeData.target}
        </div>
      {/if}
      
      <div class="properties">
        <h4>Properties:</h4>
        {#if selectedNodeData.properties && Object.keys(selectedNodeData.properties).length > 0}
          {#each Object.entries(selectedNodeData.properties) as [key, value]}
            {#if key !== 'name' && key !== 'label'}
              <div class="property">
                <span class="key">{key}:</span>
                <span class="value">{value}</span>
              </div>
            {/if}
          {/each}
        {:else}
          <p class="no-properties">No additional properties</p>
        {/if}
      </div>
    {:else if node && node.n}
      <!-- Showing main node info (default) -->
      <h3>{node.n.name}</h3>
      <span class="node-type label-{node.n.label}">
        {node.n.label}
      </span>
      
      {#if node.connections && node.connections.length > 0}
        <div class="connections-count">
          <strong>Connections:</strong> {node.connections.length}
        </div>
      {/if}
      
      <div class="properties">
        <h4>Properties:</h4>
        {#each Object.entries(node.n) as [key, value]}
          {#if key !== 'name' && key !== 'label'}
            <div class="property">
              <span class="key">{key}:</span>
              <span class="value">{value}</span>
            </div>
          {/if}
        {/each}
      </div>
    {/if}
  </div>
</div>

<!-- Context Menu Component -->
<ContextMenu
  bind:visible={contextMenuVisible}
  bind:position={contextMenuPosition}
  bind:targetNode={contextMenuTargetNode}
  on:action={handleContextMenuAction}
/>

<style>
  .connections-count {
    margin-top: 0.75rem;
    padding: 0.5rem;
    background: rgba(255, 255, 255, 0.05);
    border-radius: 0.25rem;
    font-size: 0.85rem;
  }

  .loading-overlay {
    position: absolute;
    top: 50%;
    left: 50%;
    transform: translate(-50%, -50%);
    background: rgba(0, 0, 0, 0.8);
    padding: 2rem;
    border-radius: 0.5rem;
    display: flex;
    flex-direction: column;
    align-items: center;
    gap: 1rem;
    z-index: 100;
  }

  .loading-spinner {
    width: 40px;
    height: 40px;
    border: 4px solid var(--color-border);
    border-top-color: var(--color-accent);
    border-radius: 50%;
    animation: spin 0.8s linear infinite;
  }

  @keyframes spin {
    to { transform: rotate(360deg); }
  }

  .loading-overlay p {
    color: var(--color-text);
    margin: 0;
    font-size: 0.9rem;
  }

  .edge-connection {
    margin-top: 0.75rem;
    padding: 0.5rem;
    background: rgba(255, 255, 255, 0.05);
    border-radius: 0.25rem;
    font-size: 0.85rem;
    line-height: 1.6;
  }

  .properties h4 {
    margin: 1rem 0 0.5rem 0;
    font-size: 0.9rem;
    color: var(--color-muted);
    text-transform: uppercase;
    letter-spacing: 0.5px;
  }

  .no-properties {
    color: var(--color-muted);
    font-size: 0.85rem;
    font-style: italic;
    margin: 0.5rem 0;
  }

  .loading-spinner {
    width: 40px;
    height: 40px;
    border: 4px solid var(--color-border);
    border-top-color: var(--color-accent);
    border-radius: 50%;
    animation: spin 0.8s linear infinite;
  }

  @keyframes spin {
    to { transform: rotate(360deg); }
  }

  .loading-overlay p {
    color: var(--color-text);
    margin: 0;
    font-size: 0.9rem;
  }

  .edge-connection {
    margin-top: 0.75rem;
    padding: 0.5rem;
    background: rgba(255, 255, 255, 0.05);
    border-radius: 0.25rem;
    font-size: 0.85rem;
    line-height: 1.6;
  }

  .properties h4 {
    margin: 1rem 0 0.5rem 0;
    font-size: 0.9rem;
    color: var(--color-muted);
    text-transform: uppercase;
    letter-spacing: 0.5px;
  }

  .no-properties {
    color: var(--color-muted);
    font-size: 0.85rem;
    font-style: italic;
    margin: 0.5rem 0;
  }
</style>
