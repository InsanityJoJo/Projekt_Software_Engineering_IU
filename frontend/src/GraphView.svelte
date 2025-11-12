<!-- GraphView.svelte -->
<script>
  import { onMount, onDestroy } from 'svelte';
  import cytoscape from 'cytoscape';


  /**
  * @type {{ n: any, connections: any[], edges?: any[], nodes?: any[] } | null}
  */
  export let node = null;

  let cy;
  let containerElement;

  // ============================================
  // COLOR MAPPINGS 
  // Change colors here to update graph appearance
  // ============================================
  
  const NODE_COLORS = {
    'AttackPattern': '#ef4444',    // Red
    'Campaign': '#f59e0b',         // Orange
    'Identity': '#8b5cf6',         // Purple
    'Incident': '#ec4899',         // Pink
    'Indicator': '#14b8a6',        // Teal
    'Malware': '#dc2626',          // Dark Red
    'Observable': '#06b6d4',       // Cyan
    'Organization': '#3b82f6',     // Blue
    'Report': '#6366f1',           // Indigo
    'ThreatActor': '#b91c1c',      // Crimson
    'Tool': '#10b981',             // Green
    'Vulnerability': '#f97316',    // Orange-Red
    'File': '#84cc16',             // Lime
    'DomainName': '#22d3ee',       // Light Cyan
    'URL': '#a855f7',              // Violet
    'EmailAddr': '#f43f5e',        // Rose
    'IPv4Adress': '#06b6d4',       // Cyan
    'default': '#497f76'           // Fallback color
  };
  
  const EDGE_COLORS = {
    'USES': '#3b82f6',             // Blue
    'TARGETS': '#ef4444',          // Red
    'DETECTS': '#10b981',          // Green
    'BASED_ON': '#8b5cf6',         // Purple
    'RELATED_TO': '#f59e0b',       // Orange
    'INVOLVES': '#ec4899',         // Pink
    'LAUNCHED': '#b91c1c',         // Crimson
    'EMPLOYES': '#f97316',         // Orange-Red
    'DESCRIBES': '#6366f1',        // Indigo
    'INDICATED_BY': '#14b8a6',     // Teal
    'HAS_IDENTITY': '#a855f7',     // Violet
    'default': '#497f76'           // Fallback color
  };

  /**
   * Get color for a node type
   */
  function getNodeColor(type) {
    return NODE_COLORS[type] || NODE_COLORS['default'];
  }
  
  /**
   * Get color for an edge/relationship type
   */
  function getEdgeColor(relType) {
    return EDGE_COLORS[relType] || EDGE_COLORS['default'];
  }

  function getRelationshipString(rel) {
    // Handle different relationship formats
    if (typeof rel === 'string') {
      return rel;
    }
    if (rel && rel.type) {
      return rel.type;
    }
    if (rel && typeof rel === 'object') {
      // Neo4j relationship object - convert to string
      return String(rel);
    }
    return 'CONNECTED';
  }

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
      console.warn('No node data provided to GraphView');
      return { nodes: [], edges: [] };
    }

    console.log('=== nodeDataToCytoscape called ===');
    console.log('Input nodeData:', nodeData);

    // Create the main node with PRE-COMPUTED styling data
    const mainNode = {
      data: {
        id: nodeData.n.name || 'unknown',
        label: nodeData.n.name || 'Unknown',
        properties: nodeData.n,
        type: nodeData.n.label || 'Unknown',
        isMainNode: true,
        // PRE-COMPUTE styling properties:
        color: getNodeColor(nodeData.n.label),  // Pre-compute color
        size: 80,                                 // Main node is bigger
        fontSize: 14,                             // Main node has larger text
        fontWeight: 'bold',                       // Main node is bold
        borderWidth: 3,                           // Main node has border
        borderColor: '#f8fafc'                    // Border color
      }
    };
    console.log('Main node color:', mainNode.data.color);
    const nodes = [mainNode];
    const edges = [];
    const processedNodes = new Set([mainNode.data.id]);

    // Check if we have full path information (new format with nodes and edges arrays)
    if (nodeData.edges && nodeData.nodes) {
      console.log('Processing full path information');
      console.log(`Found ${nodeData.nodes.length} nodes and ${nodeData.edges.length} edges`);
      
      // Add all nodes with pre-computed styling
	nodeData.nodes.forEach(nodeInfo => {
  	console.log('Raw nodeInfo:', nodeInfo);
  	console.log('nodeInfo.data:', nodeInfo.data);
  	console.log('nodeInfo.data keys:', Object.keys(nodeInfo.data));
  
  	const nodeId = nodeInfo.id || nodeInfo.data.name;
  
  	if (!processedNodes.has(nodeId)) {
    	  const isMain = nodeInfo.isMainNode || false;
    
    	  // Add this to see what label value we're getting
    	  console.log('Node label from nodeInfo.data.label:', nodeInfo.data.label);
    
    	  nodes.push({
      	  data: {
        	id: nodeId,
        	label: nodeInfo.data.name || nodeId,
        	properties: nodeInfo.data,
        	type: nodeInfo.data.label || 'Unknown',
        	isMainNode: isMain,
        	color: getNodeColor(nodeInfo.data.label),
        	size: isMain ? 80 : 60,
        	fontSize: isMain ? 14 : 12,
        	fontWeight: isMain ? 'bold' : 'normal',
        	borderWidth: isMain ? 3 : 0,
        	borderColor: '#f8fafc'
      	  }
    	});
    	processedNodes.add(nodeId);
       }
      });
            // Add all edges with pre-computed styling (preserves path structure!)
      nodeData.edges.forEach((edge, idx) => {
        const relType = getRelationshipString(edge.relationship);
        
        edges.push({
          data: {
            id: edge.id || `edge-${idx}`,
            source: edge.source,
            target: edge.target,
            label: relType,
            relationshipType: relType,
            // PRE-COMPUTE styling properties:
            color: getEdgeColor(relType),
            width: 2,
            arrowShape: 'triangle'
          }
        });
      });
      
      console.log(`Created ${nodes.length} nodes and ${edges.length} edges from paths`);
    } 
    // Fallback: old format (connections array - star topology)
    else if (nodeData.connections && Array.isArray(nodeData.connections)) {
      console.log(`Processing connections (star topology): ${nodeData.connections.length} items`);
      
      nodeData.connections.forEach((conn, idx) => {
        if (!conn.node || !conn.node.name) {
          console.warn('Invalid connection data:', conn);
          return;
        }

        const connectedNodeId = conn.node.name;
        const relType = getRelationshipString(conn.relationship);

        // Check if we have source/target info (path-aware format)
        if (conn.source && conn.target) {
          // Path-aware: use actual source and target
          const sourceId = conn.source;
          const targetId = conn.target;
          
          if (!processedNodes.has(targetId)) {
            nodes.push({
              data: {
                id: targetId,
                label: conn.node.name || targetId,
                properties: conn.node,
                type: conn.node.label || 'Unknown',
                isMainNode: false,
                // PRE-COMPUTE styling:
                color: getNodeColor(conn.node.label),
                size: 60,
                fontSize: 12,
                fontWeight: 'normal',
                borderWidth: 0,
		borderColor: '#f8fafc',
              }
            });
            processedNodes.add(targetId);
          }
          
          // Add edge with correct source and target
          edges.push({
            data: {
              id: `edge-${idx}`,
              source: sourceId,
              target: targetId,
              label: relType,
              relationshipType: relType,
              // PRE-COMPUTE styling:
              color: getEdgeColor(relType),
              width: 2,
              arrowShape: 'triangle'
            }
          });
        } else {
          // Old format: star topology (all edges from main node)
          if (!processedNodes.has(connectedNodeId)) {
            nodes.push({
              data: {
                id: connectedNodeId,
                label: connectedNodeId,
                properties: conn.node,
                type: conn.node.label || 'Unknown',
                isMainNode: false,
                // PRE-COMPUTE styling:
                color: getNodeColor(conn.node.label),
                size: 60,
                fontSize: 12,
                fontWeight: 'normal',
                borderWidth: 0,
		borderColor: '#f8fafc',
              }
            });
            processedNodes.add(connectedNodeId);
          }

          edges.push({
            data: {
              id: `edge-${idx}`,
              source: mainNode.data.id,
              target: connectedNodeId,
              label: relType,
              relationshipType: relType,
              // PRE-COMPUTE styling:
              color: getEdgeColor(relType),
              width: 3,
              arrowShape: 'triangle'
            }
          });
        }
      });

      console.log(`Created ${nodes.length} nodes and ${edges.length} edges`);
    } else {
      console.log('No connections to display - showing single node');
    }

    return { nodes, edges };
  }

  /**
   * Initialize or update the graph
   * 
   * - Call this when component mounts
   * - Also call it when node prop changes
   */
  function initializeGraph() {
    if (!containerElement) {
      console.warn('Container element not ready');
      return;
    }

    // Get CSS variables for consistent theming (only for background/text colors)
    const rootStyles = getComputedStyle(document.documentElement);
    const bgColor = rootStyles.getPropertyValue('--graph-background').trim() || '#0f172a';
    const nodeTextColor = rootStyles.getPropertyValue('--graph-node-text').trim() || '#f8fafc';

    // Convert node data to Cytoscape format
    const graphData = nodeDataToCytoscape(node);

    if (graphData.nodes.length === 0) {
      console.error('No nodes to display');
      return;
    }

    // If graph instance exists, update it
    if (cy) {
      console.log('Updating existing graph');
      cy.elements().remove(); // Clear existing elements
      cy.add(graphData.nodes);
      cy.add(graphData.edges);
      
      // Choose layout based on number of nodes
      const layoutName = graphData.nodes.length > 20 ? 'grid' : 'cose';
      cy.layout({ 
        name: layoutName,
        animate: true,
        animationDuration: 500,
      }).run();
      return;
    }

    console.log('Creating new Cytoscape instance');

    // Create new Cytoscape instance
    cy = cytoscape({
      container: containerElement,
      elements: [...graphData.nodes, ...graphData.edges],
      
      // ============================================
      // CYTOSCAPE STYLESHEET
      // Using data mappers: 'data(propertyName)' 
      // No functions needed - just reads pre-computed values!
      // ============================================
      style: [
        {
          selector: 'node',
          style: {
            // All styling from pre-computed data properties:
            'label': 'data(label)',                    // Node name
            'background-color': 'data(color)',         // Pre-computed color
            'width': 'data(size)',                     // Pre-computed size
            'height': 'data(size)',                    // Pre-computed size
            'font-size': 'data(fontSize)',             // Pre-computed font size
            'font-weight': 'data(fontWeight)',         // Pre-computed weight
            'border-width': 'data(borderWidth)',       // Pre-computed border
            'border-color': 'data(borderColor)',       // Pre-computed border color
            'color': nodeTextColor,                    // Text color from CSS
            'text-valign': 'center',
            'text-halign': 'center',
            'text-wrap': 'wrap',
            'text-max-width': 80,
          }
        },
        {
          selector: 'edge',
          style: {
            //  All styling from pre-computed data properties:
            'width': 'data(width)',                    // Pre-computed width
            'line-color': 'data(color)',               // Pre-computed color
            'target-arrow-color': 'data(color)',       // Pre-computed color
            'target-arrow-shape': 'data(arrowShape)',  // Pre-computed shape
            'curve-style': 'bezier',
            'label': 'data(label)',                    // Relationship type
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
      
      layout: {
        name: graphData.nodes.length > 20 ? 'circle' : 'cose',
        animate: true,
        animationDuration: 500,
        // For cose layout (spring-based physics)
        nodeRepulsion: 400000,
        idealEdgeLength: 100,
        edgeElasticity: 100,
        nestingFactor: 5,
      },

      // User interaction settings
      userZoomingEnabled: true,
      userPanningEnabled: true,
      boxSelectionEnabled: false,
    });

    // Set background color
    containerElement.style.backgroundColor = bgColor;

    // Add click handler for nodes
    cy.on('tap', 'node', function(evt) {
      const clickedNode = evt.target;
      console.log('Clicked node:', clickedNode.data());
      // Future: Could expand this node's connections
    });

    // Fit the graph to the container
    cy.fit(null, 50); // 50px padding
  }

  /**
   * Lifecycle: Component mounted
   */
  onMount(() => {
    console.log('=== GraphView MOUNTED ===');
    console.log('Node prop on mount:', node);
    if (node) {
      console.log('Node has n?', 'n' in node);
      console.log('Node.n:', node.n);
    }
    initializeGraph();
  });

  /**
   * Lifecycle: Clean up when component is destroyed
   */
  onDestroy(() => {
    console.log('GraphView destroyed');
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
    console.log('=== Reactive: node prop changed ===');
    console.log('New node value:', node);
    if (node) {
      console.log('Node keys:', Object.keys(node));
      console.log('Has n property?', 'n' in node);
    }
    if (cy && node) {
      console.log('Updating graph because node changed');
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
