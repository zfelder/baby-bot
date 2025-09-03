import logging
from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import Application, CommandHandler, ContextTypes, MessageHandler, filters, CallbackQueryHandler
import config
import asyncio
import json
import os
from datetime import datetime, date
from zoneinfo import ZoneInfo

# Configure logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)
logger = logging.getLogger(__name__)
logging.getLogger("httpx").setLevel(logging.WARNING)

class BabyFeedingBot:
    def __init__(self):
        print("👶 Initializing Baby Feeding Bot...")
        self.token = config.TELEGRAM_CREDENTIALS['bot_token']
        self.authorized_users = config.AUTHORIZED_USERS
        self.authorized_user_ids = config.AUTHORIZED_USER_IDS
        self.authorized_user_names = config.AUTHORIZED_USER_NAMES
        self.app = None
        self._event_loop = None  # Store event loop
        self.timezone = ZoneInfo("Europe/Amsterdam")
        self.data_file = os.path.join(os.path.dirname(__file__), 'feeding_data.json')
        print(f"📁 Data file: {self.data_file}")
        print(f"🕐 Timezone: Amsterdam (Europe/Amsterdam)")
        print(f"👥 Authorized users: {', '.join(self.authorized_users.keys())}")
        # Remove caching - always read from file when needed
        print("📊 Data will be read from file on demand (no caching)")

    def load_feeding_data(self):
        """Load feeding data from JSON file - always read fresh from disk"""
        if os.path.exists(self.data_file):
            try:
                with open(self.data_file, 'r') as f:
                    data = json.load(f)
                print(f"📖 Loaded {len(data)} days of data from {self.data_file}")
                return data
            except json.JSONDecodeError as e:
                print(f"❌ Error reading JSON file: {e}. Starting with empty data.")
                logger.error(f"Error reading feeding data file: {e}")
                return {}
            except Exception as e:
                print(f"❌ Unexpected error reading file: {e}. Starting with empty data.")
                logger.error(f"Unexpected error reading feeding data file: {e}")
                return {}
        else:
            print(f"📄 Data file {self.data_file} does not exist. Starting fresh.")
            return {}

    def get_user_name(self, user_id):
        """Get user name from user ID"""
        return self.authorized_user_names.get(user_id, "Unknown")

    def is_authorized(self, user_id):
        """Check if user ID is authorized"""
        return user_id in self.authorized_user_ids

    def get_amsterdam_time(self):
        """Get current time in Amsterdam timezone"""
        return datetime.now(self.timezone)

    def save_feeding_data(self, feeding_data=None):
        """Save feeding data to JSON file"""
        if feeding_data is None:
            # If no data provided, load current data and save it (for backward compatibility)
            feeding_data = self.load_feeding_data()
        try:
            with open(self.data_file, 'w') as f:
                json.dump(feeding_data, f, indent=2, default=str)
            print(f"💾 Data saved to {self.data_file}")
        except Exception as e:
            logger.error(f"Error saving feeding data: {e}")
            print(f"❌ Error saving data: {e}")

    def add_feeding(self, amount_ml, user_id):
        """Add a feeding entry for today - read from file, modify, save back"""
        amsterdam_time = self.get_amsterdam_time()
        today = amsterdam_time.strftime("%Y-%m-%d")
        timestamp = amsterdam_time.strftime("%H:%M:%S")
        user_name = self.get_user_name(user_id)
        user_initial = user_name[0].upper() if user_name else "?"

        # Read current data from file
        feeding_data = self.load_feeding_data()

        # Ensure today's entry exists
        if today not in feeding_data:
            feeding_data[today] = []

        # Add new feeding entry
        feeding_data[today].append({
            "time": timestamp,
            "type": "drink",
            "amount_ml": amount_ml,
            "user": user_initial
        })

        # Save back to file
        self.save_feeding_data(feeding_data)

    def add_diaper_change(self, diaper_type, user_id):
        """Add a diaper change entry for today - read from file, modify, save back"""
        amsterdam_time = self.get_amsterdam_time()
        today = amsterdam_time.strftime("%Y-%m-%d")
        timestamp = amsterdam_time.strftime("%H:%M:%S")
        user_name = self.get_user_name(user_id)
        user_initial = user_name[0].upper() if user_name else "?"

        # Read current data from file
        feeding_data = self.load_feeding_data()

        # Ensure today's entry exists
        if today not in feeding_data:
            feeding_data[today] = []

        # Add new diaper change entry
        feeding_data[today].append({
            "time": timestamp,
            "type": "diaper",
            "diaper_type": diaper_type,
            "user": user_initial
        })

        # Save back to file
        self.save_feeding_data(feeding_data)

    def add_temperature(self, temperature, user_id):
        """Add a temperature measurement entry for today - read from file, modify, save back"""
        amsterdam_time = self.get_amsterdam_time()
        today = amsterdam_time.strftime("%Y-%m-%d")
        timestamp = amsterdam_time.strftime("%H:%M:%S")
        user_name = self.get_user_name(user_id)
        user_initial = user_name[0].upper() if user_name else "?"

        # Read current data from file
        feeding_data = self.load_feeding_data()

        # Ensure today's entry exists
        if today not in feeding_data:
            feeding_data[today] = []

        # Add new temperature entry
        feeding_data[today].append({
            "time": timestamp,
            "type": "temperature",
            "temperature_celsius": temperature,
            "user": user_initial
        })

        # Save back to file
        self.save_feeding_data(feeding_data)

    def get_today_feedings(self):
        """Get all feedings for today - read directly from file"""
        amsterdam_time = self.get_amsterdam_time()
        today = amsterdam_time.strftime("%Y-%m-%d")
        feeding_data = self.load_feeding_data()
        return feeding_data.get(today, [])

    def get_today_events(self):
        """Get all events (feedings and diaper changes) for today - read directly from file"""
        amsterdam_time = self.get_amsterdam_time()
        today = amsterdam_time.strftime("%Y-%m-%d")
        feeding_data = self.load_feeding_data()
        events = feeding_data.get(today, [])

        print(f"📅 Found {len(events)} events for today ({today})")
        # Sort events by time
        events.sort(key=lambda x: x['time'])
        return events

    async def start_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle /start command"""
        user_id = update.effective_user.id
        username = update.effective_user.username or "No username"
        user_name = self.get_user_name(user_id)

        print(f"📨 /start command received from User ID: {user_id} ({user_name}) (Username: {username})")

        if not self.is_authorized(user_id):
            print(f"❌ Unauthorized user {user_id} ({user_name}) tried to use /start")
            await update.message.reply_text("❌ Sorry, you are not authorized to use this bot.")
            return

        print(f"✅ Authorized user {user_id} ({user_name}) started the bot")
        await update.message.reply_text("👶 Baby Feeding Tracker Online!\n\n📋 Commands:\n/start - Toon hulp\n/today - Bekijk dagelijkse gebeurtenissen\n/toevoegen_fles - Voeg flesvoeding toe\n/toevoegen_temp - Voeg temperatuur toe\n/toevoegen_luier - Voeg luiersessie toe")

    async def today_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle /today command to show today's feedings"""
        user_id = update.effective_user.id
        username = update.effective_user.username or "No username"
        user_name = self.get_user_name(user_id)

        print(f"📨 /today command received from User ID: {user_id} ({user_name}) (Username: {username})")

        if not self.is_authorized(user_id):
            print(f"❌ Unauthorized user {user_id} ({user_name}) tried to use /today")
            await update.message.reply_text("❌ Sorry, you are not authorized to use this bot.")
            return

        print(f"✅ Authorized user {user_id} ({user_name}) requested today's events")

        events = self.get_today_events()

        if not events:
            await update.message.reply_text("📅 No events recorded today yet.")
            return

        # Separate different types of events
        feedings = [event for event in events if event.get('type') == 'drink']
        temperatures = [event for event in events if event.get('type') == 'temperature']
        diaper_changes = [event for event in events if event.get('type') == 'diaper']

        amsterdam_time = self.get_amsterdam_time()
        message = f"📅 Today's Events ({amsterdam_time.strftime('%Y-%m-%d')} - Amsterdam time):\n\n"

        # Show bottle feedings
        if feedings:
            total_ml = sum(feeding["amount_ml"] for feeding in feedings)
            message += "🍼 Flesvoedingen:\n"
            for i, feeding in enumerate(feedings, 1):
                user_initial = feeding.get('user', '?')
                message += f"  {i}. {feeding['time']} - {feeding['amount_ml']}ml [{user_initial}]\n"
            message += f"  💧 Totaal: {total_ml}ml\n\n"

        # Show temperature measurements
        if temperatures:
            message += "🌡️ Temperaturen:\n"
            for i, temp in enumerate(temperatures, 1):
                user_initial = temp.get('user', '?')
                message += f"  {i}. {temp['time']} - {temp['temperature_celsius']}°C [{user_initial}]\n"
            message += "\n"

        # Show diaper changes
        if diaper_changes:
            diaper_names = {
                "pooped": "💩 Gepoept",
                "peed": "💧 Geplast",
                "both": "🧷 Beiden"
            }
            message += "🧷 Luiersessies:\n"
            for i, diaper in enumerate(diaper_changes, 1):
                readable_name = diaper_names.get(diaper['diaper_type'], diaper['diaper_type'])
                user_initial = diaper.get('user', '?')
                message += f"  {i}. {diaper['time']} - {readable_name} [{user_initial}]\n"

        # If no events today
        if not feedings and not temperatures and not diaper_changes:
            message = f"📅 No events recorded today yet ({amsterdam_time.strftime('%Y-%m-%d')})."

        await update.message.reply_text(message)

    async def diaper_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle /toevoegen_luier command to add diaper change"""
        user_id = update.effective_user.id
        username = update.effective_user.username or "No username"
        user_name = self.get_user_name(user_id)

        print(f"📨 /toevoegen_luier command received from User ID: {user_id} ({user_name}) (Username: {username})")

        if not self.is_authorized(user_id):
            print(f"❌ Unauthorized user {user_id} ({user_name}) tried to use /toevoegen_luier")
            await update.message.reply_text("❌ Sorry, you are not authorized to use this bot.")
            return

        print(f"✅ Authorized user {user_id} ({user_name}) requested diaper change options")

        # Create inline keyboard with diaper options
        keyboard = [
            [
                InlineKeyboardButton("💩 Gepoept", callback_data="diaper_pooped"),
                InlineKeyboardButton("💧 Geplast", callback_data="diaper_peed"),
            ],
            [
                InlineKeyboardButton("🧷 Beiden", callback_data="diaper_both"),
            ]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)

        await update.message.reply_text(
            "👶 Kies het type luierwissel:",
            reply_markup=reply_markup
        )

    async def bottle_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle /toevoegen_fles command to start bottle feeding process"""
        user_id = update.effective_user.id
        username = update.effective_user.username or "No username"
        user_name = self.get_user_name(user_id)

        print(f"📨 /toevoegen_fles command received from User ID: {user_id} ({user_name}) (Username: {username})")

        if not self.is_authorized(user_id):
            print(f"❌ Unauthorized user {user_id} ({user_name}) tried to use /toevoegen_fles")
            await update.message.reply_text("❌ Sorry, you are not authorized to use this bot.")
            return

        print(f"✅ Authorized user {user_id} ({user_name}) started bottle feeding process")

        # Set user context to expect feeding amount
        context.user_data['awaiting_feeding_amount'] = True

        await update.message.reply_text("🍼 Hoeveel ml heeft de baby gedronken?")

    async def temperature_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle /toevoegen_temp command to start temperature measurement process"""
        user_id = update.effective_user.id
        username = update.effective_user.username or "No username"
        user_name = self.get_user_name(user_id)

        print(f"📨 /toevoegen_temp command received from User ID: {user_id} ({user_name}) (Username: {username})")

        if not self.is_authorized(user_id):
            print(f"❌ Unauthorized user {user_id} ({user_name}) tried to use /toevoegen_temp")
            await update.message.reply_text("❌ Sorry, you are not authorized to use this bot.")
            return

        print(f"✅ Authorized user {user_id} ({user_name}) started temperature measurement process")

        # Set user context to expect temperature value
        context.user_data['awaiting_temperature'] = True

        await update.message.reply_text("🌡️ Wat is de lichaamstemperatuur van de baby in Celsius?")

    async def handle_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle feeding amount input and other messages."""
        user_id = update.effective_user.id
        username = update.effective_user.username or "No username"
        user_name = self.get_user_name(user_id)
        message_text = update.message.text.strip()

        print(f"📨 Message received from User ID: {user_id} ({user_name}) (Username: {username}): '{message_text}'")

        if not self.is_authorized(user_id):
            print(f"❌ Unauthorized user {user_id} ({user_name}) sent message: {message_text}")
            await update.message.reply_text("❌ Sorry, you are not authorized to use this bot.")
            return

        print(f"✅ Processing message from authorized user {user_id} ({user_name}): {message_text}")

        # Check if we're waiting for a feeding amount
        if context.user_data.get('awaiting_feeding_amount'):
            try:
                amount = int(message_text)
                if amount > 0 and amount <= 500:  # Reasonable max for baby feeding
                    self.add_feeding(amount, user_id)
                    amsterdam_time = self.get_amsterdam_time()
                    print(f"🍼 Added feeding: {amount}ml for user {user_id} ({user_name})")

                    # Clear the awaiting state
                    context.user_data['awaiting_feeding_amount'] = False

                    await update.message.reply_text(f"✅ Fles toegevoegd: {amount}ml om {amsterdam_time.strftime('%H:%M:%S')} (Amsterdam tijd)")
                else:
                    await update.message.reply_text("❌ Voer een geldig aantal ml in (1-500).")
            except ValueError:
                await update.message.reply_text("❌ Voer alleen een getal in voor de ml hoeveelheid.")
            return

        # Check if we're waiting for a temperature value
        if context.user_data.get('awaiting_temperature'):
            try:
                temperature = float(message_text.replace(',', '.'))  # Handle both comma and dot decimal separators
                if temperature >= 30.0 and temperature <= 45.0:  # Reasonable range for baby temperature
                    self.add_temperature(temperature, user_id)
                    amsterdam_time = self.get_amsterdam_time()
                    print(f"🌡️ Added temperature: {temperature}°C for user {user_id} ({user_name})")

                    # Clear the awaiting state
                    context.user_data['awaiting_temperature'] = False

                    await update.message.reply_text(f"✅ Temperatuur toegevoegd: {temperature}°C om {amsterdam_time.strftime('%H:%M:%S')} (Amsterdam tijd)")
                else:
                    await update.message.reply_text("❌ Voer een geldige temperatuur in (30.0-45.0°C).")
            except ValueError:
                await update.message.reply_text("❌ Voer alleen een getal in voor de temperatuur (bijv. 36.5 of 36,5).")
            return

        # If not waiting for feeding amount, show help
        print(f"🤔 Unrecognized message from user {user_id} ({user_name}): {message_text}")
        await update.message.reply_text("🤔 Ik begrijp dat niet.\n\n📋 Beschikbare commando's:\n/start - Toon hulp\n/today - Bekijk dagelijkse gebeurtenissen\n/toevoegen_fles - Voeg flesvoeding toe\n/toevoegen_temp - Voeg temperatuur toe\n/toevoegen_luier - Voeg luiersessie toe")

    async def handle_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle callback queries from inline keyboards"""
        query = update.callback_query
        user_id = query.from_user.id
        user_name = self.get_user_name(user_id)

        await query.answer()

        if not self.is_authorized(user_id):
            print(f"❌ Unauthorized user {user_id} ({user_name}) tried to use callback")
            return

        callback_data = query.data

        if callback_data.startswith("diaper_"):
            diaper_type = callback_data.split("_")[1]

            # Map callback data to readable names
            diaper_names = {
                "pooped": "💩 Gepoept",
                "peed": "💧 Geplast",
                "both": "🧷 Beiden"
            }

            readable_name = diaper_names.get(diaper_type, diaper_type)
            self.add_diaper_change(diaper_type, user_id)

            print(f"🧷 Diaper change recorded: {diaper_type} for user {user_id} ({user_name})")

            await query.edit_message_text(
                f"✅ Luiersessie toegevoegd: {readable_name}\n"
                f"Tijd: {self.get_amsterdam_time().strftime('%H:%M:%S')} (Amsterdam tijd)"
            )

    async def send_notification(self, message: str, parse_mode: str = 'HTML') -> None:
        """Send notification to all authorized users"""
        if not self.app:
            logger.error("Bot not initialized")
            return

        for user_name, user_id in self.authorized_users.items():
            try:
                await self.app.bot.send_message(
                    chat_id=user_id,
                    text=message,
                    parse_mode=parse_mode
                )
                print(f"📤 Notification sent to {user_name} ({user_id}): {message}")
            except Exception as e:
                print(f"❌ Failed to send notification to {user_name} ({user_id}): {e}")
                logger.error(f"Failed to send notification to {user_id}: {e}")

    async def post_init(self, application: Application) -> None:
        """Post initialization hook to send startup message"""
        print("🔗 Bot successfully connected to Telegram servers")
        print(f"👥 Bot is online and listening for messages from authorized users: {', '.join(self.authorized_users.keys())}")
        print(f"🔐 Security: Only authorized users can interact with this bot")

        await self.send_notification(
            "👶 Baby Feeding Tracker is starting up! 🕐 All times are in Amsterdam timezone (CET/CEST).\n\n"
            "📋 Features:\n"
            "🍼 Track bottle feedings (/toevoegen_fles)\n"
            "🌡️ Track temperatures (/toevoegen_temp)\n"
            "🧷 Track diaper changes (/toevoegen_luier)\n"
            "📊 View daily summaries (/today)\n\n"
            "Use the commands above to track your baby's health and feeding!"
        )

    @property
    def loop(self):
        """Get the current event loop"""
        return self._event_loop

    def run(self):
        """Run the bot"""
        print("🤖 Starting Baby Feeding Bot...")
        print(f"📋 Bot Token: {self.token[:10]}...")
        print(f"👥 Authorized Users: {', '.join([f'{name} ({id})' for name, id in self.authorized_users.items()])}")

        try:
            print("🔄 Creating event loop...")
            # Create and set event loop
            self._event_loop = asyncio.new_event_loop()
            asyncio.set_event_loop(self._event_loop)

            print("🏗️ Building application...")
            # Build application
            self.app = Application.builder().token(self.token).build()

            print("📡 Adding command handlers...")
            # Add handlers
            self.app.add_handler(CommandHandler("start", self.start_command))
            self.app.add_handler(CommandHandler("today", self.today_command))
            self.app.add_handler(CommandHandler("toevoegen_fles", self.bottle_command))
            self.app.add_handler(CommandHandler("toevoegen_temp", self.temperature_command))
            self.app.add_handler(CommandHandler("toevoegen_luier", self.diaper_command))
            self.app.add_handler(CallbackQueryHandler(self.handle_callback))
            self.app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_message))

            # Set post init hook
            self.app.post_init = self.post_init

            print("🚀 Starting bot polling...")
            print("✅ Bot is running! Send messages to your bot on Telegram.")
            print("💡 Commands: /start, /today, /toevoegen_fles, /toevoegen_temp, /toevoegen_luier")
            print("🛑 Press Ctrl+C to stop the bot")
            print("🕐 All times are displayed in Amsterdam timezone (CET/CEST)")

            # Start the bot
            self.app.run_polling(allowed_updates=Update.ALL_TYPES)

        except Exception as e:
            print(f"❌ Bot error: {e}")
            logger.error(f"Bot error: {e}")
            raise

if __name__ == "__main__":
    print("🚀 Starting Baby Feeding Bot Application...")
    baby_feeding_bot = BabyFeedingBot()
    print("🎯 Bot instance created, starting main loop...")
    baby_feeding_bot.run()
else:
    print("📦 Baby Feeding Bot module loaded")
    baby_feeding_bot = BabyFeedingBot()
