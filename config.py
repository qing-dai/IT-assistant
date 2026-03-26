from dataclasses import dataclass
import os


@dataclass(frozen=True)
class ScoringWeights:
    lexical: float = 0.30
    semantic: float = 0.35
    severity: float = 0.20
    entity: float = 0.10
    freshness: float = 0.05


OPENAI_EMBEDDING_MODEL = os.getenv(
    "OPENAI_EMBEDDING_MODEL", "text-embedding-3-small")

KEEP_THRESHOLD = 0.58

HARD_KEEP_BOOST = 0.15
TITLE_KEEP_BOOST = 0.05

MAX_BODY_CHARS_LEXICAL = 1500
MAX_BODY_CHARS_EMBEDDING = 1200

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

DISCARD_TERMS = [
    "best laptop",
    "best phone",
    "buying guide",
    "review",
    "hands-on",
    "first look",
    "gaming monitor",
    "gaming laptop",
    "smartphone launch",
    "camera comparison",
    "black friday deal",
    "discount code",
    "top 10 gadgets",
    "unboxing",
    "benchmark test",
]

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
]

LEXICAL_KEYWORDS = {
    "security": 1.0,
    "vulnerability": 1.0,
    "cve": 1.0,
    "exploit": 1.0,
    "ransomware": 1.0,
    "breach": 1.0,
    "malware": 0.9,
    "patch": 0.7,
    "critical": 0.8,
    "outage": 1.0,
    "downtime": 0.9,
    "incident": 0.7,
    "disruption": 0.8,
    "degraded": 0.7,
    "failure": 0.7,
    "broken": 0.6,
    "rollback": 0.8,
    "deprecation": 0.7,
    "deprecated": 0.7,
    "end of support": 0.9,
    "end-of-support": 0.9,
    "end of life": 0.9,
    "microsoft": 0.5,
    "google cloud": 0.7,
    "aws": 0.7,
    "azure": 0.7,
    "okta": 0.8,
    "crowdstrike": 0.8,
    "windows": 0.5,
    "vmware": 0.6,
    "cisco": 0.6,
}

SEVERITY_TERMS = {
    "critical": 1.0,
    "actively exploited": 1.0,
    "urgent": 0.8,
    "emergency": 0.9,
    "widespread": 0.9,
    "global": 0.8,
    "multiple regions": 0.8,
    "production impact": 0.9,
    "service unavailable": 1.0,
    "remote code execution": 1.0,
    "privilege escalation": 0.9,
    "data loss": 0.9,
    "breach": 1.0,
    "ransomware": 1.0,
    "zero-day": 1.0,
}

VENDOR_TERMS = {
    "microsoft": 1.0,
    "aws": 1.0,
    "amazon web services": 1.0,
    "azure": 1.0,
    "google cloud": 1.0,
    "okta": 0.9,
    "crowdstrike": 0.9,
    "vmware": 0.8,
    "cisco": 0.8,
    "oracle": 0.7,
    "cloudflare": 0.8,
    "github": 0.7,
    "gitlab": 0.7,
    "salesforce": 0.7,
    "servicenow": 0.7,
    "linux kernel": 0.8,
    "windows": 0.8,
}
