import json
import os
import re
from typing import Dict, List, Optional, Set, Tuple

import google.generativeai as genai
from bs4 import BeautifulSoup

# More comprehensive email patterns
EMAIL_PATTERNS = [
    # Standard email pattern
    re.compile(r"\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b", re.I),
    # Email with spaces around @ (sometimes obfuscated)
    re.compile(r"\b[A-Z0-9._%+-]+\s*@\s*[A-Z0-9.-]+\.[A-Z]{2,}\b", re.I),
    # Email with [at] or (at) instead of @
    re.compile(r"\b[A-Z0-9._%+-]+\s*(?:\[at\]|\(at\)|@)\s*[A-Z0-9.-]+\.[A-Z]{2,}\b", re.I),
    # Email split across lines or with extra spaces
    re.compile(r"\b[A-Z0-9._%+-]+\s*[@]\s*[A-Z0-9.-]+\s*\.\s*[A-Z]{2,}\b", re.I),
]

# Very loose phone matcher for US/UK styles
PHONE_RE = re.compile(r"(?:\+?\d{1,3}[\s.-]?)?(?:\(?\d{3}\)?[\s.-]?)?\d{3}[\s.-]?\d{4}")


def extract_emails(soup: BeautifulSoup, text: Optional[str] = None) -> Set[str]:
    emails: Set[str] = set()
    
    # 1. Extract from mailto links (highest priority)
    for a in soup.select('a[href^="mailto:"]'):
        href = a.get("href", "")
        addr = href.split(":", 1)[-1].split("?")[0].strip()
        if addr:
            emails.add(addr.lower())
    
    # 2. Look in footer/contact sections first (common location)
    priority_sections = []
    for selector in ['footer', '[class*="footer"]', '[class*="contact"]', '[id*="contact"]', '[class*="bottom"]']:
        priority_sections.extend(soup.select(selector))
    
    for section in priority_sections:
        section_text = section.get_text(" ", strip=True)
        for pattern in EMAIL_PATTERNS:
            for match in pattern.findall(section_text):
                clean_email = clean_email_match(match)
                if clean_email:
                    emails.add(clean_email.lower())
    
    # 3. Search entire page text
    page_text = text or soup.get_text(" ", strip=True)
    for pattern in EMAIL_PATTERNS:
        for match in pattern.findall(page_text):
            clean_email = clean_email_match(match)
            if clean_email:
                emails.add(clean_email.lower())
    
    # 4. Look in HTML attributes and comments
    html_content = str(soup)
    for pattern in EMAIL_PATTERNS:
        for match in pattern.findall(html_content):
            clean_email = clean_email_match(match)
            if clean_email:
                emails.add(clean_email.lower())
    
    # 5. LLM fallback if no emails found and API key available
    if not emails:
        llm_emails = extract_emails_with_llm(soup)
        emails.update(llm_emails)
    
    return emails


def clean_email_match(email_text: str) -> Optional[str]:
    """Clean and validate email match"""
    if not email_text:
        return None
    
    # Clean up the email
    email = email_text.strip()
    
    # Replace common obfuscations
    email = re.sub(r'\s*\[at\]\s*', '@', email, flags=re.I)
    email = re.sub(r'\s*\(at\)\s*', '@', email, flags=re.I)
    
    # Remove extra spaces
    email = re.sub(r'\s+', '', email)
    
    # Basic validation
    if '@' not in email or '.' not in email.split('@')[-1]:
        return None
    
    # Filter out obvious garbage
    if len(email) < 5 or len(email) > 100:
        return None
    
    # Filter out common false positives
    false_positives = {'example@example.com', 'test@test.com', 'email@domain.com'}
    if email.lower() in false_positives:
        return None
    
    return email


