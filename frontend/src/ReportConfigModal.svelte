<!-- ReportConfigModal.svelte -->
<script>
  import { createEventDispatcher } from 'svelte';
  import { labelFilter, startDate, endDate } from './stores.js';

  const dispatch = createEventDispatcher();

  // ============================================
  // PROPS
  // ============================================
  
  /** @type {boolean} Whether modal is visible */
  export let show = false;
  
  /** @type {Array} Available labels from current graph */
  export let availableLabels = [];
  
  /** @type {boolean} Whether timeline exists */
  export let hasTimeline = false;

  // ============================================
  // STATE
  // ============================================
  
  /** @type {'quick'|'custom'} Current mode */
  let mode = 'quick';
  
  /** @type {'executive'|'analyst'|'full'} Quick report type */
  let quickReportType = 'executive';
  
  // Custom report selections
  let includeSearchParams = true;
  let includeGraph = true;
  let includeTimeline = true;
  let includeNodes = true;
  let includeRelationships = true;
  let includeUserText = false;
  
  /** @type {Array<string>} Selected labels for node filtering */
  let selectedLabels = [];
  
  /** @type {string} User-defined text content */
  let userText = '';
  
  /** @type {number} Character limit for user text */
  const MAX_USER_TEXT_LENGTH = 5000;

  // ============================================
  // REACTIVE STATEMENTS
  // ============================================
  
  /**
   * Reset selectedLabels when modal opens or availableLabels change
   * Default: all labels selected (no filtering)
   */
  $: if (show && availableLabels.length > 0) {
    // Only reset if selectedLabels is empty or doesn't match availableLabels
    if (selectedLabels.length === 0) {
      selectedLabels = [...availableLabels];
    }
  }
    
  /**
   * Update selectedLabels when availableLabels changes
   * Keep only labels that still exist in the new availableLabels
   */
  $: if (availableLabels.length > 0) {
    // Filter out labels that no longer exist
    selectedLabels = selectedLabels.filter(label => availableLabels.includes(label));
    // If all were filtered out, select all available labels
    if (selectedLabels.length === 0) {
      selectedLabels = [...availableLabels];
    }
  }

  /**
   * Calculate remaining characters for user text
   */
  $: remainingChars = MAX_USER_TEXT_LENGTH - userText.length;
  
  /**
   * Disable timeline checkbox if no timeline exists
   */
  $: timelineDisabled = !hasTimeline;

  // ============================================
  // HANDLERS
  // ============================================
  
  /**
   * Switch between Quick and Custom modes
   */
  function setMode(newMode) {
    mode = newMode;
  }
  
  /**
   * Toggle label selection
   */
  function toggleLabel(label) {
    if (selectedLabels.includes(label)) {
      selectedLabels = selectedLabels.filter(l => l !== label);
    } else {
      selectedLabels = [...selectedLabels, label];
    }
  }
  
  /**
   * Select all labels
   */
  function selectAllLabels() {
    selectedLabels = [...availableLabels];
  }
  
  /**
   * Deselect all labels
   */
  function deselectAllLabels() {
    selectedLabels = [];
  }
  
  /**
   * Generate report with current configuration
   */
  function handleGenerate() {
    let config;
    
    if (mode === 'quick') {
      // Quick report configuration
      config = buildQuickReportConfig();
    } else {
      // Custom report configuration
      config = buildCustomReportConfig();
    }
    
    // Emit configuration to parent
    dispatch('generate', config);
    
    // Reset and close
    resetModal();
  }
  
  /**
   * Build configuration for quick reports
   */
  function buildQuickReportConfig() {
    const baseConfig = {
      mode: 'quick',
      type: quickReportType,
      includeMainNode: true,
      includeSearchParams: true,
      includeGraph: true,
      includeTimeline: hasTimeline,
      includeUserText: false,
      userText: '',
    };
    
    switch (quickReportType) {
      case 'executive':
        return {
          ...baseConfig,
          includeNodes: false,
          includeRelationships: false,
          selectedLabels: [],
        };
      
      case 'analyst':
        return {
          ...baseConfig,
          includeNodes: true,
          includeRelationships: false,
          selectedLabels: ['ThreatActor', 'Malware', 'Campaign'],
        };
      
      case 'full':
        return {
          ...baseConfig,
          includeNodes: true,
          includeRelationships: true,
          selectedLabels: [...availableLabels], // All labels
        };
      
      default:
        return baseConfig;
    }
  }
  
  /**
   * Build configuration for custom reports
   */
  function buildCustomReportConfig() {
    return {
      mode: 'custom',
      includeMainNode: true,
      includeSearchParams,
      includeGraph,
      includeTimeline: includeTimeline && hasTimeline,
      includeNodes,
      includeRelationships,
      includeUserText,
      userText: includeUserText ? userText.trim() : '',
      selectedLabels: includeNodes ? selectedLabels : [],
    };
  }
  
  /**
   * Close modal without generating
   */
  function handleCancel() {
    resetModal();
  }
  
  /**
   * Reset modal state
   */
  function resetModal() {
    show = false;
    mode = 'quick';
    quickReportType = 'executive';
    includeSearchParams = true;
    includeGraph = true;
    includeTimeline = true;
    includeNodes = true;
    includeRelationships = true;
    includeUserText = false;
    selectedLabels = [];
    userText = '';
  }
  
  /**
   * Get formatted search filters for display
   */
  function getSearchFiltersPreview() {
    const labelText = $labelFilter === 'all' ? 'All' : $labelFilter;
    const timeText = $startDate || $endDate 
      ? `from [${$startDate || 'any'}] to [${$endDate || 'any'}]`
      : 'any';
    
    return `Labels: [${labelText}] | Time: ${timeText}`;
  }
