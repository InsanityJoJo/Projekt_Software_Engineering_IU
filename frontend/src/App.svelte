<script>
	import {
		Search,
		Settings,
		FileText,
		ChartNoAxesCombined,
		Copyright,
		X,
	} from "lucide-svelte";
	import GraphView from "./GraphView.svelte";
	import SettingsMenu from "./SettingsMenu.svelte";
	import TimelineAnalysis from "./TimelineAnalysis.svelte";
	import { getAutocompleteSuggestions, getNodeByName } from "./api.js";
	import { contextDepth, labelFilter, startDate, endDate } from "./stores.js";
	
	// ============================================
	// DEBUG CONFIGURATION
	// ============================================
	const DEBUG = true;
	
	/**
	 * Debug logging wrapper
	 * Only logs when DEBUG is enabled
	 * 
	 * @param {...any} args - Arguments to log
	 */
	function debugLog(...args) {
		if (DEBUG) {
			console.log(...args);
		}
	}
	
	// ============================================
	// STATE MANAGEMENT
	// ============================================
	
	/** @type {string} Search query input */
	let query = "";
	
	/** @type {boolean} Whether to show the graph view */
	let showGraph = false;
	
	/** @type {Array} Autocomplete suggestions */
	let suggestions = [];
	
	/** @type {boolean} Whether to show suggestions dropdown */
	let showSuggestions = false;
	
	/** @type {boolean} Loading state for API calls */
	let isLoading = false;
	
	/** @type {string|null} Error message */
	let error = null;
	
	/** @type {Object|null} Selected node data from API */
	let selectedNode = null;
	
	/** @type {number|null} Debounce timer for autocomplete */
	let debounceTimer = null;
	
	/** @type {boolean} Whether settings menu is visible */
	let showSettings = false;
	
	/** @type {GraphView} Reference to GraphView component for report generation */
	let graphViewComponent;
	
	/** @type {TimelineAnalysis} Reference to TimelineAnalysis component */
	let timelineComponent;
	
	/** @type {boolean} Whether timeline analysis is visible */
	let showTimeline = false;
	
	/** @type {string|null} Currently highlighted node ID for timeline sync */
	let highlightedNodeId = null;
	
	/** @type {Array} Visible nodes to pass to timeline */
	let visibleNodes = [];

	// ============================================
	// AUTOCOMPLETE & SEARCH HANDLERS
	// ============================================

	/**
	 * Handle input changes and trigger autocomplete
	 * 
	 * Debounces requests to avoid excessive API calls.
	 * Only triggers autocomplete when query is 3+ characters.
	 * Waits 300ms after last keystroke before making request.
	 */
	function handleInputChange() {
		// Clear previous debounce timer
		if (debounceTimer) {
			clearTimeout(debounceTimer);
		}

		// Reset state if query is too short
		if (query.length < 3) {
			suggestions = [];
			showSuggestions = false;
			return;
		}

		// Set new timer - wait 300ms before making request
		debounceTimer = setTimeout(async () => {
			try {
				isLoading = true;
				error = null;

				// Get filter values from stores
				const currentLabel = $labelFilter === "all" ? null : $labelFilter;
				const currentStartDate = $startDate;
				const currentEndDate = $endDate;

				const result = await getAutocompleteSuggestions(query, currentLabel, currentStartDate, currentEndDate);

				if (result.success) {
					suggestions = result.suggestions || [];
					showSuggestions = suggestions.length > 0;
				} else {
					error = result.error || "Failed to fetch suggestions";
					suggestions = [];
					showSuggestions = false;
				}
			} catch (err) {
				console.error("Autocomplete error:", err);
				error = err.message;
				suggestions = [];
				showSuggestions = false;
			} finally {
				isLoading = false;
			}
		}, 300);
	}

	/**
	 * Handle suggestion selection from autocomplete dropdown
	 * 
	 * Fetches full node details from API and displays graph.
	 * 
	 * @param {Object} suggestion - Selected suggestion object
	 * @param {string} suggestion.name - Entity name
	 * @param {string} suggestion.label - Entity type
	 */
	async function handleSuggestionSelect(suggestion) {
		try {
			isLoading = true;
			error = null;
			
			// Update search input and close dropdown
			query = suggestion.name;
			showSuggestions = false;

			debugLog(`Fetching node: "${suggestion.name}" (${suggestion.label})`);
			const result = await getNodeByName(suggestion.name, suggestion.label);
			
			debugLog('=== API RESPONSE ===');
			debugLog('Success:', result.success);
			debugLog('Data length:', result.data?.length);
			
			if (result.data && result.data.length > 0) {
				debugLog('First item keys:', Object.keys(result.data[0]));
				debugLog('Has required properties:', {
					n: 'n' in result.data[0],
					connections: 'connections' in result.data[0]
				});
			}
			
			if (result.success && result.data && result.data.length > 0) {
				selectedNode = result.data[0];
				showGraph = true;
				
				debugLog('=== Node Selected ===');
				debugLog('Node name:', selectedNode.n?.name);
				debugLog('Connections count:', selectedNode.connections?.length);
			} else {
				error = "Node not found";
				showGraph = false;
				debugLog('Node not found or invalid response');
			}
		} catch (err) {
			console.error("Error fetching node:", err);
			error = err.message;
			showGraph = false;
		} finally {
			isLoading = false;
		}
	}

	/**
	 * Handle search button click or Enter key
	 * 
	 * Attempts to search by selecting first suggestion or direct name lookup.
	 */
	async function handleSearch() {
		if (query.trim() === "") return;

		// If we have suggestions, select the first one
		if (suggestions.length > 0) {
			await handleSuggestionSelect(suggestions[0]);
		} else {
			// Try to fetch node directly by name
			try {
				isLoading = true;
				error = null;
				
				debugLog(`Direct search for: "${query.trim()}"`);
				const result = await getNodeByName(query.trim());
				
				if (result.success && result.data && result.data.length > 0) {
					selectedNode = result.data[0];
					showGraph = true;
					debugLog('Direct search successful');
				} else {
					error = `No entity found with name "${query.trim()}"`;
					showGraph = false;
					debugLog('Direct search failed: no results');
				}
			} catch (err) {
				console.error("Search error:", err);
				error = err.message;
				showGraph = false;
			} finally {
				isLoading = false;
			}
		}
	}

	/**
	 * Clear search and reset application to initial state
	 */
	function handleClearSearch() {
		query = "";
		suggestions = [];
		showSuggestions = false;
		showGraph = false;
		selectedNode = null;
		error = null;
		
		debugLog('Search cleared, app reset to initial state');
	}

	/**
	 * Handle keyboard navigation in search input
	 * 
	 * - Enter: Trigger search
	 * - Escape: Close suggestions dropdown
	 * 
	 * @param {KeyboardEvent} event - Keyboard event
	 */
	function handleKeyDown(event) {
		if (event.key === 'Enter') {
			handleSearch();
		} else if (event.key === 'Escape') {
			showSuggestions = false;
		}
	}

	// ============================================
	// UI INTERACTION HANDLERS
	// ============================================

	/**
	 * Handle clicks outside of dropdowns and menus
	 * 
	 * Closes suggestions dropdown and settings menu when clicking outside.
	 * 
	 * @param {MouseEvent} event - Click event
	 */
	function handleClickOutside(event) {
		// Close suggestions if click was outside search wrapper
		if (!event.target.closest('.search-wrapper')) {
			showSuggestions = false;
		}
		
		// Close settings menu if click was outside settings wrapper
		if (showSettings && !event.target.closest('.settings-wrapper')) {
			showSettings = false;
		}
	}

	// ============================================
	// FEATURE HANDLERS
	// ============================================

	/**
	 * Generate HTML report from current graph state
	 * 
	 * Calls the exposed function from GraphView component to generate
	 * a printable HTML report with all visible nodes and relationships.
	 * Also includes timeline if visible.
	 */
	function handleGenerateReport() {
		if (graphViewComponent) {
			debugLog('Generating report from current graph state');
			
			// Get timeline image if timeline is visible
			let timelineImage = null;
			if (showTimeline && timelineComponent) {
				timelineImage = timelineComponent.exportAsImage();
				debugLog('Timeline image exported for report');
			}
			
			// Pass timeline image to GraphView report generation
			graphViewComponent.generateReportFromGraph(timelineImage);
		} else {
			console.error('GraphView component not initialized');
		}
	}

	/**
	 * Toggle time analysis view
	 * 
	 * Shows/hides temporal analysis of all visible nodes with date properties.
	 * Displays timeline visualization of entity activity periods.
	 */
	function handleTimeAnalysis() {
		showTimeline = !showTimeline;
		debugLog('Timeline visibility toggled:', showTimeline);
	}
	
	/**
	 * Handle node selection from timeline
	 * Highlights the corresponding node in the graph
	 * 
	 * @param {CustomEvent} event - Event with nodeId and nodeName
	 */
	function handleTimelineNodeSelected(event) {
		const { nodeId, nodeName } = event.detail;
		debugLog('Timeline node selected:', nodeName);
		
		// Update highlighted node
		highlightedNodeId = nodeId;
		
		// Tell GraphView to highlight this node
		if (graphViewComponent) {
			graphViewComponent.highlightNode(nodeId);
		}
	}
	
	/**
	 * Handle node selection from graph
	 * Highlights the corresponding bar in timeline
	 * 
	 * @param {CustomEvent} event - Event with nodeId
	 */
	function handleGraphNodeSelected(event) {
		const { nodeId } = event.detail;
		debugLog('Graph node selected:', nodeId);
		
		// Update highlighted node for timeline
		highlightedNodeId = nodeId;
	}
	
	/**
	 * Update visible nodes when graph changes
	 * Called after graph is rendered or modified
	 */
	function updateVisibleNodes() {
		if (graphViewComponent && showGraph) {
			visibleNodes = graphViewComponent.getVisibleNodes();
			debugLog('Updated visible nodes:', visibleNodes.length);
		}
	}

	// ============================================
	// REACTIVE STATEMENTS
	// ============================================

	/**
	 * React to selectedNode changes
	 * Logs node information for debugging
	 */
	$: {
		if (DEBUG && selectedNode) {
			debugLog('=== Selected Node Changed ===');
			debugLog('Node type:', typeof selectedNode);
			debugLog('Available keys:', Object.keys(selectedNode));
			debugLog('Main entity:', selectedNode.n?.name);
		}
	}

	/**
	 * React to showGraph changes
	 * Logs graph visibility state
	 */
	$: {
		if (DEBUG) {
			debugLog('=== Graph Visibility Changed ===');
			debugLog('showGraph:', showGraph);
		}
	}
	
	/**
	 * React to selectedNode changes - update visible nodes
	 */
	$: {
		if (selectedNode && graphViewComponent) {
			// Wait for graph to render, then update visible nodes
			setTimeout(() => {
				updateVisibleNodes();
			}, 500);
		}
	}
