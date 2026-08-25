from slowapi import Limiter
from slowapi.util import get_remote_address

# Global SlowAPI Limiter Instance
limiter = Limiter(key_func=get_remote_address)
