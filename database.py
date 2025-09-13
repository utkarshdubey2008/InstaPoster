from datetime import datetime
import os
from supabase import create_client, Client

class Database:
    def __init__(self, supabase_url: str, supabase_key: str):
        """Initialize Supabase client"""
        self.supabase: Client = create_client(supabase_url, supabase_key)
    
    def get_user(self, telegram_user_id: str) -> dict:
        """Get user by telegram ID"""
        response = self.supabase.table('users') \
            .select('*') \
            .eq('telegram_user_id', str(telegram_user_id)) \
            .execute()
        
        if response.data:
            return response.data[0]
        return None
    
    def create_user(self, telegram_user_id: str, telegram_username: str = None) -> dict:
        """Create new user"""
        user_data = {
            'telegram_user_id': str(telegram_user_id),
            'telegram_username': telegram_username,
            'instagram_user_id': None,
            'instagram_username': None,
            'instagram_access_token': None,
            'is_connected': False,
            'created_at': datetime.utcnow().isoformat(),
            'last_used': datetime.utcnow().isoformat()
        }
        
        response = self.supabase.table('users') \
            .insert(user_data) \
            .execute()
            
        if response.data:
            return response.data[0]
        return None
    
    def update_user_instagram(self, telegram_user_id: str, instagram_user_id: str, 
                            instagram_username: str, access_token: str) -> bool:
        """Update user's Instagram connection"""
        update_data = {
            'instagram_user_id': instagram_user_id,
            'instagram_username': instagram_username,
            'instagram_access_token': access_token,
            'is_connected': bool(access_token),
            'last_used': datetime.utcnow().isoformat()
        }
        
        response = self.supabase.table('users') \
            .update(update_data) \
            .eq('telegram_user_id', str(telegram_user_id)) \
            .execute()
            
        return bool(response.data)
    
    def store_oauth_state(self, state: str, telegram_user_id: str) -> bool:
        """Store OAuth state temporarily"""
        oauth_data = {
            'state': state,
            'telegram_user_id': str(telegram_user_id),
            'created_at': datetime.utcnow().isoformat()
        }
        
        response = self.supabase.table('oauth_states') \
            .insert(oauth_data) \
            .execute()
            
        return bool(response.data)
    
    def get_oauth_state(self, state: str) -> dict:
        """Get OAuth state"""
        response = self.supabase.table('oauth_states') \
            .select('*') \
            .eq('state', state) \
            .execute()
            
        if response.data:
            return response.data[0]
        return None
    
    def delete_oauth_state(self, state: str) -> bool:
        """Delete OAuth state"""
        response = self.supabase.table('oauth_states') \
            .delete() \
            .eq('state', state) \
            .execute()
            
        return bool(response.data)
    
    def add_post_history(self, telegram_user_id: str, instagram_media_id: str, 
                        caption: str, success: bool = True, error_message: str = None) -> bool:
        """Add post to history"""
        post_data = {
            'telegram_user_id': str(telegram_user_id),
            'instagram_media_id': instagram_media_id,
            'caption': caption,
            'media_type': 'REEL',
            'success': success,
            'error_message': error_message,
            'posted_at': datetime.utcnow().isoformat()
        }
        
        response = self.supabase.table('post_history') \
            .insert(post_data) \
            .execute()
            
        return bool(response.data)
    
    def get_user_posts(self, telegram_user_id: str, limit: int = 10) -> list:
        """Get user's recent posts"""
        response = self.supabase.table('post_history') \
            .select('*') \
            .eq('telegram_user_id', str(telegram_user_id)) \
            .order('posted_at', desc=True) \
            .limit(limit) \
            .execute()
            
        return response.data if response.data else []
