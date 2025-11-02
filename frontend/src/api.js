// API service for backend communication
// Handles all HTTP requests to the Flask backend

const API_BASE_URL = import.meta.env.VITE_API_URL || "http://localhost:8000";

/**
 * fetch wrapper with error handling
 * @param {string} endpoint - API endpoint (api/query)
 * @param {object} options - Fetch options
 * @returns {Promise<object>} - Response data
 */

async function apiFetch(endpoint, options = {}) {
  try {
    const response = await fetch(`${API_BASE_URL}${endpoint}`, {
      headers: {
        "Content-Type": "application/json",
        ...options.headers,
      },
      ...options,
    });

    if (!response.ok) {
      const errorData = await response.json().catch(() => ({}));
      throw new Error(
        errorData.error || `HTTP ${response.status}: ${response.statusText}`,
      );
    }

    return await response.json();
  } catch (error) {
    console.error(`API Error [${endpoint}]:`, error);
    throw error;
  }
}

/**
 * Health check -verify backend is running
 * @retruns {Promise<object>} Health status
 */
export async function healthCheck() {
  return apiFetch("/health");
}

/**
 * Search for nodes by name or properties
 * @param {string} searchTerm - Search term to find nodes
 * @returns {Promise<object>} Query result with nodes and relationships
 */
export async function searchNodes(searchTerm) {
  return apiFetch("/api/query", {
    method: "POST",
    body: JSON.stringify({
      label: null, // Search across all labels
      property: "name",
      value: searchTerm,
      limit: 50,
    }),
  });
}

/**
 * Get a specific node by label and name
 * @param {string} label - Node label (e.g., 'ThreatActor')
 * @param {string} name - Node name/identifier
 * @returns {Promise<object>} Query result
 */
export async function getNode(label, name) {
  return apiFetch("/api/query", {
    method: "POST",
    body: JSON.stringify({
      label: label,
      property: "name",
      value: name,
      limit: 1,
    }),
  });
}

/**
 * Get database statistics
 * @returns {Promise<object>} Stats with node and relationship counts
 */
export async function getStats() {
  return apiFetch("/api/stats");
}

/**
 * Create a new node
 * @param {string} label - Node label
 * @param {object} properties - Node properties
 * @returns {Promise<object>} Creation result
 */
export async function createNode(label, properties) {
  return apiFetch("/api/node", {
    method: "POST",
    body: JSON.stringify({
      label: label,
      properties: properties,
    }),
  });
}

// Export API_BASE_URL for debugging/display purposes
export { API_BASE_URL };
