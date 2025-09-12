import os
from pymongo import MongoClient
from datetime import datetime
import secrets

class Database:
    def __init__(self, mongodb_uri):
        self.client = MongoClient(mongodb_uri)
        self.db = self.client.telegram_instagram_bot
        
        # Collections
        self.users = self.db.users
        self.oauth_states = self.db.oauth_states
        self.post_history = self.db.post_history
        
        # Create indexes
        self.users.create_index("telegram_user_id", unique=True)
        self.oauth_states.create_index("state", unique=True)
        self.oauth_states.create_index("created_at", expireAfterSeconds=3600)  # Auto-delete after 1 hour
    
    def get_user(self, telegram_user_id):
        """Get user by telegram ID"""
        return self.users.find_one({"telegram_user_id": str(telegram_user_id)})
    
    def create_user(self, telegram_user_id, telegram_username=None):
        """Create new user"""
        user_data = {
            "telegram_user_id": str(telegram_user_id),
            "telegram_username": telegram_username,
            "instagram_user_id": None,
            "instagram_username": None,
            "instagram_access_token": None,
            "is_connected": False,
            "created_at": datetime.utcnow(),
            "last_used": datetime.utcnow()
        }
        
        try:
            result = self.users.insert_one(user_data)
            user_data["_id"] = result.inserted_id
            return user_data
        except Exception as e:
            print(f"Error creating user: {e}")
            return None
    
    def update_user_instagram(self, telegram_user_id, instagram_user_id, instagram_username, access_token):
        """Update user's Instagram connection"""
        update_data = {
            "$set": {
                "instagram_user_id": instagram_user_id,
                "instagram_username": instagram_username,
                "instagram_access_token": access_token,
                "is_connected": True if access_token else False,
                "last_used": datetime.utcnow()
            }
        }
        
        result = self.users.update_one(
            {"telegram_user_id": str(telegram_user_id)}, 
            update_data
        )
        return result.modified_count > 0
    
    def store_oauth_state(self, state, telegram_user_id):
        """Store OAuth state temporarily"""
        oauth_data = {
            "state": state,
            "telegram_user_id": str(telegram_user_id),
            "created_at": datetime.utcnow()
        }
        
        try:
            self.oauth_states.insert_one(oauth_data)
            return True
        except Exception as e:
            print(f"Error storing OAuth state: {e}")
            return False
    
    def get_oauth_state(self, state):
        """Get OAuth state"""
        return self.oauth_states.find_one({"state": state})
    
    def delete_oauth_state(self, state):
        """Delete OAuth state"""
        result = self.oauth_states.delete_one({"state": state})
        return result.deleted_count > 0
    
    def add_post_history(self, telegram_user_id, instagram_media_id, caption, success=True, error_message=None):
        """Add post to history"""
        post_data = {
            "telegram_user_id": str(telegram_user_id),
            "instagram_media_id": instagram_media_id,
            "caption": caption,
            "media_type": "REEL",
            "success": success,
            "error_message": error_message,
            "posted_at": datetime.utcnow()
        }
        
        try:
            self.post_history.insert_one(post_data)
            return True
        except Exception as e:
            print(f"Error adding post history: {e}")
            return False
    
    def get_user_posts(self, telegram_user_id, limit=10):
        """Get user's recent posts"""
        return list(self.post_history.find(
            {"telegram_user_id": str(telegram_user_id)}
        ).sort("posted_at", -1).limit(limit))
