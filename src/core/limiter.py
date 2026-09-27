from slowapi import Limiter
from slowapi.util import get_remote_address

# Global SlowAPI Limiter Instance.
#
# Limits are declared per route with @limiter.limit rather than through
# default_limits: a default limit makes slowapi inject a `response: Response`
# parameter into every endpoint, which breaks any route that does not declare
# one. Every state-changing and authentication route carries an explicit
# decorator instead.
limiter = Limiter(
    key_func=get_remote_address,
)
