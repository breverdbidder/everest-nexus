"""
Nexus Domain Scanner — Layer 6: Domain Intelligence
Checks SSL expiry, DNS records, and HTTP status for all known domains.
Runs daily via pg_cron. Generates P0 alert for SSL < 14 days, P1 for < 30 days.
"""
import os
import ssl
import socket
import logging
import json
from datetime import datetime, timezone, timedelta
from typing import Optional
import requests

logger = logging.getLogger(__name__)

SUPABASE_URL = os.environ.get("SUPABASE_URL", "")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY", "")

# All known domains per spec
KNOWN_DOMAINS = [
    {
        "domain":            "biddeed.ai",
        "registrar":         "cloudflare",
        "dns_provider":      "cloudflare",
        "hosting_provider":  "vercel",
        "purpose":           "production",
        "monthly_cost":      0.00,
    },
    {
        "domain":            "zonewise.ai",
        "registrar":         "cloudflare",
        "dns_provider":      "cloudflare",
        "hosting_provider":  "vercel",
        "purpose":           "production",
        "monthly_cost":      0.00,
    },
    {
        "domain":            "nexus.zonewise.ai",
        "registrar":         "cloudflare",
        "dns_provider":      "cloudflare",
        "hosting_provider":  "vercel",
        "purpose":           "monitoring",
        "monthly_cost":      0.00,
    },
    {
        "domain":            "watch.biddeed.ai",
        "registrar":         "cloudflare",
        "dns_provider":      "cloudflare",
        "hosting_provider":  "vercel",
        "purpose":           "monitoring",
        "monthly_cost":      0.00,
    },
]

SSL_WARN_CRITICAL_DAYS = 14
SSL_WARN_P1_DAYS       = 30


def _sb_headers() -> dict:
    return {
        "apikey":        SUPABASE_KEY,
        "Authorization": f"Bearer {SUPABASE_KEY}",
        "Content-Type":  "application/json",
        "Prefer":        "resolution=merge-duplicates",
    }


def _sb_upsert(table: str, rows: list) -> None:
    if not rows:
        return
    url = f"{SUPABASE_URL}/rest/v1/{table}"
    for i in range(0, len(rows), 50):
        batch = rows[i:i+50]
        r = requests.post(url, headers=_sb_headers(), json=batch, timeout=20)
        r.raise_for_status()


def _write_insight(insight: dict) -> None:
    try:
        url = f"{SUPABASE_URL}/rest/v1/nexus_insights"
        headers = {**_sb_headers(), "Prefer": "resolution=ignore-duplicates"}
        requests.post(url, headers=headers, json=insight, timeout=10)
    except Exception as e:
        logger.warning(f"Failed to write insight: {e}")


def check_ssl(domain: str) -> dict:
    """
    Connect via TLS and read the certificate expiry.
    Returns {ssl_expiry, ssl_issuer, ssl_ok, days_remaining}.
    """
    result = {
        "ssl_expiry":     None,
        "ssl_issuer":     None,
        "ssl_ok":         False,
        "days_remaining": None,
    }
    try:
        ctx = ssl.create_default_context()
        with ctx.wrap_socket(
            socket.create_connection((domain, 443), timeout=10),
            server_hostname=domain,
        ) as ssock:
            cert = ssock.getpeercert()

        # Parse expiry
        not_after = cert.get("notAfter", "")
        if not_after:
            expiry = datetime.strptime(not_after, "%b %d %H:%M:%S %Y %Z")
            expiry = expiry.replace(tzinfo=timezone.utc)
            days_remaining = (expiry - datetime.now(timezone.utc)).days
            result["ssl_expiry"]     = expiry.isoformat()
            result["days_remaining"] = days_remaining
            result["ssl_ok"]         = days_remaining > 0

        # Extract issuer
        issuer_parts = dict(x[0] for x in cert.get("issuer", []))
        result["ssl_issuer"] = issuer_parts.get("organizationName") or issuer_parts.get("O", "Unknown")

    except ssl.SSLCertVerificationError as e:
        logger.warning(f"SSL verification failed for {domain}: {e}")
        result["ssl_ok"] = False
    except Exception as e:
        logger.warning(f"SSL check failed for {domain}: {e}")

    return result


def check_dns(domain: str) -> list:
    """
    Resolve A records and return list of DNS record dicts.
    """
    records = []
    try:
        # Resolve A records
        answers = socket.getaddrinfo(domain, None, socket.AF_INET)
        seen_ips = set()
        for answer in answers:
            ip = answer[4][0]
            if ip not in seen_ips:
                seen_ips.add(ip)
                records.append({
                    "type":    "A",
                    "name":    domain,
                    "content": ip,
                    "ttl":     None,
                })
    except socket.gaierror as e:
        logger.warning(f"DNS resolution failed for {domain}: {e}")
        records.append({
            "type":    "ERROR",
            "name":    domain,
            "content": str(e),
            "ttl":     None,
        })
    return records


def check_http(domain: str) -> dict:
    """
    Send HTTP GET and return status code + redirect chain.
    """
    result = {
        "http_status":   None,
        "is_active":     False,
        "redirect_url":  None,
    }
    try:
        r = requests.get(
            f"https://{domain}",
            timeout=10,
            allow_redirects=True,
            headers={"User-Agent": "Nexus-DomainScanner/1.0"},
        )
        result["http_status"] = r.status_code
        result["is_active"]   = r.status_code < 500
        if r.history:
            result["redirect_url"] = r.url
    except requests.exceptions.SSLError:
        result["http_status"] = 0
        result["is_active"]   = False
    except requests.exceptions.ConnectionError:
        result["http_status"] = 0
        result["is_active"]   = False
    except Exception as e:
        logger.warning(f"HTTP check failed for {domain}: {e}")
    return result


