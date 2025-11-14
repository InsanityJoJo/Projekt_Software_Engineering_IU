<!-- TimelineAnalysis.svelte -->
<script>
  import { onMount, onDestroy, createEventDispatcher } from 'svelte';
  import { Chart, registerables } from 'chart.js';
  import 'chartjs-adapter-date-fns';  // ← CRITICAL: Required for time scale
  
  // Register Chart.js components
  Chart.register(...registerables);
  
  const dispatch = createEventDispatcher();
  
  // ============================================
  // CHART.JS CUSTOM PLUGIN - DATE MARKERS
  // ============================================
  
  /**
   * Custom Chart.js plugin to draw date markers (circles) on timeline bars
   * Shows intermediate dates like published_date, detection_date, etc.
   */
  const dateMarkersPlugin = {
    id: 'dateMarkers',
    afterDatasetsDraw(chart) {
      const ctx = chart.ctx;
      const meta = chart.getDatasetMeta(0);
      
      if (!meta || !timelineData) return;
      
      // For each bar in the chart
      meta.data.forEach((bar, index) => {
        const data = timelineData[index];
        if (!data || !data.markers || data.markers.length === 0) return;
        
        const yAxis = chart.scales.y;
        const xAxis = chart.scales.x;
        const barY = yAxis.getPixelForValue(index);
        
        // Draw markers for intermediate dates
        data.markers.forEach(marker => {
          const markerX = xAxis.getPixelForValue(marker.date);
          
          // Draw circle marker
          ctx.save();
          ctx.fillStyle = hexToRgba(data.color, 0.9);
          ctx.strokeStyle = '#ffffff';
          ctx.lineWidth = 2;
          
          ctx.beginPath();
          ctx.arc(markerX, barY, 6, 0, 2 * Math.PI);
          ctx.fill();
          ctx.stroke();
          ctx.restore();
        });
      });
    }
  };
  
  // Register the custom plugin
  Chart.register(dateMarkersPlugin);
  
  // ============================================
  // DEBUG CONFIGURATION
  // ============================================
  const DEBUG = true;
  
  function debugLog(...args) {
    if (DEBUG) {
      console.log(...args);
    }
  }
  
  // ============================================
  // PROPS
  // ============================================
  
  /**
   * @type {Array} All visible nodes from Cytoscape
   */
  export let nodes = [];
  
  /**
   * @type {string|null} Currently highlighted node ID
   */
  export let highlightedNodeId = null;
  
  // ============================================
  // STATE
  // ============================================
  
  let chartCanvas;
  let chart = null;
  let timelineData = [];
  
  // Known date field names from data model
  const DATE_FIELDS = [
    'first_seen',
    'last_seen',
    'published_date',
    'start_date',
    'end_date',
    'detection_date',
    'resolved_date'
  ];
  
  // ============================================
  // DATE EXTRACTION & PROCESSING
  // ============================================
  
  /**
   * Parse date string to Date object
   * Expects format: "YYYY-MM-DD"
   * 
   * @param {string} dateStr - Date string
   * @returns {Date|null} Parsed date or null if invalid
   */
  function parseDate(dateStr) {
    if (!dateStr) return null;
    
    try {
      const date = new Date(dateStr);
      if (!isNaN(date.getTime())) {
        return date;
      }
    } catch (e) {
      debugLog('Failed to parse date:', dateStr, e);
    }
    
    return null;
  }
  
  /**
   * Extract all date fields from node properties
   * 
   * @param {Object} properties - Node properties
   * @returns {Object} Object with date field names as keys and Date objects as values
   */
  function extractDateFields(properties) {
    const dates = {};
    
    for (const field of DATE_FIELDS) {
      if (properties[field]) {
        const date = parseDate(properties[field]);
        if (date) {
          dates[field] = date;
        }
      }
    }
    
    return dates;
  }
  
  /**
   * Get earliest and latest dates from date fields
   * 
   * @param {Object} dateFields - Object with Date values
   * @returns {Object} { startDate: Date, endDate: Date, markers: Array }
   */
  function getDateRange(dateFields) {
    const dateValues = Object.values(dateFields);
    
    if (dateValues.length === 0) {
      return null;
    }
    
    // Sort dates
    const sortedDates = dateValues.sort((a, b) => a - b);
    
    // Get start and end
    const startDate = sortedDates[0];
    const endDate = sortedDates[sortedDates.length - 1];
    
    // Get all intermediate dates as markers
    const markers = Object.entries(dateFields)
      //.filter(([field]) => field !== 'first_seen' && field !== 'last_seen')
      .map(([field, date]) => ({
        field,
        date
      }));
    
    return {
      startDate,
      endDate,
      markers
    };
  }
  
  /**
   * Process nodes and extract timeline data
   * 
   * @param {Array} nodes - Cytoscape nodes
   * @returns {Array} Timeline data for Chart.js
   */
  function processNodesForTimeline(nodes) {
    const data = [];
    
    for (const node of nodes) {
      const nodeData = node.data;
      const properties = nodeData.properties || {};
      
      // Extract date fields
      const dateFields = extractDateFields(properties);
      
      // Skip nodes without dates
      if (Object.keys(dateFields).length === 0) {
        debugLog(`Node ${nodeData.label} has no date fields, skipping`);
        continue;
      }
      
      // Get date range
      const range = getDateRange(dateFields);
      
      if (range) {
        data.push({
          nodeId: nodeData.id,
          nodeName: nodeData.label,
          nodeType: nodeData.type,
          startDate: range.startDate,
          endDate: range.endDate,
          markers: range.markers,
          dateFields: dateFields,
          color: nodeData.color
        });
      }
    }
    
    // Sort by start date (chronological)
    data.sort((a, b) => a.startDate - b.startDate);
    
    debugLog(`Processed ${data.length} nodes with temporal data`);
    return data;
  }
  
  // ============================================
  // COLOR UTILITIES
  // ============================================
  
  /**
   * Convert hex color to rgba with opacity
   * 
   * @param {string} hex - Hex color code
   * @param {number} opacity - Opacity (0-1)
   * @returns {string} rgba color string
   */
  function hexToRgba(hex, opacity = 0.6) {
    // Remove # if present
    hex = hex.replace('#', '');
    
    // Parse hex to RGB
    const r = parseInt(hex.substring(0, 2), 16);
    const g = parseInt(hex.substring(2, 4), 16);
    const b = parseInt(hex.substring(4, 6), 16);
    
    return `rgba(${r}, ${g}, ${b}, ${opacity})`;
  }
  
  /**
   * Get muted color for timeline bar
   * 
   * @param {string} color - Original hex color
   * @returns {string} Muted rgba color
   */
  function getMutedColor(color) {
    return hexToRgba(color, 0.6);
  }
  
  /**
   * Get highlight color for timeline bar
   * 
   * @param {string} color - Original hex color
   * @returns {string} Highlighted rgba color
   */
  function getHighlightColor(color) {
    return hexToRgba(color, 0.9);
  }
  
  /**
   * Calculate min and max dates for X-axis based on timeline data
   * Adds 2-month padding on each side for better visualization
   * 
   * @param {Array} data - Timeline data array
   * @returns {Object} { min: Date, max: Date }
   */
  function calculateDateRange(data) {
    if (!data || data.length === 0) {
      return null;
    }
    
    // Find earliest and latest dates across all entities
    let minDate = null;
    let maxDate = null;
    
    for (const item of data) {
      if (!minDate || item.startDate < minDate) {
        minDate = item.startDate;
      }
      if (!maxDate || item.endDate > maxDate) {
        maxDate = item.endDate;
      }
    }
    
    if (!minDate || !maxDate) {
      return null;
    }
    
    // Add 2-month padding
    const paddedMin = new Date(minDate);
    paddedMin.setMonth(paddedMin.getMonth() - 2);
    
    const paddedMax = new Date(maxDate);
    paddedMax.setMonth(paddedMax.getMonth() + 2);
    
    debugLog(`Date range: ${formatDate(paddedMin)} to ${formatDate(paddedMax)}`);
    
    return {
      min: paddedMin,
      max: paddedMax
    };
  }
  
  // ============================================
  // CHART CREATION
  // ============================================
  
  /**
   * Create Chart.js timeline
   */
  function createTimeline() {
    if (!chartCanvas || timelineData.length === 0) {
      debugLog('Cannot create timeline: missing canvas or data');
      return;
    }
    
    // Destroy existing chart
    if (chart) {
      chart.destroy();
    }
    
    debugLog('Creating timeline chart with', timelineData.length, 'nodes');
    
    // Calculate date range for X-axis
    const dateRange = calculateDateRange(timelineData);
    if (!dateRange) {
      debugLog('Cannot calculate date range');
      return;
    }
    
    // Prepare data for Chart.js
    const labels = timelineData.map(d => d.nodeName);
    const datasets = [{
      label: 'Activity Period',
      data: timelineData.map(d => [d.startDate, d.endDate]),
      backgroundColor: timelineData.map((d, i) => {
        // Highlight if this node is selected
        if (highlightedNodeId && d.nodeId === highlightedNodeId) {
          return getHighlightColor(d.color);
        }
        return getMutedColor(d.color);
      }),
      borderColor: timelineData.map(d => d.color),
      borderWidth: 1,
      borderSkipped: false
    }];
    
    // Create chart
    chart = new Chart(chartCanvas, {
      type: 'bar',
      data: {
        labels: labels,
        datasets: datasets
      },
      options: {
        indexAxis: 'y', // Horizontal bars
        responsive: true,
        maintainAspectRatio: false,
        plugins: {
          title: {
            display: true,
            text: 'Temporal Analysis - Entity Activity Timeline',
            font: {
              size: 16,
              weight: 'bold'
            }
          },
          legend: {
            display: false
          },
          tooltip: {
            callbacks: {
              title: (context) => {
                const index = context[0].dataIndex;
                return timelineData[index].nodeName;
              },
              label: (context) => {
                const index = context.dataIndex;
                const data = timelineData[index];
                
                const lines = [
                  `Type: ${data.nodeType}`,
                  `Period: ${formatDate(data.startDate)} → ${formatDate(data.endDate)}`,
                  ''
                ];
                
                // Add all date fields
                for (const [field, date] of Object.entries(data.dateFields)) {
                  lines.push(`${formatFieldName(field)}: ${formatDate(date)}`);
                }
                
                return lines;
              }
            }
          }
        },
        scales: {
          x: {
            type: 'time',
            min: dateRange.min,
            max: dateRange.max,
            time: {
              unit: 'month',
              displayFormats: {
                month: 'MMM yyyy'
              }
            },
            title: {
              display: true,
              text: 'Timeline'
            }
          },
          y: {
            title: {
              display: true,
              text: 'Entities'
            }
          }
        },
        onClick: handleChartClick
      }
    });
    
    debugLog('Timeline chart created successfully');
  }
  
  /**
   * Handle click on chart bar
   * 
   * @param {Event} event - Click event
   * @param {Array} elements - Clicked chart elements
   */
  function handleChartClick(event, elements) {
    if (elements.length > 0) {
      const index = elements[0].index;
      const clickedNode = timelineData[index];
      
      debugLog('Timeline bar clicked:', clickedNode.nodeName);
      
      // Emit event to parent
      dispatch('nodeSelected', {
        nodeId: clickedNode.nodeId,
        nodeName: clickedNode.nodeName
      });
    }
  }
  
  // ============================================
  // UTILITY FUNCTIONS
  // ============================================
  
  /**
   * Format date for display
   * 
   * @param {Date} date - Date object
   * @returns {string} Formatted date string
   */
  function formatDate(date) {
    return date.toISOString().split('T')[0]; // YYYY-MM-DD
  }
  
  /**
   * Format field name for display
   * 
   * @param {string} field - Field name (snake_case)
   * @returns {string} Formatted field name
   */
  function formatFieldName(field) {
    return field
      .split('_')
      .map(word => word.charAt(0).toUpperCase() + word.slice(1))
      .join(' ');
  }
  
  /**
   * Export timeline as image for reports
   * 
   * @returns {string} Base64 PNG image
   */
  export function exportAsImage() {
    if (chart) {
      return chart.toBase64Image();
    }
    return null;
  }
  
  // ============================================
  // LIFECYCLE & REACTIVITY
  // ============================================
  
  /**
   * Process nodes and create timeline when nodes change
   */
  $: {
    if (nodes && nodes.length > 0) {
      debugLog('Processing nodes for timeline');
      timelineData = processNodesForTimeline(nodes);
      
      if (timelineData.length > 0) {
        // Wait for next tick to ensure canvas is ready
        setTimeout(() => createTimeline(), 0);
      } else {
        debugLog('No nodes with temporal data found');
      }
    }
  }
  
  /**
   * Update chart when highlighted node changes
   */
  $: {
    if (chart && highlightedNodeId !== null) {
      debugLog('Updating timeline highlight for:', highlightedNodeId);
      
      // Update bar colors
      chart.data.datasets[0].backgroundColor = timelineData.map((d) => {
        if (d.nodeId === highlightedNodeId) {
          return getHighlightColor(d.color);
        }
        return getMutedColor(d.color);
      });
      
      chart.update('none'); // Update without animation for responsiveness
    }
  }
  
  onMount(() => {
    debugLog('TimelineAnalysis mounted');
  });
  
  onDestroy(() => {
    debugLog('TimelineAnalysis destroyed');
    if (chart) {
      chart.destroy();
    }
  });
