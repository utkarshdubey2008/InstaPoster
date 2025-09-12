import requests
import secrets
import time
from config import Config

class InstagramClient:
    def __init__(self):
        self.app_id = Config.INSTAGRAM_APP_ID
        self.app_secret = Config.INSTAGRAM_APP_SECRET
        self.redirect_uri = Config.REDIRECT_URI
    
    def generate_auth_url(self, state):
        """Generate Instagram OAuth URL"""
        params = {
            'client_id': self.app_id,
            'redirect_uri': self.redirect_uri,
            'scope': 'user_profile,user_media',
            'response_type': 'code',
            'state': state
        }
        
        url_params = '&'.join([f"{k}={v}" for k, v in params.items()])
        return f"{Config.INSTAGRAM_AUTH_URL}?{url_params}"
    
    def exchange_code_for_token(self, code):
        """Exchange authorization code for access token"""
        data = {
            'client_id': self.app_id,
            'client_secret': self.app_secret,
            'grant_type': 'authorization_code',
            'redirect_uri': self.redirect_uri,
            'code': code
        }
        
        try:
            response = requests.post(Config.INSTAGRAM_TOKEN_URL, data=data)
            response.raise_for_status()
            return response.json()
        except requests.RequestException as e:
            print(f"Token exchange error: {e}")
            return None
    
    def get_user_info(self, access_token):
        """Get Instagram user profile information"""
        url = f"{Config.INSTAGRAM_GRAPH_URL}/me"
        params = {
            'fields': 'id,username',
            'access_token': access_token
        }
        
        try:
            response = requests.get(url, params=params)
            response.raise_for_status()
            return response.json()
        except requests.RequestException as e:
            print(f"User info error: {e}")
            return None
    
    def create_media_container(self, access_token, video_url, caption):
        """Create media container for reel"""
        url = f"{Config.INSTAGRAM_GRAPH_URL}/me/media"
        
        data = {
            'media_type': 'REELS',
            'video_url': video_url,
            'caption': caption,
            'access_token': access_token
        }
        
        try:
            response = requests.post(url, data=data)
            response.raise_for_status()
            return response.json()
        except requests.RequestException as e:
            print(f"Media container creation error: {e}")
            return None
    
    def publish_media(self, access_token, creation_id):
        """Publish the media container"""
        url = f"{Config.INSTAGRAM_GRAPH_URL}/me/media_publish"
        
        data = {
            'creation_id': creation_id,
            'access_token': access_token
        }
        
        try:
            response = requests.post(url, data=data)
            response.raise_for_status()
            return response.json()
        except requests.RequestException as e:
            print(f"Media publish error: {e}")
            return None
    
    def check_media_status(self, access_token, container_id):
        """Check if media container is ready for publishing"""
        url = f"{Config.INSTAGRAM_GRAPH_URL}/{container_id}"
        params = {
            'fields': 'status_code',
            'access_token': access_token
        }
        
        try:
            response = requests.get(url, params=params)
            response.raise_for_status()
            result = response.json()
            return result.get('status_code') == 'FINISHED'
        except requests.RequestException as e:
            print(f"Media status check error: {e}")
            return False
    
    def post_reel(self, access_token, video_url, caption):
        """Complete reel posting workflow"""
        # Create media container
        container_result = self.create_media_container(access_token, video_url, caption)
        if not container_result or 'id' not in container_result:
            return {'success': False, 'error': 'Failed to create media container'}
        
        container_id = container_result['id']
        
        # Wait for processing (Instagram needs time to process video)
        max_attempts = 30
        for attempt in range(max_attempts):
            if self.check_media_status(access_token, container_id):
                break
            time.sleep(10)  # Wait 10 seconds between checks
        else:
            return {'success': False, 'error': 'Media processing timeout'}
        
        # Publish media
        publish_result = self.publish_media(access_token, container_id)
        if not publish_result or 'id' not in publish_result:
            return {'success': False, 'error': 'Failed to publish media'}
        
        return {
            'success': True, 
            'media_id': publish_result['id'],
            'message': 'Reel posted successfully!'
          }
