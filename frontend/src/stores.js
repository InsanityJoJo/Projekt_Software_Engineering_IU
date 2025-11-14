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

// Label filter store
export const labelFilter = writable(
  localStorage.getItem("labelFilter") || "all",
);

// Time filter stores
export const startDate = writable(localStorage.getItem("startDate") || null);

export const endDate = writable(localStorage.getItem("endDate") || null);

// Save to localStorage
contextDepth.subscribe((value) => {
  localStorage.setItem("contextDepth", value);
});

labelFilter.subscribe((value) => {
  localStorage.setItem("labelFilter", value);
});

startDate.subscribe((value) => {
  if (value) localStorage.setItem("startDate", value);
  else localStorage.removeItem("startDate");
});

endDate.subscribe((value) => {
  if (value) localStorage.setItem("endDate", value);
  else localStorage.removeItem("endDate");
});
