// src/inputValidation.js
/**
 * Input Validation Utility
 *
 * Provides validation and sanitization for user input according to security requirements:
 * - Minimum length: 3 characters
 * - Maximum length: 100 characters
 * - Allowed characters: A-Z, a-z, 0-9, .-_@
 * - Spaces allowed between characters, but not at start/end
 * - No control characters, emojis, escape sequences, or code fragments
 *
 * Sanitization includes:
 * - Unicode normalization (NFKC)
 * - Trimming leading/trailing whitespace
 * - Converting to lowercase for backend processing
 */

/**
 * Validation result object
 * @typedef {Object} ValidationResult
 * @property {boolean} isValid - Whether input passes validation
 * @property {string|null} error - Error message if validation fails
 * @property {string} sanitized - Sanitized input (trimmed, normalized)
 */

// Validation constants
const MIN_LENGTH = 3;
const MAX_LENGTH = 100;

// Allowed characters: alphanumeric, period, hyphen, underscore, @ symbol
// Spaces are allowed but will be validated separately for position
const ALLOWED_CHARS_REGEX = /^[A-Za-z0-9.\-_@ ]+$/;

// Detect control characters (U+0000 to U+001F, U+007F to U+009F)
const CONTROL_CHARS_REGEX = /[\x00-\x1F\x7F-\x9F]/;

// Detect emojis and other non-basic multilingual plane characters
// This catches most emojis (U+1F000 and above)
const EMOJI_REGEX = /[\u{1F000}-\u{10FFFF}]/u;

