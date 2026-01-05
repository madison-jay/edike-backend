# erp_backend/auth.py
from flask import request, g, current_app, jsonify
from functools import wraps
from supabase import create_client, Client
from typing import Optional
import jwt
import os

# Initialize Supabase clients (these will be set from app.py's config)
# We'll use current_app.config to get these values after app context is pushed
public_supabase_client: Optional[Client] = None
service_supabase_client: Optional[Client] = None


def init_supabase_clients(app):
    """Initializes global Supabase clients using app config."""
    print("Initializing Supabase clients...")
    global public_supabase_client, service_supabase_client
    public_supabase_client = create_client(app.config['SUPABASE_URL'], app.config['SUPABASE_KEY'])
    service_supabase_client = create_client(app.config['SUPABASE_URL'], app.config['SUPABASE_SERVICE_KEY'])
    print("Supabase clients initialized successfully.")
    print(f"Public client: {public_supabase_client}")
    print(f"Service client: {service_supabase_client}")

def load_user_from_jwt():
    """
    Middleware to extract and verify JWT from Authorization header.
    Sets g.current_user (auth.uid) and g.user_role (from user_metadata)
    and initializes g.supabase_user_client for RLS-aware database operations.
    """
    if request.method == "OPTIONS":
        return None

    auth_header = request.headers.get('Authorization')
    refresh_token = request.headers.get('X-Refresh-Token')
    g.current_user = None
    g.user_role = None
    g.jwt_error = None
    # Ensure public_supabase_client is initialized before use
    if service_supabase_client is None:
        init_supabase_clients(current_app)
    g.supabase_user_client = public_supabase_client # Default to public client

    if auth_header and auth_header.startswith('Bearer '):
        token = auth_header.split(' ')[1]
        try:
            decoded_token = jwt.decode(
                token,
                current_app.config['SUPABASE_JWT_SECRET'],
                algorithms=["HS256"],
                audience="authenticated"
            )
            print(f"Decoded JWT: {decoded_token.get('app_metadata', {})}") 
            g.supabase_user_client = create_client(
                current_app.config['SUPABASE_URL'],
                current_app.config['SUPABASE_KEY'],
            )
            g.service_supabase_client = create_client(
                current_app.config['SUPABASE_URL'],
                current_app.config['SUPABASE_SERVICE_KEY'],
            )

            if not refresh_token:
                raise ValueError("Refresh token is required for this operation")
            g.supabase_user_client.auth.set_session(token, refresh_token)  # Set the auth token for RLS-aware operations
            g.current_user = decoded_token['sub']  
            print("current_user: ", g.current_user)
            g.user_role = decoded_token.get("app_metadata").get('role', 'employee')  
            
            print(f"User role fetched from DB: {g.user_role}")
            

        except ValueError as ve:
            g.jwt_error = str(ve)
        except jwt.ExpiredSignatureError:
            g.jwt_error = "Token has expired"
        except jwt.InvalidTokenError:
            g.jwt_error = "Invalid token"
        except Exception as e:
            print(e)
            g.jwt_error = f"JWT processing error: {str(e)}"


def login_required(f):
    """Decorator to ensure a user is authenticated."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not g.current_user:
            return jsonify({"message": "Authentication required", "error": g.jwt_error or "No token provided"}), 401
        return f(*args, **kwargs)
    return decorated_function

def role_required(roles):
    """
    Decorator to ensure the authenticated user has one of the specified roles.
    Takes a list of allowed roles.
    """
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if not g.current_user:
                return jsonify({"message": "Authentication required", "error": g.jwt_error or "No token provided"}), 401
            if g.user_role not in roles:
                print(f"User role {g.user_role} does not have access. Required roles: {roles}")
                return jsonify({"message": "Permission denied", "required_roles": roles, "your_role": g.user_role}), 403
            return f(*args, **kwargs)
        return decorated_function
    return decorator