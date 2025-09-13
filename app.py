import os
import threading
import asyncio
from flask import Flask, request, jsonify, render_template_string
from config import Config
from database import SupabaseClient
from instagram_client import InstagramClient
from telegram_bot import TelegramBot

# Validate configuration
try:
    Config.validate()
except ValueError as e:
    print(f"Configuration error: {e}")
    exit(1)

# Initialize Flask app
app = Flask(__name__)
app.config['SECRET_KEY'] = Config.SECRET_KEY

# Initialize components
print("Connecting to Supabase...")
database = SupabaseClient(Config.SUPABASE_URL, Config.SUPABASE_KEY)
print("Supabase connected successfully!")

instagram_client = InstagramClient()
telegram_bot = TelegramBot(database, instagram_client)

# Create Telegram application
telegram_app = telegram_bot.create_application()

def run_telegram_bot():
    """Run Telegram bot in a separate thread"""
    print("Starting Telegram bot...")
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    telegram_app.run_polling(drop_pending_updates=True)

@app.route('/')
def home():
    """Home page - shows bot status"""
    return render_template_string("""
    <!DOCTYPE html>
    <html>
    <head>
        <title>Instagram Reels Bot</title>
        <meta name="viewport" content="width=device-width, initial-scale=1">
        <style>
            body { 
                font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
                margin: 0; padding: 20px; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                min-height: 100vh; color: #333;
            }
            .container { 
                max-width: 600px; margin: 0 auto; background: white; 
                padding: 40px; border-radius: 20px; box-shadow: 0 20px 40px rgba(0,0,0,0.1);
            }
            .header { text-align: center; margin-bottom: 30px; }
            .status { 
                padding: 15px 20px; border-radius: 10px; margin: 20px 0; 
                border: none; font-weight: 500;
            }
            .success { background: #d4edda; color: #155724; }
            .info { background: #e3f2fd; color: #0d47a1; }
            .feature { 
                background: #f8f9fa; padding: 15px; margin: 10px 0; 
                border-radius: 8px; border-left: 4px solid #667eea;
            }
            .code { 
                background: #f1f3f4; padding: 10px; border-radius: 6px; 
                font-family: 'Courier New', monospace; margin: 10px 0;
            }
            h1 { color: #667eea; margin: 0; }
            h2 { color: #555; border-bottom: 2px solid #eee; padding-bottom: 10px; }
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <h1>🎬 Instagram Reels Bot</h1>
                <p>Post videos to Instagram Reels directly from Telegram</p>
            </div>
            
            <div class="status success">
                ✅ Bot is running successfully!
            </div>
            
            <h2>📱 How to use:</h2>
            <div class="feature">
                <strong>1.</strong> Find the bot on Telegram and start a chat
            </div>
            <div class="feature">
                <strong>2.</strong> Use <code>/connect</code> to link your Instagram account
            </div>
            <div class="feature">
                <strong>3.</strong> Send a video file (3-90 seconds, MP4 format)
            </div>
            <div class="feature">
                <strong>4.</strong> Use <code>/post</code> to publish as Instagram Reel
            </div>
            
            <h2>🤖 Bot Commands:</h2>
            <div class="code">
/start - Get started<br>
/connect - Connect Instagram<br>
/status - Check connection<br>
/post - Post your video<br>
/help - Get help
            </div>
            
            <div class="status info">
                <strong>🌐 Callback URL:</strong> {{ request.url_root }}oauth/callback<br>
                <strong>⚡ Status:</strong> Online<br>
                <strong>🏗️ Platform:</strong> Supabase<br>
                <strong>📊 Storage:</strong> Supabase Storage
            </div>
        </div>
    </body>
    </html>
    """)

@app.route('/health')
def health_check():
    """Health check endpoint"""
    try:
        # Test Supabase connection by fetching a user
        database.check_connection()
        return jsonify({
            "status": "healthy",
            "database": "connected",
            "telegram_bot": "running"
        })
    except Exception as e:
        return jsonify({
            "status": "unhealthy",
            "error": str(e)
        }), 500

