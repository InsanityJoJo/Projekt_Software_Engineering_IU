// /src/api.js
// API service for backend communication
// Handles all HTTP requests to the Flask backend

import { sanitizeInput } from "./inputValidation.js";

const API_BASE_URL = import.meta.env.VITE_API_URL || "http://localhost:8000";

/**
 * fetch wrapper with error handling
 *
 * @param {string} endpoint - API endpoint (api/query)
 * @param {object} options - Fetch options
 * @returns {Promise<object>} - Response data
 * @throws {Error}
 */

async function apiRequest(endpoint, options = {}) {
  try {
    const response = await fetch(`${API_BASE_URL}${endpoint}`, {
      headers: {
        "Content-Type": "application/json",
        ...options.headers,
      },
      ...options,
    });
    //Check if response is ok (status code 200-299)
    if (!response.ok) {
      const errorData = await response.json().catch(() => ({}));
      throw new Error(
        errorData.error ||
          `HTTP error! staus:  ${response.status}: ${response.statusText}`,
      );
    }

    return await response.json();
  } catch (error) {
    console.error(`API Error [${endpoint}]:`, error);
    throw error;
  }
}

/**
 * Sanitize and prepare query string for backend
 * - Normalizes Unicode (NFKC)
 * - Trims whitespace
 *
 * @param {string} query - Raw query string
 * @returns {string} - Sanitized lowercase query for backend
 */
function prepareQueryForBackend(query) {
  return sanitizeInput(query);
}

/**
 * Get autocomplete suggestions with optional filtering
 *
 * @param {string} query - Search query (minimum 3 characters)
 * @param {string} label - Optional: filter by entity type
 * @param {string} startDate - Optional: filter start date (ISO format)
 * @param {string} endDate - Optional: filter end date (ISO format)
 * @returns {Promise<object>} - { success, suggestions, count }
 */
export async function getAutocompleteSuggestions(
  query,
  label = null,
  startDate = null,
  endDate = null,
) {
  if (!query || query.length < 3) {
    return {
      success: true,
      suggestions: [],
      count: 0,
      message: "Minimum 3 characters required",
    };
  }

  // Sanitize and prepare query for backend
  const sanitizedQuery = prepareQueryForBackend(query);

  const params = new URLSearchParams({ q: sanitizedQuery });

  if (label && label !== "all") {
    params.append("label", label);
  }

  if (startDate) {
    params.append("start_date", startDate);
  }

  if (endDate) {
    params.append("end_date", endDate);
  }

  return apiRequest(`/api/autocomplete?${params.toString()}`);
}

/**
 * Get a specific node by name
 *
 * This is called when user selects an entity from autocomplete
 * Returns the full node details with its connections
 *
 * @param {string} name - Entity name (e.g., 'APT28')
 * @param {string} label - Optional: entity type filter
 * @param {number} hops - Optional: context depth (0-3). If not provided, uses setting from SettingsMenu
 * @returns {Promise<object>} - { success, data, count, hops }
 */
export async function getNodeByName(name, label = null, hops = null) {
  if (!name) {
    throw new Error("Node name is required");
  }

  // Sanitize and prepare name for backend
  const sanitizedName = prepareQueryForBackend(name);

  // If hops not explicitly provided, get from settings store
  if (hops === null) {
    // Import store dynamically to avoid circular dependencies
    const { contextDepth } = await import("./stores.js");
    const { get } = await import("svelte/store");
    hops = get(contextDepth);
  }
  hops = parseInt(hops, 10);

  // Validate and fallback to 1 if invalid
  if (isNaN(hops) || hops < 0 || hops > 3) {
    console.warn(`Invalid hops value: ${hops}, falling back to 1`);
    hops = 1;
  }

  // Build query parameters
  const params = new URLSearchParams();
  if (label) {
    params.append("label", encodeURIComponent(label));
  }
  params.append("hops", String(hops));

  return apiRequest(
    `/api/node/${encodeURIComponent(sanitizedName)}?${params.toString()}`,
  );
}
/**
 * Health check -verify backend is running
 * @retruns {Promise<object>} Health status
 */
export async function healthCheck() {
  return apiRequest("/api/health");
}

/**
 * Get database statistics
 * @returns {Promise<object>} Stats with node and relationship counts
 */
export async function getStats() {
  return apiRequest("/api/stats");
}

// Export API_BASE_URL for debugging/display purposes
export { API_BASE_URL };
