import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    # Telegram
    TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
    
    # Instagram
    INSTAGRAM_APP_ID = os.getenv('INSTAGRAM_APP_ID')
    INSTAGRAM_APP_SECRET = os.getenv('INSTAGRAM_APP_SECRET')
    REDIRECT_URI = os.getenv('REDIRECT_URI')
    
    # Supabase
    SUPABASE_URL = os.getenv('SUPABASE_URL')
    SUPABASE_KEY = os.getenv('SUPABASE_KEY')
    
    # Security
    SECRET_KEY = os.getenv('SECRET_KEY', 'fallback-secret-key')
    
    # Server
    PORT = int(os.getenv('PORT', 10000))
    
    # Instagram API URLs
    INSTAGRAM_AUTH_URL = "https://api.instagram.com/oauth/authorize"
    INSTAGRAM_TOKEN_URL = "https://api.instagram.com/oauth/access_token"
    INSTAGRAM_GRAPH_URL = "https://graph.instagram.com"
    
    @classmethod
    def validate(cls):
        """Validate required environment variables"""
        required = [
            'TELEGRAM_BOT_TOKEN',
            'INSTAGRAM_APP_ID', 
            'INSTAGRAM_APP_SECRET',
            'SUPABASE_URL',
            'SUPABASE_KEY',
            'REDIRECT_URI'
        ]
        
        missing = []
        for var in required:
            if not getattr(cls, var):
                missing.append(var)
        
        if missing:
            raise ValueError(f"Missing required environment variables: {', '.join(missing)}")
        
        return True
