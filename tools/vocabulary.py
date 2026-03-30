"""
tools/vocabulary.py — Expandable domain vocabulary for scoring tools.

This is the single place to add new terms when expanding coverage:
  - CATEGORY_PROTOTYPES: prototype texts for embedding-based category scoring
  - BM25_QUERY_TERMS:    lexical query terms for BM25 scoring
  - KEEP_TERMS:          hard-keep keyword triggers (rules-based filter)
"""

CATEGORY_PROTOTYPES = {
    "security_incident": (
        "News about critical vulnerabilities, CVEs, ransomware, zero-day exploits, "
        "active exploitation, data breaches, malware campaigns, urgent security patches, "
        "enterprise security incidents."
    ),
    "service_outage": (
        "News about cloud outages, SaaS downtime, infrastructure failures, authentication "
        "failures, network incidents, degraded service, service disruption, regional outages, "
        "enterprise IT service unavailability."
    ),
    "major_bug_patch": (
        "News about severe software bugs, broken updates, faulty patches, rollback events, "
        "kernel crashes, blue screens, application failures, major defects affecting enterprise operations."
    ),
    "vendor_advisory": (
        "News about product end-of-support, deprecation, breaking vendor changes, security advisories, "
        "forced migrations, certificate changes, API shutdowns, platform changes affecting enterprise IT teams."
    ),
}


KEEP_TERMS = [
    "cve-",
    "zero-day",
    "actively exploited",
    "ransomware",
    "data breach",
    "critical vulnerability",
    "remote code execution",
    "authentication outage",
    "service disruption",
    "service unavailable",
    "outage",
    "downtime",
    "degraded service",
    "emergency patch",
    "rollback",
    "broken update",
    "kernel panic",
    "widespread issue",
    "end of support",
    "end-of-support",
    "end of life",
    "deprecated api",
    "certificate expiration",
    "privilege escalation",
    "account compromise",
    "security advisory",
    "active exploit",
    "phishing campaign",
    "supply chain attack",
    "data theft"]


BM25_QUERY_TERMS = [
    "security",
    "vulnerability",
    "vulnerabilities",
    "cve",
    "exploit",
    "exploited",
    "ransomware",
    "breach",
    "malware",
    "patch",
    "advisory",
    "critical",
    "urgent",
    "outage",
    "downtime",
    "incident",
    "disruption",
    "degraded",
    "failure",
    "unavailable",
    "rollback",
    "broken",
    "crash",
    "deprecation",
    "deprecated",
    "migration",
    "certificate",
    "expiration",
    "authentication",
    "microsoft",
    "windows",
    "azure",
    "aws",
    "google",
    "okta",
    "crowdstrike",
    "vmware",
    "cisco",
    "cloudflare",
    "oracle",
    "hacked",
    "compromised",
    "attack",
    "backdoor",
    "infected",
    "malware",
    "stealthy",
    "exfiltration",
    "phishing"
]
