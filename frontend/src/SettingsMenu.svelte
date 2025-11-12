<script>
  import { contextDepth } from './stores.js';
  
  // Props from parent (App.svelte controls visibility)
  export let show = false;
  export let onClose = () => {};
  
  // Update when slider changes
  function handleDepthChange(event) {
    const value = parseInt(event.target.value);
    contextDepth.set(value);
  }
</script>

<!-- Settings Menu Panel (no button - controlled by parent) -->
{#if show}
  <div class="settings-menu">
    <div class="settings-header">
      <h3>Search Settings</h3>
      <button on:click={onClose}>×</button>
    </div>
    
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
  </div>
{/if}

<style>
  /* Component-specific positioning relative to parent button */
  .settings-menu {
    position: absolute;
    top: 100%;
    right: 0;
    margin-top: 8px;
  }
</style>
