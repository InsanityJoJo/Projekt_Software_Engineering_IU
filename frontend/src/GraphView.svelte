<!-- GraphView.svelte -->
<script>
  import { onMount, onDestroy } from 'svelte';
  import cytoscape from 'cytoscape';

  // DEBUG CONFIGURATION
  // Set to false to disable console logs
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

  // COLOR HELPERS
  // Read colors from CSS variables in :root
  
  /**
   * Get computed CSS variable value from :root
   * @param {string} varName - CSS variable name (e.g., '--node-Malware')
   * @returns {string} - Color value
   */
  function getCSSVariable(varName) {
    return getComputedStyle(document.documentElement).getPropertyValue(varName).trim();
  }

  /**
   * Get color for a node type from CSS variables
   * @param {string} type - Node type (e.g., 'Malware', 'ThreatActor')
   * @returns {string} - Hex color code
   */
  function getNodeColor(type) {
    const color = getCSSVariable(`--node-${type}`);
    return color || getCSSVariable('--node-default');
  }
  
  /**
   * Get color for an edge/relationship type from CSS variables
   * @param {string} relType - Relationship type (e.g., 'USES', 'TARGETS')
   * @returns {string} - Hex color code
   */
  function getEdgeColor(relType) {
    const color = getCSSVariable(`--edge-${relType}`);
    return color || getCSSVariable('--edge-default');
  }

  // HELPER FUNCTIONS

  /**
   * Extract relationship type as string from various formats
   * @param {string|object} rel - Relationship in various formats
   * @returns {string} - Relationship type as string
   */
  function getRelationshipString(rel) {
    if (typeof rel === 'string') return rel;
    if (rel && rel.type) return rel.type;
    if (rel && typeof rel === 'object') return String(rel);
    return 'CONNECTED';
  }

  /**
   * Create style data object for a node
   * @param {object} nodeData - Node data from backend
   * @param {boolean} isMainNode - Whether this is the main/central node
   * @returns {object} - Pre-computed style properties
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
   * @param {string} relType - Relationship type
   * @returns {object} - Pre-computed style properties
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
   * @param {string} id - Node ID
   * @param {string} label - Display label
   * @param {object} properties - Node properties
   * @param {string} type - Node type
   * @param {boolean} isMainNode - Is this the main node?
   * @returns {object} - Cytoscape node object
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
        ...styleData  // Spread pre-computed style properties
      }
    };
  }

  /**
   * Create a Cytoscape edge object
   * @param {string} id - Edge ID
   * @param {string} source - Source node ID
   * @param {string} target - Target node ID
   * @param {string} relType - Relationship type
   * @returns {object} - Cytoscape edge object
   */
  function createCytoscapeEdge(id, source, target, relType) {
    const styleData = createEdgeStyleData(relType);
    
    return {
      data: {
        id,
        source,
        target,
        label: relType,
        relationshipType: relType,
        ...styleData  // Spread pre-computed style properties
      }
    };
  }

  // DATA CONVERSION

  /**
   * Convert backend node data to Cytoscape format with pre-computed colors
   * 
   * Backend returns: { n: {...}, connections: [...], nodes: [...], edges: [...] }
   * Cytoscape expects: { nodes: [...], edges: [...] }
   * 
   * Pre-compute all styling data (color, size, etc.) and store in node.data
   * Then Cytoscape just reads from data using 'data(property)'
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
      true  // isMainNode
    );
    
    debugLog('Main node created:', mainNode.data.id, 'Color:', mainNode.data.color);
    
    const nodes = [mainNode];
    const edges = [];
    const processedNodes = new Set([mainNode.data.id]);

    // Process the nodes and edges arrays from backend
    // Backend ALWAYS provides these in the correct format with source/target
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
    
    // Add all edges with pre-computed styling (preserves actual path structure!)
    nodeData.edges.forEach((edge, idx) => {
      const relType = getRelationshipString(edge.relationship);
      
      const cytoscapeEdge = createCytoscapeEdge(
        edge.id || `edge-${idx}`,
        edge.source,
        edge.target,
        relType
      );
      
      edges.push(cytoscapeEdge);
    });
    
    debugLog(`Created ${nodes.length} nodes and ${edges.length} edges`);
    debugLog('Graph will show ACTUAL relationships, not artificial star topology');

    return { nodes, edges };
  }

  // GRAPH INITIALIZATION

  /**
   * Initialize or update the graph
   * 
   * - Call this when component mounts
   * - Also call it when node prop changes
   */
  function initializeGraph() {
    if (!containerElement) {
      debugLog('Container element not ready');
      return;
    }

    // Get CSS variables for consistent theming (background/text colors)
    const bgColor = getCSSVariable('--graph-background') || '#0f172a';
    const nodeTextColor = getCSSVariable('--graph-node-text') || '#f8fafc';

    // Convert node data to Cytoscape format
    const graphData = nodeDataToCytoscape(node);

    if (graphData.nodes.length === 0) {
      console.error('No nodes to display');
      return;
    }

    // If graph instance exists, update it
    if (cy) {
      debugLog('Updating existing graph');
      cy.elements().remove(); // Clear existing elements
      cy.add(graphData.nodes);
      cy.add(graphData.edges);
      
      // Apply cose layout for natural node spacing
      cy.layout(getCoseLayoutConfig()).run();
      return;
    }

    debugLog('Creating new Cytoscape instance');

    // Create new Cytoscape instance
    cy = cytoscape({
      container: containerElement,
      elements: [...graphData.nodes, ...graphData.edges],
      
      // CYTOSCAPE STYLESHEET
      // Using data mappers: 'data(propertyName)' 
      // reads pre-computed values
      style: [
        {
          selector: 'node',
          style: {
            // All styling from pre-computed data properties:
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
            // All styling from pre-computed data properties:
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
        }
      ],
      
      layout: getCoseLayoutConfig()
    });

    // Set background color
    containerElement.style.backgroundColor = bgColor;

    // Add click handler for nodes
    cy.on('tap', 'node', function(evt) {
      const clickedNode = evt.target;
      debugLog('Clicked node:', clickedNode.data());
      // Future: Could expand this node's connections
    });

    // Fit the graph to the container
    cy.fit(null, 50); // 50px padding
  }

  /**
   * Get CoSE (Compound Spring Embedder) layout configuration
   * CoSE is great for organic, force-directed layouts with good node spacing
   * 
   * @returns {object} - Cytoscape layout configuration
   */
  function getCoseLayoutConfig() {
    return {
      name: 'cose',
      
      // Physics simulation
      idealEdgeLength: 100,         // Preferred edge length
      nodeOverlap: 20,              // Min space between nodes
      refresh: 20,                  // Refresh rate (ms)
      fit: true,
      padding: 50,
      randomize: false,             // Start from current positions
      
      // Forces
      nodeRepulsion: 400000,        // Nodes push each other away
      edgeElasticity: 100,          // Edges pull nodes together
      nestingFactor: 5,             // How much to nest clusters
      gravity: 80,                  // Pull toward center
      
      // Incremental layout
      numIter: 1000,                // Max iterations
      initialTemp: 200,             // Initial temperature
      coolingFactor: 0.95,          // Cooling rate
      minTemp: 1.0,                 // Stop temperature
      
      animate: true,
      animationDuration: 500
    };
  }

  // LIFECYCLE HOOKS

  /**
   * Lifecycle: Component mounted
   */
  onMount(() => {
    debugLog('=== GraphView MOUNTED ===');
    debugLog('Node prop on mount:', node);
    initializeGraph();
  });

  /**
   * Lifecycle: Clean up when component is destroyed
   */
  onDestroy(() => {
    debugLog('GraphView destroyed');
    if (cy) {
      cy.destroy();
      cy = null;
    }
  });

  /**
   * Reactive statement: runs when 'node' prop changes
   * 
   * - Whenever 'node' changes, this runs
   * - Updates the graph with new data
   */
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
  
  {#if node && node.n}
    <div class="node-info">
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
        {#each Object.entries(node.n) as [key, value]}
          {#if key !== 'name' && key !== 'label'}
            <div class="property">
              <span class="key">{key}:</span>
              <span class="value">{value}</span>
            </div>
          {/if}
        {/each}
      </div>
    </div>
  {/if}
</div>

<style>
  .connections-count {
    margin-top: 0.75rem;
    padding: 0.5rem;
    background: rgba(255, 255, 255, 0.05);
    border-radius: 0.25rem;
    font-size: 0.85rem;
  }
</style>
