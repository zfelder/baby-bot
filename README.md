# 👸 Baby Feeding Tracker

<div align="center">
  <img src="https://img.shields.io/badge/Python-3.8+-blue.svg" alt="Python Version">
  <img src="https://img.shields.io/badge/Telegram-Bot_API-blue.svg" alt="Telegram Bot">
  <img src="https://img.shields.io/badge/Timezone-Amsterdam-orange.svg" alt="Timezone">
  <img src="https://img.shields.io/badge/Language-Dutch-green.svg" alt="Language">
</div>

## ✨ About

**Baby Feeding Tracker** is a sophisticated Telegram bot designed to help parents track and monitor their baby's daily activities with elegance and precision. Keep track of feedings, diaper changes, and temperature measurements while generating beautiful statistical insights.

## 🎯 Key Features

### 🍼 Feeding Tracking
- **Precise bottle feeding logs** with custom timestamps
- **Multiple feeding amounts** (25ml, 35ml, 65ml typical ranges)
- **User attribution** with initials for multi-parent households
- **Amsterdam timezone** support for accurate timing

### 🌡️ Temperature Monitoring
- **Body temperature tracking** with Celsius precision
- **Normal range indicators** (37°C reference line)
- **Temperature trends** visualization
- **Health monitoring** capabilities

### 🧷 Diaper Change Logging
- **Three diaper types**: Pooped 💩, Peed 💧, Both 🧷
- **Change frequency tracking**
- **Pattern analysis** for health insights
- **Visual statistics** with color-coded charts

### 📊 Advanced Analytics
- **Beautiful matplotlib charts** for data visualization
- **Multi-timeframe statistics**: Weekly, Monthly, All-time
- **Interactive graphs** with value annotations
- **Trend analysis** for feeding and health patterns

### 🔐 Security & Privacy
- **User authorization system** with whitelisted users
- **Personal data protection** - only authorized users can access
- **Secure data storage** in JSON format
- **Timezone-aware** timestamping

## 🚀 Quick Start

### Prerequisites
- Python 3.8+
- Telegram Bot Token (from [@BotFather](https://t.me/botfather))
- Authorized user IDs

### Installation

1. **Clone the repository**
   ```bash
   git clone <repository-url>
   cd baby-bot
   ```

2. **Install dependencies**
   ```bash
   pip install python-telegram-bot matplotlib numpy zoneinfo
   ```

3. **Configure the bot**
   - Edit `config.py` with your bot token and authorized users
   - Update user IDs in `AUTHORIZED_USERS` dictionary

4. **Run the bot**
   ```bash
   python main.py
   ```

## 📱 Bot Commands

| Command | Description | Usage |
|---------|-------------|-------|
| `/start` | Show welcome message and help | `/start` |
| `/overzicht` | View today's activities summary | `/overzicht` |
| `/toevoegen_fles` | Add bottle feeding entry | `/toevoegen_fles` → Enter ml amount → Enter time |
| `/toevoegen_temp` | Add temperature measurement | `/toevoegen_temp` → Enter temperature in °C |
| `/toevoegen_luier` | Add diaper change | `/toevoegen_luier` → Select diaper type |
| `/verwijder_laatste` | Delete last entry of any type | `/verwijder_laatste` → Choose entry type |
| `/grafiek` | View statistical charts | `/grafiek` → Select time period |

## 📈 Data Visualization

### Weekly Overview
- **7-day feeding trends** with daily totals
- **Temperature monitoring** with normal range indicators
- **Diaper change patterns** in grouped bar charts
- **Color-coded visualizations** for easy interpretation

### Monthly Insights
- **30-day comprehensive view**
- **Feeding volume analysis**
- **Temperature stability tracking**
- **Diaper change frequency patterns**

### All-Time Statistics
- **Complete historical data** from day one
- **Long-term feeding trends**
- **Growth pattern visualization**
- **Health monitoring overview**

## 🏗️ Technical Architecture

### Core Components
- **Telegram Bot API** for user interaction
- **Async/Await Architecture** for responsive performance
- **JSON Data Storage** for persistent tracking
- **Matplotlib Integration** for statistical visualization
- **Timezone Handling** with Europe/Amsterdam support

### Data Structure
```json
{
  "2025-09-03": [
    {
      "time": "09:15",
      "type": "drink",
      "amount_ml": 65,
      "user": "Z"
    },
    {
      "time": "09:15",
      "type": "temperature",
      "temperature_celsius": 36.6,
      "user": "Z"
    }
  ]
}
```

### Security Features
- **User Authentication** with Telegram user ID validation
- **Authorized User Lists** for access control
- **Input Validation** for data integrity
- **Error Handling** with graceful failure recovery

## 🎨 User Experience

### Intuitive Interface
- **Dutch language support** for native experience
- **Interactive inline keyboards** for easy selection
- **Emoji-enhanced messages** for visual appeal
- **Real-time feedback** on all actions

### Smart Features
- **Time difference calculations** ("2u3m geleden")
- **Automatic data sorting** by timestamp
- **Daily summaries** with formatted dates
- **User attribution** with initials

## 📊 Sample Statistics Output

The bot generates beautiful visualizations showing:
- Daily feeding volumes with trend lines
- Temperature measurements with reference ranges
- Diaper change frequencies by type
- Multi-day pattern analysis
- Growth and health trend monitoring

## 🔧 Configuration

### config.py Structure
```python
TELEGRAM_CREDENTIALS = {
    'bot_token': 'YOUR_BOT_TOKEN_HERE',
}

AUTHORIZED_USERS = {
    'Parent1': 123456789,
    'Parent2': 987654321,
}

AUTHORIZED_USER_IDS = list(AUTHORIZED_USERS.values())
AUTHORIZED_USER_NAMES = {v: k for k, v in AUTHORIZED_USERS.items()}
```

## 🌟 Advanced Features

### Custom Time Entry
- Support for custom feeding start times
- HH:MM format validation
- Historical data entry capabilities

### Multi-User Support
- User identification with initials
- Separate tracking per caregiver
- Collaborative baby care monitoring

### Health Monitoring
- Temperature trend analysis
- Feeding pattern recognition
- Diaper change frequency alerts
- Health data correlation

## 🚨 Important Notes

- **Timezone**: All times are in Amsterdam (CET/CEST)
- **Data Storage**: JSON file-based storage in `feeding_data.json`
- **Backup**: Regular backup of `feeding_data.json` recommended
- **Updates**: Bot sends notifications on startup to all authorized users

## 🤝 Contributing

This project welcomes contributions! Feel free to:
- Report bugs and issues
- Suggest new features
- Submit pull requests
- Improve documentation

## 📄 License

This project is developed with ❤️ for modern parenting.

---

<div align="center">
  <p><strong>Built with ❤️ for modern parents tracking their baby's journey</strong></p>
  <p><em>All times in Amsterdam timezone • Dutch interface • Beautiful visualizations</em></p>
</div>
