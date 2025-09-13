from supabase import create_client
from datetime import datetime

class Database:
    def __init__(self, url, key):
        """Initialize database connection"""
        self.supabase = create_client(url, key)
        self.setup_tables()
    
    def setup_tables(self):
        """Create required tables if they don't exist"""
        # Note: You need to create these tables in your Supabase dashboard
        # users table
        """
        create table public.users (
            telegram_id bigint primary key,
            telegram_username text,
            instagram_id text,
            instagram_username text,
            instagram_access_token text,
            is_connected boolean default false,
            last_used timestamp with time zone default now(),
            created_at timestamp with time zone default now()
        );
        """
        
        # oauth_states table
        """
        create table public.oauth_states (
            state text primary key,
            telegram_user_id bigint references public.users(telegram_id),
            created_at timestamp with time zone default now()
        );
        """
        
        # post_history table
        """
        create table public.post_history (
            id serial primary key,
            telegram_user_id bigint references public.users(telegram_id),
            media_id text,
            caption text,
            success boolean,
            error_message text,
            created_at timestamp with time zone default now()
        );
        """

    def get_user(self, telegram_id):
        """Get user by Telegram ID"""
        response = self.supabase.table('users').select('*').eq('telegram_id', telegram_id).execute()
        return response.data[0] if response.data else None

    def create_user(self, telegram_id, telegram_username):
        """Create new user"""
        data = {
            'telegram_id': telegram_id,
            'telegram_username': telegram_username,
            'is_connected': False
        }
        return self.supabase.table('users').insert(data).execute()

    def update_user_instagram(self, telegram_id, instagram_id, instagram_username, access_token):
        """Update user's Instagram information"""
        data = {
            'instagram_id': instagram_id,
            'instagram_username': instagram_username,
            'instagram_access_token': access_token,
            'is_connected': bool(instagram_id and access_token),
            'last_used': datetime.utcnow().isoformat()
        }
        return self.supabase.table('users').update(data).eq('telegram_id', telegram_id).execute()

    def store_oauth_state(self, state, telegram_user_id):
        """Store OAuth state"""
        data = {
            'state': state,
            'telegram_user_id': telegram_user_id
        }
        return self.supabase.table('oauth_states').insert(data).execute()

    def get_oauth_state(self, state):
        """Get OAuth state"""
        response = self.supabase.table('oauth_states').select('*').eq('state', state).execute()
        return response.data[0] if response.data else None

    def delete_oauth_state(self, state):
        """Delete OAuth state"""
        return self.supabase.table('oauth_states').delete().eq('state', state).execute()

    def add_post_history(self, telegram_user_id, media_id, caption, success=True, error_message=None):
        """Add post to history"""
        data = {
            'telegram_user_id': telegram_user_id,
            'media_id': media_id,
            'caption': caption,
            'success': success,
            'error_message': error_message
        }
        return self.supabase.table('post_history').insert(data).execute()
