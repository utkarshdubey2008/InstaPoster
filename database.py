from datetime import datetime
from postgrest import PostgrestClient
from supabase import create_client, Client

class Database:
    def __init__(self, url: str, key: str):
        """Initialize Supabase client"""
        self.supabase: Client = create_client(url, key)
        self.init_tables()
    
    def init_tables(self):
        """Initialize database tables if they don't exist"""
        # Create users table
        self.supabase.table("users").insert({
            "id": "schema",  # Dummy row for schema creation
            "telegram_id": "bigint",
            "telegram_username": "text",
            "instagram_id": "text",
            "instagram_username": "text", 
            "instagram_access_token": "text",
            "last_used": "timestamp",
            "is_connected": "boolean"
        }).execute()
        
        # Create oauth_states table
        self.supabase.table("oauth_states").insert({
            "id": "schema",
            "state": "text",
            "telegram_user_id": "bigint",
            "created_at": "timestamp"
        }).execute()
        
        # Create post_history table
        self.supabase.table("post_history").insert({
            "id": "schema",
            "telegram_user_id": "bigint",
            "media_id": "text",
            "caption": "text",
            "success": "boolean",
            "error_message": "text",
            "created_at": "timestamp"
        }).execute()

    def get_user(self, telegram_id: int):
        """Get user by Telegram ID"""
        return self.supabase.table("users").select("*").eq("telegram_id", telegram_id).single().execute()

    def create_user(self, telegram_id: int, telegram_username: str):
        """Create new user"""
        return self.supabase.table("users").insert({
            "telegram_id": telegram_id,
            "telegram_username": telegram_username,
            "is_connected": False,
            "last_used": datetime.utcnow().isoformat()
        }).execute()

    def update_user_instagram(self, telegram_id: int, instagram_id: str, instagram_username: str, access_token: str):
        """Update user's Instagram credentials"""
        return self.supabase.table("users").update({
            "instagram_id": instagram_id,
            "instagram_username": instagram_username,
            "instagram_access_token": access_token,
            "is_connected": True,
            "last_used": datetime.utcnow().isoformat()
        }).eq("telegram_id", telegram_id).execute()

    def store_oauth_state(self, state: str, telegram_user_id: int):
        """Store OAuth state"""
        return self.supabase.table("oauth_states").insert({
            "state": state,
            "telegram_user_id": telegram_user_id,
            "created_at": datetime.utcnow().isoformat()
        }).execute()

    def get_oauth_state(self, state: str):
        """Get OAuth state"""
        return self.supabase.table("oauth_states").select("*").eq("state", state).single().execute()

    def delete_oauth_state(self, state: str):
        """Delete OAuth state"""
        return self.supabase.table("oauth_states").delete().eq("state", state).execute()

    def add_post_history(self, telegram_user_id: int, media_id: str, caption: str, success: bool, error_message: str = None):
        """Add post to history"""
        return self.supabase.table("post_history").insert({
            "telegram_user_id": telegram_user_id,
            "media_id": media_id,
            "caption": caption,
            "success": success,
            "error_message": error_message,
            "created_at": datetime.utcnow().isoformat()
        }).execute()
