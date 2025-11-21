/**
 * Unit Tests for ReportGenerator.js
 *
 * Tests HTML report generation from graph data
 * Mocks browser APIs (window.open, document.write)
 * Covers: functions, edge cases, error handling
 */

import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { generateReport } from "../../src/ReportGenerator.js";

describe("ReportGenerator", () => {
  // Mock browser APIs
  let mockWindow;
  let mockDocument;
  let originalWindowOpen;

  beforeEach(() => {
    // Create mock document
    mockDocument = {
      write: vi.fn(),
      close: vi.fn(),
    };

    // Create mock window with document
    mockWindow = {
      document: mockDocument,
      print: vi.fn(),
      onload: null,
    };

    // Mock window.open to return our mock window
    originalWindowOpen = global.window.open;
    global.window = global.window || {};
    global.window.open = vi.fn(() => mockWindow);
  });

  afterEach(() => {
    // Restore original window.open
    if (originalWindowOpen) {
      global.window.open = originalWindowOpen;
    }
    vi.clearAllMocks();
  });

  describe("generateReport - Main Function", () => {
    it("should generate a report with minimal required data", () => {
      const reportData = {
        mainNode: { name: "APT28", type: "ThreatActor" },
        nodes: [{ data: { id: "apt28", label: "APT28", type: "ThreatActor" } }],
        edges: [],
        graphImage: "data:image/png;base64,iVBORw0KG",
        timelineImage: null,
        config: null,
        searchParams: null,
      };

      generateReport(reportData);

      expect(global.window.open).toHaveBeenCalledWith("", "_blank");
      expect(mockDocument.write).toHaveBeenCalledTimes(1);
      expect(mockDocument.close).toHaveBeenCalledTimes(1);

      const htmlOutput = mockDocument.write.mock.calls[0][0];
      expect(htmlOutput).toContain("<!DOCTYPE html>");
      expect(htmlOutput).toContain("APT28");
      expect(htmlOutput).toContain("ThreatActor");
    });

    it("should include timeline when provided", () => {
      const reportData = {
        mainNode: { name: "APT29", type: "ThreatActor" },
        nodes: [{ data: { id: "apt29", label: "APT29", type: "ThreatActor" } }],
        edges: [],
        graphImage: "data:image/png;base64,graph",
        timelineImage: "data:image/png;base64,timeline",
        config: { includeTimeline: true },
      };

      generateReport(reportData);

      const htmlOutput = mockDocument.write.mock.calls[0][0];
      expect(htmlOutput).toContain("Temporal Analysis");
      expect(htmlOutput).toContain("data:image/png;base64,timeline");
    });

    it("should include search parameters when configured", () => {
      const reportData = {
        mainNode: { name: "Emotet", type: "Malware" },
        nodes: [{ data: { id: "emotet", label: "Emotet", type: "Malware" } }],
        edges: [],
        graphImage: "data:image/png;base64,test",
        config: { includeSearchParams: true },
        searchParams: {
          labelFilter: "Malware",
          startDate: "2024-01-01",
          endDate: "2024-12-31",
        },
      };

      generateReport(reportData);

      const htmlOutput = mockDocument.write.mock.calls[0][0];
      expect(htmlOutput).toContain("Search Parameters");
      expect(htmlOutput).toContain("Malware");
      expect(htmlOutput).toContain("2024-01-01");
      expect(htmlOutput).toContain("2024-12-31");
    });

    it("should include user text when configured", () => {
      const reportData = {
        mainNode: { name: "WannaCry", type: "Malware" },
        nodes: [
          { data: { id: "wannacry", label: "WannaCry", type: "Malware" } },
        ],
        edges: [],
        graphImage: "data:image/png;base64,test",
        config: {
          includeUserText: true,
          userText: "This is a critical threat.\nRequires immediate attention.",
        },
      };

      generateReport(reportData);

      const htmlOutput = mockDocument.write.mock.calls[0][0];
      expect(htmlOutput).toContain("User Notes");
      expect(htmlOutput).toContain("This is a critical threat");
      expect(htmlOutput).toContain("<br>");
    });

    it("should include connections section with multiple nodes", () => {
      const reportData = {
        mainNode: { name: "APT28", type: "ThreatActor" },
        nodes: [
          {
            data: {
              id: "apt28",
              label: "APT28",
              type: "ThreatActor",
              isMainNode: true,
            },
          },
          {
            data: {
              id: "malware1",
              label: "XAgent",
              type: "Malware",
              properties: {},
            },
          },
        ],
        edges: [
          {
            data: {
              source: "apt28",
              target: "malware1",
              relationshipType: "USES",
            },
          },
        ],
        graphImage: "data:image/png;base64,test",
        config: { includeNodes: true, includeRelationships: true },
      };

      generateReport(reportData);

      const htmlOutput = mockDocument.write.mock.calls[0][0];
      expect(htmlOutput).toContain("Connected Entities");
      expect(htmlOutput).toContain("XAgent");
      expect(htmlOutput).toContain("Relationships Overview");
    });
  });

  describe("HTML Structure and Content", () => {
    it("should generate valid HTML5 document structure", () => {
      const reportData = {
        mainNode: { name: "Test", type: "Test" },
        nodes: [{ data: { id: "test", label: "Test", type: "Test" } }],
        edges: [],
        graphImage: "data:image/png;base64,test",
      };

      generateReport(reportData);

      const htmlOutput = mockDocument.write.mock.calls[0][0];
      expect(htmlOutput).toContain("<!DOCTYPE html>");
      expect(htmlOutput).toContain('<html lang="en">');
      expect(htmlOutput).toContain("<head>");
      expect(htmlOutput).toContain("<body>");
      expect(htmlOutput).toContain("</html>");
    });

    it("should include CSS styles in the document", () => {
      const reportData = {
        mainNode: { name: "Test", type: "Test" },
        nodes: [{ data: { id: "test", label: "Test", type: "Test" } }],
        edges: [],
        graphImage: "data:image/png;base64,test",
      };

      generateReport(reportData);

      const htmlOutput = mockDocument.write.mock.calls[0][0];
      expect(htmlOutput).toContain("<style>");
      expect(htmlOutput).toContain(".report-container");
      expect(htmlOutput).toContain(".report-header");
      expect(htmlOutput).toContain("@media print");
    });

    it("should include print button with onclick handler", () => {
      const reportData = {
        mainNode: { name: "Test", type: "Test" },
        nodes: [{ data: { id: "test", label: "Test", type: "Test" } }],
        edges: [],
        graphImage: "data:image/png;base64,test",
      };

      generateReport(reportData);

      const htmlOutput = mockDocument.write.mock.calls[0][0];
      expect(htmlOutput).toContain('class="print-button"');
      expect(htmlOutput).toContain('onclick="printReport()"');
      expect(htmlOutput).toContain("function printReport()");
    });

    it("should include metadata section with generated date", () => {
      const reportData = {
        mainNode: { name: "Test", type: "Test" },
        nodes: [{ data: { id: "test", label: "Test", type: "Test" } }],
        edges: [],
        graphImage: "data:image/png;base64,test",
      };

      generateReport(reportData);

      const htmlOutput = mockDocument.write.mock.calls[0][0];
      expect(htmlOutput).toContain("Report Metadata");
      expect(htmlOutput).toContain("Generated");
      expect(htmlOutput).toContain("Total Nodes");
      expect(htmlOutput).toContain("Total Relationships");
    });

    it("should include footer with copyright", () => {
      const reportData = {
        mainNode: { name: "Test", type: "Test" },
        nodes: [{ data: { id: "test", label: "Test", type: "Test" } }],
        edges: [],
        graphImage: "data:image/png;base64,test",
      };

      generateReport(reportData);

      const htmlOutput = mockDocument.write.mock.calls[0][0];
      expect(htmlOutput).toContain("Threat Intelligence Platform");
      expect(htmlOutput).toContain("For internal use only");
    });
  });

  describe("Main Node Section", () => {
    it("should display main node with properties", () => {
      const reportData = {
        mainNode: {
          name: "APT28",
          type: "ThreatActor",
          properties: {
            country: "Russia",
            aliases: "Fancy Bear, Sofacy",
            active_since: "2007",
          },
        },
        nodes: [{ data: { id: "apt28", label: "APT28", type: "ThreatActor" } }],
        edges: [],
        graphImage: "data:image/png;base64,test",
      };

      generateReport(reportData);

      const htmlOutput = mockDocument.write.mock.calls[0][0];
      expect(htmlOutput).toContain("Main Entity Information");
      expect(htmlOutput).toContain("APT28");
      expect(htmlOutput).toContain("ThreatActor");
      expect(htmlOutput).toContain("country");
      expect(htmlOutput).toContain("Russia");
      expect(htmlOutput).toContain("aliases");
      expect(htmlOutput).toContain("Fancy Bear, Sofacy");
    });

    it("should handle main node with unknown name and type", () => {
      const reportData = {
        mainNode: {},
        nodes: [{ data: { id: "unknown", label: "Unknown", type: "Unknown" } }],
        edges: [],
        graphImage: "data:image/png;base64,test",
      };

      generateReport(reportData);

      const htmlOutput = mockDocument.write.mock.calls[0][0];
      expect(htmlOutput).toContain("Unknown");
    });
  });

  describe("Search Parameters Section", () => {
    it("should format search parameters with label filter", () => {
      const reportData = {
        mainNode: { name: "Test", type: "Test" },
        nodes: [{ data: { id: "test", label: "Test", type: "Test" } }],
        edges: [],
        graphImage: "data:image/png;base64,test",
        config: { includeSearchParams: true },
        searchParams: {
          labelFilter: "ThreatActor",
          startDate: null,
          endDate: null,
        },
      };

      generateReport(reportData);

      const htmlOutput = mockDocument.write.mock.calls[0][0];
      expect(htmlOutput).toContain("[ThreatActor]");
    });

    it("should show 'All Types' when no label filter", () => {
      const reportData = {
        mainNode: { name: "Test", type: "Test" },
        nodes: [{ data: { id: "test", label: "Test", type: "Test" } }],
        edges: [],
        graphImage: "data:image/png;base64,test",
        config: { includeSearchParams: true },
        searchParams: {
          labelFilter: "all",
          startDate: null,
          endDate: null,
        },
      };

      generateReport(reportData);

      const htmlOutput = mockDocument.write.mock.calls[0][0];
      expect(htmlOutput).toContain("[All Types]");
    });

    it("should show 'No time filter' when dates are missing", () => {
      const reportData = {
        mainNode: { name: "Test", type: "Test" },
        nodes: [{ data: { id: "test", label: "Test", type: "Test" } }],
        edges: [],
        graphImage: "data:image/png;base64,test",
        config: { includeSearchParams: true },
        searchParams: {
          labelFilter: "all",
          startDate: null,
          endDate: null,
        },
      };

      generateReport(reportData);

      const htmlOutput = mockDocument.write.mock.calls[0][0];
      expect(htmlOutput).toContain("No time filter");
    });

    it("should format date range when provided", () => {
      const reportData = {
        mainNode: { name: "Test", type: "Test" },
        nodes: [{ data: { id: "test", label: "Test", type: "Test" } }],
        edges: [],
        graphImage: "data:image/png;base64,test",
        config: { includeSearchParams: true },
        searchParams: {
          labelFilter: "Malware",
          startDate: "2024-01-01",
          endDate: "2024-12-31",
        },
      };

      generateReport(reportData);

      const htmlOutput = mockDocument.write.mock.calls[0][0];
      expect(htmlOutput).toContain("from [2024-01-01] to [2024-12-31]");
    });
  });

  describe("Node Cards and Relationships", () => {
    it("should render node cards for connected entities", () => {
      const reportData = {
        mainNode: { name: "APT28", type: "ThreatActor" },
        nodes: [
          {
            data: {
              id: "apt28",
              label: "APT28",
              type: "ThreatActor",
              isMainNode: true,
            },
          },
          {
            data: {
              id: "xagent",
              label: "XAgent",
              type: "Malware",
              properties: {
                first_seen: "2010",
                platform: "Windows",
              },
            },
          },
        ],
        edges: [
          {
            data: {
              source: "apt28",
              target: "xagent",
              relationshipType: "USES",
            },
          },
        ],
        graphImage: "data:image/png;base64,test",
        config: { includeNodes: true },
      };

      generateReport(reportData);

      const htmlOutput = mockDocument.write.mock.calls[0][0];
      expect(htmlOutput).toContain("XAgent");
      expect(htmlOutput).toContain("Malware");
      expect(htmlOutput).toContain("first_seen");
      expect(htmlOutput).toContain("2010");
      expect(htmlOutput).toContain("Connections:");
    });

    it("should limit properties in node cards to 5", () => {
      const manyProperties = {};
      for (let i = 1; i <= 10; i++) {
        manyProperties[`prop${i}`] = `value${i}`;
      }

      const reportData = {
        mainNode: { name: "Test", type: "Test" },
        nodes: [
          {
            data: { id: "test", label: "Test", type: "Test", isMainNode: true },
          },
          {
            data: {
              id: "node1",
              label: "Node1",
              type: "Test",
              properties: manyProperties,
            },
          },
        ],
        edges: [],
        graphImage: "data:image/png;base64,test",
        config: { includeNodes: true },
      };

      generateReport(reportData);

      const htmlOutput = mockDocument.write.mock.calls[0][0];
      // Should contain first 5 properties
      expect(htmlOutput).toContain("prop1");
      expect(htmlOutput).toContain("prop5");
      // Should not contain properties beyond 5
      expect(htmlOutput).not.toContain("prop6");
    });

    it("should truncate long property values", () => {
      const longValue = "a".repeat(150);

      const reportData = {
        mainNode: { name: "Test", type: "Test" },
        nodes: [
          {
            data: { id: "test", label: "Test", type: "Test", isMainNode: true },
          },
          {
            data: {
              id: "node1",
              label: "Node1",
              type: "Test",
              properties: { longProp: longValue },
            },
          },
        ],
        edges: [],
        graphImage: "data:image/png;base64,test",
        config: { includeNodes: true },
      };

      generateReport(reportData);

      const htmlOutput = mockDocument.write.mock.calls[0][0];
      expect(htmlOutput).toContain("...");
      expect(htmlOutput).not.toContain(longValue);
    });

    it("should render relationship items", () => {
      const reportData = {
        mainNode: { name: "APT28", type: "ThreatActor" },
        nodes: [
          { data: { id: "apt28", label: "APT28", type: "ThreatActor" } },
          { data: { id: "xagent", label: "XAgent", type: "Malware" } },
        ],
        edges: [
          {
            data: {
              source: "apt28",
              target: "xagent",
              relationshipType: "USES",
              label: "USES",
            },
          },
        ],
        graphImage: "data:image/png;base64,test",
        config: { includeNodes: true, includeRelationships: true },
      };

      generateReport(reportData);

      const htmlOutput = mockDocument.write.mock.calls[0][0];
      expect(htmlOutput).toContain("Relationships Overview");
      expect(htmlOutput).toContain("APT28");
      expect(htmlOutput).toContain("USES");
      expect(htmlOutput).toContain("XAgent");
    });

    it("should hide relationships when config disables them", () => {
      const reportData = {
        mainNode: { name: "APT28", type: "ThreatActor" },
        nodes: [
          { data: { id: "apt28", label: "APT28", type: "ThreatActor" } },
          { data: { id: "xagent", label: "XAgent", type: "Malware" } },
        ],
        edges: [
          {
            data: {
              source: "apt28",
              target: "xagent",
              relationshipType: "USES",
            },
          },
        ],
        graphImage: "data:image/png;base64,test",
        config: { includeNodes: true, includeRelationships: false },
      };

      generateReport(reportData);

      const htmlOutput = mockDocument.write.mock.calls[0][0];
      expect(htmlOutput).not.toContain("Relationships Overview");
    });

    it("should count node connections correctly", () => {
      const reportData = {
        mainNode: { name: "APT28", type: "ThreatActor" },
        nodes: [
          { data: { id: "apt28", label: "APT28", type: "ThreatActor" } },
          { data: { id: "malware1", label: "Malware1", type: "Malware" } },
        ],
        edges: [
          {
            data: {
              source: "apt28",
              target: "malware1",
              relationshipType: "USES",
            },
          },
          {
            data: {
              source: "malware1",
              target: "apt28",
              relationshipType: "TARGETS",
            },
          },
        ],
        graphImage: "data:image/png;base64,test",
        config: { includeNodes: true },
      };

      generateReport(reportData);

      const htmlOutput = mockDocument.write.mock.calls[0][0];
      expect(htmlOutput).toContain("Connections:");
      expect(htmlOutput).toContain("2"); // Should count 2 connections for malware1
    });
    it("should escape HTML in node properties", () => {
      const reportData = {
        mainNode: {
          name: "Test",
          type: "Test",
          properties: {
            malicious: '<img src=x onerror="alert(1)">',
          },
        },
        nodes: [{ data: { id: "test", label: "Test", type: "Test" } }],
        edges: [],
        graphImage: "data:image/png;base64,test",
      };

      generateReport(reportData);

      const htmlOutput = mockDocument.write.mock.calls[0][0];
      expect(htmlOutput).not.toContain("<img src=x");
      expect(htmlOutput).toContain("&lt;img");
      expect(htmlOutput).toContain("&gt;");
    });

    it("should escape special characters: ampersand, quotes", () => {
      const reportData = {
        mainNode: { name: "Test & \"quotes\" 'apostrophe'", type: "Test" },
        nodes: [{ data: { id: "test", label: "Test", type: "Test" } }],
        edges: [],
        graphImage: "data:image/png;base64,test",
      };

      generateReport(reportData);

      const htmlOutput = mockDocument.write.mock.calls[0][0];
      expect(htmlOutput).toContain("&amp;");
      expect(htmlOutput).toContain("&quot;");
      expect(htmlOutput).toContain("&#039;");
    });
  });

  describe("Edge Cases and Error Handling", () => {
    it("should handle empty nodes array", () => {
      const reportData = {
        mainNode: { name: "Test", type: "Test" },
        nodes: [],
        edges: [],
        graphImage: "data:image/png;base64,test",
      };

      generateReport(reportData);

      const htmlOutput = mockDocument.write.mock.calls[0][0];
      expect(htmlOutput).toContain("<!DOCTYPE html>");
      expect(mockDocument.write).toHaveBeenCalled();
    });

    it("should handle empty edges array", () => {
      const reportData = {
        mainNode: { name: "Test", type: "Test" },
        nodes: [{ data: { id: "test", label: "Test", type: "Test" } }],
        edges: [],
        graphImage: "data:image/png;base64,test",
      };

      generateReport(reportData);

      const htmlOutput = mockDocument.write.mock.calls[0][0];
      expect(htmlOutput).toContain("Total Relationships");
      expect(htmlOutput).toContain("0");
    });

    it("should handle nodes without properties", () => {
      const reportData = {
        mainNode: { name: "Test", type: "Test" },
        nodes: [
          {
            data: { id: "test", label: "Test", type: "Test", isMainNode: true },
          },
          { data: { id: "node1", label: "Node1", type: "Test" } },
        ],
        edges: [],
        graphImage: "data:image/png;base64,test",
        config: { includeNodes: true },
      };

      generateReport(reportData);

      const htmlOutput = mockDocument.write.mock.calls[0][0];
      expect(htmlOutput).toContain("No additional properties");
    });

    it("should handle very long entity names gracefully", () => {
      const longName = "A".repeat(200);

      const reportData = {
        mainNode: { name: longName, type: "Test" },
        nodes: [{ data: { id: "test", label: longName, type: "Test" } }],
        edges: [],
        graphImage: "data:image/png;base64,test",
      };

      generateReport(reportData);

      const htmlOutput = mockDocument.write.mock.calls[0][0];
      expect(htmlOutput).toContain(longName);
      expect(mockDocument.write).toHaveBeenCalled();
    });

    it("should handle special characters in all fields", () => {
      const specialChars = "Test < > & \" ' / \\";

      const reportData = {
        mainNode: { name: specialChars, type: specialChars },
        nodes: [
          {
            data: {
              id: "test",
              label: specialChars,
              type: specialChars,
              properties: { key: specialChars },
            },
          },
        ],
        edges: [],
        graphImage: "data:image/png;base64,test",
      };

      generateReport(reportData);

      const htmlOutput = mockDocument.write.mock.calls[0][0];
      expect(htmlOutput).not.toContain("< >");
      expect(htmlOutput).toContain("&lt;");
      expect(htmlOutput).toContain("&gt;");
      expect(htmlOutput).toContain("&amp;");
    });

    it("should handle numeric values in properties", () => {
      const reportData = {
        mainNode: {
          name: "Test",
          type: "Test",
          properties: {
            count: 42,
            percentage: 75.5,
            boolean: true,
          },
        },
        nodes: [{ data: { id: "test", label: "Test", type: "Test" } }],
        edges: [],
        graphImage: "data:image/png;base64,test",
      };

      generateReport(reportData);

      const htmlOutput = mockDocument.write.mock.calls[0][0];
      expect(htmlOutput).toContain("42");
      expect(htmlOutput).toContain("75.5");
      expect(htmlOutput).toContain("true");
    });

    it("should handle newlines in user text", () => {
      const reportData = {
        mainNode: { name: "Test", type: "Test" },
        nodes: [{ data: { id: "test", label: "Test", type: "Test" } }],
        edges: [],
        graphImage: "data:image/png;base64,test",
        config: {
          includeUserText: true,
          userText: "Line 1\nLine 2\nLine 3",
        },
      };

      generateReport(reportData);

      const htmlOutput = mockDocument.write.mock.calls[0][0];
      const brCount = (htmlOutput.match(/<br>/g) || []).length;
      expect(brCount).toBeGreaterThanOrEqual(2);
    });
  });

  describe("Report Metadata", () => {
    it("should include current date in metadata", () => {
      const reportData = {
        mainNode: { name: "Test", type: "Test" },
        nodes: [{ data: { id: "test", label: "Test", type: "Test" } }],
        edges: [],
        graphImage: "data:image/png;base64,test",
      };

      generateReport(reportData);

      const htmlOutput = mockDocument.write.mock.calls[0][0];
      const currentYear = new Date().getFullYear();
      expect(htmlOutput).toContain(currentYear.toString());
    });

    it("should count nodes correctly", () => {
      const reportData = {
        mainNode: { name: "Test", type: "Test" },
        nodes: [
          { data: { id: "test1", label: "Test1", type: "Test" } },
          { data: { id: "test2", label: "Test2", type: "Test" } },
          { data: { id: "test3", label: "Test3", type: "Test" } },
        ],
        edges: [],
        graphImage: "data:image/png;base64,test",
      };

      generateReport(reportData);

      const htmlOutput = mockDocument.write.mock.calls[0][0];
      expect(htmlOutput).toContain("3");
    });

    it("should count edges correctly", () => {
      const reportData = {
        mainNode: { name: "Test", type: "Test" },
        nodes: [
          { data: { id: "node1", label: "Node1", type: "Test" } },
          { data: { id: "node2", label: "Node2", type: "Test" } },
        ],
        edges: [
          {
            data: {
              source: "node1",
              target: "node2",
              relationshipType: "CONNECTS",
            },
          },
          {
            data: {
              source: "node2",
              target: "node1",
              relationshipType: "RELATES",
            },
          },
        ],
        graphImage: "data:image/png;base64,test",
      };

      generateReport(reportData);

      const htmlOutput = mockDocument.write.mock.calls[0][0];
      expect(htmlOutput).toContain("2");
    });
  });

  describe("Window.open Integration", () => {
    it("should open report in new tab", () => {
      const reportData = {
        mainNode: { name: "Test", type: "Test" },
        nodes: [{ data: { id: "test", label: "Test", type: "Test" } }],
        edges: [],
        graphImage: "data:image/png;base64,test",
      };

      generateReport(reportData);

      expect(global.window.open).toHaveBeenCalledWith("", "_blank");
    });

    it("should write HTML to opened window", () => {
      const reportData = {
        mainNode: { name: "Test", type: "Test" },
        nodes: [{ data: { id: "test", label: "Test", type: "Test" } }],
        edges: [],
        graphImage: "data:image/png;base64,test",
      };

      generateReport(reportData);

      expect(mockDocument.write).toHaveBeenCalledTimes(1);
      expect(mockDocument.close).toHaveBeenCalledTimes(1);
    });
  });
});
