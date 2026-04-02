"""PII filter — masks sensitive data in OCR text before returning to agents."""
from __future__ import annotations

import re
from dataclasses import dataclass, field


# Default pattern definitions
PATTERNS = {
    "api_keys": [
        r"(sk-[a-zA-Z0-9_-]{10,})",           # OpenAI, Anthropic, OpenRouter
        r"(key-[a-zA-Z0-9_-]{10,})",           # generic API keys
        r"(token-[a-zA-Z0-9_-]{10,})",         # tokens
        r"(Bearer\s+[a-zA-Z0-9_.\-]{20,})",    # Bearer tokens
        r"(ghp_[a-zA-Z0-9]{36,})",             # GitHub PAT
        r"(gho_[a-zA-Z0-9]{36,})",             # GitHub OAuth
        r"(AKIA[0-9A-Z]{16})",                 # AWS access key
    ],
    "credit_cards": [
        r"(\b[0-9]{4}[\s\-]?[0-9]{4}[\s\-]?[0-9]{4}[\s\-]?[0-9]{4}\b)",  # 16 digits
    ],
    "crypto_keys": [
        r"(0x[a-fA-F0-9]{64})",                # Ethereum private key
        r"(0x[a-fA-F0-9]{40})",                # Ethereum address (optional)
    ],
    "emails": [
        r"([a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,})",
    ],
    "phones": [
        r"(\+?[0-9]{1,3}[\s\-]?\(?[0-9]{3}\)?[\s\-]?[0-9]{3}[\s\-]?[0-9]{2}[\s\-]?[0-9]{2})",
    ],
    "passwords": [
        r"(?i)(password|пароль|passwd|pwd)[\s:=]+(\S+)",
    ],
}

DEFAULT_CATEGORIES = ["api_keys", "credit_cards", "crypto_keys", "passwords"]


@dataclass
class PiiFilter:
    """Filters sensitive data from text by replacing with masked versions."""

    enabled_categories: list[str] = field(default_factory=lambda: list(DEFAULT_CATEGORIES))
    whitelist_apps: list[str] = field(default_factory=list)
    custom_patterns: dict[str, list[str]] = field(default_factory=dict)

    def _get_patterns(self) -> list[re.Pattern]:
        """Compile all enabled patterns."""
        compiled = []
        all_patterns = {**PATTERNS, **self.custom_patterns}
        for category in self.enabled_categories:
            for pattern_str in all_patterns.get(category, []):
                try:
                    compiled.append(re.compile(pattern_str))
                except re.error:
                    pass
        return compiled

    def is_whitelisted(self, app_name: str) -> bool:
        """Check if app is whitelisted (no masking)."""
        app_lower = app_name.lower()
        return any(w.lower() in app_lower for w in self.whitelist_apps)

    def mask_text(self, text: str, app_name: str = "") -> str:
        """Mask sensitive data in text. Returns masked version."""
        if not text:
            return text
        if app_name and self.is_whitelisted(app_name):
            return text

        masked = text
        for pattern in self._get_patterns():
            if pattern.groups > 1:
                # For password pattern: mask only the value (group 2)
                def replace_password(m):
                    return m.group(1) + ": " + "***"
                masked = pattern.sub(replace_password, masked)
            else:
                def replace_match(m):
                    original = m.group(0)
                    if len(original) <= 8:
                        return "***"
                    # Show first 4 and last 3 chars
                    return original[:4] + "***" + original[-3:]
                masked = pattern.sub(replace_match, masked)

        return masked

    def mask_elements(self, elements: list[dict], app_name: str = "") -> list[dict]:
        """Mask sensitive data in OCR elements list."""
        if app_name and self.is_whitelisted(app_name):
            return elements
        return [
            {**e, "text": self.mask_text(e.get("text", ""), app_name)}
            for e in elements
        ]