</script>

{#if show}
  <div class="modal-overlay" on:click={handleCancel}>
    <div class="modal-content" on:click|stopPropagation>
      
      <!-- Mode Selection Buttons -->
      <div class="mode-selector">
        <button
          class="mode-btn"
          class:active={mode === 'quick'}
          on:click={() => setMode('quick')}
        >
          Quick Report
        </button>
        <button
          class="mode-btn"
          class:active={mode === 'custom'}
          on:click={() => setMode('custom')}
        >
          Custom Report
        </button>
      </div>
      
      <!-- Quick Report Mode -->
      {#if mode === 'quick'}
        <div class="mode-content">
          <h3>Quick Report</h3>
          <p class="description">Choose a pre-configured report format for your audience.</p>
          
          <div class="report-types">
            <label class="report-type-option">
              <input
                type="radio"
                bind:group={quickReportType}
                value="executive"
              />
              <div class="option-content">
                <strong>Executive Summary</strong>
                <span class="option-description">
                  Main entity, search filters, graph visualization, and timeline
                </span>
              </div>
            </label>
            
            <label class="report-type-option">
              <input
                type="radio"
                bind:group={quickReportType}
                value="analyst"
              />
              <div class="option-content">
                <strong>Analyst Report</strong>
                <span class="option-description">
                  Executive summary with Details ThreatActor, Malware, and Campaign nodes
                </span>
              </div>
            </label>
            
            <label class="report-type-option">
              <input
                type="radio"
                bind:group={quickReportType}
                value="full"
              />
              <div class="option-content">
                <strong>Full Investigation</strong>
                <span class="option-description">
                  Complete report with all nodes and relationships
                </span>
              </div>
            </label>
          </div>
        </div>
      {/if}
      
      <!-- Custom Report Mode -->
      {#if mode === 'custom'}
        <div class="mode-content">
          <h3>Custom Report</h3>
          <p class="description">Select which elements to include in your report.</p>
          
          <div class="custom-options">
            
            <!-- Search Parameters -->
            <label class="option-item">
              <input type="checkbox" bind:checked={includeSearchParams} />
              <span>Search Parameters</span>
              {#if includeSearchParams}
                <div class="option-preview">
                  {getSearchFiltersPreview()}
                </div>
              {/if}
            </label>
            
            <!-- Graph Image -->
            <label class="option-item">
              <input type="checkbox" bind:checked={includeGraph} />
              <span>Graph Visualization</span>
            </label>
            
            <!-- Timeline -->
            <label class="option-item" class:disabled={timelineDisabled}>
              <input
                type="checkbox"
                bind:checked={includeTimeline}
                disabled={timelineDisabled}
              />
              <span>Timeline Analysis</span>
              {#if timelineDisabled}
                <span class="disabled-note">(No timeline available)</span>
              {/if}
            </label>
            
            <!-- Nodes with Label Filter -->
            <label class="option-item">
              <input type="checkbox" bind:checked={includeNodes} />
              <span>Connected Nodes</span>
            </label>
            
            {#if includeNodes}
              <div class="label-selector">
                <div class="label-selector-header">
                  <span class="label-title">Filter by labels:</span>
                  <div class="label-actions">
                    <button class="link-btn" on:click={selectAllLabels}>All</button>
                    <button class="link-btn" on:click={deselectAllLabels}>None</button>
                  </div>
                </div>
                
                {#if availableLabels.length > 0}
                  <div class="label-list">
                    {#each availableLabels as label}
                      <label class="label-checkbox">
                        <input
                          type="checkbox"
                          checked={selectedLabels.includes(label)}
                          on:change={() => toggleLabel(label)}
                        />
                        <span class="label-name">{label}</span>
                      </label>
                    {/each}
                  </div>
                {:else}
                  <p class="no-labels">No labels available in current graph</p>
                {/if}
              </div>
            {/if}
            
            <!-- Relationships -->
            <label class="option-item">
              <input type="checkbox" bind:checked={includeRelationships} />
              <span>Relationships</span>
            </label>
            
            <!-- User Text -->
            <label class="option-item">
              <input type="checkbox" bind:checked={includeUserText} />
              <span>User-Defined Text</span>
            </label>
            
            {#if includeUserText}
              <div class="user-text-editor">
                <div class="editor-header">
                  <span class="editor-title">Additional Notes</span>
                  <span class="char-counter" class:warning={remainingChars < 500}>
                    {remainingChars} characters remaining
                  </span>
                </div>
                <textarea
                  bind:value={userText}
                  maxlength={MAX_USER_TEXT_LENGTH}
                  placeholder="Add notes here..."
                  rows="6"
                ></textarea>
              </div>
            {/if}
            
          </div>
        </div>
      {/if}
      
      <!-- Action Buttons -->
      <div class="modal-actions">
        <button class="btn-cancel" on:click={handleCancel}>
          Cancel
        </button>
        <button class="btn-generate" on:click={handleGenerate}>
          Generate Report
        </button>
      </div>
      
    </div>
  </div>
{/if}

<style>
  .modal-overlay {
    position: fixed;
    top: 0;
    left: 0;
    right: 0;
    bottom: 0;
    background: rgba(0, 0, 0, 0.7);
    display: flex;
    justify-content: center;
    align-items: center;
    z-index: 1000;
    padding: 1rem;
  }

  .modal-content {
    background: var(--color-background-secondary);
    border: 1px solid var(--color-border);
    border-radius: 0.5rem;
    width: 100%;
    max-width: 600px;
    max-height: 90vh;
    overflow-y: auto;
    box-shadow: 0 10px 40px rgba(0, 0, 0, 0.22);
  }

  /* Mode Selector */
  .mode-selector {
    display: flex;
    border-bottom: 1px solid var(--color-border);
    background: var(--color-bg);
  }

  .mode-btn {
    flex: 1;
    padding: 1rem;
    background: transparent;
    border: none;
    color: var(--color-muted);
    font-size: 0.95rem;
    font-weight: 600;
    cursor: pointer;
    transition: all 0.2s;
    border-bottom: 3px solid transparent;
  }

  .mode-btn:hover {
    color: var(--color-text);
    background: rgba(255, 255, 255, 0.05);
  }

  .mode-btn.active {
    color: var(--color-accent);
    border-bottom-color: var(--color-accent);
    background: var(--color-bg-elevated);
  }

  /* Mode Content */
  .mode-content {
    padding: 1.5rem;
  }

  .mode-content h3 {
    margin: 0 0 0.5rem 0;
    font-size: 1.25rem;
    color: var(--color-text);
  }

  .description {
    margin: 0 0 1.5rem 0;
    color: var(--color-muted);
    font-size: 0.9rem;
  }

  /* Quick Report Options */
  .report-types {
    display: flex;
    flex-direction: column;
    gap: 0.75rem;
  }

  .report-type-option {
    display: flex;
    gap: 0.75rem;
    padding: 1rem;
    border: 2px solid var(--color-border);
    border-radius: 0.375rem;
    cursor: pointer;
    transition: all 0.2s;
  }

  .report-type-option:hover {
    border-color: var(--color-accent);
    background: rgba(255, 255, 255, 0.02);
  }

  .report-type-option input[type="radio"] {
    margin-top: 0.25rem;
    cursor: pointer;
  }

  .option-content {
    display: flex;
    flex-direction: column;
    gap: 0.25rem;
    flex: 1;
  }

  .option-content strong {
    color: var(--color-text);
    font-size: 1rem;
  }

  .option-description {
    color: var(--color-muted);
    font-size: 0.85rem;
    line-height: 1.4;
  }

  /* Custom Report Options */
  .custom-options {
    display: flex;
    flex-direction: column;
    gap: 1rem;
  }

  .option-item {
    display: flex;
    flex-direction: row;
    padding: 0.75rem;
    border: 1px solid var(--color-border);
    border-radius: 0.375rem;
    cursor: pointer;
    transition: all 0.2s;
  }


  .option-item:hover:not(.disabled) {
    background: rgba(255, 255, 255, 0.02);
  }

  .option-item.disabled {
    opacity: 0.5;
    cursor: not-allowed;
  }

  .option-item > input[type="checkbox"] {
    margin-right: 0.5rem;
    cursor: pointer;
    flex-shrink: 0; 
  }

  .option-item > span {
    color: var(--color-text);
    font-weight: 500;
  }

  .disabled-note {
    color: var(--color-muted);
    font-size: 0.8rem;
    font-style: italic;
    margin-left: 0.5rem;
  }

  .option-preview {
    margin-left: 1.5rem;
    padding: 0.5rem;
    background: var(--color-bg);
    border-radius: 0.25rem;
    font-size: 0.85rem;
    color: var(--color-muted);
    font-family: monospace;
  }

  /* Label Selector */
  .label-selector {
    margin-left: rem;
    padding: 0.75rem;
    background: var(--color-bg);
    border-radius: 0.25rem;
    border: 1px solid var(--color-border);
  }

  .label-selector-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 0.75rem;
  }

  .label-title {
    font-size: 0.9rem;
    color: var(--color-muted);
    font-weight: 600;
  }

  .label-actions {
    display: flex;
    gap: 0.5rem;
  }

  .link-btn {
    background: none;
    border: none;
    color: var(--color-accent);
    font-size: 0.85rem;
    cursor: pointer;
    padding: 0.25rem 0.5rem;
    border-radius: 0.25rem;
    transition: all 0.2s;
  }

  .link-btn:hover {
    background: rgba(255, 255, 255, 0.05);
  }

  .label-list {
    display: flex;
    flex-wrap: wrap;
    gap: 0.5rem;
  }

  .label-checkbox {
    display: flex;
    align-items: center;
    gap: 0.375rem;
    padding: 0.375rem 0.75rem;
    background: var(--color-bg-elevated);
    border: 1px solid var(--color-border);
    border-radius: 0.25rem;
    cursor: pointer;
    transition: all 0.2s;
    font-size: 0.85rem;
  }

  .label-checkbox:hover {
    border-color: var(--color-accent);
    background: rgba(255, 255, 255, 0.02);
  }

  .label-checkbox input[type="checkbox"] {
    cursor: pointer;
  }

  .label-name {
    color: var(--color-text);
    font-weight: 500;
  }

  .no-labels {
    color: var(--color-muted);
    font-size: 0.85rem;
    font-style: italic;
    margin: 0;
  }

  /* User Text Editor */
  .user-text-editor {
    padding: 0.75rem;
    background: var(--color-bg);
    border-radius: 0.25rem;
    border: 1px solid var(--color-border);
  }

  .editor-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 0.5rem;
  }

  .editor-title {
    font-size: 0.9rem;
    color: var(--color-muted);
    font-weight: 600;
  }

  .char-counter {
    font-size: 0.8rem;
    color: var(--color-muted);
  }

  .char-counter.warning {
    color: #f59e0b;
    font-weight: 600;
  }

  .user-text-editor textarea {
    width: 100%;
    background: var(--color-bg-elevated);
    border: 1px solid var(--color-border);
    border-radius: 0.25rem;
    color: var(--color-text);
    font-size: 0.9rem;
    font-family: inherit;
    line-height: 1.5;
    resize: vertical;
    min-height: 120px;
  }

  .user-text-editor textarea:focus {
    outline: none;
    border-color: var(--color-accent);
  }

  .user-text-editor textarea::placeholder {
    color: var(--color-muted);
  }

  /* Modal Actions */
  .modal-actions {
    display: flex;
    justify-content: flex-end;
    gap: 0.75rem;
    padding: 1rem 1.5rem;
    border-top: 1px solid var(--color-border);
    background: var(--color-bg);
  }

  .modal-actions button {
    padding: 0.625rem 1.5rem;
    border-radius: 0.375rem;
    font-size: 0.95rem;
    font-weight: 600;
    cursor: pointer;
    transition: all 0.2s;
    border: none;
  }

  .btn-cancel {
    background: transparent;
    color: var(--color-muted);
    border: 1px solid var(--color-border);
  }

  .btn-cancel:hover {
    background: rgba(255, 255, 255, 0.05);
    color: var(--color-text);
  }

  .btn-generate {
    background: var(--color-accent);
    color: white;
  }

  .btn-generate:hover {
    background: var(--color-accent-hover);
    transform: translateY(-1px);
  }

  /* Scrollbar Styling */
  .modal-content::-webkit-scrollbar {
    width: 8px;
  }

  .modal-content::-webkit-scrollbar-track {
    background: var(--color-bg);
  }

  .modal-content::-webkit-scrollbar-thumb {
    background: var(--color-border);
    border-radius: 4px;
  }

  .modal-content::-webkit-scrollbar-thumb:hover {
    background: var(--color-muted);
  }
</style>
