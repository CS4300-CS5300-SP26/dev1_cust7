import itertools
import hashlib
import urllib.request
import urllib.parse
import urllib.error
import json
from django.core.cache import cache
from django.conf import settings

# Build the key cycle once at startup from the list in settings
_KEYS = [k.strip() for k in settings.SPOONACULAR_API_KEY]
_key_cycle = itertools.cycle(_KEYS)


def _get_next_key():
    """Round-robin through keys, skipping any marked as exhausted."""
    for _ in range(len(_KEYS)):
        key = next(_key_cycle)
        if not cache.get(f"spoon_exhausted_{key}"):
            return key
    # Every key is exhausted
    return None  


def spoonacular_get(endpoint, params={}):
    #Check Cache First
    cache_key = "spoon_" + hashlib.md5(f"{endpoint}{sorted(params.items())}".encode()).hexdigest()

    cached = cache.get(cache_key)
    #free response no API call
    if cached is not None:
        return cached 
    #Rotates keys automatically on 402 
    #Key rotation
    key = _get_next_key()
    if not key:
        raise Exception("All Spoonacular API keys are exhausted for today.")

    params = dict(params) 
    params["apiKey"] = key

    encoded = urllib.parse.urlencode(params)
    req = urllib.request.Request(
        f"https://api.spoonacular.com/{endpoint}?{encoded}",
        headers={"User-Agent": "Mozilla/5.0"}
    )
    
    try:
        with urllib.request.urlopen(req) as res:
            data = json.loads(res.read().decode())
    except urllib.error.HTTPError as e:
        if e.code == 402:
            # This key is out of credits — mark it and retry with next key
            # Mark the key as exhausted if out of credits(24hr timeout)
            cache.set(f"spoon_exhausted_{key}", True, timeout=86400)
            return spoonacular_get(endpoint, params={k: v for k, v in params.items() if k != "apiKey"})
        # Re-raise anything else so views can handle it
        raise

    # Cache successful response for 1 hour
    cache.set(cache_key, data, timeout=3600)
    return data