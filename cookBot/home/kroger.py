import urllib.request
import urllib.parse
import urllib.error
import json
import base64
from django.core.cache import cache
from django.conf import settings
 
 
KROGER_BASE_URL = "https://api-ce.kroger.com/v1"
 
 
def _get_access_token():
    """
    Fetches a client_credentials OAuth token from Kroger.
    Caches the token until 60 seconds before it expires to avoid redundant requests.
    """
    cached_token = cache.get("kroger_access_token")
    if cached_token:
        return cached_token
 
    client_id = settings.KROGER_CLIENT_ID
    client_secret = settings.KROGER_CLIENT_SECRET
 
    # Encode credentials as Base64 for the Authorization header
    credentials = base64.b64encode(f"{client_id}:{client_secret}".encode()).decode()
 
    body = urllib.parse.urlencode({
        "grant_type": "client_credentials",
        "scope": "product.compact",
    }).encode()
 
    req = urllib.request.Request(
        f"{KROGER_BASE_URL}/connect/oauth2/token",
        data=body,
        headers={
            "Content-Type": "application/x-www-form-urlencoded",
            "Authorization": f"Basic {credentials}",
        },
    )
 
    with urllib.request.urlopen(req) as res:
        data = json.loads(res.read().decode())
 
    token = data["access_token"]
    expires_in = data.get("expires_in", 1800)
 
    # Cache with a 60-second buffer before expiry
    cache.set("kroger_access_token", token, timeout=max(expires_in - 60, 0))
    return token
 
 
def kroger_get(endpoint, params=None):
    params = params or {}
    token = _get_access_token()
    encoded = urllib.parse.urlencode(params)
    url = f"{KROGER_BASE_URL}/{endpoint}?{encoded}"
 
    req = urllib.request.Request(
        url,
        headers={
            "Authorization": f"Bearer {token}",
            "Accept": "application/json",
        },
    )
 
    with urllib.request.urlopen(req) as res:
        return json.loads(res.read().decode())
 
 
def get_nearby_stores(lat, lon, radius_in_miles=10, limit=5):
    """
    Returns a list of nearby Kroger-family stores given a lat/lon.
    Each store includes name, address, city, state, zip, and distance.
    """
    data = kroger_get("locations", {
        "filter.lat.near": lat,
        "filter.lon.near": lon,
        "filter.radiusInMiles": radius_in_miles,
        "filter.limit": limit,
    })
 
    stores = []
    for location in data.get("data", []):
        address = location.get("address", {})
        stores.append({
            "name": location.get("name", "Unknown Store"),
            "address": address.get("addressLine1", ""),
            "city": address.get("city", ""),
            "state": address.get("state", ""),
            "zip": address.get("zipCode", ""),
            "distance": location.get("geolocation", {}).get("distanceInMiles", ""),
            "phone": location.get("phone", ""),
        })
 
    return stores
 