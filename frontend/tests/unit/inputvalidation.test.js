/**
 * Tests for Input Validation Utility
 *
 * Test suite covering all validation rules and edge cases
 */

import { describe, it, expect } from "vitest";
import {
  normalizeUnicode,
  trimAndCollapseSpaces,
  hasControlCharacters,
  hasEmojis,
  hasEscapeSequences,
  hasCodePatterns,
  validateLength,
  validateAllowedCharacters,
  validateSafety,
  sanitizeInput,
  validateInput,
  isValidForAutocomplete,
  escapeHtml,
} from "./src/inputValidation.js";

describe("Input Validation", () => {
  describe("normalizeUnicode", () => {
    it("should normalize compatible characters", () => {
      // Roman numeral IV (single character) vs I + V (two characters)
      const single = "Ⅳ"; // U+2163
      const composed = "IV"; // I + V
      expect(normalizeUnicode(single)).toBe("IV");
    });

    it("should handle empty string", () => {
      expect(normalizeUnicode("")).toBe("");
    });

    it("should handle non-string input", () => {
      expect(normalizeUnicode(null)).toBe("");
      expect(normalizeUnicode(undefined)).toBe("");
      expect(normalizeUnicode(123)).toBe("");
    });

    it("should normalize accented characters", () => {
      const input = "café"; // e with combining acute accent
      const normalized = normalizeUnicode(input);
      expect(normalized).toBe("café");
    });
  });

  describe("trimAndCollapseSpaces", () => {
    it("should trim leading and trailing spaces", () => {
      expect(trimAndCollapseSpaces("  hello  ")).toBe("hello");
    });

    it("should collapse multiple spaces to single space", () => {
      expect(trimAndCollapseSpaces("hello    world")).toBe("hello world");
    });

    it("should handle tabs and newlines", () => {
      expect(trimAndCollapseSpaces("hello\t\n  world")).toBe("hello world");
    });

    it("should handle empty string", () => {
      expect(trimAndCollapseSpaces("")).toBe("");
    });

    it("should handle only whitespace", () => {
      expect(trimAndCollapseSpaces("   ")).toBe("");
    });
  });

  describe("hasControlCharacters", () => {
    it("should detect null character", () => {
      expect(hasControlCharacters("hello\x00world")).toBe(true);
    });

    it("should detect tab character", () => {
      expect(hasControlCharacters("hello\tworld")).toBe(true);
    });

    it("should detect newline", () => {
      expect(hasControlCharacters("hello\nworld")).toBe(true);
    });

    it("should detect carriage return", () => {
      expect(hasControlCharacters("hello\rworld")).toBe(true);
    });

    it("should not detect normal characters", () => {
      expect(hasControlCharacters("hello world")).toBe(false);
    });

    it("should detect DEL character", () => {
      expect(hasControlCharacters("hello\x7Fworld")).toBe(true);
    });
  });

  describe("hasEmojis", () => {
    it("should detect common emojis", () => {
      expect(hasEmojis("hello 😀 world")).toBe(true);
      expect(hasEmojis("test 🔥")).toBe(true);
      expect(hasEmojis("👍 good")).toBe(true);
    });

    it("should not detect normal text", () => {
      expect(hasEmojis("hello world")).toBe(false);
      expect(hasEmojis("APT28")).toBe(false);
    });

    it("should detect various emoji ranges", () => {
      expect(hasEmojis("🚀")).toBe(true); // Transport emoji
      expect(hasEmojis("💻")).toBe(true); // Object emoji
    });
  });

  describe("hasEscapeSequences", () => {
    it("should detect backslash n", () => {
      expect(hasEscapeSequences("hello\\nworld")).toBe(true);
    });

    it("should detect hex escapes", () => {
      expect(hasEscapeSequences("\\x41")).toBe(true);
    });

    it("should detect unicode escapes", () => {
      expect(hasEscapeSequences("\\u0041")).toBe(true);
      expect(hasEscapeSequences("\\u{1F600}")).toBe(true);
    });

    it("should not detect normal backslashes in paths", () => {
      // Only literal escape sequences in strings are detected
      expect(hasEscapeSequences("normal text")).toBe(false);
    });

    it("should detect various escape types", () => {
      expect(hasEscapeSequences("\\t")).toBe(true);
      expect(hasEscapeSequences("\\r")).toBe(true);
      expect(hasEscapeSequences("\\\\")).toBe(true);
    });
  });

  describe("hasCodePatterns", () => {
    it("should detect script tags", () => {
      expect(hasCodePatterns("<script>alert(1)</script>")).toBe(true);
      expect(hasCodePatterns("<SCRIPT>alert(1)</SCRIPT>")).toBe(true);
    });

    it("should detect iframe tags", () => {
      expect(hasCodePatterns('<iframe src="evil"></iframe>')).toBe(true);
    });

    it("should detect javascript protocol", () => {
      expect(hasCodePatterns("javascript:alert(1)")).toBe(true);
    });

    it("should detect event handlers", () => {
      expect(hasCodePatterns("onclick=alert(1)")).toBe(true);
      expect(hasCodePatterns("onload = doEvil()")).toBe(true);
    });

    it("should detect eval", () => {
      expect(hasCodePatterns("eval(userInput)")).toBe(true);
    });

    it("should detect Function constructor", () => {
      expect(hasCodePatterns('Function("return evil")')).toBe(true);
    });

    it("should not detect normal text", () => {
      expect(hasCodePatterns("APT28")).toBe(false);
      expect(hasCodePatterns("malware.exe")).toBe(false);
    });
  });

  describe("validateLength", () => {
    it("should accept valid length", () => {
      const result = validateLength("APT28");
      expect(result.isValid).toBe(true);
      expect(result.error).toBeNull();
    });

    it("should reject too short input", () => {
      const result = validateLength("AB");
      expect(result.isValid).toBe(false);
      expect(result.error).toContain("at least 3 characters");
    });

    it("should reject too long input", () => {
      const longString = "a".repeat(101);
      const result = validateLength(longString);
      expect(result.isValid).toBe(false);
      expect(result.error).toContain("not exceed 100 characters");
    });

    it("should accept exactly 3 characters", () => {
      const result = validateLength("ABC");
      expect(result.isValid).toBe(true);
    });

    it("should accept exactly 100 characters", () => {
      const result = validateLength("a".repeat(100));
      expect(result.isValid).toBe(true);
    });
  });

  describe("validateAllowedCharacters", () => {
    it("should accept alphanumeric", () => {
      const result = validateAllowedCharacters("APT28");
      expect(result.isValid).toBe(true);
    });

    it("should accept allowed special characters", () => {
      expect(validateAllowedCharacters("test.file").isValid).toBe(true);
      expect(validateAllowedCharacters("test-name").isValid).toBe(true);
      expect(validateAllowedCharacters("test_value").isValid).toBe(true);
      expect(validateAllowedCharacters("user@domain").isValid).toBe(true);
    });

    it("should accept spaces between characters", () => {
      const result = validateAllowedCharacters("APT 28");
      expect(result.isValid).toBe(true);
    });

    it("should reject special characters", () => {
      expect(validateAllowedCharacters("test!").isValid).toBe(false);
      expect(validateAllowedCharacters("test#hash").isValid).toBe(false);
      expect(validateAllowedCharacters("test$dollar").isValid).toBe(false);
      expect(validateAllowedCharacters("test%percent").isValid).toBe(false);
    });

    it("should reject brackets and parentheses", () => {
      expect(validateAllowedCharacters("test(param)").isValid).toBe(false);
      expect(validateAllowedCharacters("test[index]").isValid).toBe(false);
      expect(validateAllowedCharacters("test{obj}").isValid).toBe(false);
    });
  });

  describe("validateSafety", () => {
    it("should pass safe input", () => {
      const result = validateSafety("APT28");
      expect(result.isValid).toBe(true);
      expect(result.error).toBeNull();
    });

    it("should reject control characters", () => {
      const result = validateSafety("test\x00");
      expect(result.isValid).toBe(false);
      expect(result.error).toContain("Control characters");
    });

    it("should reject emojis", () => {
      const result = validateSafety("test 😀");
      expect(result.isValid).toBe(false);
      expect(result.error).toContain("Emojis");
    });

    it("should reject escape sequences", () => {
      const result = validateSafety("test\\n");
      expect(result.isValid).toBe(false);
      expect(result.error).toContain("Escape sequences");
    });

    it("should reject code patterns", () => {
      const result = validateSafety("<script>alert(1)</script>");
      expect(result.isValid).toBe(false);
    });
  });

  describe("sanitizeInput", () => {
    it("should trim and normalize", () => {
      expect(sanitizeInput("  APT28  ")).toBe("APT28");
    });

    it("should collapse multiple spaces", () => {
      expect(sanitizeInput("APT   28")).toBe("APT 28");
    });

    it("should normalize unicode", () => {
      const input = "  café  ";
      const result = sanitizeInput(input);
      expect(result).toBe("café");
      expect(result.charAt(0)).not.toBe(" ");
    });

    it("should handle empty input", () => {
      expect(sanitizeInput("")).toBe("");
      expect(sanitizeInput("   ")).toBe("");
    });

    it("should handle non-string input", () => {
      expect(sanitizeInput(null)).toBe("");
      expect(sanitizeInput(undefined)).toBe("");
    });
  });

  describe("validateInput - Main validation function", () => {
    it("should validate correct input", () => {
      const result = validateInput("APT28");
      expect(result.isValid).toBe(true);
      expect(result.error).toBeNull();
      expect(result.sanitized).toBe("APT28");
    });

    it("should trim and normalize input", () => {
      const result = validateInput("  APT28  ");
      expect(result.isValid).toBe(true);
      expect(result.sanitized).toBe("APT28");
    });

    it("should reject too short input", () => {
      const result = validateInput("AB");
      expect(result.isValid).toBe(false);
      expect(result.error).toContain("at least 3 characters");
    });

    it("should reject too long input", () => {
      const result = validateInput("a".repeat(101));
      expect(result.isValid).toBe(false);
      expect(result.error).toContain("not exceed 100 characters");
    });

    it("should reject invalid characters", () => {
      const result = validateInput("APT28!");
      expect(result.isValid).toBe(false);
      expect(result.error).toContain("Only letters, numbers");
    });

    it("should reject emojis", () => {
      const result = validateInput("APT28 😀");
      expect(result.isValid).toBe(false);
      expect(result.error).toContain("Only letters, numbers, and characters");
    });

    it("should reject code patterns", () => {
      const result = validateInput("<script>alert(1)</script>");
      expect(result.isValid).toBe(false);
      expect(result.error).toContain("Only letters, numbers, and characters");
    });

    it("should handle non-string input", () => {
      const result = validateInput(123);
      expect(result.isValid).toBe(false);
      expect(result.error).toContain("must be a string");
    });

    it("should accept valid names with spaces", () => {
      const result = validateInput("Threat Actor Group");
      expect(result.isValid).toBe(true);
      expect(result.sanitized).toBe("Threat Actor Group");
    });

    it("should accept valid names with allowed special chars", () => {
      expect(validateInput("malware.exe").isValid).toBe(true);
      expect(validateInput("user@domain").isValid).toBe(true);
      expect(validateInput("apt-28").isValid).toBe(true);
      expect(validateInput("group_name").isValid).toBe(true);
    });

    it("should collapse multiple spaces", () => {
      const result = validateInput("APT    28");
      expect(result.isValid).toBe(true);
      expect(result.sanitized).toBe("APT 28");
    });
  });

  describe("isValidForAutocomplete", () => {
    it("should accept short valid input", () => {
      expect(isValidForAutocomplete("A")).toBe(true);
      expect(isValidForAutocomplete("AB")).toBe(true);
    });

    it("should reject empty input", () => {
      expect(isValidForAutocomplete("")).toBe(false);
      expect(isValidForAutocomplete("   ")).toBe(false);
    });

    it("should reject dangerous content even when short", () => {
      expect(isValidForAutocomplete("😀")).toBe(false);
      expect(isValidForAutocomplete("\x00")).toBe(false);
    });

    it("should accept normal input", () => {
      expect(isValidForAutocomplete("APT")).toBe(true);
      expect(isValidForAutocomplete("APT28")).toBe(true);
    });
  });

  describe("escapeHtml", () => {
    it("should escape HTML entities", () => {
      expect(escapeHtml("<script>")).toBe("&lt;script&gt;");
      expect(escapeHtml("a & b")).toBe("a &amp; b");
      expect(escapeHtml('"quoted"')).toBe("&quot;quoted&quot;");
      expect(escapeHtml("'quoted'")).toBe("&#x27;quoted&#x27;");
    });

    it("should handle empty string", () => {
      expect(escapeHtml("")).toBe("");
    });

    it("should handle non-string input", () => {
      expect(escapeHtml(null)).toBe("");
    });

    it("should escape all dangerous characters", () => {
      const dangerous = "<>&\"'/";
      const escaped = escapeHtml(dangerous);
      expect(escaped).not.toContain("<");
      expect(escaped).not.toContain(">");
      expect(escaped).toContain("&lt;");
      expect(escaped).toContain("&gt;");
      expect(escaped).toContain("&amp;");
    });
  });

  describe("Edge cases and real-world scenarios", () => {
    it("should handle typical threat actor names", () => {
      expect(validateInput("APT28").isValid).toBe(true);
      expect(validateInput("Fancy Bear").isValid).toBe(true);
      expect(validateInput("Lazarus Group").isValid).toBe(true);
    });

    it("should handle malware names", () => {
      expect(validateInput("WannaCry").isValid).toBe(true);
      expect(validateInput("Emotet").isValid).toBe(true);
      expect(validateInput("trojan.win32").isValid).toBe(true);
    });

    it("should handle CVE identifiers", () => {
      expect(validateInput("CVE-2021-44228").isValid).toBe(true);
    });

    it("should handle email-like patterns", () => {
      expect(validateInput("user@example.com").isValid).toBe(true);
    });

    it("should handle IP addresses", () => {
      expect(validateInput("192.168.1.1").isValid).toBe(true);
    });

    it("should handle domain names", () => {
      expect(validateInput("example.com").isValid).toBe(true);
      expect(validateInput("sub-domain.example.com").isValid).toBe(true);
    });

    it("should reject SQL injection attempts", () => {
      expect(validateInput("' OR '1'='1").isValid).toBe(false);
      expect(validateInput("admin'--").isValid).toBe(false);
    });

    it("should reject Cypher injection attempts", () => {
      expect(validateInput("') MATCH (n) DETACH DELETE n//").isValid).toBe(
        false,
      );
    });
  });

  describe("Performance and boundary testing", () => {
    it("should handle exactly 3 characters", () => {
      expect(validateInput("ABC").isValid).toBe(true);
    });

    it("should handle exactly 100 characters", () => {
      const input = "A".repeat(100);
      expect(validateInput(input).isValid).toBe(true);
    });

    it("should reject 101 characters", () => {
      const input = "A".repeat(101);
      expect(validateInput(input).isValid).toBe(false);
    });

    it("should handle mixed valid characters at max length", () => {
      const input = "ABCabc123.-_@".repeat(7) + "ABCabc123"; // Exactly 100 chars
      expect(input.length).toBe(100);
      expect(validateInput(input).isValid).toBe(true);
    });
  });
});
