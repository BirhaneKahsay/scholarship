"""
Utility functions and helpers used across the application.
"""

import hashlib
import re
from datetime import datetime
from typing import Any, Dict, List, Optional
from urllib.parse import urlparse


def generate_hash(text: str, algorithm: str = "sha256") -> str:
    """
    Generate a hash for the given text.
    Used for duplicate detection and content comparison.
    
    Args:
        text: Text to hash
        algorithm: Hash algorithm (default: sha256)
        
    Returns:
        Hex digest of the hash
        
    Example:
        hash_val = generate_hash("DAAD Scholarship")
    """
    if not text:
        return ""
    
    text_bytes = text.encode("utf-8")
    return hashlib.new(algorithm, text_bytes).hexdigest()


def calculate_similarity(text1: str, text2: str) -> float:
    """
    Calculate similarity between two texts using Levenshtein distance.
    Returns value between 0 (completely different) and 1 (identical).
    
    Args:
        text1: First text
        text2: Second text
        
    Returns:
        Similarity score (0-1)
        
    Example:
        sim = calculate_similarity("DAAD Scholarship", "DAAD scholarship")
        # Returns close to 1.0
    """
    if not text1 or not text2:
        return 0.0 if text1 != text2 else 1.0
    
    # Normalize text
    text1 = text1.lower().strip()
    text2 = text2.lower().strip()
    
    if text1 == text2:
        return 1.0
    
    # Calculate Levenshtein distance
    if len(text1) < len(text2):
        text1, text2 = text2, text1
    
    if len(text2) == 0:
        return 0.0
    
    distances = range(len(text2) + 1)
    for i1, c1 in enumerate(text1):
        new_distances = [i1 + 1]
        for i2, c2 in enumerate(text2):
            if c1 == c2:
                new_distances.append(distances[i2])
            else:
                new_distances.append(
                    1 + min((distances[i2], distances[i2 + 1], new_distances[-1]))
                )
        distances = new_distances
    
    levenshtein_distance = distances[-1]
    max_length = max(len(text1), len(text2))
    
    return 1 - (levenshtein_distance / max_length)


def is_valid_url(url: str) -> bool:
    """
    Validate if a string is a valid URL.
    
    Args:
        url: URL string to validate
        
    Returns:
        True if valid URL, False otherwise
        
    Example:
        is_valid_url("https://www.daad.de/scholarships")  # True
    """
    try:
        result = urlparse(url)
        return all([result.scheme, result.netloc])
    except Exception:
        return False


def clean_text(text: str) -> str:
    """
    Clean and normalize text.
    Removes extra whitespace, special characters, etc.
    
    Args:
        text: Text to clean
        
    Returns:
        Cleaned text
    """
    if not text:
        return ""
    
    # Remove extra whitespace
    text = re.sub(r"\s+", " ", text).strip()
    
    # Remove special formatting characters
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    
    return text


def extract_emails(text: str) -> List[str]:
    """
    Extract email addresses from text.
    
    Args:
        text: Text to search for emails
        
    Returns:
        List of found email addresses
    """
    if not text:
        return []
    
    email_pattern = r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b"
    return re.findall(email_pattern, text)


def extract_urls(text: str) -> List[str]:
    """
    Extract URLs from text.
    
    Args:
        text: Text to search for URLs
        
    Returns:
        List of found URLs
    """
    if not text:
        return []
    
    url_pattern = r"https?://[^\s\)]+"
    return re.findall(url_pattern, text)


def parse_date_flexible(date_string: str) -> Optional[datetime]:
    """
    Parse date string in multiple formats.
    Handles various date formats commonly found in web content.
    
    Args:
        date_string: Date string to parse
        
    Returns:
        Parsed datetime object or None if parsing fails
        
    Example:
        parse_date_flexible("15 December 2026")
    """
    if not date_string:
        return None
    
    date_string = date_string.strip()
    
    # Common date formats
    formats = [
        "%d %B %Y",        # 15 December 2026
        "%d-%m-%Y",        # 15-12-2026
        "%d/%m/%Y",        # 15/12/2026
        "%Y-%m-%d",        # 2026-12-15
        "%B %d, %Y",       # December 15, 2026
        "%d %b %Y",        # 15 Dec 2026
        "%Y/%m/%d",        # 2026/12/15
    ]
    
    for fmt in formats:
        try:
            return datetime.strptime(date_string, fmt)
        except ValueError:
            continue
    
    return None


def is_deadline_passed(deadline: datetime) -> bool:
    """
    Check if a deadline has passed.
    
    Args:
        deadline: Deadline datetime
        
    Returns:
        True if deadline has passed, False otherwise
    """
    if not deadline:
        return True
    
    return datetime.now() > deadline


def format_for_telegram(data: Dict[str, Any]) -> str:
    """
    Format scholarship data for Telegram message.
    
    Args:
        data: Scholarship data dictionary
        
    Returns:
        Formatted message string
        
    Example:
        msg = format_for_telegram(scholarship_dict)
    """
    lines = []
    
    # Country and emoji
    country = data.get("country", "Unknown")
    country_emojis = {
        "Germany": "🇩🇪",
        "Netherlands": "🇳🇱",
        "France": "🇫🇷",
        "USA": "🇺🇸",
        "UK": "🇬🇧",
        "Canada": "🇨🇦",
        "Australia": "🇦🇺",
    }
    
    emoji = country_emojis.get(country, "🌍")
    lines.append(f"{emoji} {country}\n")
    
    # Title
    title = data.get("title", "")
    if title:
        lines.append(f"<b>{title}</b>\n")
    
    # Degree level
    degree = data.get("degree_level", "")
    if degree:
        lines.append(f"🎓 {degree}\n")
    
    # Benefits
    benefits = data.get("benefits", "")
    if benefits:
        lines.append(f"💰 Benefits\n{benefits}\n")
    
    # Deadline
    deadline = data.get("application_deadline", "")
    if deadline:
        lines.append(f"📅 Deadline\n{deadline}\n")
    
    # Link
    link = data.get("official_link", "")
    if link:
        lines.append(f"🔗 Apply\n{link}\n")
    
    # Tags
    tags = []
    if country:
        tags.append(f"#{country.replace(' ', '')}")
    tags.append("#Scholarship")
    if degree:
        tags.append(f"#{degree.split()[0]}")
    tags.append("#Ethiopia")
    
    lines.append(" ".join(tags))
    
    return "".join(lines)


def batch_list(items: List[Any], batch_size: int) -> List[List[Any]]:
    """
    Split a list into batches of specified size.
    
    Args:
        items: List to batch
        batch_size: Size of each batch
        
    Returns:
        List of batches
        
    Example:
        batches = batch_list([1,2,3,4,5], batch_size=2)
        # Returns [[1,2], [3,4], [5]]
    """
    return [items[i : i + batch_size] for i in range(0, len(items), batch_size)]


def truncate_text(text: str, max_length: int = 100, suffix: str = "...") -> str:
    """
    Truncate text to maximum length.
    
    Args:
        text: Text to truncate
        max_length: Maximum length
        suffix: Suffix to add if truncated
        
    Returns:
        Truncated text
    """
    if not text or len(text) <= max_length:
        return text
    
    return text[: max_length - len(suffix)] + suffix