@app.route('/oauth/callback')
def oauth_callback():
    """Handle Instagram OAuth callback"""
    code = request.args.get('code')
    state = request.args.get('state')
    error = request.args.get('error')
    
    if error:
        return render_template_string("""
        <html>
        <head><title>Connection Error</title></head>
        <body style="font-family: Arial; text-align: center; margin: 50px;">
            <h1 style="color: #dc3545;">❌ Connection Failed</h1>
            <p>Error: {{ error }}</p>
            <p>Please try connecting again in the Telegram bot.</p>
        </body>
        </html>
        """, error=error), 400
    
    if not code or not state:
        return render_template_string("""
        <html>
        <head><title>Invalid Request</title></head>
        <body style="font-family: Arial; text-align: center; margin: 50px;">
            <h1 style="color: #dc3545;">❌ Invalid Request</h1>
            <p>Missing required parameters.</p>
        </body>
        </html>
        """), 400
    
    # Verify state from Supabase
    oauth_state = database.get_oauth_state(state)
    if not oauth_state:
        return render_template_string("""
        <html>
        <head><title>Invalid State</title></head>
        <body style="font-family: Arial; text-align: center; margin: 50px;">
            <h1 style="color: #dc3545;">❌ Invalid State</h1>
            <p>This authorization link has expired or is invalid.</p>
            <p>Please try connecting again in the Telegram bot.</p>
        </body>
        </html>
        """), 400
    
    telegram_user_id = oauth_state['telegram_user_id']
    
    try:
        # Exchange code for access token
        token_data = instagram_client.exchange_code_for_token(code)
        if not token_data or 'access_token' not in token_data:
            raise Exception("Failed to get access token")
        
        access_token = token_data['access_token']
        
        # Get Instagram user info
        user_info = instagram_client.get_user_info(access_token)
        if not user_info:
            raise Exception("Failed to get user info")
        
        # Update user in Supabase
        database.update_user_instagram(
            telegram_user_id,
            user_info['id'],
            user_info['username'],
            access_token
        )
        
        # Clean up OAuth state
        database.delete_oauth_state(state)
        
        return render_template_string("""
        <html>
        <head>
            <title>Connected Successfully</title>
            <meta name="viewport" content="width=device-width, initial-scale=1">
            <style>
                body { font-family: Arial, sans-serif; text-align: center; margin: 20px; background: #f0f2f5; }
                .container { max-width: 400px; margin: 50px auto; background: white; padding: 30px; border-radius: 15px; box-shadow: 0 4px 12px rgba(0,0,0,0.1); }
                .success { color: #28a745; margin-bottom: 20px; }
                .username { background: #e3f2fd; padding: 10px; border-radius: 8px; margin: 15px 0; }
                .instruction { background: #fff3cd; padding: 15px; border-radius: 8px; margin-top: 20px; color: #856404; }
            </style>
        </head>
        <body>
            <div class="container">
                <h1 class="success">✅ Connected!</h1>
                <p>Your Instagram account has been successfully connected.</p>
                
                <div class="username">
                    <strong>@{{ username }}</strong>
                </div>
                
                <div class="instruction">
                    <strong>🔄 Next Steps:</strong><br>
                    Go back to the Telegram bot and send a video to start posting reels!
                </div>
                
                <p style="margin-top: 30px; color: #666; font-size: 14px;">
                    You can safely close this window.
                </p>
            </div>
        </body>
        </html>
        """, username=user_info['username'])
        
    except Exception as e:
        print(f"OAuth callback error: {e}")
        return render_template_string("""
        <html>
        <head><title>Connection Error</title></head>
        <body style="font-family: Arial; text-align: center; margin: 50px;">
            <h1 style="color: #dc3545;">❌ Connection Error</h1>
            <p>Failed to complete the connection process.</p>
            <p>Please try again in the Telegram bot.</p>
            <p style="color: #666; font-size: 12px;">Error: {{ error }}</p>
        </body>
        </html>
        """, error=str(e)), 500

@app.route('/deauth', methods=['POST'])
def deauth_callback():
    """Handle Instagram deauthorization"""
    return jsonify({"status": "ok"})

@app.route('/delete', methods=['POST'])
def delete_callback():
    """Handle data deletion request"""
    return jsonify({"status": "ok"})

# ... rest of imports remain same ...

# Initialize components
print("Connecting to Supabase...")
database = Database(Config.SUPABASE_URL, Config.SUPABASE_KEY)
print("Supabase connected successfully!")

# ... rest of the file remains same ...

if __name__ == '__main__':
    # Start Telegram bot in background thread
    bot_thread = threading.Thread(target=run_telegram_bot, daemon=True)
    bot_thread.start()
    
    # Start Flask app
    port = Config.PORT
    print(f"Starting Flask app on port {port}")
    app.run(host='0.0.0.0', port=port, debug=False)
