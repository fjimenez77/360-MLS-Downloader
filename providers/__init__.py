"""
Provider registry for 360 MLS Downloader.
Each provider handles a specific tour platform (Zillow, Ricoh360, etc.)
"""

from providers import ricoh360, zillow

PROVIDERS = [zillow, ricoh360]


def detect_provider(url_or_id):
    """Detect which provider handles the given URL. Returns (provider, url_or_id) or (None, url_or_id)."""
    for provider in PROVIDERS:
        if provider.detect(url_or_id):
            return provider
    return None
