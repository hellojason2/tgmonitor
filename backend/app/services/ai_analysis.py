"""
Gemini 2.5 Flash-Lite AI analysis service.

Analyzes screenshots to generate activity captions and risk scores.
"""

import re
import io
import logging
from pathlib import Path
from typing import Optional

import google.generativeai as genai
from PIL import Image

from app.config import Settings

logger = logging.getLogger(__name__)

# Risk keywords for rule-based scoring
RISK_KEYWORDS = {
    "high": [
        r"\bupload\b", r"\btransfer\b", r"\busb\b", r"\bflash drive\b",
        r"\bcloud\b", r"\bdrive\b", r"\bdropbox\b", r"\bgoogle drive\b",
        r"\bonedrive\b", r"\biCloud\b", r"\bfilezilla\b", r"\bftp\b",
        r"\bsecurity\b", r"\bfirewall\b", r"\badmin\b", r"\bpassword\b",
        r"\bcredential\b", r"\bkeychain\b", r"\bterminal\b", r"\bsudo\b",
        r"\bssh\b", r"\bvpn\b", r"\bkeychain access\b",
    ],
    "medium": [
        r"\bemail\b", r"\bmail\b", r"\boutlook\b", r"\bgmail\b",
        r"\bchat\b", r"\bslack\b", r"\bmessages\b", r"\bzoom\b",
        r"\bteams\b", r"\bmeet\b", r"\bdiscord\b",
    ],
}


def build_prompt(app_name: Optional[str], window_title: Optional[str]) -> str:
    return (
        "You are an employee activity monitor analyzing a screenshot. "
        "Describe what the employee is doing in ONE SHORT SENTENCE. "
        "Format your response exactly as: "
        "CAPTION: <one sentence description>. "
        "Focus on: visible application, window title, and key activity. "
        f"App: {app_name or 'Unknown'}, Window: {window_title or 'Unknown'}"
    )


def calculate_risk_score(caption: str) -> str:
    """Rule-based risk scoring from caption keywords."""
    caption_lower = caption.lower()
    for keyword_pattern in RISK_KEYWORDS["high"]:
        if re.search(keyword_pattern, caption_lower, re.IGNORECASE):
            return "high"
    for keyword_pattern in RISK_KEYWORDS["medium"]:
        if re.search(keyword_pattern, caption_lower, re.IGNORECASE):
            return "medium"
    return "low"


def determine_alert_type(caption: str, risk_score: str) -> Optional[str]:
    """Determine alert type from caption if risk is high."""
    if risk_score != "high":
        return None

    caption_lower = caption.lower()
    if re.search(r"\bupload\b|\btransfer\b|\bdrive\b|\bdropbox\b|\bgoogle drive\b|\bonedrive\b|\bicloud\b|\bfilezilla\b|\bftp\b", caption_lower):
        return "file_transfer"
    if re.search(r"\busb\b|\bflash drive\b", caption_lower):
        return "usb_activity"
    if re.search(r"\bcloud\b|\bupload\b", caption_lower):
        return "cloud_upload"
    if re.search(r"\bsecurity\b|\bpassword\b|\bcredential\b|\badmin\b|\bsudo\b|\bterminal\b", caption_lower):
        return "security_event"
    return "suspicious_activity"


def analyze_screenshot(
    screenshot_path: Path,
    app_name: Optional[str],
    window_title: Optional[str],
    settings: Settings,
) -> tuple[str, str, int, float]:
    """
    Analyze a screenshot with Gemini 2.5 Flash-Lite.

    Returns:
        (caption, risk_score, tokens_used, api_cost_usd)
    """
    genai.configure(api_key=settings.gemini_api_key)

    # Load and resize image to 768px short side (tile size for Gemini)
    img = Image.open(screenshot_path)
    img.thumbnail((768, 768), Image.LANCZOS)
    img_bytes = io.BytesIO()
    img.save(img_bytes, format="JPEG", quality=95)
    img_bytes.seek(0)

    model = genai.GenerativeModel("gemini-2.5-flash-lite")

    prompt = build_prompt(app_name, window_title)

    response = model.generate_content(
        [{"mime_type": "image/jpeg", "data": img_bytes.read()}],
        generation_config={
            "max_output_tokens": 200,
            "temperature": 0.3,
        },
    )

    raw = response.text.strip()

    # Parse CAPTION: prefix
    caption = raw
    if raw.startswith("CAPTION:"):
        caption = raw[len("CAPTION:"):].strip()

    # Extract usage metadata
    usage_metadata = getattr(response, "usage_metadata", {})
    tokens_used = usage_metadata.get("total_token_count", 0) or 0

    # Cost: $0.10/MTok input for Flash-Lite
    api_cost = (tokens_used / 1_000_000) * 0.10 if tokens_used > 0 else 0.0

    risk_score = calculate_risk_score(caption)

    logger.info(
        f"Analysis complete: risk={risk_score}, tokens={tokens_used}, "
        f"cost=${api_cost:.6f}, caption={caption[:80]}"
    )

    return caption, risk_score, tokens_used, api_cost
