/**
 * Shared stores for the application
 */
import { writable } from "svelte/store";

/**
 * Context depth (hops) setting for graph queries
 * Stored in localStorage for persistence
 */
export const contextDepth = writable(
  parseInt(localStorage.getItem("contextDepth")) || 1,
);

// Subscribe to changes and save to localStorage
contextDepth.subscribe((value) => {
  localStorage.setItem("contextDepth", value);
});
