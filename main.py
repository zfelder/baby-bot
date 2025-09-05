import logging
from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import Application, CommandHandler, ContextTypes, MessageHandler, filters, CallbackQueryHandler
import config
import asyncio
import json
import os
import re
from datetime import datetime, date, timedelta
from zoneinfo import ZoneInfo
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import numpy as np
from io import BytesIO

# Configure logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)
logger = logging.getLogger(__name__)
logging.getLogger("httpx").setLevel(logging.WARNING)

class BabyFeedingBot:
    def __init__(self):
        print("👸 Initializing Baby Feeding Bot...")
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

    def _validate_time_format(self, time_str):
        """Validate time format HH:MM"""
        try:
            # Check format with regex: HH:MM where H and M are digits
            if not re.match(r'^\d{1,2}:\d{2}$', time_str):
                return False

            # Parse hours and minutes
            parts = time_str.split(':')
            hours = int(parts[0])
            minutes = int(parts[1])

            # Validate ranges
            if hours < 0 or hours > 23:
                return False
            if minutes < 0 or minutes > 59:
                return False

            return True
        except (ValueError, IndexError):
            return False

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

    def add_feeding(self, amount_ml, user_id, custom_time=None):
        """Add a feeding entry for today - read from file, modify, save back"""
        amsterdam_time = self.get_amsterdam_time()
        today = amsterdam_time.strftime("%Y-%m-%d")

        # Use custom time if provided, otherwise use current time
        if custom_time:
            # custom_time should be in HH:MM format, convert to HH:MM:SS
            timestamp = f"{custom_time}:00"
        else:
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

    def delete_last_entry(self, entry_type):
        """Delete the last entry of a specific type for today - read from file, modify, save back"""
        amsterdam_time = self.get_amsterdam_time()
        today = amsterdam_time.strftime("%Y-%m-%d")

        # Read current data from file
        feeding_data = self.load_feeding_data()

        # Ensure today's entry exists
        if today not in feeding_data:
            return None, "Geen data gevonden voor vandaag"

        # Find all entries of the specified type for today
        type_entries = []
        for entry in feeding_data[today]:
            if entry.get('type') == entry_type:
                type_entries.append(entry)

        if not type_entries:
            return None, f"Geen {entry_type} entries gevonden voor vandaag"

        # Sort by time to find the last one
        type_entries.sort(key=lambda x: x['time'])

        # Get the last entry
        last_entry = type_entries[-1]

        # Remove the last entry
        feeding_data[today].remove(last_entry)

        # Save back to file
        self.save_feeding_data(feeding_data)

        return last_entry, None

    def get_total_ml_for_date(self, date_str):
        """Get total ml for a specific date"""
        feeding_data = self.load_feeding_data()
        total_ml = 0

        if date_str in feeding_data:
            for event in feeding_data[date_str]:
                if event.get('type') == 'drink':
                    total_ml += event.get('amount_ml', 0)

        return total_ml

    def get_temperature_for_date(self, date_str):
        """Get temperature readings for a specific date"""
        feeding_data = self.load_feeding_data()
        temperatures = []

        if date_str in feeding_data:
            for event in feeding_data[date_str]:
                if event.get('type') == 'temperature':
                    temperatures.append(event.get('temperature_celsius', 0))

        return temperatures

    def get_diaper_data_for_date(self, date_str):
        """Get diaper change counts for a specific date"""
        feeding_data = self.load_feeding_data()
        diaper_counts = {"pooped": 0, "peed": 0, "both": 0}

        if date_str in feeding_data:
            for event in feeding_data[date_str]:
                if event.get('type') == 'diaper':
                    diaper_type = event.get('diaper_type', '')
                    if diaper_type in diaper_counts:
                        diaper_counts[diaper_type] += 1

        return diaper_counts

    def get_diaper_totals_for_period(self, dates):
        """Get diaper totals for a list of dates - returns separate arrays for each type"""
        pooped_counts = []
        peed_counts = []
        both_counts = []

        for date in dates:
            if isinstance(date, str):
                date_str = date
            else:
                date_str = date.strftime("%Y-%m-%d")

            diaper_data = self.get_diaper_data_for_date(date_str)
            pooped_counts.append(diaper_data['pooped'])
            peed_counts.append(diaper_data['peed'])
            both_counts.append(diaper_data['both'])

        return pooped_counts, peed_counts, both_counts

    def get_weekly_stats(self):
        """Generate multi-plot graph for the past 7 days showing feeding, temperature, and diaper data"""
        amsterdam_time = self.get_amsterdam_time()
        dates = []
        ml_totals = []
        temp_data = []
        diaper_data = []

        # Get data for the past 7 days (including today)
        for i in range(6, -1, -1):  # Start from 6 days ago to today
            day = amsterdam_time - timedelta(days=i)
            date_str = day.strftime("%Y-%m-%d")
            dates.append(day)
            ml_totals.append(self.get_total_ml_for_date(date_str))

            # Get temperature data (average if multiple readings)
            temps = self.get_temperature_for_date(date_str)
            avg_temp = sum(temps) / len(temps) if temps else None
            temp_data.append(avg_temp)

            # Get diaper data (total changes)
            diapers = self.get_diaper_data_for_date(date_str)
            total_diapers = diapers['pooped'] + diapers['peed'] + diapers['both']
            diaper_data.append(total_diapers)

        # Create subplots
        fig, (ax1, ax2, ax3) = plt.subplots(3, 1, figsize=(12, 15))
        fig.suptitle('Baby Data - Afgelopen Week', fontsize=18, fontweight='bold')

        # Plot 1: Feeding data
        ax1.plot(dates, ml_totals, marker='o', linestyle='-', color='green', linewidth=2, markersize=8)
        ax1.set_title('Flesvoeding (Totaal ML per Dag)', fontsize=14)
        ax1.set_ylabel('ML', fontsize=12)
        ax1.grid(True, alpha=0.3)
        ax1.xaxis.set_major_formatter(mdates.DateFormatter('%d-%m'))
        ax1.set_xticks(dates)

        if ml_totals:
            max_ml = max(ml_totals)
            ax1.set_ylim(0, max(max_ml + 100, 200))

        for i, ml in enumerate(ml_totals):
            ax1.annotate(f'{ml}ml', (dates[i], ml_totals[i]), textcoords="offset points", xytext=(0,10), ha='center')

        # Plot 2: Temperature data
        valid_temps = [(d, t) for d, t in zip(dates, temp_data) if t is not None]
        if valid_temps:
            temp_dates, temp_values = zip(*valid_temps)
            ax2.plot(temp_dates, temp_values, marker='s', linestyle='-', color='red', linewidth=2, markersize=8)
            ax2.set_title('Temperatuur (Gemiddeld per Dag)', fontsize=14)
            ax2.set_ylabel('°C', fontsize=12)
            ax2.grid(True, alpha=0.3)
            ax2.xaxis.set_major_formatter(mdates.DateFormatter('%d-%m'))
            ax2.set_xticks(dates)

            # Draw reference line at 37°C with 50% opacity
            ax2.axhline(y=37, color='red', linestyle='-', alpha=0.5, linewidth=2, label='Normaal (37°C)')

            # Set y-axis range from 34 to 40
            ax2.set_ylim(34, 40)

            for i, temp in enumerate(temp_data):
                if temp is not None:
                    ax2.annotate(f'{temp:.1f}°C', (dates[i], temp), textcoords="offset points", xytext=(0,10), ha='center')

            for i, temp in enumerate(temp_data):
                if temp is not None:
                    ax2.annotate(f'{temp:.1f}°C', (dates[i], temp), textcoords="offset points", xytext=(0,10), ha='center')
        else:
            ax2.text(0.5, 0.5, 'Geen temperatuur data beschikbaar', ha='center', va='center', transform=ax2.transAxes)
            ax2.set_title('Temperatuur (Geen data)', fontsize=14)
            # Set default range 34 to 40 even when no data
            ax2.set_ylim(34, 40)
            # Still draw the reference line
            ax2.axhline(y=37, color='red', linestyle='-', alpha=0.5, linewidth=2, label='Normaal (37°C)')

        # Plot 3: Diaper data (bar chart)
        pooped_counts, peed_counts, both_counts = self.get_diaper_totals_for_period(dates)

        # Create bar positions
        x = np.arange(len(dates))
        width = 0.25  # width of each bar

        # Create grouped bars
        bars1 = ax3.bar(x - width, pooped_counts, width, label='Gepoept', color='#D2B48C', alpha=0.8)  # Light brown
        bars2 = ax3.bar(x, peed_counts, width, label='Geplast', color='#4169E1', alpha=0.8)  # Blue
        bars3 = ax3.bar(x + width, both_counts, width, label='Beiden', color='#8B4513', alpha=0.8)  # Dark poop brown

        # Add value labels above bars
        for bars, counts in [(bars1, pooped_counts), (bars2, peed_counts), (bars3, both_counts)]:
            for bar, count in zip(bars, counts):
                if count > 0:  # Only show label if count > 0
                    height = bar.get_height()
                    ax3.text(bar.get_x() + bar.get_width()/2., height + 0.1,
                            f'{int(count)}', ha='center', va='bottom', color='black', fontweight='bold')

        ax3.set_title('Luiers (per Type per Dag)', fontsize=14)
        ax3.set_xlabel('Datum', fontsize=12)
        ax3.set_ylabel('Aantal', fontsize=12)
        ax3.set_xticks(x)
        ax3.set_xticklabels([d.strftime('%d-%m') for d in dates])
        ax3.legend()
        ax3.grid(True, alpha=0.3, axis='y')

        # Set y-axis limits
        max_diapers = max(max(pooped_counts), max(peed_counts), max(both_counts)) if pooped_counts else 0
        ax3.set_ylim(0, max(max_diapers + 2, 5))

        plt.tight_layout()

        # Save to BytesIO for Telegram
        buf = BytesIO()
        plt.savefig(buf, format='png', dpi=100, bbox_inches='tight')
        buf.seek(0)
        plt.close()

        return buf

    def get_monthly_stats(self):
        """Generate multi-plot graph for the past 30 days showing feeding, temperature, and diaper data"""
        amsterdam_time = self.get_amsterdam_time()
        dates = []
        ml_totals = []
        temp_data = []
        diaper_data = []

        # Get data for the past 30 days (including today)
        for i in range(29, -1, -1):  # Start from 29 days ago to today
            day = amsterdam_time - timedelta(days=i)
            date_str = day.strftime("%Y-%m-%d")
            dates.append(day)
            ml_totals.append(self.get_total_ml_for_date(date_str))

            # Get temperature data (average if multiple readings)
            temps = self.get_temperature_for_date(date_str)
            avg_temp = sum(temps) / len(temps) if temps else None
            temp_data.append(avg_temp)

            # Get diaper data (total changes)
            diapers = self.get_diaper_data_for_date(date_str)
            total_diapers = diapers['pooped'] + diapers['peed'] + diapers['both']
            diaper_data.append(total_diapers)

        # Create subplots
        fig, (ax1, ax2, ax3) = plt.subplots(3, 1, figsize=(14, 16))
        fig.suptitle('Baby Data - Afgelopen Maand', fontsize=18, fontweight='bold')

        # Plot 1: Feeding data
        ax1.plot(dates, ml_totals, marker='o', linestyle='-', color='green', linewidth=2, markersize=8)
        ax1.set_title('Flesvoeding (Totaal ML per Dag)', fontsize=14)
        ax1.set_ylabel('ML', fontsize=12)
        ax1.grid(True, alpha=0.3)
        ax1.xaxis.set_major_formatter(mdates.DateFormatter('%d-%m'))
        ax1.set_xticks(dates)

        if ml_totals:
            max_ml = max(ml_totals)
            ax1.set_ylim(0, max(max_ml + 100, 200))

        for i, ml in enumerate(ml_totals):
            ax1.annotate(f'{ml}ml', (dates[i], ml_totals[i]), textcoords="offset points", xytext=(0,10), ha='center')

        # Plot 2: Temperature data
        valid_temps = [(d, t) for d, t in zip(dates, temp_data) if t is not None]
        if valid_temps:
            temp_dates, temp_values = zip(*valid_temps)
            ax2.plot(temp_dates, temp_values, marker='s', linestyle='-', color='red', linewidth=2, markersize=8)
            ax2.set_title('Temperatuur (Gemiddeld per Dag)', fontsize=14)
            ax2.set_ylabel('°C', fontsize=12)
            ax2.grid(True, alpha=0.3)
            ax2.xaxis.set_major_formatter(mdates.DateFormatter('%d-%m'))
            ax2.set_xticks(dates)

            # Draw reference line at 37°C with 50% opacity
            ax2.axhline(y=37, color='red', linestyle='-', alpha=0.5, linewidth=2, label='Normaal (37°C)')

            # Set y-axis range from 34 to 40
            ax2.set_ylim(34, 40)

            for i, temp in enumerate(temp_data):
                if temp is not None:
                    ax2.annotate(f'{temp:.1f}°C', (dates[i], temp), textcoords="offset points", xytext=(0,10), ha='center')
        else:
            ax2.text(0.5, 0.5, 'Geen temperatuur data beschikbaar', ha='center', va='center', transform=ax2.transAxes)
            ax2.set_title('Temperatuur (Geen data)', fontsize=14)
            # Set default range 34 to 40 even when no data
            ax2.set_ylim(34, 40)
            # Still draw the reference line
            ax2.axhline(y=37, color='red', linestyle='-', alpha=0.5, linewidth=2, label='Normaal (37°C)')

        # Plot 3: Diaper data (bar chart)
        pooped_counts, peed_counts, both_counts = self.get_diaper_totals_for_period(dates)

        # Create bar positions
        x = np.arange(len(dates))
        width = 0.25  # width of each bar

        # Create grouped bars
        bars1 = ax3.bar(x - width, pooped_counts, width, label='Gepoept', color='#D2B48C', alpha=0.8)  # Light brown
        bars2 = ax3.bar(x, peed_counts, width, label='Geplast', color='#4169E1', alpha=0.8)  # Blue
        bars3 = ax3.bar(x + width, both_counts, width, label='Beiden', color='#8B4513', alpha=0.8)  # Dark poop brown

        # Add value labels above bars
        for bars, counts in [(bars1, pooped_counts), (bars2, peed_counts), (bars3, both_counts)]:
            for bar, count in zip(bars, counts):
                if count > 0:  # Only show label if count > 0
                    height = bar.get_height()
                    ax3.text(bar.get_x() + bar.get_width()/2., height + 0.1,
                            f'{int(count)}', ha='center', va='bottom', color='black', fontweight='bold')

        ax3.set_title('Luiers (per Type per Dag)', fontsize=14)
        ax3.set_xlabel('Datum', fontsize=12)
        ax3.set_ylabel('Aantal', fontsize=12)
        ax3.set_xticks(x)
        ax3.set_xticklabels([d.strftime('%d-%m') for d in dates])
        ax3.legend()
        ax3.grid(True, alpha=0.3, axis='y')

        # Set y-axis limits
        max_diapers = max(max(pooped_counts), max(peed_counts), max(both_counts)) if pooped_counts else 0
        ax3.set_ylim(0, max(max_diapers + 2, 5))

        plt.tight_layout()

        # Save to BytesIO for Telegram
        buf = BytesIO()
        plt.savefig(buf, format='png', dpi=100, bbox_inches='tight')
        buf.seek(0)
        plt.close()

        return buf

    def get_all_time_stats(self):
        """Generate multi-plot graph for all time showing feeding, temperature, and diaper data"""
        feeding_data = self.load_feeding_data()
        amsterdam_time = self.get_amsterdam_time()

        # Sort dates chronologically
        sorted_dates = sorted(feeding_data.keys())
        dates = []
        ml_totals = []

        for date_str in sorted_dates:
            # Convert string date to datetime object
            date_obj = datetime.strptime(date_str, "%Y-%m-%d").date()
            dates.append(date_obj)
            ml_totals.append(self.get_total_ml_for_date(date_str))

        # Add today's date as the last point if not already included
        today_date = amsterdam_time.date()
        if not dates or dates[-1] != today_date:
            dates.append(today_date)
            ml_totals.append(self.get_total_ml_for_date(amsterdam_time.strftime("%Y-%m-%d")))


        # Add temperature and diaper data for existing dates
        temp_data = []
        diaper_data = []

        for date_str in sorted_dates:
            # Get temperature data (average if multiple readings)
            temps = self.get_temperature_for_date(date_str)
            avg_temp = sum(temps) / len(temps) if temps else None
            temp_data.append(avg_temp)

            # Get diaper data (total changes)
            diapers = self.get_diaper_data_for_date(date_str)
            total_diapers = diapers['pooped'] + diapers['peed'] + diapers['both']
            diaper_data.append(total_diapers)

        # Add today's data if not already included
        if not dates or dates[-1] != today_date:
            # Add temperature and diaper data for today
            temps = self.get_temperature_for_date(amsterdam_time.strftime("%Y-%m-%d"))
            avg_temp = sum(temps) / len(temps) if temps else None
            temp_data.append(avg_temp)

            diapers = self.get_diaper_data_for_date(amsterdam_time.strftime("%Y-%m-%d"))
            total_diapers = diapers['pooped'] + diapers['peed'] + diapers['both']
            diaper_data.append(total_diapers)

        # Create subplots
        fig, (ax1, ax2, ax3) = plt.subplots(3, 1, figsize=(16, 18))
        fig.suptitle('Baby Data - Vanaf Begin', fontsize=18, fontweight='bold')

        # Plot 1: Feeding data
        ax1.plot(dates, ml_totals, marker='o', linestyle='-', color='green', linewidth=2, markersize=8)
        ax1.set_title('Flesvoeding (Totaal ML per Dag)', fontsize=14)
        ax1.set_ylabel('ML', fontsize=12)
        ax1.grid(True, alpha=0.3)
        ax1.xaxis.set_major_formatter(mdates.DateFormatter('%d-%m-%Y'))
        ax1.set_xticks(dates)

        if ml_totals:
            max_ml = max(ml_totals)
            ax1.set_ylim(0, max_ml + 100)

        for i, ml in enumerate(ml_totals):
            ax1.annotate(f'{ml}ml', (dates[i], ml_totals[i]), textcoords="offset points", xytext=(0,10), ha='center')

        # Plot 2: Temperature data
        valid_temps = [(d, t) for d, t in zip(dates, temp_data) if t is not None]
        if valid_temps:
            temp_dates, temp_values = zip(*valid_temps)
            ax2.plot(temp_dates, temp_values, marker='s', linestyle='-', color='red', linewidth=2, markersize=8)
            ax2.set_title('Temperatuur (Gemiddeld per Dag)', fontsize=14)
            ax2.set_ylabel('°C', fontsize=12)
            ax2.grid(True, alpha=0.3)
            ax2.xaxis.set_major_formatter(mdates.DateFormatter('%d-%m-%Y'))
            ax2.set_xticks(dates)

            # Draw reference line at 37°C with 50% opacity
            ax2.axhline(y=37, color='red', linestyle='-', alpha=0.5, linewidth=2, label='Normaal (37°C)')

            # Set y-axis range from 34 to 40
            ax2.set_ylim(34, 40)

            for i, temp in enumerate(temp_data):
                if temp is not None:
                    ax2.annotate(f'{temp:.1f}°C', (dates[i], temp), textcoords="offset points", xytext=(0,10), ha='center')
        else:
            ax2.text(0.5, 0.5, 'Geen temperatuur data beschikbaar', ha='center', va='center', transform=ax2.transAxes)
            ax2.set_title('Temperatuur (Geen data)', fontsize=14)
            # Set default range 34 to 40 even when no data
            ax2.set_ylim(34, 40)
            # Still draw the reference line
            ax2.axhline(y=37, color='red', linestyle='-', alpha=0.5, linewidth=2, label='Normaal (37°C)')

        # Plot 3: Diaper data (bar chart)
        pooped_counts, peed_counts, both_counts = self.get_diaper_totals_for_period(dates)

        # Create bar positions
        x = np.arange(len(dates))
        width = 0.25  # consistent width like weekly/monthly

        # Create grouped bars
        bars1 = ax3.bar(x - width, pooped_counts, width, label='Gepoept', color='#D2B48C', alpha=0.8)  # Light brown
        bars2 = ax3.bar(x, peed_counts, width, label='Geplast', color='#4169E1', alpha=0.8)  # Blue
        bars3 = ax3.bar(x + width, both_counts, width, label='Beiden', color='#8B4513', alpha=0.8)  # Dark poop brown

        # Add value labels above bars
        for bars, counts in [(bars1, pooped_counts), (bars2, peed_counts), (bars3, both_counts)]:
            for bar, count in zip(bars, counts):
                if count > 0:  # Only show label if count > 0
                    height = bar.get_height()
                    ax3.text(bar.get_x() + bar.get_width()/2., height + 0.1,
                            f'{int(count)}', ha='center', va='bottom', color='black', fontweight='bold')

        ax3.set_title('Luiers (per Type per Dag)', fontsize=14)
        ax3.set_xlabel('Datum', fontsize=12)
        ax3.set_ylabel('Aantal', fontsize=12)
        ax3.legend()
        ax3.grid(True, alpha=0.3, axis='y')

        # Set consistent x-axis ticks for even spacing
        ax3.set_xticks(x)
        if len(dates) <= 15:
            ax3.set_xticklabels([d.strftime('%d-%m') for d in dates])
        else:
            # For many dates, use date formatter but maintain even spacing
            ax3.xaxis.set_major_formatter(mdates.DateFormatter('%d-%m-%Y'))
            # Ensure ticks are evenly spaced
            if len(dates) > 20:
                step = max(1, len(dates) // 10)
                ax3.set_xticks(x[::step])
                ax3.set_xticklabels([dates[i].strftime('%d-%m-%Y') for i in range(0, len(dates), step)])

        # Set y-axis limits
        max_diapers = max(max(pooped_counts), max(peed_counts), max(both_counts)) if pooped_counts else 0
        ax3.set_ylim(0, max(max_diapers + 2, 5))

        # Set tick formatting for feeding and temperature plots (exclude bar chart)
        for ax in [ax1, ax2]:
            if len(dates) <= 15:
                ax.set_xticks(dates)
            else:
                ax.xaxis.set_major_locator(mdates.DayLocator(interval=max(1, len(dates)//12)))

        plt.tight_layout()

        # Save to BytesIO for Telegram
        buf = BytesIO()
        plt.savefig(buf, format='png', dpi=100, bbox_inches='tight')
        buf.seek(0)
        plt.close()

        return buf

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

    def format_time_difference(self, past_time_str):
        """Format time difference between now and past time in Dutch"""
        try:
            amsterdam_time = self.get_amsterdam_time()
            current_time = amsterdam_time.time()
            print(f"🕐 Current Amsterdam time: {current_time.strftime('%H:%M:%S')}")
            print(f"📅 Past time to compare: {past_time_str}")

            # Parse the past time string (supports both HH:MM and HH:MM:SS formats)
            time_parts = past_time_str.split(':')

            if len(time_parts) == 2:
                # HH:MM format
                past_hour, past_minute = map(int, time_parts)
                past_second = 0
            elif len(time_parts) == 3:
                # HH:MM:SS format
                past_hour, past_minute, past_second = map(int, time_parts)
            else:
                raise ValueError(f"Invalid time format: {past_time_str}")

            # Create datetime objects for comparison
            current_datetime = amsterdam_time.replace(hour=current_time.hour, minute=current_time.minute, second=current_time.second)
            past_datetime = amsterdam_time.replace(hour=past_hour, minute=past_minute, second=past_second)

            print(f"🔍 Comparing: Current={current_datetime.strftime('%H:%M:%S')}, Past={past_datetime.strftime('%H:%M:%S')}")

            # Calculate difference
            if past_datetime > current_datetime:
                # If past time is later than current time, it might be from yesterday
                past_datetime = past_datetime.replace(day=past_datetime.day - 1)
                print(f"📆 Adjusted past time to yesterday: {past_datetime.strftime('%H:%M:%S')}")

            time_diff = current_datetime - past_datetime
            print(f"⏱️ Time difference: {time_diff}")

            # Format the difference
            total_minutes = int(time_diff.total_seconds() / 60)
            hours = total_minutes // 60
            minutes = total_minutes % 60

            result = ""
            if hours > 0:
                if minutes > 0:
                    result = f"{hours}u{minutes}m geleden"
                else:
                    result = f"{hours}u geleden"
            else:
                result = f"{minutes}m geleden"

            print(f"📊 Final result: {result}")
            return result

        except (ValueError, AttributeError) as e:
            print(f"❌ Error calculating time difference: {e}")
            return "tijd onbekend"

    def format_dutch_date(self, datetime_obj):
        """Format datetime object to Dutch date format"""
        # Dutch day names
        dutch_days = {
            0: "maandag",
            1: "dinsdag",
            2: "woensdag",
            3: "donderdag",
            4: "vrijdag",
            5: "zaterdag",
            6: "zondag"
        }

        # Dutch month names
        dutch_months = {
            1: "januari",
            2: "februari",
            3: "maart",
            4: "april",
            5: "mei",
            6: "juni",
            7: "juli",
            8: "augustus",
            9: "september",
            10: "oktober",
            11: "november",
            12: "december"
        }

        day_name = dutch_days[datetime_obj.weekday()]
        day = datetime_obj.day
        month_name = dutch_months[datetime_obj.month]

        return f"{day_name} {day} {month_name}"

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
        await update.message.reply_text("👸 Baby Feeding Tracker Online!\n\n📋 Commands:\n/start - Toon hulp\n/overzicht - Overzicht van vandaag\n/toevoegen_fles - Fles registreren\n/toevoegen_temp - Temperatuur registreren\n/toevoegen_luier - Luier registreren\n/verwijder_laatste - Laatste invoer ongedaan maken\n/grafiek - Krijg informatie van de afgelopen week, maand of begin")

    async def overzicht_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle /overzicht command to show today's feedings"""
        user_id = update.effective_user.id
        username = update.effective_user.username or "No username"
        user_name = self.get_user_name(user_id)

        print(f"📨 /overzicht command received from User ID: {user_id} ({user_name}) (Username: {username})")

        if not self.is_authorized(user_id):
            print(f"❌ Unauthorized user {user_id} ({user_name}) tried to use /overzicht")
            await update.message.reply_text("❌ Sorry, you are not authorized to use this bot.")
            return

        print(f"✅ Authorized user {user_id} ({user_name}) requested today's events")

        events = self.get_today_events()

        if not events:
            await update.message.reply_text("📅 No events recorded today yet.")
            return

        # Separate different types of events and sort each by time
        feedings = [event for event in events if event.get('type') == 'drink']
        temperatures = [event for event in events if event.get('type') == 'temperature']
        diaper_changes = [event for event in events if event.get('type') == 'diaper']

        # Sort each category by time (earliest first) with proper time parsing
        def parse_time(time_str):
            """Parse time string and return comparable value"""
            try:
                parts = time_str.split(':')
                if len(parts) >= 2:
                    hours = int(parts[0])
                    minutes = int(parts[1])
                    return hours * 60 + minutes  # Convert to total minutes
                return 0
            except (ValueError, IndexError):
                return 0

        feedings.sort(key=lambda x: parse_time(x['time']))
        temperatures.sort(key=lambda x: parse_time(x['time']))
        diaper_changes.sort(key=lambda x: parse_time(x['time']))

        amsterdam_time = self.get_amsterdam_time()

        # Format date in Dutch
        dutch_date = self.format_dutch_date(amsterdam_time)
        message = f"👸 Sofia's momentjes op {dutch_date}:\n\n"

        # Show bottle feedings
        if feedings:
            total_ml = sum(feeding["amount_ml"] for feeding in feedings)
            message += "🍼 Flesjes:\n"
            for i, feeding in enumerate(feedings, 1):
                user_initial = feeding.get('user', '?')
                # Show time without seconds (HH:MM instead of HH:MM:SS)
                short_time = feeding['time'][:5] if len(feeding['time']) >= 5 else feeding['time']
                message += f"  {i}. {short_time} - {feeding['amount_ml']}ml [{user_initial}]\n"
            message += f"  💧 Totaal: {total_ml}ml\n\n"

        # Show temperature measurements
        if temperatures:
            message += "🌡️ Temperaturen:\n"
            for i, temp in enumerate(temperatures, 1):
                user_initial = temp.get('user', '?')
                # Show time without seconds (HH:MM instead of HH:MM:SS)
                short_time = temp['time'][:5] if len(temp['time']) >= 5 else temp['time']
                message += f"  {i}. {short_time} - {temp['temperature_celsius']}°C [{user_initial}]\n"
            message += "\n"

        # Show diaper changes
        if diaper_changes:
            diaper_names = {
                "pooped": "💩 Gepoept",
                "peed": "💧 Geplast",
                "both": "🧷 Beiden"
            }
            message += "🧷 Luiers:\n"
            for i, diaper in enumerate(diaper_changes, 1):
                readable_name = diaper_names.get(diaper['diaper_type'], diaper['diaper_type'])
                user_initial = diaper.get('user', '?')
                # Show time without seconds (HH:MM instead of HH:MM:SS)
                short_time = diaper['time'][:5] if len(diaper['time']) >= 5 else diaper['time']
                message += f"  {i}. {short_time} - {readable_name} [{user_initial}]\n"

        # If no events today
        if not feedings and not temperatures and not diaper_changes:
            dutch_date = self.format_dutch_date(amsterdam_time)
            message = f"📅 Nog geen momentjes vandaag op {dutch_date}."
        else:
            # Add time since last feeding information
            if feedings:
                # After sorting, the last item is the most recent
                last_feeding = feedings[-1]  # Get the most recent feeding
                print(f"🔍 Last feeding time: {last_feeding['time']} (after sorting)")
                time_ago = self.format_time_difference(last_feeding['time'])
                print(f"⏰ Time difference calculated: {time_ago}")
                message += f"\n🍼 Laatste flesje was {time_ago} 🕐"

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
            "👸 Kies het type luierwissel:",
            reply_markup=reply_markup
        )

    async def grafiek_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle /grafiek command to show statistics for different time periods"""
        user_id = update.effective_user.id
        username = update.effective_user.username or "No username"
        user_name = self.get_user_name(user_id)

        print(f"📨 /grafiek command received from User ID: {user_id} ({user_name}) (Username: {username})")

        if not self.is_authorized(user_id):
            print(f"❌ Unauthorized user {user_id} ({user_name}) tried to use /grafiek")
            await update.message.reply_text("❌ Sorry, you are not authorized to use this bot.")
            return

        print(f"✅ Authorized user {user_id} ({user_name}) requested statistics options")

        # Create inline keyboard with time period options
        keyboard = [
            [
                InlineKeyboardButton("📅 Afgelopen Week", callback_data="stats_week"),
                InlineKeyboardButton("📊 Afgelopen Maand", callback_data="stats_month"),
            ],
            [
                InlineKeyboardButton("🗓️ Vanaf Begin", callback_data="stats_all"),
            ]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)

        await update.message.reply_text(
            "📊 Kies de periode waarvoor je statistieken wilt zien:",
            reply_markup=reply_markup
        )

    async def verwijder_laatste_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle /verwijder_laatste command to delete the last entry of a specific type"""
        user_id = update.effective_user.id
        username = update.effective_user.username or "No username"
        user_name = self.get_user_name(user_id)

        print(f"📨 /verwijder_laatste command received from User ID: {user_id} ({user_name}) (Username: {username})")

        if not self.is_authorized(user_id):
            print(f"❌ Unauthorized user {user_id} ({user_name}) tried to use /verwijder_laatste")
            await update.message.reply_text("❌ Sorry, you are not authorized to use this bot.")
            return

        print(f"✅ Authorized user {user_id} ({user_name}) requested delete options")

        # Create inline keyboard with delete options
        keyboard = [
            [
                InlineKeyboardButton("🍼 Laatste Fles", callback_data="delete_drink"),
                InlineKeyboardButton("🌡️ Laatste Temp", callback_data="delete_temperature"),
            ],
            [
                InlineKeyboardButton("🧷 Laatste Luier", callback_data="delete_diaper"),
            ]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)

        await update.message.reply_text(
            "🗑️ Welke laatste invoer wil je verwijderen?",
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
                    print(f"🍼 Received feeding amount: {amount}ml for user {user_id} ({user_name})")

                    # Store the amount and set flag to wait for time
                    context.user_data['feeding_amount'] = amount
                    context.user_data['awaiting_feeding_amount'] = False
                    context.user_data['awaiting_feeding_time'] = True

                    await update.message.reply_text("🕐 Wanneer is het begin van deze flesvoeding? Geef de tijd in het formaat UU:MM (bijvoorbeeld 13:02 of 22:04)")
                else:
                    await update.message.reply_text("❌ Voer een geldig aantal ml in (1-500).")
            except ValueError:
                await update.message.reply_text("❌ Voer alleen een getal in voor de ml hoeveelheid.")
            return

        # Check if we're waiting for a feeding time
        if context.user_data.get('awaiting_feeding_time'):
            # Validate time format HH:MM
            if self._validate_time_format(message_text):
                amount = context.user_data['feeding_amount']
                self.add_feeding(amount, user_id, message_text)
                print(f"🍼 Added feeding with custom time: {amount}ml at {message_text} for user {user_id} ({user_name})")

                # Clear the awaiting states
                context.user_data['awaiting_feeding_time'] = False
                context.user_data.pop('feeding_amount', None)

                await update.message.reply_text(f"✅ Fles toegevoegd: {amount}ml om {message_text} (Amsterdam tijd)")
            else:
                await update.message.reply_text("❌ Ongeldig tijdformaat. Gebruik UU:MM formaat (bijvoorbeeld 13:02 of 22:04). Probeer opnieuw:")
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

                    await update.message.reply_text(f"✅ Temperatuur toegevoegd: {temperature}°C om {amsterdam_time.strftime('%H:%M')} (Amsterdam tijd)")
                else:
                    await update.message.reply_text("❌ Voer een geldige temperatuur in (30.0-45.0°C).")
            except ValueError:
                await update.message.reply_text("❌ Voer alleen een getal in voor de temperatuur (bijv. 36.5 of 36,5).")
            return

        # If not waiting for feeding amount, show help
        print(f"🤔 Unrecognized message from user {user_id} ({user_name}): {message_text}")
        await update.message.reply_text("🤔 Ik begrijp dat niet.\n\n📋 Beschikbare commando's:\n/start - Toon hulp\n/overzicht - Overzicht van vandaag\n/toevoegen_fles - Fles registreren\n/toevoegen_temp - Temperatuur registreren\n/toevoegen_luier - Luier registreren\n/verwijder_laatste - Laatste invoer ongedaan maken\n/grafiek - Krijg informatie van de afgelopen week, maand of begin")

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
                f"Tijd: {self.get_amsterdam_time().strftime('%H:%M')} (Amsterdam tijd)"
            )

        elif callback_data.startswith("delete_"):
            entry_type = callback_data.split("_")[1]

            # Map entry types to readable names
            type_names = {
                "drink": "🍼 Flesvoeding",
                "temperature": "🌡️ Temperatuur",
                "diaper": "🧷 Luiersessie"
            }

            readable_name = type_names.get(entry_type, entry_type)

            # Delete the last entry
            deleted_entry, error = self.delete_last_entry(entry_type)

            if error:
                print(f"❌ Delete failed for {entry_type}: {error}")
                await query.edit_message_text(f"❌ {error}")
            else:
                print(f"🗑️ Deleted last {entry_type} entry for user {user_id} ({user_name})")
                # Format confirmation message
                if entry_type == "drink":
                    amount = deleted_entry.get('amount_ml', 'N/A')
                    time_str = deleted_entry.get('time', 'N/A')
                    confirmation = f"✅ Laatste {readable_name} verwijderd:\n{amount}ml om {time_str[:5]}"
                elif entry_type == "temperature":
                    temp = deleted_entry.get('temperature_celsius', 'N/A')
                    time_str = deleted_entry.get('time', 'N/A')
                    confirmation = f"✅ Laatste {readable_name} verwijderd:\n{temp}°C om {time_str[:5]}"
                elif entry_type == "diaper":
                    diaper_type = deleted_entry.get('diaper_type', 'N/A')
                    diaper_names = {
                        "pooped": "💩 Gepoept",
                        "peed": "💧 Geplast",
                        "both": "🧷 Beiden"
                    }
                    readable_diaper = diaper_names.get(diaper_type, diaper_type)
                    time_str = deleted_entry.get('time', 'N/A')
                    confirmation = f"✅ Laatste {readable_name} verwijderd:\n{readable_diaper} om {time_str[:5]}"

                await query.edit_message_text(confirmation)

        elif callback_data.startswith("stats_"):
            period = callback_data.split("_")[1]

            # Get statistics based on period
            if period == "week":
                stats_image = self.get_weekly_stats()
                period_name = "afgelopen week"
            elif period == "month":
                stats_image = self.get_monthly_stats()
                period_name = "afgelopen maand"
            elif period == "all":
                stats_image = self.get_all_time_stats()
                period_name = "vanaf het begin"
            else:
                await query.edit_message_text("❌ Ongeldige periode geselecteerd.")
                return

            # Send the graph as a photo
            await query.message.reply_photo(
                photo=stats_image,
                caption=f"📊 Baby voeding overzicht - {period_name}"
            )
            await query.edit_message_text(f"✅ Grafiek verzonden voor {period_name}!")

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
            "👸 Baby Feeding Tracker is starting up! 🕐 All times are in Amsterdam timezone (CET/CEST).\n\n"
            "📋 Features:\n"
            "🍼 Track bottle feedings (/toevoegen_fles)\n"
            "🌡️ Track temperatures (/toevoegen_temp)\n"
            "🧷 Track diaper changes (/toevoegen_luier)\n"
            "📊 View daily summaries (/overzicht)\n"
            "🗑️ Delete last entries (/verwijder_laatste)\n"
            "📈 View statistics (/grafiek)\n\n"
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
            self.app.add_handler(CommandHandler("overzicht", self.overzicht_command))
            self.app.add_handler(CommandHandler("toevoegen_fles", self.bottle_command))
            self.app.add_handler(CommandHandler("toevoegen_temp", self.temperature_command))
            self.app.add_handler(CommandHandler("toevoegen_luier", self.diaper_command))
            self.app.add_handler(CommandHandler("verwijder_laatste", self.verwijder_laatste_command))
            self.app.add_handler(CommandHandler("grafiek", self.grafiek_command))
            self.app.add_handler(CallbackQueryHandler(self.handle_callback))
            self.app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_message))

            # Set post init hook
            self.app.post_init = self.post_init

            print("🚀 Starting bot polling...")
            print("✅ Bot is running! Send messages to your bot on Telegram.")
            print("💡 Commands: /start, /overzicht, /toevoegen_fles, /toevoegen_temp, /toevoegen_luier, /verwijder_laatste, /grafiek")
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
