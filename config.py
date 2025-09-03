# Baby Feeding Bot Configuration

TELEGRAM_CREDENTIALS = {
    'bot_token': '8473554233:AAGZp1e3VU9GpxbwET0V6l0RaS7k12TXY8s',
}

# Authorized users with their names and IDs
AUTHORIZED_USERS = {
    'Zjelco': 5978790342,
    'Rachel': 5896150482,
}

# Convert to list for easy checking
AUTHORIZED_USER_IDS = list(AUTHORIZED_USERS.values())
AUTHORIZED_USER_NAMES = {v: k for k, v in AUTHORIZED_USERS.items()}