</script>

<div class="timeline-container">
  {#if timelineData.length > 0}
    <div class="timeline-canvas-wrapper">
      <canvas bind:this={chartCanvas}></canvas>
    </div>
    
    <div class="timeline-info">
      <p>
        <strong>{timelineData.length}</strong> entities with temporal data
        | Click a bar to highlight in graph
      </p>
    </div>
  {:else}
    <div class="timeline-empty">
      <p>No temporal data available for visible nodes</p>
      <p class="hint">Nodes need date properties like first_seen, last_seen, published_date, etc.</p>
    </div>
  {/if}
</div>

<style>
  /* 
   * Timeline container matches graph-container styling from app.css
   * for consistent width and appearance across different viewports
   */
  .timeline-container {
    width: 100%;
    background: var(--color-surface);
    border: 1px solid var(--color-border);
    border-radius: 0.5rem;
    margin-top: 2rem;
    /* Match graph-container properties */
    display: flex;
    flex-direction: column;
  }
  
  .timeline-canvas-wrapper {
    width: 100%;
    height: 600px;
    overflow-y: auto;
    overflow-x: hidden;
    /* padding: 1.5rem 1.5rem 0.5rem 1.5rem;
    /* Ensure canvas fills container properly */
    position: relative;
  }
  
  .timeline-canvas-wrapper canvas {
    max-width: 100%;
    /* Prevent canvas from being too small */
    min-width: 100%;
  }
  
  .timeline-info {
    margin-top: 1rem;
    padding-top: 1rem;
    border-top: 1px solid var(--color-border);
    text-align: center;
    color: var(--color-muted);
    font-size: 0.9rem;
  }
  
  .timeline-empty {
    text-align: center;
    padding: 3rem 1rem;
    color: var(--color-muted);
  }
  
  .timeline-empty p {
    margin: 0.5rem 0;
  }
  
  .timeline-empty .hint {
    font-size: 0.85rem;
    font-style: italic;
  }
  
  /* Scrollbar styling for timeline */
  .timeline-canvas-wrapper::-webkit-scrollbar {
    width: 8px;
  }
  
  .timeline-canvas-wrapper::-webkit-scrollbar-track {
    background: rgba(0, 0, 0, 0.1);
    border-radius: 4px;
  }
  
  .timeline-canvas-wrapper::-webkit-scrollbar-thumb {
    background: var(--color-border);
    border-radius: 4px;
  }
  
  .timeline-canvas-wrapper::-webkit-scrollbar-thumb:hover {
    background: var(--color-accent);
  }
</style>
