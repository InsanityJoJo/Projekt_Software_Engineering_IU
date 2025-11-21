/**
 * Unit Tests for api.js
 *
 * Tests API service for backend communication
 * Covers: HTTP requests, input sanitization, error handling, edge cases
 */

import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import {
  getAutocompleteSuggestions,
  getNodeByName,
  healthCheck,
  getStats,
  API_BASE_URL,
} from "../../src/api.js";

// Mock the input validation module
vi.mock("../../src/inputValidation.js", () => ({
  sanitizeInput: vi.fn((input) => String(input).trim().toLowerCase()),
}));

// Mock the stores module
vi.mock("../../src/stores.js", () => ({
  contextDepth: { subscribe: vi.fn() },
}));

describe("API Service", () => {
  let originalFetch;

  beforeEach(() => {
    // Save original fetch
    originalFetch = global.fetch;
    // Mock fetch
    global.fetch = vi.fn();
    // Clear all mocks
    vi.clearAllMocks();
  });

  afterEach(() => {
    // Restore original fetch
    global.fetch = originalFetch;
  });

  describe("API_BASE_URL", () => {
    it("should have a default API base URL", () => {
      expect(API_BASE_URL).toBeDefined();
      expect(typeof API_BASE_URL).toBe("string");
    });
  });

  describe("getAutocompleteSuggestions", () => {
    it("should return empty suggestions for queries under 3 characters", async () => {
      const result = await getAutocompleteSuggestions("ab");

      expect(result.success).toBe(true);
      expect(result.suggestions).toEqual([]);
      expect(result.count).toBe(0);
      expect(result.message).toBe("Minimum 3 characters required");
      expect(global.fetch).not.toHaveBeenCalled();
    });

    it("should return empty suggestions for empty query", async () => {
      const result = await getAutocompleteSuggestions("");

      expect(result.success).toBe(true);
      expect(result.suggestions).toEqual([]);
      expect(result.count).toBe(0);
      expect(global.fetch).not.toHaveBeenCalled();
    });

    it("should fetch suggestions for valid query", async () => {
      const mockResponse = {
        success: true,
        suggestions: [{ name: "APT28", label: "ThreatActor" }],
        count: 1,
      };

      global.fetch.mockResolvedValueOnce({
        ok: true,
        json: async () => mockResponse,
      });

      const result = await getAutocompleteSuggestions("apt28");

      expect(global.fetch).toHaveBeenCalledTimes(1);
      expect(global.fetch).toHaveBeenCalledWith(
        expect.stringContaining("/api/autocomplete?q=apt28"),
        expect.any(Object),
      );
      expect(result.success).toBe(true);
      expect(result.suggestions).toHaveLength(1);
    });

    it("should include label filter when provided", async () => {
      global.fetch.mockResolvedValueOnce({
        ok: true,
        json: async () => ({ success: true, suggestions: [], count: 0 }),
      });

      await getAutocompleteSuggestions("test", "ThreatActor");

      const callUrl = global.fetch.mock.calls[0][0];
      expect(callUrl).toContain("label=ThreatActor");
    });

    it("should not include label filter when set to 'all'", async () => {
      global.fetch.mockResolvedValueOnce({
        ok: true,
        json: async () => ({ success: true, suggestions: [], count: 0 }),
      });

      await getAutocompleteSuggestions("test", "all");

      const callUrl = global.fetch.mock.calls[0][0];
      expect(callUrl).not.toContain("label=");
    });

    it("should include date filters when provided", async () => {
      global.fetch.mockResolvedValueOnce({
        ok: true,
        json: async () => ({ success: true, suggestions: [], count: 0 }),
      });

      await getAutocompleteSuggestions(
        "test",
        null,
        "2024-01-01",
        "2024-12-31",
      );

      const callUrl = global.fetch.mock.calls[0][0];
      expect(callUrl).toContain("start_date=2024-01-01");
      expect(callUrl).toContain("end_date=2024-12-31");
    });

    it("should handle API errors gracefully", async () => {
      global.fetch.mockResolvedValueOnce({
        ok: false,
        status: 500,
        statusText: "Internal Server Error",
        json: async () => ({ error: "Database connection failed" }),
      });

      await expect(getAutocompleteSuggestions("test")).rejects.toThrow(
        "Database connection failed",
      );
    });

    it("should handle network errors", async () => {
      global.fetch.mockRejectedValueOnce(new Error("Network request failed"));

      await expect(getAutocompleteSuggestions("test")).rejects.toThrow(
        "Network request failed",
      );
    });

    it("should sanitize input before sending to API", async () => {
      const { sanitizeInput } = await import("../../src/inputValidation.js");

      global.fetch.mockResolvedValueOnce({
        ok: true,
        json: async () => ({ success: true, suggestions: [], count: 0 }),
      });

      await getAutocompleteSuggestions("  APT28  ");

      expect(sanitizeInput).toHaveBeenCalledWith("  APT28  ");
    });

    it("should handle null query", async () => {
      const result = await getAutocompleteSuggestions(null);

      expect(result.success).toBe(true);
      expect(result.suggestions).toEqual([]);
      expect(global.fetch).not.toHaveBeenCalled();
    });

    it("should handle undefined query", async () => {
      const result = await getAutocompleteSuggestions(undefined);

      expect(result.success).toBe(true);
      expect(result.suggestions).toEqual([]);
      expect(global.fetch).not.toHaveBeenCalled();
    });
  });

  describe("getNodeByName", () => {
    it("should fetch node data with default hops", async () => {
      // Mock svelte/store module for dynamic import
      vi.doMock("svelte/store", () => ({
        get: vi.fn(() => 1), // Return default hops value
      }));

      const mockResponse = {
        success: true,
        data: {
          n: { name: "APT28", label: "ThreatActor" },
          connections: [],
        },
        count: 1,
        hops: 1,
      };

      global.fetch.mockResolvedValueOnce({
        ok: true,
        json: async () => mockResponse,
      });

      const result = await getNodeByName("APT28");

      expect(global.fetch).toHaveBeenCalledTimes(1);
      expect(global.fetch).toHaveBeenCalledWith(
        expect.stringContaining("/api/node/apt28"),
        expect.any(Object),
      );
      expect(result.success).toBe(true);
    });

    it("should throw error for empty name", async () => {
      await expect(getNodeByName("")).rejects.toThrow("Node name is required");
    });

    it("should throw error for null name", async () => {
      await expect(getNodeByName(null)).rejects.toThrow(
        "Node name is required",
      );
    });

    it("should throw error for undefined name", async () => {
      await expect(getNodeByName(undefined)).rejects.toThrow(
        "Node name is required",
      );
    });

    it("should include label filter when provided", async () => {
      vi.doMock("svelte/store", () => ({
        get: vi.fn(() => 1),
      }));

      global.fetch.mockResolvedValueOnce({
        ok: true,
        json: async () => ({
          success: true,
          data: { n: {}, connections: [] },
        }),
      });

      await getNodeByName("APT28", "ThreatActor");

      const callUrl = global.fetch.mock.calls[0][0];
      expect(callUrl).toContain("label=ThreatActor");
    });

    it("should accept explicit hops parameter", async () => {
      global.fetch.mockResolvedValueOnce({
        ok: true,
        json: async () => ({
          success: true,
          data: { n: {}, connections: [] },
        }),
      });

      await getNodeByName("APT28", null, 2);

      const callUrl = global.fetch.mock.calls[0][0];
      expect(callUrl).toContain("hops=2");
    });

    it("should validate hops parameter (too low)", async () => {
      const consoleWarnSpy = vi
        .spyOn(console, "warn")
        .mockImplementation(() => {});

      global.fetch.mockResolvedValueOnce({
        ok: true,
        json: async () => ({
          success: true,
          data: { n: {}, connections: [] },
        }),
      });

      await getNodeByName("APT28", null, -1);

      expect(consoleWarnSpy).toHaveBeenCalledWith(
        expect.stringContaining("Invalid hops value"),
      );
      const callUrl = global.fetch.mock.calls[0][0];
      expect(callUrl).toContain("hops=1"); // Fallback to 1

      consoleWarnSpy.mockRestore();
    });

    it("should validate hops parameter (too high)", async () => {
      const consoleWarnSpy = vi
        .spyOn(console, "warn")
        .mockImplementation(() => {});

      global.fetch.mockResolvedValueOnce({
        ok: true,
        json: async () => ({
          success: true,
          data: { n: {}, connections: [] },
        }),
      });

      await getNodeByName("APT28", null, 5);

      expect(consoleWarnSpy).toHaveBeenCalledWith(
        expect.stringContaining("Invalid hops value"),
      );
      const callUrl = global.fetch.mock.calls[0][0];
      expect(callUrl).toContain("hops=1");

      consoleWarnSpy.mockRestore();
    });

    it("should validate hops parameter (NaN)", async () => {
      const consoleWarnSpy = vi
        .spyOn(console, "warn")
        .mockImplementation(() => {});

      global.fetch.mockResolvedValueOnce({
        ok: true,
        json: async () => ({
          success: true,
          data: { n: {}, connections: [] },
        }),
      });

      await getNodeByName("APT28", null, "invalid");

      expect(consoleWarnSpy).toHaveBeenCalled();
      const callUrl = global.fetch.mock.calls[0][0];
      expect(callUrl).toContain("hops=1");

      consoleWarnSpy.mockRestore();
    });

    it("should handle API errors", async () => {
      global.fetch.mockResolvedValueOnce({
        ok: false,
        status: 404,
        statusText: "Not Found",
        json: async () => ({ error: "Node not found" }),
      });

      await expect(getNodeByName("NonExistent", null, 1)).rejects.toThrow(
        "Node not found",
      );
    });

    it("should sanitize node name before sending", async () => {
      const { sanitizeInput } = await import("../../src/inputValidation.js");

      global.fetch.mockResolvedValueOnce({
        ok: true,
        json: async () => ({
          success: true,
          data: { n: {}, connections: [] },
        }),
      });

      await getNodeByName("  APT28  ", null, 1);

      expect(sanitizeInput).toHaveBeenCalledWith("  APT28  ");
    });

    it("should encode special characters in node name", async () => {
      global.fetch.mockResolvedValueOnce({
        ok: true,
        json: async () => ({
          success: true,
          data: { n: {}, connections: [] },
        }),
      });

      await getNodeByName("APT 28 / Group", null, 1);

      const callUrl = global.fetch.mock.calls[0][0];
      // The name should be URL encoded
      expect(callUrl).toContain(encodeURIComponent("apt 28 / group"));
    });

    it("should handle network errors", async () => {
      global.fetch.mockRejectedValueOnce(new Error("Network request failed"));

      await expect(getNodeByName("APT28", null, 1)).rejects.toThrow(
        "Network request failed",
      );
    });
  });

  describe("healthCheck", () => {
    it("should fetch health status", async () => {
      const mockResponse = {
        status: "healthy",
        database: "connected",
      };

      global.fetch.mockResolvedValueOnce({
        ok: true,
        json: async () => mockResponse,
      });

      const result = await healthCheck();

      expect(global.fetch).toHaveBeenCalledTimes(1);
      expect(global.fetch).toHaveBeenCalledWith(
        expect.stringContaining("/api/health"),
        expect.any(Object),
      );
      expect(result.status).toBe("healthy");
    });

    it("should handle unhealthy backend", async () => {
      global.fetch.mockResolvedValueOnce({
        ok: false,
        status: 503,
        statusText: "Service Unavailable",
        json: async () => ({ error: "Database connection failed" }),
      });

      await expect(healthCheck()).rejects.toThrow();
    });

    it("should handle network errors", async () => {
      global.fetch.mockRejectedValueOnce(new Error("Network request failed"));

      await expect(healthCheck()).rejects.toThrow("Network request failed");
    });
  });

  describe("getStats", () => {
    it("should fetch database statistics", async () => {
      const mockResponse = {
        nodes: 1000,
        relationships: 5000,
        labels: ["ThreatActor", "Malware", "Campaign"],
      };

      global.fetch.mockResolvedValueOnce({
        ok: true,
        json: async () => mockResponse,
      });

      const result = await getStats();

      expect(global.fetch).toHaveBeenCalledTimes(1);
      expect(global.fetch).toHaveBeenCalledWith(
        expect.stringContaining("/api/stats"),
        expect.any(Object),
      );
      expect(result.nodes).toBe(1000);
      expect(result.relationships).toBe(5000);
    });

    it("should handle API errors", async () => {
      global.fetch.mockResolvedValueOnce({
        ok: false,
        status: 500,
        statusText: "Internal Server Error",
        json: async () => ({ error: "Failed to fetch stats" }),
      });

      await expect(getStats()).rejects.toThrow();
    });

    it("should handle network errors", async () => {
      global.fetch.mockRejectedValueOnce(new Error("Network request failed"));

      await expect(getStats()).rejects.toThrow("Network request failed");
    });
  });

  describe("apiRequest (internal error handling)", () => {
    it("should handle malformed JSON responses", async () => {
      global.fetch.mockResolvedValueOnce({
        ok: false,
        status: 500,
        statusText: "Internal Server Error",
        json: async () => {
          throw new Error("Invalid JSON");
        },
      });

      await expect(getStats()).rejects.toThrow();
    });

    it("should include Content-Type header", async () => {
      global.fetch.mockResolvedValueOnce({
        ok: true,
        json: async () => ({ status: "ok" }),
      });

      await healthCheck();

      const fetchCall = global.fetch.mock.calls[0];
      expect(fetchCall[1].headers["Content-Type"]).toBe("application/json");
    });

    it("should log errors to console", async () => {
      const consoleErrorSpy = vi
        .spyOn(console, "error")
        .mockImplementation(() => {});

      global.fetch.mockRejectedValueOnce(new Error("Test error"));

      await expect(healthCheck()).rejects.toThrow();
      expect(consoleErrorSpy).toHaveBeenCalledWith(
        expect.stringContaining("API Error"),
        expect.any(Error),
      );

      consoleErrorSpy.mockRestore();
    });
  });

  describe("Edge Cases and Special Scenarios", () => {
    it("should handle very long query strings", async () => {
      const longQuery = "a".repeat(200);

      global.fetch.mockResolvedValueOnce({
        ok: true,
        json: async () => ({ success: true, suggestions: [], count: 0 }),
      });

      await getAutocompleteSuggestions(longQuery);

      expect(global.fetch).toHaveBeenCalled();
    });

    it("should handle special characters in queries", async () => {
      global.fetch.mockResolvedValueOnce({
        ok: true,
        json: async () => ({ success: true, suggestions: [], count: 0 }),
      });

      await getAutocompleteSuggestions("test@example.com");

      expect(global.fetch).toHaveBeenCalled();
    });

    it("should handle concurrent requests", async () => {
      global.fetch.mockResolvedValue({
        ok: true,
        json: async () => ({ success: true, suggestions: [], count: 0 }),
      });

      const requests = [
        getAutocompleteSuggestions("apt28"),
        getAutocompleteSuggestions("lazarus"),
        getAutocompleteSuggestions("fancy bear"),
      ];

      const results = await Promise.all(requests);

      expect(results).toHaveLength(3);
      expect(global.fetch).toHaveBeenCalledTimes(3);
    });

    it("should handle empty response data", async () => {
      global.fetch.mockResolvedValueOnce({
        ok: true,
        json: async () => ({}),
      });

      const result = await getStats();

      expect(result).toEqual({});
    });

    it("should handle null response data", async () => {
      global.fetch.mockResolvedValueOnce({
        ok: true,
        json: async () => null,
      });

      const result = await getStats();

      expect(result).toBeNull();
    });
  });

  describe("URL Construction", () => {
    it("should construct correct autocomplete URL with all params", async () => {
      global.fetch.mockResolvedValueOnce({
        ok: true,
        json: async () => ({ success: true, suggestions: [] }),
      });

      await getAutocompleteSuggestions(
        "test",
        "ThreatActor",
        "2024-01-01",
        "2024-12-31",
      );

      const callUrl = global.fetch.mock.calls[0][0];
      expect(callUrl).toContain("/api/autocomplete?");
      expect(callUrl).toContain("q=test");
      expect(callUrl).toContain("label=ThreatActor");
      expect(callUrl).toContain("start_date=2024-01-01");
      expect(callUrl).toContain("end_date=2024-12-31");
    });

    it("should construct correct node URL with all params", async () => {
      global.fetch.mockResolvedValueOnce({
        ok: true,
        json: async () => ({ success: true, data: {} }),
      });

      await getNodeByName("APT28", "ThreatActor", 2);

      const callUrl = global.fetch.mock.calls[0][0];
      expect(callUrl).toContain("/api/node/");
      expect(callUrl).toContain("label=ThreatActor");
      expect(callUrl).toContain("hops=2");
    });
  });
});
