"""Shared constants across the backend."""

# Node Labels
ALLOWED_LABELS = {
    "AttackPattern",
    "Campaign",
    "Identity",
    "Incident",
    "Indicator",
    "Malware",
    "Observable",
    "File",
    "DomainName",
    "URL",
    "EmailAddr",
    "IPv4Address",
    "Organization",
    "Report",
    "ThreatActor",
    "Tool",
    "Vulnerability",
}

# Relationship Types
ALLOWED_RELATIONSHIPS = {
    "BASED_ON",
    "DETECTS",
    "DESCRIBES",
    "EMPLOYES",
    "HAS_IDENTITY",
    "INDICATED_BY",
    "INVOLVES",
    "LAUNCHED",
    "RELATED_TO",
    "TARGETS",
    "USES",
}

# Allowed Properties (for validation)
ALLOWED_PROPERTIES = {
    "name",
    "description",
    "title",
    "published_date",
    "source",
    "aliases",
    "type",
    "id",
    "motivation",
    "first_seen",
    "last_seen",
    "version",
    "start_date",
    "end_date",
    "cve_id",
    "cvss_score",
    "family",
    "detection_date",
    "resolved_date",
    "sector",
    "region",
}

# API Configuration
DEFAULT_LIMIT = 10
MAX_LIMIT = 100
MIN_SEARCH_LENGTH = 3
AUTOCOMPLETE_TIMEOUT_MS = 50
