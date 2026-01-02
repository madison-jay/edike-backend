from os import getenv
from dotenv import load_dotenv

load_dotenv()  

class Config:
    """Base configuration class."""

    SECRET_KEY = getenv('FLASK_SECRET_KEY')
    SUPABASE_URL = getenv('SUPABASE_URL')
    SUPABASE_KEY = getenv('SUPABASE_KEY')
    SUPABASE_SERVICE_KEY = getenv('SUPABASE_SERVICE_KEY')
    SUPABASE_JWT_SECRET = getenv('SUPABASE_JWT_SECRET')

    # Ensure all required Supabase variables are set
    if not all([SUPABASE_URL, SUPABASE_KEY, SUPABASE_SERVICE_KEY, SUPABASE_JWT_SECRET]):
        raise ValueError("One or more Supabase environment variables are not set.")