</script>

<svelte:window on:click={handleClickOutside} />

<div class="app-container">
	<!-- ============================================ -->
	<!-- HEADER: Search and Controls                 -->
	<!-- ============================================ -->
	<header class:compact={showGraph} class="search-container">
		<h1>Threat Intelligence Platform</h1>
		
		<div class="search-wrapper">
			<div class="search-button">
				<!-- Search Input -->
				<input
					type="text"
					class="searchbar"
					bind:value={query}
					on:input={handleInputChange}
					on:keydown={handleKeyDown}
					placeholder="Search for entities (min. 3 characters)..."
					disabled={isLoading}
				/>
				
				<!-- Action Buttons -->
				<div class="button-group">
					<!-- Clear Button (shown when query exists) -->
					{#if query.length > 0}
						<button 
							on:click={handleClearSearch} 
							disabled={isLoading} 
							title="Clear search"
							class="clear-btn"
						>
							<X size={20} />
						</button>
					{/if}
					
					<!-- Search Button -->
					<button 
						on:click={handleSearch} 
						disabled={isLoading} 
						title="Search"
					>
						<Search size={20} />
					</button>
					
					<!-- Settings Button and Menu -->
					<div class="settings-wrapper">
						<button 
							class="settings-btn"
							on:click={() => showSettings = !showSettings} 
							title="Settings"
						>
							<Settings size={20} />
						</button>
						
						<SettingsMenu 
							show={showSettings} 
							onClose={() => showSettings = false} 
						/>
					</div>
					
					<!-- Feature Buttons (shown when graph is visible) -->
					{#if showGraph}
						<button 
							on:click={handleTimeAnalysis}
							title="Time Analysis"
						>
							<ChartNoAxesCombined size={20} />
						</button>
						
						<button 
							on:click={handleGenerateReport}
							title="Generate Report"
						>
							<FileText size={20} />
						</button>
					{/if}
				</div>
			</div>

			<!-- Autocomplete Suggestions Dropdown -->
			{#if showSuggestions && suggestions.length > 0}
				<div class="suggestions-dropdown">
					{#each suggestions as suggestion}
						<button
							class="suggestion-item"
							on:mousedown|preventDefault={() => handleSuggestionSelect(suggestion)}
							type="button"
						>
							<span class="suggestion-name">{suggestion.name}</span>
							<span class="suggestion-label label-{suggestion.label}">
								{suggestion.label}
							</span>
						</button>
					{/each}
				</div>
			{/if}

			<!-- Loading Indicator -->
			{#if isLoading}
				<div class="loading-indicator">Loading...</div>
			{/if}

			<!-- Error Message -->
			{#if error}
				<div class="error-message">{error}</div>
			{/if}
		</div>
	</header>

	<!-- ============================================ -->
	<!-- DEBUG PANEL (Development Only)              -->
	<!-- ============================================ -->
	{#if DEBUG}
		<div class="debug-panel">
			<details>
				<summary>Debug Info (click to expand)</summary>
				<div class="debug-content">
					<p><strong>showGraph:</strong> {showGraph}</p>
					<p><strong>selectedNode exists:</strong> {selectedNode !== null}</p>
					{#if selectedNode}
						<p><strong>selectedNode keys:</strong> {Object.keys(selectedNode).join(', ')}</p>
						<p><strong>Has 'n' property:</strong> {'n' in selectedNode}</p>
						<p><strong>Has 'connections' property:</strong> {'connections' in selectedNode}</p>
					{/if}
					<p><strong>Current hops setting:</strong> {$contextDepth}</p>
				</div>
			</details>
		</div>
	{/if}

	<!-- ============================================ -->
	<!-- MAIN CONTENT: Graph View                    -->
	<!-- ============================================ -->
	{#if showGraph && selectedNode}
		<div class="graph-container">
			<GraphView 
				bind:this={graphViewComponent} 
				node={selectedNode}
				on:nodeSelected={handleGraphNodeSelected}
			/>
		</div>
	{:else if showGraph && !selectedNode}
		<!-- Loading State -->
		<div class="graph-container">
			<div class="graph-loading">
				<p>Loading graph...</p>
			</div>
		</div>
	{/if}

	<!-- ============================================ -->
	<!-- TIMELINE ANALYSIS                           -->
	<!-- ============================================ -->
	{#if showTimeline && showGraph && visibleNodes.length > 0}
		<div class="timeline-section">
			<TimelineAnalysis
				bind:this={timelineComponent}
				nodes={visibleNodes}
				highlightedNodeId={highlightedNodeId}
				on:nodeSelected={handleTimelineNodeSelected}
			/>
		</div>
	{/if}

	<!-- ============================================ -->
	<!-- FOOTER                                       -->
	<!-- ============================================ -->
	<footer class="footer">
		<p>
			<Copyright size={13} /> 2025 Johannes Liebscher — CTI Platform Version 0.21 Prototype
		</p>
		<p>Impressum</p>
	</footer>
</div>
