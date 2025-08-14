import os
import time
import re
from typing import Optional, Set

import requests
import tldextract
from dotenv import load_dotenv
from email_validator import EmailNotValidError, validate_email
import dns.resolver

load_dotenv()

USER_AGENT = os.getenv("USER_AGENT", "Mozilla/5.0 (compatible; LeadScraper/1.0)")
REQUEST_TIMEOUT = int(os.getenv("REQUEST_TIMEOUT", "15"))
DELAY_SECONDS = float(os.getenv("DELAY_SECONDS", "1.0"))

HEADERS = {"User-Agent": USER_AGENT}

_email_re = re.compile(r"[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}", re.I)


def polite_get(url: str) -> Optional[requests.Response]:
    time.sleep(DELAY_SECONDS)
    try:
        resp = requests.get(url, headers=HEADERS, timeout=REQUEST_TIMEOUT, allow_redirects=True)
        if 200 <= resp.status_code < 400:
            return resp
    except requests.RequestException:
        return None
    return None


def normalize_domain(url: str) -> Optional[str]:
    try:
        parts = tldextract.extract(url)
        if not parts.registered_domain:
            return None
        return parts.registered_domain.lower()
    except Exception:
        return None


def is_same_registered_domain(a_url: str, b_url: str) -> bool:
    a = normalize_domain(a_url)
    b = normalize_domain(b_url)
    return a is not None and a == b


def load_suppression_list(path: str = "suppression_list.txt") -> Set[str]:
    entries: Set[str] = set()
    if not os.path.exists(path):
        return entries
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            value = line.strip().lower()
            if not value or value.startswith("#"):
                continue
            entries.add(value)
    return entries


def is_suppressed(value: str, suppression: Set[str]) -> bool:
    val = value.lower()
    if val in suppression:
        return True
    domain = val.split("@")[-1] if "@" in val else val
    return domain in suppression


NO_MARKETING_PHRASES = [
    "no marketing",
    "do not contact",
    "do not email", 
    "no solicitations",
    "no cold email",
    "no unsolicited",
]

# Domains to exclude (not actual businesses)
EXCLUDED_DOMAINS = {
    # Job sites
    "indeed.com", 
    "linkedin.com",
    "glassdoor.com",
    "ziprecruiter.com",
    "monster.com",
    "careerbuilder.com",
    "jobs.com",
    "workopolis.com",
    
    # Social media
    "facebook.com",
    "instagram.com",
    "twitter.com",
    "tiktok.com",
    "youtube.com",
    "snapchat.com",
    "pinterest.com",
    "reddit.com",
    
    # Review/directory sites
    "yelp.com",
    "yellowpages.com",
    "angieslist.com",
    "bbb.org",
    "foursquare.com",
    "tripadvisor.com",
    
    # News/media sites
    "cnn.com",
    "bbc.com",
    "nytimes.com",
    "washingtonpost.com",
    "reuters.com",
    "ap.org",
    "npr.org",
    "abc.com",
    "cbs.com",
    "nbc.com",
    "fox.com",
    "espn.com",
    
    # Forums/communities
    "quora.com",
    "stackoverflow.com",
    "craigslist.org",
    "nextdoor.com",
    "discord.com",
    
    # E-commerce/marketplaces
    "amazon.com",
    "ebay.com",
    "etsy.com",
    "shopify.com",
    "walmart.com",
    "target.com",
    
    # Wiki/reference
    "wikipedia.org",
    "wikihow.com",
    "answers.com",
    
    # Government/education
    "gov",
    "edu",
    ".mil",
    
    # Other platforms
    "medium.com",
    "tumblr.com",
    "blogger.com",
    "wordpress.com",
    "wix.com",
    "squarespace.com",
}

def is_excluded_domain(url: str) -> bool:
    domain = normalize_domain(url)
    if not domain:
        return False
    
    # Check if any excluded domain is in the URL domain
    if any(excluded in domain for excluded in EXCLUDED_DOMAINS):
        return True
    
    # Exclude non-US domains for US city searches
    non_us_tlds = {'.com.au', '.co.uk', '.in', '.ca', '.de', '.fr', '.it', '.es', '.nl'}
    if any(domain.endswith(tld) for tld in non_us_tlds):
        return True
    
    # Exclude obviously non-automotive domains
    non_automotive_keywords = {
        'bank', 'insurance', 'real-estate', 'hotel', 'restaurant', 'school', 'hospital',
        'kitchen', 'bath', 'remodel', 'cabinet', 'plumb', 'electric', 'hvac', 'roof'
    }
    if any(keyword in domain for keyword in non_automotive_keywords):
        return True
        
    return False


def is_automotive_business(page_text: str) -> bool:
    """Check if page content suggests it's an automotive business"""
    text_lower = page_text.lower()
    
    # Automotive keywords (must have some)
    automotive_keywords = {
        'car', 'auto', 'vehicle', 'engine', 'brake', 'transmission', 'oil change',
        'tire', 'battery', 'diagnostic', 'smog', 'emissions', 'muffler', 'exhaust'
    }
    
    # Non-automotive keywords (red flags)
    non_automotive_keywords = {
        'kitchen', 'bathroom', 'cabinet', 'countertop', 'tile', 'backsplash',
        'remodel', 'renovation', 'interior design', 'flooring', 'plumbing',
        'electrical', 'hvac', 'roofing', 'landscaping', 'construction'
    }
    
    auto_score = sum(1 for keyword in automotive_keywords if keyword in text_lower)
    non_auto_score = sum(1 for keyword in non_automotive_keywords if keyword in text_lower)
    
    # Must have automotive keywords and fewer non-automotive keywords
    return auto_score >= 2 and auto_score > non_auto_score


def page_disallows_marketing(page_text: str) -> bool:
    text_lower = page_text.lower()
    return any(phrase in text_lower for phrase in NO_MARKETING_PHRASES)


def validate_email_for_outreach(address: str, strict_mx_check: bool = False) -> bool:
    try:
        info = validate_email(address, check_deliverability=False)
        domain = info.domain
    except EmailNotValidError:
        return False
    
    if not strict_mx_check:
        return True  # Just basic syntax validation
    
    try:
        # MX lookup (only if strict_mx_check=True)
        answers = dns.resolver.resolve(domain, "MX")
        return any(getattr(rdata, "exchange", None) for rdata in answers)
    except Exception:
        return False
