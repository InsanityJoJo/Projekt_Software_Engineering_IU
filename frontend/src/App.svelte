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
	import { getAutocompleteSuggestions, getNodeByName } from "./api.js";
	import { contextDepth } from "./stores.js";
	
	// State management
	let query = "";
	let showGraph = false;
	let suggestions = [];
	let showSuggestions = false;
	let isLoading = false;
	let error = null;
	let selectedNode = null;
	let debounceTimer = null;
	let showSettings = false;



	/**
	 * Handle input changes and trigger autocomplete
	 * Wait 300 ms before making request after keystroke
	 */
	function handleInputChange() {
		// Clear previous timer
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

				const result = await getAutocompleteSuggestions(query);
				
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
	 * Handle suggestion selection
	 * 
	 * When user clicks on a suggestion:
	 * 1. Close the suggestions dropdown
	 * 2. Fetch the full node details
	 * 3. Pass data to GraphView component
	 */
	async function handleSuggestionSelect(suggestion) {
		try {
			isLoading = true;
			error = null;
			
			// Update search input
			query = suggestion.name;
			showSuggestions = false;

			console.log(`Calling getNodeByName("${suggestion.name}", "${suggestion.label}")`);
			const result = await getNodeByName(suggestion.name, suggestion.label);
			
			console.log('=== API RESPONSE ===');
			console.log('Full result:', result);
			console.log('result.success:', result.success);
			console.log('result.data:', result.data);
			console.log('result.data type:', typeof result.data);
			console.log('result.data is Array?', Array.isArray(result.data));
						
						if (result.data && result.data.length > 0) {
				console.log('First data item:', result.data[0]);
				console.log('First data item keys:', Object.keys(result.data[0]));
				console.log('Has n property?', 'n' in result.data[0]);
				console.log('Has connections property?', 'connections' in result.data[0]);
			}
			
			if (result.success && result.data && result.data.length > 0) {
				selectedNode = result.data[0];
				showGraph = true;
				
				console.log('=== SETTING selectedNode ===');
				console.log('selectedNode:', selectedNode);
				console.log('selectedNode keys:', Object.keys(selectedNode));
				console.log('selectedNode.n:', selectedNode.n);
				console.log('selectedNode.connections:', selectedNode.connections);
			} else {
				error = "Node not found";
				showGraph = false;
				console.error('Node not found or invalid response');
			}
		} catch (err) {
			console.error("=== ERROR fetching node ===");
			console.error("Error:", err);
			console.error("Error message:", err.message);
			console.error("Error stack:", err.stack);
			error = err.message;
			showGraph = false;
		} finally {
			isLoading = false;
		}
	}	/**
	 * Handle search button click or Enter key
	 * 
	 * This allows users to search without selecting from autocomplete
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
				
				const result = await getNodeByName(query.trim());
				
				if (result.success && result.data && result.data.length > 0) {
					selectedNode = result.data[0];
					showGraph = true;
				} else {
					error = `No entity found with name "${query.trim()}"`;
					showGraph = false;
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
	 * Clear the search and reset to initial state
	 */
	function handleClearSearch() {
		query = "";
		suggestions = [];
		showSuggestions = false;
		showGraph = false;
		selectedNode = null;
		error = null;
	}

	/**
	 * Handle keyboard navigation
	 * 
	 */
	function handleKeyDown(event) {
		if (event.key === 'Enter') {
			handleSearch();
		} else if (event.key === 'Escape') {
			showSuggestions = false;
		}
		// All other keys pass through normally - user can keep typing
	}

	/**
	 * Close suggestions when clicking outside
	 */
	function handleClickOutside(event) {
		// Check if click was outside search wrapper (for suggestions)
		if (!event.target.closest('.search-wrapper')) {
			showSuggestions = false;
		}
		
		// Check if click was outside settings wrapper (for settings menu)
		// Only close if settings is open AND click was outside
		if (showSettings && !event.target.closest('.settings-wrapper')) {
			showSettings = false;
		}
	}
	
	// Reactive logging
	$: {
		console.log('=== REACTIVE: selectedNode changed ===');
		console.log('New selectedNode:', selectedNode);
		if (selectedNode) {
			console.log('selectedNode type:', typeof selectedNode);
			console.log('selectedNode keys:', Object.keys(selectedNode));
		}
	}
	
	$: {
		console.log('=== REACTIVE: showGraph changed ===');
		console.log('showGraph:', showGraph);
	}
</script>

<svelte:window on:click={handleClickOutside} />

<div class="app-container">
	<header class:compact={showGraph} class="search-container">
		<h1>Threat Intelligence Platform</h1>
		<div class="search-wrapper">
			<div class="search-button">
				<input
					type="text"
					class="searchbar"
					bind:value={query}
					on:input={handleInputChange}
					on:keydown={handleKeyDown}
					placeholder="Search for entities (min. 3 characters)..."
					disabled={isLoading}
				/>
				<div class="button-group">
					<!-- Clear button - shows when there's text -->
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
					<button on:click={handleSearch} disabled={isLoading} title="Search">
						<Search size={20} />
					</button>
				<div class="settings-wrapper">
						<button 
							class="settings-btn"
							on:click={() => showSettings = !showSettings} 
							title="Einstellungen"
						>
							<Settings size={20} />
						</button>
						
						<!-- Settings Menu Component -->
						<SettingsMenu 
							show={showSettings} 
							onClose={() => showSettings = false} 
						/>
					</div>
					{#if showGraph}
						<button title="Zeitanalyse">
							<ChartNoAxesCombined size={20} />
						</button>
						<button title="Bericht">
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

	<!-- Debug info panel -->
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

	{#if showGraph && selectedNode}
		<div class="graph-container">
			<GraphView node={selectedNode} />
		</div>
	{:else if showGraph && !selectedNode}
		<!-- Loading state for graph -->
		<div class="graph-container">
			<div class="graph-loading">
				<p>Loading graph...</p>
			</div>
		</div>
	{/if}

	<footer class="footer">
		<Copyright size={13} /> 2025 Johannes Liebscher â€“ CTI Platform Version
		0.21 Prototype
		<p>Impressum</p>
	</footer>
</div>
