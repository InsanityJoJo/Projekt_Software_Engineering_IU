<!-- ContextMenu.svelte -->
<script>
  import { createEventDispatcher } from 'svelte';

  const dispatch = createEventDispatcher();

  /**
   * @type {{ x: number, y: number } | null}
   */
  export let position = null;

  /**
   * @type {boolean}
   */
  export let visible = false;

  /**
   * @type {object | null}
   */
  export let targetNode = null;

  /**
   * Menu items configuration
   */
  const menuItems = [
    { id: 'info', label: 'Information', icon: 'i' },
    { id: 'extend', label: 'Extend', icon: '+' },
    { id: 'collapse', label: 'Collapse', icon: '-' },
    { id: 'delete', label: 'Delete', icon: 'x' }
  ];

  /**
   * Handle menu item click
   * @param {string} action - The action to perform
   */
  function handleAction(action) {
    dispatch('action', { action, node: targetNode });
    visible = false;
  }

  /**
   * Close menu when clicking outside
   */
  function handleClickOutside(event) {
    if (visible && event.target.closest('.context-menu') === null) {
      visible = false;
    }
  }

  /**
   * Close menu on Escape key
   */
  function handleKeydown(event) {
    if (event.key === 'Escape' && visible) {
      visible = false;
    }
  }
</script>

<svelte:window 
  on:click={handleClickOutside}
  on:keydown={handleKeydown}
/>

{#if visible && position}
  <div 
    class="context-menu"
    style="left: {position.x}px; top: {position.y}px;"
  >
    {#each menuItems as item}
      <button
        class="context-menu-item"
        on:click={() => handleAction(item.id)}
        title={item.label}
      >
        <span class="menu-icon">{item.icon}</span>
        <span class="menu-label">{item.label}</span>
      </button>
    {/each}
  </div>
{/if}

<style>
  .context-menu {
    position: fixed;
    z-index: 10000;
    background: var(--color-surface);
    border: 1px solid var(--color-border);
    border-radius: 0.5rem;
    box-shadow: 
      0 10px 15px -3px rgba(0, 0, 0, 0.3),
      0 4px 6px -2px rgba(0, 0, 0, 0.2);
    padding: 0.25rem;
    min-width: 160px;
    animation: slideIn 0.15s ease-out;
  }

  @keyframes slideIn {
    from {
      opacity: 0;
      transform: translateY(-5px);
    }
    to {
      opacity: 1;
      transform: translateY(0);
    }
  }

  .context-menu-item {
    width: 100%;
    display: flex;
    align-items: center;
    gap: 0.75rem;
    padding: 0.6rem 0.75rem;
    background: transparent;
    border: none;
    border-radius: 0.375rem;
    color: var(--color-text);
    cursor: pointer;
    transition: background-color 0.15s ease;
    font-size: 0.9rem;
    text-align: left;
  }

  .context-menu-item:hover {
    background: var(--color-hover);
  }

  .context-menu-item:active {
    background: var(--color-accent);
    color: var(--color-background);
  }

  .menu-icon {
    display: flex;
    align-items: center;
    justify-content: center;
    width: 20px;
    height: 20px;
    font-weight: bold;
    font-size: 1rem;
    opacity: 0.7;
  }

  .menu-label {
    flex: 1;
    font-weight: 500;
  }

  /* Delete item gets special color */
  .context-menu-item:last-child:hover {
    background: rgba(239, 68, 68, 0.1);
    color: var(--color-error);
  }

  .context-menu-item:last-child:hover .menu-icon {
    opacity: 1;
  }
</style>
