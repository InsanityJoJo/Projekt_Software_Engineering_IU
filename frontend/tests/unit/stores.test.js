/**
 * Unit Tests for stores.js
 *
 * Tests Svelte stores for application state management
 * Covers: writable stores, localStorage persistence, subscriptions
 */

import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { get } from "svelte/store";

describe("Stores", () => {
  let localStorageMock;
  let contextDepth, labelFilter, startDate, endDate;

  beforeEach(() => {
    // Mock localStorage
    localStorageMock = {
      getItem: vi.fn(),
      setItem: vi.fn(),
      removeItem: vi.fn(),
      clear: vi.fn(),
    };
    global.localStorage = localStorageMock;

    // Clear module cache to get fresh stores
    vi.resetModules();
  });

  afterEach(() => {
    vi.clearAllMocks();
  });

  describe("contextDepth store", () => {
    it("should initialize with default value of 1 when localStorage is empty", async () => {
      localStorageMock.getItem.mockReturnValue(null);

      const { contextDepth } = await import("../../src/stores.js");
      const value = get(contextDepth);

      expect(value).toBe(1);
      expect(localStorageMock.getItem).toHaveBeenCalledWith("contextDepth");
    });

    it("should initialize from localStorage when available", async () => {
      localStorageMock.getItem.mockReturnValue("2");

      const { contextDepth } = await import("../../src/stores.js");
      const value = get(contextDepth);

      expect(value).toBe(2);
    });

    it("should save to localStorage when value changes", async () => {
      localStorageMock.getItem.mockReturnValue(null);

      const { contextDepth } = await import("../../src/stores.js");

      contextDepth.set(3);

      // Give time for subscription to fire
      await new Promise((resolve) => setTimeout(resolve, 10));

      expect(localStorageMock.setItem).toHaveBeenCalledWith("contextDepth", 3);
    });

    it("should handle invalid localStorage values", async () => {
      localStorageMock.getItem.mockReturnValue("invalid");

      const { contextDepth } = await import("../../src/stores.js");
      const value = get(contextDepth);

      // parseInt("invalid") returns NaN, which is falsy, so should default to 1
      expect(value).toBe(1);
    });

    it("should handle numeric string values correctly", async () => {
      localStorageMock.getItem.mockReturnValue("3");

      const { contextDepth } = await import("../../src/stores.js");
      const value = get(contextDepth);

      expect(value).toBe(3);
    });

    it("should update subscribers when value changes", async () => {
      localStorageMock.getItem.mockReturnValue(null);

      const { contextDepth } = await import("../../src/stores.js");

      const values = [];
      const unsubscribe = contextDepth.subscribe((value) => {
        values.push(value);
      });

      contextDepth.set(2);
      contextDepth.set(3);

      unsubscribe();

      expect(values).toEqual([1, 2, 3]);
    });
  });

  describe("labelFilter store", () => {
    it("should initialize with 'all' when localStorage is empty", async () => {
      localStorageMock.getItem.mockReturnValue(null);

      const { labelFilter } = await import("../../src/stores.js");
      const value = get(labelFilter);

      expect(value).toBe("all");
      expect(localStorageMock.getItem).toHaveBeenCalledWith("labelFilter");
    });

    it("should initialize from localStorage when available", async () => {
      localStorageMock.getItem.mockReturnValue("ThreatActor");

      const { labelFilter } = await import("../../src/stores.js");
      const value = get(labelFilter);

      expect(value).toBe("ThreatActor");
    });

    it("should save to localStorage when value changes", async () => {
      localStorageMock.getItem.mockReturnValue(null);

      const { labelFilter } = await import("../../src/stores.js");

      labelFilter.set("Malware");

      await new Promise((resolve) => setTimeout(resolve, 10));

      expect(localStorageMock.setItem).toHaveBeenCalledWith(
        "labelFilter",
        "Malware",
      );
    });

    it("should handle empty string value", async () => {
      localStorageMock.getItem.mockReturnValue("");

      const { labelFilter } = await import("../../src/stores.js");
      const value = get(labelFilter);

      expect(value).toBe("all"); // Empty string is falsy, defaults to "all"
    });

    it("should update subscribers when value changes", async () => {
      localStorageMock.getItem.mockReturnValue(null);

      const { labelFilter } = await import("../../src/stores.js");

      const values = [];
      const unsubscribe = labelFilter.subscribe((value) => {
        values.push(value);
      });

      labelFilter.set("ThreatActor");
      labelFilter.set("Malware");

      unsubscribe();

      expect(values).toEqual(["all", "ThreatActor", "Malware"]);
    });
  });

  describe("startDate store", () => {
    it("should initialize with null when localStorage is empty", async () => {
      localStorageMock.getItem.mockReturnValue(null);

      const { startDate } = await import("../../src/stores.js");
      const value = get(startDate);

      expect(value).toBeNull();
      expect(localStorageMock.getItem).toHaveBeenCalledWith("startDate");
    });

    it("should initialize from localStorage when available", async () => {
      localStorageMock.getItem.mockReturnValue("2024-01-01");

      const { startDate } = await import("../../src/stores.js");
      const value = get(startDate);

      expect(value).toBe("2024-01-01");
    });

    it("should save to localStorage when value is set", async () => {
      localStorageMock.getItem.mockReturnValue(null);

      const { startDate } = await import("../../src/stores.js");

      startDate.set("2024-01-01");

      await new Promise((resolve) => setTimeout(resolve, 10));

      expect(localStorageMock.setItem).toHaveBeenCalledWith(
        "startDate",
        "2024-01-01",
      );
    });

    it("should remove from localStorage when value is set to null", async () => {
      localStorageMock.getItem.mockReturnValue("2024-01-01");

      const { startDate } = await import("../../src/stores.js");

      startDate.set(null);

      await new Promise((resolve) => setTimeout(resolve, 10));

      expect(localStorageMock.removeItem).toHaveBeenCalledWith("startDate");
    });

    it("should remove from localStorage when value is set to empty string", async () => {
      localStorageMock.getItem.mockReturnValue("2024-01-01");

      const { startDate } = await import("../../src/stores.js");

      startDate.set("");

      await new Promise((resolve) => setTimeout(resolve, 10));

      expect(localStorageMock.removeItem).toHaveBeenCalledWith("startDate");
    });

    it("should update subscribers when value changes", async () => {
      localStorageMock.getItem.mockReturnValue(null);

      const { startDate } = await import("../../src/stores.js");

      const values = [];
      const unsubscribe = startDate.subscribe((value) => {
        values.push(value);
      });

      startDate.set("2024-01-01");
      startDate.set("2024-06-01");
      startDate.set(null);

      unsubscribe();

      expect(values).toEqual([null, "2024-01-01", "2024-06-01", null]);
    });
  });

  describe("endDate store", () => {
    it("should initialize with null when localStorage is empty", async () => {
      localStorageMock.getItem.mockReturnValue(null);

      const { endDate } = await import("../../src/stores.js");
      const value = get(endDate);

      expect(value).toBeNull();
      expect(localStorageMock.getItem).toHaveBeenCalledWith("endDate");
    });

    it("should initialize from localStorage when available", async () => {
      localStorageMock.getItem.mockReturnValue("2024-12-31");

      const { endDate } = await import("../../src/stores.js");
      const value = get(endDate);

      expect(value).toBe("2024-12-31");
    });

    it("should save to localStorage when value is set", async () => {
      localStorageMock.getItem.mockReturnValue(null);

      const { endDate } = await import("../../src/stores.js");

      endDate.set("2024-12-31");

      await new Promise((resolve) => setTimeout(resolve, 10));

      expect(localStorageMock.setItem).toHaveBeenCalledWith(
        "endDate",
        "2024-12-31",
      );
    });

    it("should remove from localStorage when value is set to null", async () => {
      localStorageMock.getItem.mockReturnValue("2024-12-31");

      const { endDate } = await import("../../src/stores.js");

      endDate.set(null);

      await new Promise((resolve) => setTimeout(resolve, 10));

      expect(localStorageMock.removeItem).toHaveBeenCalledWith("endDate");
    });

    it("should remove from localStorage when value is set to undefined", async () => {
      localStorageMock.getItem.mockReturnValue("2024-12-31");

      const { endDate } = await import("../../src/stores.js");

      endDate.set(undefined);

      await new Promise((resolve) => setTimeout(resolve, 10));

      expect(localStorageMock.removeItem).toHaveBeenCalledWith("endDate");
    });

    it("should update subscribers when value changes", async () => {
      localStorageMock.getItem.mockReturnValue(null);

      const { endDate } = await import("../../src/stores.js");

      const values = [];
      const unsubscribe = endDate.subscribe((value) => {
        values.push(value);
      });

      endDate.set("2024-12-31");
      endDate.set("2024-06-30");
      endDate.set(null);

      unsubscribe();

      expect(values).toEqual([null, "2024-12-31", "2024-06-30", null]);
    });
  });

  describe("Store Integration", () => {
    it("should handle multiple stores independently", async () => {
      localStorageMock.getItem.mockReturnValue(null);

      const stores = await import("../../src/stores.js");

      stores.contextDepth.set(2);
      stores.labelFilter.set("Malware");
      stores.startDate.set("2024-01-01");
      stores.endDate.set("2024-12-31");

      await new Promise((resolve) => setTimeout(resolve, 10));

      expect(get(stores.contextDepth)).toBe(2);
      expect(get(stores.labelFilter)).toBe("Malware");
      expect(get(stores.startDate)).toBe("2024-01-01");
      expect(get(stores.endDate)).toBe("2024-12-31");
    });

    it("should persist all stores to localStorage", async () => {
      localStorageMock.getItem.mockReturnValue(null);

      const stores = await import("../../src/stores.js");

      stores.contextDepth.set(3);
      stores.labelFilter.set("Campaign");
      stores.startDate.set("2023-01-01");
      stores.endDate.set("2023-12-31");

      await new Promise((resolve) => setTimeout(resolve, 10));

      expect(localStorageMock.setItem).toHaveBeenCalledWith("contextDepth", 3);
      expect(localStorageMock.setItem).toHaveBeenCalledWith(
        "labelFilter",
        "Campaign",
      );
      expect(localStorageMock.setItem).toHaveBeenCalledWith(
        "startDate",
        "2023-01-01",
      );
      expect(localStorageMock.setItem).toHaveBeenCalledWith(
        "endDate",
        "2023-12-31",
      );
    });
  });

  describe("Edge Cases", () => {
    it("should handle rapid successive updates", async () => {
      localStorageMock.getItem.mockReturnValue(null);

      const { contextDepth } = await import("../../src/stores.js");

      contextDepth.set(1);
      contextDepth.set(2);
      contextDepth.set(3);

      await new Promise((resolve) => setTimeout(resolve, 50));

      // Should have been called for each update
      expect(localStorageMock.setItem).toHaveBeenCalled();
    });

    it("should handle update and subscribe pattern", async () => {
      localStorageMock.getItem.mockReturnValue(null);

      const { labelFilter } = await import("../../src/stores.js");

      const values = [];

      labelFilter.update((current) => {
        return "ThreatActor";
      });

      labelFilter.subscribe((value) => {
        values.push(value);
      });

      expect(values).toContain("ThreatActor");
    });

    it("should handle unsubscribe correctly", async () => {
      localStorageMock.getItem.mockReturnValue(null);

      const { contextDepth } = await import("../../src/stores.js");

      const values = [];
      const unsubscribe = contextDepth.subscribe((value) => {
        values.push(value);
      });

      contextDepth.set(2);
      unsubscribe();
      contextDepth.set(3);

      // Should only have initial value and first update
      expect(values).toEqual([1, 2]);
      expect(values).not.toContain(3);
    });

    it("should handle zero values correctly", async () => {
      localStorageMock.getItem.mockReturnValue(null);

      const { contextDepth } = await import("../../src/stores.js");

      contextDepth.set(0);

      await new Promise((resolve) => setTimeout(resolve, 10));

      expect(localStorageMock.setItem).toHaveBeenCalledWith("contextDepth", 0);
    });

    it("should handle false values correctly for date stores", async () => {
      localStorageMock.getItem.mockReturnValue(null);

      const { startDate } = await import("../../src/stores.js");

      startDate.set(false);

      await new Promise((resolve) => setTimeout(resolve, 10));

      // False is falsy, should remove from storage
      expect(localStorageMock.removeItem).toHaveBeenCalledWith("startDate");
    });
  });

  describe("Type Coercion", () => {
    it("should handle string numbers for contextDepth", async () => {
      localStorageMock.getItem.mockReturnValue("5");

      const { contextDepth } = await import("../../src/stores.js");
      const value = get(contextDepth);

      expect(value).toBe(5);
      expect(typeof value).toBe("number");
    });

    it("should handle floating point strings for contextDepth", async () => {
      localStorageMock.getItem.mockReturnValue("2.5");

      const { contextDepth } = await import("../../src/stores.js");
      const value = get(contextDepth);

      // parseInt truncates decimals
      expect(value).toBe(2);
    });

    it("should preserve string values for labelFilter", async () => {
      localStorageMock.getItem.mockReturnValue("ThreatActor");

      const { labelFilter } = await import("../../src/stores.js");
      const value = get(labelFilter);

      expect(value).toBe("ThreatActor");
      expect(typeof value).toBe("string");
    });

    it("should preserve string values for date stores", async () => {
      localStorageMock.getItem.mockReturnValue("2024-01-01");

      const { startDate } = await import("../../src/stores.js");
      const value = get(startDate);

      expect(value).toBe("2024-01-01");
      expect(typeof value).toBe("string");
    });
  });

  describe("localStorage Persistence Behavior", () => {
    it("should not save null/undefined values to localStorage for dates", async () => {
      localStorageMock.getItem.mockReturnValue(null);

      const { startDate } = await import("../../src/stores.js");

      startDate.set(null);

      await new Promise((resolve) => setTimeout(resolve, 10));

      // Should not call setItem for null
      expect(localStorageMock.setItem).not.toHaveBeenCalledWith(
        "startDate",
        expect.anything(),
      );
    });

    it("should always save values to localStorage for contextDepth", async () => {
      localStorageMock.getItem.mockReturnValue(null);

      const { contextDepth } = await import("../../src/stores.js");

      contextDepth.set(0);

      await new Promise((resolve) => setTimeout(resolve, 10));

      expect(localStorageMock.setItem).toHaveBeenCalledWith("contextDepth", 0);
    });

    it("should always save values to localStorage for labelFilter", async () => {
      localStorageMock.getItem.mockReturnValue(null);

      const { labelFilter } = await import("../../src/stores.js");

      labelFilter.set("all");

      await new Promise((resolve) => setTimeout(resolve, 10));

      expect(localStorageMock.setItem).toHaveBeenCalledWith(
        "labelFilter",
        "all",
      );
    });
  });
});
