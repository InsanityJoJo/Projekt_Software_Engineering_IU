<!-- GraphView.svelte -->
<script>
  import { onMount, onDestroy } from 'svelte';
  import cytoscape from 'cytoscape';

  /**
   * Props received from parent component
   */
  export let node = null;

  let cy;
  let containerElement;

  /**
   * Convert backend node data to Cytoscape format
   * 
   * Backend returns: { n: {...}, connections: [...] }
   * Cytoscape expects: { nodes: [...], edges: [...] }
   */
  function nodeDataToCytoscape(nodeData) {
    if (!nodeData || !nodeData.n) {
      return { nodes: [], edges: [] };
    }

    // Create the main node
    const mainNode = {
      data: {
        id: nodeData.n.name || 'unknown',
        label: nodeData.n.name || 'Unknown',
        // Store all properties for tooltip/inspection
        properties: nodeData.n,
        // Node type for styling
        type: nodeData.n.label || 'Unknown',
      }
    };

    const nodes = [mainNode];
    const edges = [];

    // For now, only showing the single node
    // Later, add connections here when implementing hops
    // 
    // if (nodeData.connections) {
    //   nodeData.connections.forEach((conn, idx) => {
    //     nodes.push({
    //       data: {
    //         id: conn.node.name,
    //         label: conn.node.name,
    //         ...
    //       }
    //     });
    //     edges.push({
    //       data: {
    //         id: `edge-${idx}`,
    //         source: mainNode.data.id,
    //         target: conn.node.name,
    //         label: conn.relationship,
    //         ...
    //       }
    //     });
    //   });
    // }

    return { nodes, edges };
  }

  /**
   * Initialize or update the graph
   * 
   * - Call this when component mounts
   * - Also call it when node prop changes
   */
  function initializeGraph() {
    if (!containerElement) return;

    // Get CSS variables for consistent theming
    const rootStyles = getComputedStyle(document.documentElement);
    const bgColor = rootStyles.getPropertyValue('--graph-background').trim();
    const edgeColor = rootStyles.getPropertyValue('--graph-edge').trim();
    const nodeTextColor = rootStyles.getPropertyValue('--graph-node-text').trim();

    // Convert node data to Cytoscape format
    const graphData = nodeDataToCytoscape(node);

    // If graph iinstance exists, update it
    if (cy) {
      cy.elements().remove(); // Clear existing elements
      cy.add(graphData.nodes);
      cy.add(graphData.edges);
      cy.layout({ name: 'cose' }).run();
      return;
    }

    // Create new Cytoscape instance
    cy = cytoscape({
      container: containerElement,
      elements: [...graphData.nodes, ...graphData.edges],
      
      style: [
        {
          selector: 'node',
          style: {
            'label': 'data(label)',
            'background-color': function(ele) {
              // Get color from CSS variable based on node type
              const type = ele.data('type');
              const rootStyles = getComputedStyle(document.documentElement);
              const color = rootStyles.getPropertyValue(`--node-${type}`).trim();
              return color || rootStyles.getPropertyValue('--node-default').trim();
            },
            'color': nodeTextColor,
            'text-valign': 'center',
            'text-halign': 'center',
            'width': 60,
            'height': 60,
            'font-size': 12,
            'text-wrap': 'wrap',
            'text-max-width': 80,
          }
        },
        {
          selector: 'edge',
          style: {
            'width': 2,
            'line-color': edgeColor,
            'target-arrow-color': edgeColor,
            'target-arrow-shape': 'triangle',
            'curve-style': 'bezier',
            'label': 'data(label)',
            'font-size': 10,
            'text-rotation': 'autorotate',
            'color': nodeTextColor,
          }
        }
      ],
      
      layout: {
        name: 'cose', // Spring-like physics layout
        animate: true,
        animationDuration: 500,
      },

      // User interaction settings
      userZoomingEnabled: true,
      userPanningEnabled: true,
      boxSelectionEnabled: false,
    });

    // Set background color
    containerElement.style.backgroundColor = bgColor;

    // Add click handler for nodes (for future expansion)
    cy.on('tap', 'node', function(evt) {
      const clickedNode = evt.target;
      console.log('Clicked node:', clickedNode.data());
      // Future: Could open detail panel or expand connections
    });
  }

  /**
   * Lifecycle: Run when component is mounted to DOM
   */
  onMount(() => {
    initializeGraph();
  });

  /**
   * Lifecycle: Clean up when component is destroyed
   */
  onDestroy(() => {
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
  $: if (cy && node) {
    initializeGraph();
  }
</script>

<div class="graph-wrapper">
  <div bind:this={containerElement} id="cy" class="graph-canvas"></div>
  
  {#if node}
    <div class="node-info">
      <h3>{node.n.name}</h3>
      <span class="node-type label-{node.n.label}">
        {node.n.label}
      </span>
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