// Detect escape sequences and code-like patterns
const ESCAPE_SEQUENCE_REGEX =
  /\\[nrtbfv'"\\]|\\x[0-9a-fA-F]{2}|\\u[0-9a-fA-F]{4}|\\u\{[0-9a-fA-F]+\}/;

// Detect potentially dangerous code patterns
const CODE_PATTERN_REGEX =
  /<script|<iframe|javascript:|on\w+\s*=|eval\(|Function\(/i;

/**
 * Normalize Unicode string using NFKC
 * NFKC (Compatibility Composition) normalizes formatting and composes characters
 * This handles variations in how the same character can be represented
 *
 * @param {string} input - Input string
 * @returns {string} - Normalized string
 */
export function normalizeUnicode(input) {
  if (typeof input !== "string") {
    return "";
  }
  return input.normalize("NFKC");
}

/**
 * Trim leading and trailing whitespace
 * Also collapses multiple internal spaces to single space
 *
 * @param {string} input - Input string
 * @returns {string} - Trimmed string
 */
export function trimAndCollapseSpaces(input) {
  if (typeof input !== "string") {
    return "";
  }
  // Trim start and end, then collapse multiple spaces to single space
  return input.trim().replace(/\s+/g, " ");
}

/**
 * Check if input contains control characters
 *
 * @param {string} input - Input string
 * @returns {boolean} - True if control characters found
 */
export function hasControlCharacters(input) {
  return CONTROL_CHARS_REGEX.test(input);
}

/**
 * Check if input contains emojis
 *
 * @param {string} input - Input string
 * @returns {boolean} - True if emojis found
 */
export function hasEmojis(input) {
  return EMOJI_REGEX.test(input);
}

/**
 * Check if input contains escape sequences
 *
 * @param {string} input - Input string
 * @returns {boolean} - True if escape sequences found
 */
export function hasEscapeSequences(input) {
  return ESCAPE_SEQUENCE_REGEX.test(input);
}

/**
 * Check if input contains code patterns
 *
 * @param {string} input - Input string
 * @returns {boolean} - True if code patterns found
 */
export function hasCodePatterns(input) {
  return CODE_PATTERN_REGEX.test(input);
}

/**
 * Check if input has leading or trailing spaces
 * (after normalization but before trimming)
 *
 * @param {string} input - Input string
 * @returns {boolean} - True if has leading/trailing spaces
 */
export function hasLeadingOrTrailingSpaces(input) {
  return input !== input.trim();
}

/**
 * Validate input length
 *
 * @param {string} input - Input string (after trimming)
 * @returns {{isValid: boolean, error: string|null}}
 */
export function validateLength(input) {
  if (input.length < MIN_LENGTH) {
    return {
      isValid: false,
      error: `Input must be at least ${MIN_LENGTH} characters long`,
    };
  }

  if (input.length > MAX_LENGTH) {
    return {
      isValid: false,
      error: `Input must not exceed ${MAX_LENGTH} characters`,
    };
  }

  return { isValid: true, error: null };
}

/**
 * Validate allowed characters
 *
 * @param {string} input - Input string
 * @returns {{isValid: boolean, error: string|null}}
 */
export function validateAllowedCharacters(input) {
  if (!ALLOWED_CHARS_REGEX.test(input)) {
    return {
      isValid: false,
      error:
        "Only letters, numbers, and characters . - _ @ and spaces are allowed",
    };
  }

  return { isValid: true, error: null };
}

/**
 * Validate that input doesn't contain dangerous content
 *
 * @param {string} input - Input string
 * @returns {{isValid: boolean, error: string|null}}
 */
export function validateSafety(input) {
  if (hasControlCharacters(input)) {
    return {
      isValid: false,
      error: "Control characters are not allowed",
    };
  }

  if (hasEmojis(input)) {
    return {
      isValid: false,
      error: "Emojis are not allowed",
    };
  }

  if (hasEscapeSequences(input)) {
    return {
      isValid: false,
      error: "Escape sequences are not allowed",
    };
  }

  if (hasCodePatterns(input)) {
    return {
      isValid: false,
      error: "Code fragments are not allowed",
    };
  }

  return { isValid: true, error: null };
}

/**
 * Sanitize input string
 * - Normalize Unicode (NFKC)
 * - Trim and collapse spaces
 *
 * @param {string} input - Raw input string
 * @returns {string} - Sanitized string
 */
export function sanitizeInput(input) {
  if (typeof input !== "string") {
    return "";
  }

  // Step 1: Normalize Unicode
  let sanitized = normalizeUnicode(input);

  // Step 2: Trim and collapse spaces
  sanitized = trimAndCollapseSpaces(sanitized);

  return sanitized;
}

/**
 * Main validation function
 * Validates and sanitizes user input according to all security rules
 *
 * @param {string} input - Raw input string
 * @returns {ValidationResult} - Validation result object
 *
 */
export function validateInput(input) {
  // Handle non-string input
  if (typeof input !== "string") {
    return {
      isValid: false,
      error: "Input must be a string",
      sanitized: "",
    };
  }

  // Step 1: Sanitize (normalize and trim)
  const sanitized = sanitizeInput(input);

  // Step 2: Validate length
  const lengthCheck = validateLength(sanitized);
  if (!lengthCheck.isValid) {
    return {
      isValid: false,
      error: lengthCheck.error,
      sanitized: sanitized,
    };
  }

  // Step 3: Validate allowed characters
  const charsCheck = validateAllowedCharacters(sanitized);
  if (!charsCheck.isValid) {
    return {
      isValid: false,
      error: charsCheck.error,
      sanitized: sanitized,
    };
  }

  // Step 4: Validate safety (no dangerous content)
  const safetyCheck = validateSafety(sanitized);
  if (!safetyCheck.isValid) {
    return {
      isValid: false,
      error: safetyCheck.error,
      sanitized: sanitized,
    };
  }

  // All checks passed
  return {
    isValid: true,
    error: null,
    sanitized: sanitized,
  };
}

/**
 * Quick validation for autocomplete (more permissive)
 * Only checks basic requirements, allows shorter input
 *
 * @param {string} input - Input string
 * @returns {boolean} - True if valid for autocomplete
 */
export function isValidForAutocomplete(input) {
  if (typeof input !== "string" || input.length === 0) {
    return false;
  }

  const sanitized = sanitizeInput(input);

  // For autocomplete, allow shorter input (1+ chars)
  if (sanitized.length < 1) {
    return false;
  }

  // Still check for dangerous content
  const safetyCheck = validateSafety(sanitized);
  if (!safetyCheck.isValid) {
    return false;
  }

  return true;
}

/**
 * Escape special characters for HTML display (defense in depth)
 * This is an additional safety layer when displaying user input
 *
 * @param {string} input - Input string
 * @returns {string} - HTML-escaped string
 */
export function escapeHtml(input) {
  if (typeof input !== "string") {
    return "";
  }

  const escapeMap = {
    "&": "&amp;",
    "<": "&lt;",
    ">": "&gt;",
    '"': "&quot;",
    "'": "&#x27;",
    "/": "&#x2F;",
  };

  return input.replace(/[&<>"'/]/g, (char) => escapeMap[char]);
}