def extract_emails_with_llm(soup: BeautifulSoup) -> Set[str]:
    """Extract emails using Google Gemini as fallback"""
    try:
        api_key = os.getenv("GOOGLE_API_KEY")
        if not api_key:
            return set()
        
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel('gemini-2.5-flash')
        
        # Get relevant page content (focus on contact sections)
        contact_content = get_contact_relevant_content(soup)
        if not contact_content or len(contact_content) < 10:
            return set()
        
        # Limit content length to avoid token limits
        if len(contact_content) > 4000:
            contact_content = contact_content[:4000] + "..."
        
        prompt = f"""You are extracting contact emails from a single business website page.

RULES:
- Return ONLY emails that are explicitly present in the provided text/HTML.
- Do NOT guess or fabricate addresses.
- If you see an obfuscated or broken-up email (e.g., "info [at] example [dot] com"), normalize it.
- If the page shows a contact form with no email, return an empty list and set reason="contact_form_only".
- If the page refers to social profiles with emails (Facebook "About"), note that.

Return JSON:
{{
  "emails": ["..."],
  "confidence": 0..1,
  "evidence_snippets": ["short snippet showing where it came from"],
  "reason": "found|contact_form_only|none_visible"
}}

<BEGIN_PAGE>
{contact_content}
<END_PAGE>"""

        response = model.generate_content(prompt)
        response_text = response.text.strip()
        
        # Clean up response text to extract JSON
        if '```json' in response_text:
            response_text = response_text.split('```json')[1].split('```')[0]
        elif '```' in response_text:
            response_text = response_text.split('```')[1].split('```')[0]
        
        # Find JSON in response
        json_start = response_text.find('{')
        json_end = response_text.rfind('}') + 1
        if json_start >= 0 and json_end > json_start:
            response_text = response_text[json_start:json_end]
        
        result = json.loads(response_text)
        
        emails = set()
        if result.get("emails"):
            for email in result["emails"]:
                clean_email = clean_email_match(str(email))
                if clean_email:
                    emails.add(clean_email.lower())
                    print(f"    LLM found email: {clean_email}")
        
        return emails
        
    except json.JSONDecodeError as e:
        print(f"    LLM JSON parsing failed: {e}")
        return set()
    except Exception as e:
        print(f"    LLM email extraction failed: {e}")
        return set()


def get_contact_relevant_content(soup: BeautifulSoup) -> str:
    """Extract contact-relevant content for LLM processing"""
    content_parts = []
    
    # Priority sections
    for selector in ['footer', '[class*="footer"]', '[class*="contact"]', '[id*="contact"]', 
                     '[class*="about"]', '[id*="about"]', 'header', '[class*="header"]']:
        sections = soup.select(selector)
        for section in sections:
            text = section.get_text(" ", strip=True)
            if text and len(text) > 20:  # Skip tiny sections
                content_parts.append(f"[{selector}] {text}")
    
    # If no priority sections found, get page title and first part of body
    if not content_parts:
        title = soup.find('title')
        if title:
            content_parts.append(f"[title] {title.get_text()}")
        
        body_text = soup.get_text(" ", strip=True)[:2000]
        content_parts.append(f"[body] {body_text}")
    
    return "\n\n".join(content_parts)


def extract_phones(soup: BeautifulSoup, text: Optional[str] = None) -> Set[str]:
    phones: Set[str] = set()
    page_text = text or soup.get_text(" ", strip=True)
    for match in PHONE_RE.findall(page_text):
        cleaned = re.sub(r"[^+\d]", "", match)
        if len(cleaned) >= 7:
            phones.add(cleaned)
    return phones


def _first(value):
    if isinstance(value, list) and value:
        return value[0]
    return value


def extract_business_info_from_jsonld(soup: BeautifulSoup) -> Tuple[Optional[str], Optional[str]]:
    name: Optional[str] = None
    address_str: Optional[str] = None
    for script in soup.find_all("script", attrs={"type": "application/ld+json"}):
        try:
            data = json.loads(script.string or "{}")
        except Exception:
            continue
        nodes: List[Dict] = []
        if isinstance(data, list):
            nodes = data
        elif isinstance(data, dict):
            nodes = [data]
        for obj in nodes:
            t = obj.get("@type")
            if not t:
                continue
            if isinstance(t, list):
                types = [x.lower() for x in t]
            else:
                types = [str(t).lower()]
            if any(x in types for x in ["localbusiness", "automotivebusiness", "organization"]):
                if not name:
                    name = _first(obj.get("name")) or name
                addr = obj.get("address")
                if isinstance(addr, dict):
                    parts = [
                        addr.get("streetAddress"),
                        addr.get("addressLocality"),
                        addr.get("addressRegion"),
                        addr.get("postalCode"),
                        addr.get("addressCountry"),
                    ]
                    address_str = ", ".join([p for p in parts if p])
                elif isinstance(addr, str):
                    address_str = addr
    return name, address_str
