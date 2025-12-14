<script>
  import { contextDepth, labelFilter, startDate, endDate } from './stores.js';

  // Props from parent (App.svelte controls visibility)
  export let show = false;
  export let onClose = () => {};

  // Label options from constants
  const ALLOWED_LABELS = [
    "all",  // Default option
    "AttackPattern",
    "Campaign",
    "Identity",
    "Incident",
    "Indicator",
    "Malware",
    "Observable",
    "File",
    "DomainName",
    "URL",
    "EmailAddr",
    "IPv4Address",
    "Organization",
    "Report",
    "ThreatActor",
    "Tool",
    "Vulnerability",
  ];

  // Update when slider changes
  function handleDepthChange(event) {
    const value = parseInt(event.target.value);
    contextDepth.set(value);
  }

  function handleLabelChange(event) {
    labelFilter.set(event.target.value);
  }
  
  // Handle HTML5 date input changes
  function handleStartDateChange(event) {
    startDate.set(event.target.value || null);
  }
  
  function handleEndDateChange(event) {
    endDate.set(event.target.value || null);
  }
  
  function clearTimeFilter() {
    startDate.set(null);
    endDate.set(null);
  }
</script>

<!-- Settings Menu Panel -->
{#if show}
  <div class="settings-menu">
    <div class="settings-header">
      <h3>Search Settings</h3>
      <button on:click={onClose}>×</button>
    </div>
    
    <!-- Context Depth Setting -->
    <div class="setting-item">
      <label for="context-depth">Context Depth (Hops)</label>
      <input
        type="range"
        id="context-depth"
        min="0"
        max="3"
        step="1"
        value={$contextDepth}
        on:input={handleDepthChange}
      />
      <div class="slider-labels">
        <span class:active={$contextDepth === 0}>0</span>
        <span class:active={$contextDepth === 1}>1</span>
        <span class:active={$contextDepth === 2}>2</span>
        <span class:active={$contextDepth === 3}>3</span>
      </div>
      <div class="setting-description">
        {#if $contextDepth === 0}
          Show only the selected node
        {:else if $contextDepth === 1}
          Show direct connections (1 hop)
        {:else if $contextDepth === 2}
          Show connections up to 2 hops away
        {:else}
          Show connections up to 3 hops away (maximum)
        {/if}
      </div>
    </div>
    
    <!-- Label Filter -->
    <div class="setting-item">
      <label for="label-filter">Node Type Filter</label>
      <select
        id="label-filter"
        value={$labelFilter}
        on:change={handleLabelChange}
      >
        {#each ALLOWED_LABELS as label}
          <option value={label === "all" ? "all" : label}>
            {label === "all" ? "All Types" : label}
          </option>
        {/each}
      </select>
      <div class="setting-description">
        {#if $labelFilter === "all"}
          Showing all node types
        {:else}
          Showing only {$labelFilter} nodes
        {/if}
      </div>
    </div>
    
    <!-- Time Range Filter with HTML5 Date Inputs -->
    <div class="setting-item">
      <label>Time Range Filter</label>
      
      <div class="date-inputs">
        <div class="date-input-group">
          <label for="start-date">From:</label>
          <input
            type="date"
            id="start-date"
            value={$startDate || ""}
            on:change={handleStartDateChange}
          />
        </div>
        
        <div class="date-input-group">
          <label for="end-date">To:</label>
          <input
            type="date"
            id="end-date"
            value={$endDate || ""}
            on:change={handleEndDateChange}
          />
        </div>
      </div>
      
      {#if $startDate && $endDate}
        <button class="clear-filter" on:click={clearTimeFilter}>
          Clear Time Filter
        </button>
      {/if}
      
      <div class="setting-description">
        {#if $startDate && $endDate}
          Showing nodes active between {$startDate} and {$endDate}
        {:else}
          No time filter active (showing all dates)
        {/if}
      </div>
    </div>
  </div>
{/if}

<style>
  /* Component-specific positioning relative to parent button */  

  .settings-menu {
    position: absolute;
    top: 100%;
    right: 0;
    margin-top: 8px;
    background: var(--color-background-secondary);
    border: 1px solid var(--color-border);
    border-radius: 8px;
    padding: 16px;
    box-shadow: 0 2px 8px rgba(0, 0, 0, 0.22);
    min-width: 300px;
    max-width: 500px;
    z-index: 1000;
  }
  

  .settings-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 16px;
    padding-bottom: 12px;
    border-bottom: 1px solid var(--color-border);
  }
  
  .settings-header h3 {
    margin: 0;
    font-size: 18px;
    font-weight: 600;
    color: var(--color-text);
  }
  
  .settings-header button {
    background: none;
    border: none;
    font-size: 24px;
    cursor: pointer;
    color: var(--color-text);
    
    padding: 0 4px;
    line-height: 1;
    transition: color 0.2s ease;

    width: 30px;
    height: 30px;
    display: flex;
    align-items: center;
    justify-content: center;
  }
  
  .settings-header button:hover {
    color: var(--color-error);
  }
  
  .setting-item {
    margin-bottom: 24px;
  }
  
  .setting-item:last-child {
    margin-bottom: 0;
  }
  
  .setting-item > label {
    display: block;
    margin-bottom: 8px;
    font-weight: 500;
    color: #334155;
    font-size: 14px;
  }
  
  select {
    width: 100%;
    padding: 8px;
    border: 1px solid #cbd5e1;
    border-radius: 4px;
    background: white;
    font-size: 14px;
    cursor: pointer;
    color: #1e293b;
    transition: border-color 0.2s;
  }
  
  select option {
  color: #1e293b;
  background: white;
  }

  select:hover {
    border-color: #94a3b8;
  }
  
  select:focus {
    outline: none;
    border-color: #3b82f6;
    box-shadow: 0 0 0 3px rgba(59, 130, 246, 0.1);
  }
  
  .date-inputs {
    display: flex;
    flex-direction: column;
    gap: 12px;
  }
  
  .date-input-group {
    display: flex;
    flex-direction: column;
    gap: 4px;
  }
  
  .date-input-group label {
    font-size: 13px;
    font-weight: 500;
    border-radius: 4px;
    color: #131212;
    background-color: #cbd5e1;

  }
  
  input[type="date"] {
    width: 100%;
    padding: 0px;
    border: 1px solid #cbd5e1;
    color: #131212;
    background-color: #cbd5e1;	  
    border-radius: 4px;
    font-size: 16px;
    font-family: inherit;
    transition: border-color 0.2s;
  }
  
  input[type="date"]:hover {
    border-color: #94a3b8;
  }
  
  input[type="date"]:focus {
    outline: none;
    border-color: #3b82f6;
    box-shadow: 0 0 0 3px rgba(59, 130, 246, 0.1);
  }
  
  input[type="range"] {
    width: 100%;
    height: 6px;
    border-radius: 3px;
    background: #e2e8f0;
    outline: none;
    -webkit-appearance: none;
  }
  
  input[type="range"]::-webkit-slider-thumb {
    -webkit-appearance: none;
    appearance: none;
    width: 18px;
    height: 18px;
    border-radius: 50%;
    background: var(--color-border);
    cursor: pointer;
    transition: background 0.2s;
  }
  
  input[type="range"]::-webkit-slider-thumb:hover {
    background: #2563eb;
  }
  
  input[type="range"]::-moz-range-thumb {
    width: 18px;
    height: 18px;
    border-radius: 50%;
    background: var(--color-border);
    cursor: pointer;
    border: none;
    transition: background 0.2s;
  }
  
  input[type="range"]::-moz-range-thumb:hover {
    background: #2563eb;
  }
  
  .slider-labels {
    display: flex;
    justify-content: space-between;
    margin-top: 4px;
  }
  
  .slider-labels span {
    font-size: 12px;
    color: #94a3b8;
    transition: all 0.2s;
  }
  
  .slider-labels span.active {
    color: var(--color-border);
    font-weight: 600;
  }
  
  .clear-filter {
    margin-top: 8px;
    padding: 6px 12px;
    background: #ef4444;
    color: white;
    border: none;
    border-radius: 4px;
    cursor: pointer;
    font-size: 13px;
    width: 100%;
    font-weight: 500;
    transition: background 0.2s;
  }
  
  .clear-filter:hover {
    background: #dc2626;
  }
  
  .clear-filter:active {
    background: #b91c1c;
  }
  
  .setting-description {
    margin-top: 8px;
    font-size: 13px;
    color: #64748b;
    font-style: italic;
    line-height: 1.4;
  }
</style>
