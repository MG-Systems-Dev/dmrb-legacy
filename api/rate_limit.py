"""Shared slowapi limiter instance.

Import ``limiter`` here and in api/main.py to avoid circular dependencies.
Apply to routes with: @limiter.limit("10/15minutes")
The route function must include ``request: Request`` as a parameter.
"""

from slowapi import Limiter
from slowapi.util import get_remote_address

limiter = Limiter(key_func=get_remote_address)
