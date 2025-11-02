<script>
  import { onMount } from 'svelte';
  import cytoscape from 'cytoscape';

  // Prop to receive data from parent
  export let data = [];

  let cy;
  let cyContainer;

  /**
   * Transform Neo4j query results to Cytoscape format
   * @param {Array} queryResults - Results from backend API
   * @returns {Array} - Cytoscape elements (nodes + edges)
   */
  function transformDataToCytoscape(queryResults) {
    const elements = [];
    const addedNodes = new Set();
    const addedEdges = new Set();

    queryResults.forEach(record => {
      // Add nodes
      if (record.n && record.n.properties) {
        const nodeId = record.n.elementId || record.n.identity?.toString() || `node-${Math.random()}`;
        
        if (!addedNodes.has(nodeId)) {
          elements.push({
            data: {
              id: nodeId,
              label: record.n.properties.name || record.n.labels?.[0] || 'Unknown',
              nodeType: record.n.labels?.[0] || 'Node',
              properties: record.n.properties
            },
            classes: record.n.labels?.[0]?.toLowerCase() || 'default'
          });
          addedNodes.add(nodeId);
        }
      }

      // Add relationships
      if (record.r && record.r.type) {
        const sourceId = record.r.startNodeElementId || record.r.start?.toString();
        const targetId = record.r.endNodeElementId || record.r.end?.toString();
        const edgeId = record.r.elementId || `edge-${sourceId}-${targetId}`;

        if (!addedEdges.has(edgeId) && sourceId && targetId) {
          elements.push({
            data: {
              id: edgeId,
              source: sourceId,
              target: targetId,
              label: record.r.type,
              properties: record.r.properties || {}
            }
          });
          addedEdges.add(edgeId);
        }
      }

      // Add connected nodes if they exist
      if (record.m && record.m.properties) {
        const connectedNodeId = record.m.elementId || record.m.identity?.toString() || `node-${Math.random()}`;
        
        if (!addedNodes.has(connectedNodeId)) {
          elements.push({
            data: {
              id: connectedNodeId,
              label: record.m.properties.name || record.m.labels?.[0] || 'Unknown',
              nodeType: record.m.labels?.[0] || 'Node',
              properties: record.m.properties
            },
            classes: record.m.labels?.[0]?.toLowerCase() || 'default'
          });
          addedNodes.add(connectedNodeId);
        }
      }
    });

    // If we only have one node with no relationships, still show it
    if (elements.length === 0 && queryResults.length > 0) {
      const firstRecord = queryResults[0];
      if (firstRecord.n) {
        const nodeId = firstRecord.n.elementId || 'single-node';
        elements.push({
          data: {
            id: nodeId,
            label: firstRecord.n.properties?.name || 'Result',
            nodeType: firstRecord.n.labels?.[0] || 'Node',
            properties: firstRecord.n.properties || {}
          }
        });
      }
    }

    return elements;
  }

  /**
   * Initialize or update the Cytoscape graph
   */
  function initGraph() {
    if (!cyContainer) return;

    const rootStyles = getComputedStyle(document.documentElement);
    const bgColor = rootStyles.getPropertyValue('--graph-background').trim();
    const nodeColor = rootStyles.getPropertyValue('--graph-node').trim();
    const nodeTextColor = rootStyles.getPropertyValue('--graph-node-text').trim();
    const edgeColor = rootStyles.getPropertyValue('--graph-edge').trim();

    const elements = transformDataToCytoscape(data);

    // Destroy existing instance if it exists
    if (cy) {
      cy.destroy();
    }

    cy = cytoscape({
      container: cyContainer,
      elements: elements,
      style: [
        {
          selector: 'node',
          style: {
            'label': 'data(label)',
            'background-color': nodeColor,
            'color': nodeTextColor,
            'text-valign': 'center',
            'text-halign': 'center',
            'width': 60,
            'height': 60,
            'font-size': '12px',
            'text-wrap': 'wrap',
            'text-max-width': '100px'
          }
        },
        {
          selector: 'node.threatactor',
          style: {
            'background-color': '#ef4444',
            'shape': 'triangle'
          }
        },
        {
          selector: 'node.malware',
          style: {
            'background-color': '#f59e0b',
            'shape': 'diamond'
          }
        },
        {
          selector: 'node.campaign',
          style: {
            'background-color': '#8b5cf6',
            'shape': 'rectangle'
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
            'font-size': '10px',
            'text-rotation': 'autorotate',
            'text-margin-y': -10
          }
        }
      ],
      layout: {
        name: elements.length > 1 ? 'cose' : 'grid',
        padding: 50,
        animate: true,
        animationDuration: 500
      }
    });

    cyContainer.style.backgroundColor = bgColor;

    // Add interactivity
    cy.on('tap', 'node', function(evt) {
      const node = evt.target;
      console.log('Node clicked:', node.data());
    });
  }

  // Initialize graph when component mounts or data changes
  onMount(() => {
    initGraph();
  });

  // Re-initialize graph when data changes
  $: if (data && cyContainer) {
    initGraph();
  }
</script>

<div bind:this={cyContainer} id="cy" style="width: 100%; height: 100%"></div>

<style>
  #cy {
    width: 100%;
    height: 100%;
  }
</style>
