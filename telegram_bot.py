import os
import secrets
import tempfile
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, filters, ContextTypes
from config import Config
from database import Database
from instagram_client import InstagramClient

class TelegramBot:
    def __init__(self, db, instagram_client):
        self.db = db
        self.instagram_client = instagram_client
        self.user_videos = {}  # Store videos temporarily
        self.user_captions = {}  # Store captions temporarily
    
    async def start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /start command"""
        user = update.effective_user
        
        # Create user if not exists
        db_user = self.db.get_user(user.id)
        if not db_user:
            self.db.create_user(user.id, user.username)
        
        welcome_message = f"""
🎬 Welcome to Instagram Reels Bot!

Hi {user.first_name}! I can help you post videos as Instagram Reels.

📋 Available Commands:
/connect - Connect your Instagram account
/status - Check connection status
/disconnect - Disconnect Instagram account
/help - Show this help message

🎥 To post a reel:
1. First, connect your Instagram account with /connect
2. Send me a video file
3. Use /post command to start posting process

Let's get started! Use /connect to link your Instagram account.
        """
        
        await update.message.reply_text(welcome_message)
    
    async def connect(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /connect command"""
        user_id = update.effective_user.id
        
        # Check if already connected
        db_user = self.db.get_user(user_id)
        if db_user and db_user.is_connected:
            await update.message.reply_text(
                f"✅ You're already connected to Instagram as @{db_user.instagram_username}\n"
                "Use /disconnect if you want to connect a different account."
            )
            return
        
        # Generate state for OAuth
        state = secrets.token_urlsafe(32)
        self.db.store_oauth_state(state, user_id)
        
        # Generate Instagram OAuth URL
        auth_url = self.instagram_client.generate_auth_url(state)
        
        keyboard = [[InlineKeyboardButton("🔗 Connect Instagram", url=auth_url)]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(
            "🔗 Click the button below to connect your Instagram account:\n\n"
            "⚠️ You'll be redirected to Instagram to authorize this app.\n"
            "After authorization, you'll receive a confirmation message here.",
            reply_markup=reply_markup
        )
    
    async def status(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /status command"""
        user_id = update.effective_user.id
        db_user = self.db.get_user(user_id)
        
        if not db_user:
            await update.message.reply_text("❌ You haven't started using the bot yet. Use /start first.")
            return
        
        if db_user.is_connected:
            await update.message.reply_text(
                f"✅ Connected to Instagram\n"
                f"📱 Account: @{db_user.instagram_username}\n"
                f"🔗 Connected on: {db_user.last_used.strftime('%Y-%m-%d %H:%M:%S')}\n\n"
                f"You can now send videos and use /post to share them as reels!"
            )
        else:
            await update.message.reply_text(
                "❌ Not connected to Instagram\n"
                "Use /connect to link your Instagram account."
            )
    
    async def disconnect(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /disconnect command"""
        user_id = update.effective_user.id
        db_user = self.db.get_user(user_id)
        
        if not db_user or not db_user.is_connected:
            await update.message.reply_text("❌ You're not connected to any Instagram account.")
            return
        
        keyboard = [
            [
                InlineKeyboardButton("✅ Yes, Disconnect", callback_data="disconnect_yes"),
                InlineKeyboardButton("❌ Cancel", callback_data="disconnect_no")
            ]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(
            f"⚠️ Are you sure you want to disconnect from @{db_user.instagram_username}?",
            reply_markup=reply_markup
        )
    
    async def handle_video(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle video uploads"""
        user_id = update.effective_user.id
        
        # Check if user is connected
        db_user = self.db.get_user(user_id)
        if not db_user or not db_user.is_connected:
            await update.message.reply_text(
                "❌ Please connect your Instagram account first using /connect"
            )
            return
        
        # Get video file
        video = update.message.video or update.message.document
        if not video:
            await update.message.reply_text("❌ Please send a valid video file.")
            return
        
        # Check video duration (Instagram reels: 3-90 seconds)
        if hasattr(video, 'duration') and video.duration:
            if video.duration < 3 or video.duration > 90:
                await update.message.reply_text(
                    f"❌ Video duration must be between 3-90 seconds.\n"
                    f"Your video is {video.duration} seconds long."
                )
                return
        
        # Store video temporarily
        self.user_videos[user_id] = video
        
        await update.message.reply_text(
            "📹 Video received! Now use /post to start posting process."
        )
    
    async def post(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /post command"""
        user_id = update.effective_user.id
        
        # Check if user is connected
        db_user = self.db.get_user(user_id)
        if not db_user or not db_user.is_connected:
            await update.message.reply_text(
                "❌ Please connect your Instagram account first using /connect"
            )
            return
        
        # Check if user has uploaded a video
        if user_id not in self.user_videos:
            await update.message.reply_text(
                "❌ Please send a video file first, then use /post"
            )
            return
        
        await update.message.reply_text(
            "✍️ Please send the caption for your reel:\n\n"
            "💡 Tips:\n"
            "- Use relevant hashtags\n"
            "- Keep it engaging\n"
            "- Mention other accounts with @username"
        )
        
        # Set user in caption waiting state
        context.user_data['waiting_for_caption'] = True
    
    async def handle_caption(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle caption input"""
        user_id = update.effective_user.id
        
        if not context.user_data.get('waiting_for_caption'):
            return  # Not waiting for caption
        
        caption = update.message.text
        self.user_captions[user_id] = caption
        
        # Clear waiting state
        context.user_data['waiting_for_caption'] = False
        
        # Show confirmation
        keyboard = [
            [
                InlineKeyboardButton("🚀 Post Now", callback_data="post_confirm"),
                InlineKeyboardButton("❌ Cancel", callback_data="post_cancel")
            ]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        preview_text = f"📋 Ready to post!\n\n📝 Caption:\n{caption[:200]}{'...' if len(caption) > 200 else ''}"
        
        await update.message.reply_text(
            preview_text,
            reply_markup=reply_markup
        )
    
    async def handle_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle inline keyboard callbacks"""
        query = update.callback_query
        user_id = query.from_user.id
        data = query.data
        
        await query.answer()
        
        if data == "disconnect_yes":
            # Disconnect user
            db_user = self.db.get_user(user_id)
            if db_user:
                self.db.update_user_instagram(user_id, None, None, None)
            
            await query.edit_message_text("✅ Successfully disconnected from Instagram.")
        
        elif data == "disconnect_no":
            await query.edit_message_text("❌ Disconnection cancelled.")
        
        elif data == "post_confirm":
            await self.process_reel_upload(query, user_id)
        
        elif data == "post_cancel":
            # Clean up
            self.user_videos.pop(user_id, None)
            self.user_captions.pop(user_id, None)
            
            await query.edit_message_text("❌ Post cancelled.")
    
    async def process_reel_upload(self, query, user_id):
        """Process the actual reel upload to Instagram"""
        await query.edit_message_text("🔄 Uploading your reel to Instagram...")
        
        try:
            # Get user data
            db_user = self.db.get_user(user_id)
            video = self.user_videos.get(user_id)
            caption = self.user_captions.get(user_id)
            
            if not all([db_user, video, caption]):
                await query.edit_message_text("❌ Missing required data. Please try again.")
                return
            
            # Download video file
            video_file = await video.get_file()
            
            # Create temporary file
            with tempfile.NamedTemporaryFile(suffix='.mp4', delete=False) as temp_file:
                await video_file.download_to_drive(temp_file.name)
                video_path = temp_file.name
            
            # For Instagram API, we need to upload video to a publicly accessible URL
            # This is a simplified version - in production, you'd upload to cloud storage
            # For now, we'll use a placeholder
            public_video_url = f"{Config.REDIRECT_URI.replace('/oauth/callback', '')}/video/{user_id}"
            
            # Post to Instagram
            result = self.instagram_client.post_reel(
                db_user.instagram_access_token,
                public_video_url,
                caption
            )
            
            # Clean up
            os.unlink(video_path)
            self.user_videos.pop(user_id, None)
            self.user_captions.pop(user_id, None)
            
            if result['success']:
                # Save to history
                self.db.add_post_history(
                    user_id, 
                    result['media_id'], 
                    caption,
                    success=True
                )
                
                await query.edit_message_text(
                    f"🎉 Successfully posted your reel!\n\n"
                    f"📱 Check your Instagram: @{db_user.instagram_username}\n"
                    f"🆔 Media ID: {result['media_id']}"
                )
            else:
                # Save error to history
                self.db.add_post_history(
                    user_id, 
                    None, 
                    caption,
                    success=False,
                    error_message=result['error']
                )
                
                await query.edit_message_text(
                    f"❌ Failed to post reel:\n{result['error']}\n\n"
                    f"Please try again later or contact support."
                )
        
        except Exception as e:
            print(f"Upload error: {e}")
            await query.edit_message_text(
                "❌ An error occurred while uploading. Please try again later."
            )
    
    async def help_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /help command"""
        help_text = """
🤖 Instagram Reels Bot Help

📋 Commands:
/start - Welcome message and setup
/connect - Connect your Instagram account
/status - Check connection status  
/disconnect - Disconnect Instagram account
/post - Start posting process (after sending video)
/help - Show this help message

📱 How to post a reel:
1️⃣ Connect Instagram account: /connect
2️⃣ Send a video file (3-90 seconds)
3️⃣ Use /post command
4️⃣ Enter your caption
5️⃣ Confirm and post!

⚠️ Requirements:
- Video must be 3-90 seconds long
- MP4 format recommended
- File size under 100MB

🔧 Need help? Contact support or check our documentation.
        """
        
        await update.message.reply_text(help_text)

    def create_application(self):
        """Create and configure the Telegram application"""
        application = Application.builder().token(Config.TELEGRAM_BOT_TOKEN).build()
        
        # Add handlers
        application.add_handler(CommandHandler("start", self.start))
        application.add_handler(CommandHandler("connect", self.connect))
        application.add_handler(CommandHandler("status", self.status))
        application.add_handler(CommandHandler("disconnect", self.disconnect))
        application.add_handler(CommandHandler("post", self.post))
        application.add_handler(CommandHandler("help", self.help_command))
        
        # Handle videos
        application.add_handler(MessageHandler(
            filters.VIDEO | filters.Document.VIDEO, 
            self.handle_video
        ))
        
        # Handle text (captions)
        application.add_handler(MessageHandler(
            filters.TEXT & ~filters.COMMAND, 
            self.handle_caption
        ))
        
        # Handle inline keyboard callbacks
        application.add_handler(CallbackQueryHandler(self.handle_callback))
        
        return application


# Entry point to start the bot when running the script directly
if __name__ == "__main__":
    db = Database(Config.MONGODB_URI)
    instagram_client = InstagramClient(
        Config.INSTAGRAM_APP_ID,
        Config.INSTAGRAM_APP_SECRET,
        Config.REDIRECT_URI
    )
    bot = TelegramBot(db, instagram_client)
    application = bot.create_application()
    application.run_polling()
