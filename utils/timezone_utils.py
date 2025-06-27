# utils/timezone_utils.py

from django.contrib.gis.geoip2 import GeoIP2
from pytz import timezone as pytz_timezone
from django.utils import timezone

def get_client_ip(request):
    """Get client IP from request headers."""
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        return x_forwarded_for.split(',')[0]
    return request.META.get('REMOTE_ADDR')

def get_user_timezone(request):
    """Detect timezone from IP address."""
    try:
        ip = get_client_ip(request)
        g = GeoIP2()
        city_data = g.city(ip)
        return city_data['time_zone']  # e.g., 'Europe/Moscow'
    except Exception:
        return 'America/New_York'  # fallback

def get_user_local_time(request):
    """Return user's current datetime in their timezone."""
    tz = get_user_timezone(request)
    return timezone.now().astimezone(pytz_timezone(tz))
