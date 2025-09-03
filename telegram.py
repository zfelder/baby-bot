import logging
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes, MessageHandler, filters
import config
import asyncio
import json
# Configure logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)
logger = logging.getLogger(__name__)
logging.getLogger("httpx").setLevel(logging.WARNING)

class TradingBot:
    def __init__(self):
        self.token = config.TELEGRAM_CREDENTIALS['bot_token']
        self.authorized_user_id = int(config.TELEGRAM_CREDENTIALS['authorized_user_id'])
        self.app = None
        self._event_loop = None  # Store event loop

    async def start_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle /start command"""
        if update.effective_user.id != self.authorized_user_id:
            return
        await update.message.reply_text("🤖 Bot Online! Send me any message and I'll echo it back.")

    async def handle_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Echo the user message."""
        if update.effective_user.id != self.authorized_user_id:
            return

        print(json.dumps(update.to_dict(), indent=2))
        await update.message.reply_text(f"Echo: {update.message.text}")

    async def send_notification(self, message: str, parse_mode: str = 'HTML') -> None:
        """Send notification to authorized user"""
        if not self.app:
            logger.error("Bot not initialized")
            return
        try:
            await self.app.bot.send_message(
                chat_id=self.authorized_user_id,
                text=message,
                parse_mode=parse_mode
            )
            logger.info(f"Notification sent: {message}")
        except Exception as e:
            logger.error(f"Failed to send notification: {e}")

    async def post_init(self, application: Application) -> None:
        """Post initialization hook to send startup message"""
        await self.send_notification(
            "🚀 Trading Bot is starting up! Ready to receive messages."
        )

    @property
    def loop(self):
        """Get the current event loop"""
        return self._event_loop

    def run(self):
        """Run the bot"""
        try:
            # Create and set event loop
            self._event_loop = asyncio.new_event_loop()
            asyncio.set_event_loop(self._event_loop)

            # Build application
            self.app = Application.builder().token(self.token).build()

            # Add handlers
            self.app.add_handler(CommandHandler("start", self.start_command))
            self.app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_message))

            # Set post init hook
            self.app.post_init = self.post_init

            # Start the bot
            self.app.run_polling(allowed_updates=Update.ALL_TYPES)

        except Exception as e:
            logger.error(f"Bot error: {e}")
            raise

trading_bot = TradingBot()
