<script>
	import {
		Search,
		Settings,
		FileText,
		ChartNoAxesCombined,
		Copyright,
		AlertCircle,
	} from "lucide-svelte";
	import GraphView from "./GraphView.svelte";
	import { searchNodes } from "./api.js";
	
	let query = "";
	let showGraph = false;
	let graphData = null;
	let loading = false;
	let error = null;


	async function handleSearch() {
		if (query.trim() === "") {
			error = "Please enter a search term";
			return;
		}

		loading = true;
		error = null;
		showGraph = false;

		try {
			const result = await searchNodes(query.trim());

			if (result.success && result.data && result.data.length > 0) {
				graphData = result.data;
				showGraph = true;
				error = null;
			} else {
				error = "No result found";
				graphData = null;
				showGraph = false;
			}
		} catch (err) {
			error = 'Error: ${err.message}';
			graphData = null;
			showGraph = false;
			console.error("Search error:", err);
		} finally {
			loading = false;
		}
	}
	function clearError() {
		error = null;
	}

</script>

<div class="app-container">
	<header class:compact={showGraph} class="search-container">
		<h1>Threat Intelligence Platform</h1>
		<div class="search-button">
			<input
				type="text"
				class="searchbar"
				bind:value={query}
				on:keydown={(e) =>
					e.key === "Enter" && handleSearch()}
				placeholder="Type to search..."
				disabled={loading}
			/>
			<div class="button-group">
				<button 
					on:click={handleSearch}
					disabled={loading}
					title="Suche"
					><Search size={20} /></button
				>
				<button title="Einstellungen"
					><Settings size={20} /></button
				>
				{#if showGraph}
					<button title="Zeitanalyse"
						><ChartNoAxesCombined
							size={20}
						/></button
					>
					<button title="Bericht"
						><FileText size={20} /></button
					>
				{/if}
			</div>
		</div>
		{#if error}
			<div class="error-message">
			<AlertCircle size={16} />
			<span>{error}</span>
			<button class="close-btn" on:click={clearError}>x</button>
			</div>
		{/if}

		{#if loading}
			<div class="loading-message">
				Searching...
			</div>
			
		{/if}
	</header>
	{#if showGraph && graphData}
		<div class="graph-container">
			<GraphView data={graphData} />
		</div>
	{/if}

	<footer class="footer">
		<Copyright size={13} /> 2025 Johannes Liebscher – CTI Platform Version
		0.2 Prototype
		<p>Impressum</p>
	</footer>
</div>
