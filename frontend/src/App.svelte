<script>
	import {
		Search,
		Settings,
		FileText,
		ChartNoAxesCombined,
		Copyright,
	} from "lucide-svelte";
	import GraphView from "./GraphView.svelte";
	import { getAutocompleteSuggestions, getNodeByName } from "./api.js";
	
	// State management
	let query = "";
	let showGraph = false;
	let suggestions = [];
	let showSuggestions = false;
	let isLoading = false;
	let error = null;
	let selectedNode = null;
	let debounceTimer = null;



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

			const result = await getNodeByName(suggestion.name, suggestion.label);
			
			if (result.success && result.data && result.data.length > 0) {
				selectedNode = result.data[0];
				showGraph = true;
			} else {
				error = "Node not found";
				showGraph = false;
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
		if (!event.target.closest('.search-wrapper')) {
			showSuggestions = false;
		}
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
					<button on:click={handleSearch} disabled={isLoading} title="Search">
						<Search size={20} />
					</button>
					<button title="Einstellungen">
						<Settings size={20} />
					</button>
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

	{#if showGraph && selectedNode}
		<div class="graph-container">
			<GraphView node={selectedNode} />
		</div>
	{/if}

	<footer class="footer">
		<Copyright size={13} /> 2025 Johannes Liebscher – CTI Platform Version
		0.21 Prototype
		<p>Impressum</p>
	</footer>
</div>
