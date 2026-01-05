from os import getenv
from dotenv import load_dotenv

load_dotenv()

from supabase import create_client, Client

# Your Supabase credentials
SUPABASE_URL = getenv("SUPABASE_URL")
SERVICE_ROLE_KEY = getenv("SUPABASE_SERVICE_KEY")

# Create Supabase client with admin privileges
supabase: Client = create_client(SUPABASE_URL, SERVICE_ROLE_KEY)

# The user ID (UUID) from the Supabase Auth user list
user_id = "65771fda-1388-4956-a161-86c61e48ca40"

# New metadata you want to set
new_metadata = {
    "role": "authenticated",
}

# Update user metadata
response = supabase.auth.admin.update_user_by_id(user_id, {
    "app_metadata": {"role": "hr_manager"},
})

print(response)

if not response:
    print("Error updating user:", response.error)
else:
    print("User updated successfully!")
    print(response.user)