def scan_domain(domain_config: dict) -> dict:
    """Scan a single domain: SSL + DNS + HTTP. Return nexus_domains row."""
    domain = domain_config["domain"]
    logger.info(f"Scanning domain: {domain}")

    ssl_info  = check_ssl(domain)
    dns_info  = check_dns(domain)
    http_info = check_http(domain)

    now = datetime.now(timezone.utc).isoformat()

    row = {
        "domain":           domain,
        "registrar":        domain_config.get("registrar"),
        "dns_provider":     domain_config.get("dns_provider"),
        "hosting_provider": domain_config.get("hosting_provider"),
        "ssl_expiry":       ssl_info["ssl_expiry"],
        "ssl_issuer":       ssl_info["ssl_issuer"],
        "dns_records":      dns_info,
        "is_active":        http_info["is_active"],
        "monthly_cost":     domain_config.get("monthly_cost", 0.00),
        "purpose":          domain_config.get("purpose"),
        "updated_at":       now,
    }

    # Generate insights
    days = ssl_info.get("days_remaining")
    if days is not None:
        _generate_ssl_insights(domain, days, ssl_info)

    if not http_info["is_active"]:
        _write_insight({
            "layer":           "domain",
            "insight_type":    "domain_down",
            "severity":        "critical",
            "title":           f"Domain not responding: {domain}",
            "body":            f"{domain} returned HTTP {http_info['http_status']} or failed to connect.",
            "recommendation":  f"CHECK {domain} immediately — hosting or DNS may be broken",
            "affected_entity": domain,
            "auto_fixable":    False,
            "resolved":        False,
        })

    return row


def _generate_ssl_insights(domain: str, days_remaining: int, ssl_info: dict) -> None:
    if days_remaining <= 0:
        _write_insight({
            "layer":           "domain",
            "insight_type":    "ssl_expired",
            "severity":        "critical",
            "title":           f"SSL EXPIRED: {domain}",
            "body":            f"SSL certificate for {domain} has expired. Issuer: {ssl_info.get('ssl_issuer')}. Users see security warnings.",
            "recommendation":  f"RENEW SSL certificate for {domain} immediately — it is expired",
            "affected_entity": domain,
            "auto_fixable":    False,
            "resolved":        False,
        })
    elif days_remaining <= SSL_WARN_CRITICAL_DAYS:
        _write_insight({
            "layer":           "domain",
            "insight_type":    "ssl_expiry_critical",
            "severity":        "critical",
            "title":           f"SSL expiring in {days_remaining} days: {domain}",
            "body":            f"SSL certificate for {domain} expires in {days_remaining} days ({ssl_info.get('ssl_expiry', '')[:10]}). Issuer: {ssl_info.get('ssl_issuer')}.",
            "recommendation":  f"RENEW SSL for {domain} NOW — expires in {days_remaining} days",
            "affected_entity": domain,
            "auto_fixable":    False,
            "resolved":        False,
        })
    elif days_remaining <= SSL_WARN_P1_DAYS:
        _write_insight({
            "layer":           "domain",
            "insight_type":    "ssl_expiry_warning",
            "severity":        "warning",
            "title":           f"SSL expiring soon: {domain} ({days_remaining} days)",
            "body":            f"SSL certificate for {domain} expires in {days_remaining} days ({ssl_info.get('ssl_expiry', '')[:10]}). Schedule renewal.",
            "recommendation":  f"SCHEDULE SSL renewal for {domain} — {days_remaining} days remaining",
            "affected_entity": domain,
            "auto_fixable":    False,
            "resolved":        False,
        })


def scan_all_domains(domain_configs: list = None) -> dict:
    """
    Scan all known domains. Upsert to nexus_domains. Return summary.
    """
    if domain_configs is None:
        domain_configs = KNOWN_DOMAINS

    rows = []
    active_count = 0
    ssl_ok_count = 0
    expiry_warnings = 0

    for config in domain_configs:
        try:
            row = scan_domain(config)
            rows.append(row)
            if row.get("is_active"):
                active_count += 1
            if row.get("ssl_expiry"):
                # Check if SSL is valid
                expiry = datetime.fromisoformat(row["ssl_expiry"])
                if expiry > datetime.now(timezone.utc):
                    ssl_ok_count += 1
                    days_left = (expiry - datetime.now(timezone.utc)).days
                    if days_left <= SSL_WARN_P1_DAYS:
                        expiry_warnings += 1
        except Exception as e:
            logger.error(f"Failed to scan domain {config['domain']}: {e}")

    if rows:
        _sb_upsert("nexus_domains", rows)
        logger.info(f"Upserted {len(rows)} domain rows")

    summary = {
        "domains_scanned":  len(domain_configs),
        "active_count":     active_count,
        "ssl_ok_count":     ssl_ok_count,
        "expiry_warnings":  expiry_warnings,
        "scanned_at":       datetime.now(timezone.utc).isoformat(),
    }
    logger.info(f"Domain scan complete: {summary}")
    return summary


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    summary = scan_all_domains()
    print(json.dumps(summary, indent=2))
