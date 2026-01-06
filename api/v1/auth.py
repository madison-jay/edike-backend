# erp_backend/auth.py

from flask import request, g, current_app, jsonify
from functools import wraps
from supabase import create_client, Client
import jwt
from jwt import PyJWKClient
import os
import certifi
import ssl

# Force default SSL context to use certifi's CA bundle
ssl._create_default_https_context = ssl._create_unverified_context
# Better: create a context with certifi
default_context = ssl.create_default_context(cafile=certifi.where())
ssl._create_default_https_context = lambda: default_context

# Global Supabase clients (initialized once via init_supabase_clients)
public_supabase_client: Client | None = None
service_supabase_client: Client | None = None

# Supabase JWKS URL — replace with your actual project ref if different
JWKS_URL = "https://dxijucrxupbqfvqdttwi.supabase.co/auth/v1/.well-known/jwks.json"

# Create a single shared JWK client for efficiency
jwk_client = PyJWKClient(JWKS_URL, cache_keys=True, lifespan=3600)


def init_supabase_clients(app):
    """
    Initialize global Supabase clients using config from the Flask app.
    Call this once in your app factory (e.g., in app.py).
    """
    global public_supabase_client, service_supabase_client

    if public_supabase_client is None or service_supabase_client is None:
        print("Initializing Supabase clients...")
        public_supabase_client = create_client(
            app.config["SUPABASE_URL"], app.config["SUPABASE_KEY"]
        )
        service_supabase_client = create_client(
            app.config["SUPABASE_URL"], app.config["SUPABASE_SERVICE_KEY"]
        )
        print("Supabase clients initialized successfully.")


def load_user_from_jwt():
    """
    Middleware function to validate the Supabase JWT from the Authorization header.
    On success:
        - Sets g.current_user = user ID (sub)
        - Sets g.user_role = role from app_metadata (e.g., 'hr_manager', 'admin')
        - Sets g.supabase_user_client = public client (for potential RLS use)
    On failure:
        - Sets g.jwt_error with reason
    """
    auth_header = request.headers.get("Authorization")
    g.current_user = None
    g.user_role = None
    g.jwt_error = None
    g.supabase_user_client = public_supabase_client  # fallback

    if not auth_header or not auth_header.startswith("Bearer "):
        g.jwt_error = "Missing or invalid Authorization header"
        return

    token = auth_header.split(" ")[1]

    try:
        # Fetch the correct signing key from Supabase JWKS based on the token
        signing_key = jwk_client.get_signing_key_from_jwt(token)

        # Decode and verify the JWT
        decoded_token = jwt.decode(
            token,
            signing_key.key,
            algorithms=["ES256"],
            audience="authenticated",
            options={
                "verify_signature": True,
                "verify_exp": True,
                "verify_aud": True,
            },
        )

        # Extract user info
        g.current_user = decoded_token.get("sub")
        app_metadata = decoded_token.get("app_metadata", {})
        g.user_role = app_metadata.get("role", "employee")  # default fallback

        # Optional: you can also store the full token or decoded payload if needed
        g.jwt_payload = decoded_token

        print(f"Authenticated user: {g.current_user} | Role: {g.user_role}")

    except jwt.ExpiredSignatureError:
        g.jwt_error = "Token has expired"
    except jwt.InvalidAudienceError:
        g.jwt_error = "Invalid audience"
    except jwt.InvalidSignatureError:
        g.jwt_error = "Invalid signature"
    except jwt.InvalidKeyError:
        g.jwt_error = "Invalid key"
    except jwt.DecodeError:
        g.jwt_error = "Token decode error"
    except Exception as e:
        g.jwt_error = f"JWT verification failed: {str(e)}"
        print(f"JWT Error: {e}")


def login_required(f):
    """
    Decorator to protect routes that require authentication.
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        load_user_from_jwt()  # Ensure JWT is processed

        if not g.current_user:
            error_msg = g.jwt_error or "Authentication required"
            return jsonify({"message": error_msg}), 401

        return f(*args, **kwargs)

    return decorated_function


def role_required(allowed_roles: list[str]):
    """
    Decorator factory to restrict access to specific roles.
    Example usage:
        @role_required(['admin', 'hr_manager'])
        def some_route():
            ...
    """
    if isinstance(allowed_roles, str):
        allowed_roles = [allowed_roles]

    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            load_user_from_jwt()

            if not g.current_user:
                error_msg = g.jwt_error or "Authentication required"
                return jsonify({"message": error_msg}), 401

            if g.user_role not in allowed_roles:
                return jsonify({
                    "message": "Permission denied",
                    "your_role": g.user_role,
                    "required_roles": allowed_roles
                }), 403

            return f(*args, **kwargs)

        return decorated_function

    return decorator


# Optional: Helper to get current user info in routes
def get_current_user():
    """
    Convenience function to get user info in protected routes.
    Returns dict with id and role, or None if not authenticated.
    """
    if hasattr(g, "current_user") and g.current_user:
        return {
            "id": g.current_user,
            "role": g.user_role,
            "payload": getattr(g, "jwt_payload", None)
        }
    return None