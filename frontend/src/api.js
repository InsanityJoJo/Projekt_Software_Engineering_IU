// API service for backend communication
// Handles all HTTP requests to the Flask backend

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
 * Get autocomplete suggestions
 *
 * This is called while the user types more than 3 characters
 * Returns a list of entity names that match the query
 *
 * @param {string} query - Search query (minimum 3 characters)
 * @param {string} label - Optional: filter by entity type (e.g., 'ThreatActor')
 * @returns {Promise<object>} - { success, suggestions, count }
 */
export async function getAutocompleteSuggestions(query, label = null) {
  if (!query || query.length < 3) {
    return {
      success: true,
      suggestions: [],
      count: 0,
      message: "Minimum 3 characters required",
    };
  }

  const params = new URLSearchParams({ q: query });
  if (label) {
    params.append("label", label);
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
 * @returns {Promise<object>} - { success, data, count }
 */
export async function getNodeByName(name, label = null) {
  if (!name) {
    throw new Error("Node name is required");
  }

  const params = label ? `?label=${encodeURIComponent(label)}` : "";
  return apiRequest(`/api/node/${encodeURIComponent(name)}${params}`);
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
