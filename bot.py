"""
Simple Telegram Bot Example
----------------------------
A beginner-friendly bot that demonstrates:
- Responding to /start and /help commands
- Echoing user messages
- Using polling to receive updates
"""

import os
import re
import random
from dotenv import load_dotenv
from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    filters,
    ContextTypes
)
from telegram.error import TimedOut, NetworkError
import requests

# ============================================================================
# CONFIGURATION
# ============================================================================

# Load environment variables from .env file
load_dotenv()

# Get the bot token from environment variable
# This keeps your token secure and out of the code
BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')

if not BOT_TOKEN:
    raise ValueError(
        "No TELEGRAM_BOT_TOKEN found! "
        "Please create a .env file with your bot token."
    )

# Get the weather API key (optional - weather feature won't work without it)
WEATHER_API_KEY = os.getenv('OPENWEATHER_API_KEY')

# List of jokes for the joke feature
JOKES = [
    "Why do programmers prefer dark mode? Because light attracts bugs! 🐛",
    "Why do Python programmers wear glasses? Because they can't C! 😎",
    "How many programmers does it take to change a light bulb? None, that's a hardware problem! 💡",
    "Why did the developer go broke? Because he used up all his cache! 💰",
    "What's a programmer's favorite place? Foo Bar! 🍺",
    "Why do Java developers wear glasses? Because they don't C#! 👓",
    "A SQL query walks into a bar, walks up to two tables and asks: 'Can I join you?' 🍻",
    "Why did the programmer quit his job? Because he didn't get arrays! 📊",
    "What do you call a programmer from Finland? Nerdic! 🇫🇮",
    "Why don't programmers like nature? It has too many bugs! 🌳",
]


# ============================================================================
# COMMAND HANDLERS
# ============================================================================

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Handles the /start command
    
    This is typically the first command users send when they open your bot.
    It's a good place to introduce your bot and show what it can do.
    
    Parameters:
    - update: Contains information about the incoming update (message, user, etc.)
    - context: Contains bot-specific context and utilities
    """
    user = update.effective_user  # Get the user who sent the message
    
    welcome_message = (
        f"👋 Hello {user.first_name}!\n\n"
        f"I'm a smart bot that can help you with various tasks!\n\n"
        f"🤖 What I can do:\n"
        f"😄 Tell jokes to make you laugh\n"
        f"🧮 Solve math calculations\n"
        f"🌍 Show weather for any city\n\n"
        f"Send /help to see examples and learn more!"
    )
    
    # Send the welcome message back to the user
    await update.message.reply_text(welcome_message)


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Handles the /help command
    
    Shows users what commands are available and how to use the bot.
    """
    help_text = (
        "📚 *Available Commands:*\n\n"
        "/start - Start the bot and see welcome message\n"
        "/help - Show this help message\n\n"
        "🎯 *Features:*\n\n"
        "😄 *Jokes* - Get a random programming joke\n"
        "   _Example: 'Tell me a joke' or 'Make me laugh'_\n\n"
        "🧮 *Calculator* - Solve math problems\n"
        "   _Example: 'Calculate 25 * 4' or '100 / 5'_\n\n"
        "🌍 *Weather* - Get current weather for any city\n"
        "   _Example: 'Weather in Delhi' or 'Mumbai temperature'_\n\n"
        "_This bot uses polling to receive your messages._"
    )
    
    # parse_mode='Markdown' allows us to use formatting in our message
    await update.message.reply_text(help_text, parse_mode='Markdown')


# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def get_joke():
    """Returns a random joke from the jokes list"""
    return random.choice(JOKES)


def calculate(expression):
    """
    Safely evaluates a mathematical expression
    
    Parameters:
    - expression: String containing the math expression
    
    Returns:
    - Result of the calculation or error message
    """
    try:
        # Remove any 'calculate' or 'calc' keywords
        expression = re.sub(r'\b(calculate|calc)\b', '', expression, flags=re.IGNORECASE)
        expression = expression.strip()
        
        # Only allow numbers, operators, parentheses, and spaces
        if not re.match(r'^[0-9+\-*/().\s]+$', expression):
            return "❌ Invalid expression. Please use only numbers and operators (+, -, *, /, parentheses)."
        
        # Evaluate the expression
        result = eval(expression)
        return f"✅ {expression} = **{result}**"
    
    except ZeroDivisionError:
        return "❌ Error: Cannot divide by zero!"
    except Exception as e:
        return f"❌ Error calculating expression. Please check your math!"


def get_weather(city):
    """
    Fetches weather data for a given city using OpenWeatherMap API
    
    Parameters:
    - city: Name of the city
    
    Returns:
    - Weather information string or error message
    """
    if not WEATHER_API_KEY:
        return (
            "⚠️ Weather feature is not configured.\n\n"
            "To enable weather:\n"
            "1. Get a free API key from https://openweathermap.org/api\n"
            "2. Add it to your .env file as: OPENWEATHER_API_KEY=your_key_here"
        )
    
    try:
        # API endpoint
        url = f"http://api.openweathermap.org/data/2.5/weather"
        params = {
            'q': city,
            'appid': WEATHER_API_KEY,
            'units': 'metric'  # Use Celsius
        }
        
        # Make request
        response = requests.get(url, params=params, timeout=10)
        response.raise_for_status()
        
        data = response.json()
        
        # Extract weather information
        city_name = data['name']
        country = data['sys']['country']
        temp = data['main']['temp']
        feels_like = data['main']['feels_like']
        humidity = data['main']['humidity']
        description = data['weather'][0]['description'].capitalize()
        wind_speed = data['wind']['speed']
        
        # Format response
        weather_info = (
            f"🌍 **Weather in {city_name}, {country}**\n\n"
            f"🌡️ Temperature: {temp}°C (Feels like {feels_like}°C)\n"
            f"☁️ Conditions: {description}\n"
            f"💧 Humidity: {humidity}%\n"
            f"💨 Wind Speed: {wind_speed} m/s"
        )
        
        return weather_info
    
    except requests.exceptions.RequestException:
        return f"❌ Could not fetch weather data. Please check your internet connection."
    except KeyError:
        return f"❌ City '{city}' not found. Please check the spelling and try again."
    except Exception as e:
        return f"❌ Error fetching weather data. Please try again later."


# ============================================================================
# MESSAGE HANDLERS
# ============================================================================

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Handles any text message that isn't a command
    
    This function detects keywords in messages and responds accordingly:
    - Jokes: "joke", "funny", "laugh"
    - Calculator: "calculate", "calc", math expressions
    - Weather: "weather", city names
    """
    user_message = update.message.text.lower()
    user_name = update.effective_user.first_name
    
    # Check for joke request
    if any(keyword in user_message for keyword in ['joke', 'funny', 'laugh', 'humor']):
        joke = get_joke()
        response = f"😄 Here's a joke for you, {user_name}!\n\n{joke}"
        await update.message.reply_text(response)
        return
    
    # Check for calculator request
    # Look for math-related keywords or numbers with operators
    calc_keywords = ['calculate', 'calc', 'what is', 'what\'s', 'solve']
    has_calc_keyword = any(keyword in user_message for keyword in calc_keywords)
    has_math_operators = any(op in user_message for op in ['+', '-', '*', '/', '×', '÷'])
    
    if has_calc_keyword or has_math_operators:
        # Extract the expression
        expression = user_message
        for keyword in calc_keywords:
            expression = expression.replace(keyword, '')
        
        # Replace common symbols
        expression = expression.replace('×', '*').replace('÷', '/')
        
        result = calculate(expression)
        await update.message.reply_text(result, parse_mode='Markdown')
        return
    
    # Check for weather request
    weather_keywords = ['weather', 'temperature', 'temp', 'forecast', 'climate']
    if any(keyword in user_message for keyword in weather_keywords):
        # Try to extract city name
        # Remove common words
        city_extract = user_message
        for word in ['weather', 'in', 'at', 'for', 'temperature', 'temp', 'forecast', 'what', 'is', 'the', 'today', 'current', 'show', 'me', 'tell', '?', "'s", "'s"]:
            city_extract = city_extract.replace(word, ' ')
        
        city = city_extract.strip()
        
        if city:
            weather_info = get_weather(city)
            await update.message.reply_text(weather_info, parse_mode='Markdown')
        else:
            await update.message.reply_text(
                "🌍 Please specify a city name!\n"
                "Example: 'Weather in Delhi' or 'Delhi weather'"
            )
        return
    
    # Default response if no keywords matched
    response = (
        f"Thanks for your message, {user_name}! 😊\n\n"
        f"I can help you with:\n\n"
        f"😄 **Jokes** - Say 'tell me a joke'\n"
        f"🧮 **Calculator** - Say 'calculate 25 * 4'\n"
        f"🌍 **Weather** - Say 'weather in Delhi'\n\n"
        f"Or send /help to see all commands!"
    )
    
    await update.message.reply_text(response, parse_mode='Markdown')


# ============================================================================
# ERROR HANDLER
# ============================================================================

async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Handles errors that occur during update processing
    
    This is useful for debugging and monitoring your bot.
    In production, you might want to log these to a file or monitoring service.
    """
    error = context.error
    
    # Handle timeout errors specifically
    if isinstance(error, TimedOut):
        print(f"⏱️  Timeout error occurred (this is usually temporary)")
        print(f"   Message: {error}")
        # Don't crash the bot, just log and continue
        
    # Handle network errors
    elif isinstance(error, NetworkError):
        print(f"🌐 Network error occurred (connection issue)")
        print(f"   Message: {error}")
        # Don't crash the bot, just log and continue
        
    # Handle other errors
    else:
        print(f"❌ Update {update} caused error: {error}")


# ============================================================================
# MAIN FUNCTION
# ============================================================================

def main():
    """
    Main function that sets up and runs the bot
    
    This is where we:
    1. Create the Application instance
    2. Register our command and message handlers
    3. Start polling for updates
    """
    
    print("🚀 Starting bot...")
    
    # Create the Application instance with increased timeouts
    # This helps prevent timeout errors on slow connections
    application = (
        Application.builder()
        .token(BOT_TOKEN)
        .connect_timeout(10.0)
        .read_timeout(30.0)
        .write_timeout(10.0)
        .pool_timeout(10.0)
        .build()
    )
    
    # Register command handlers
    # These respond to specific commands like /start and /help
    application.add_handler(CommandHandler("start", start_command))
    application.add_handler(CommandHandler("help", help_command))
    
    # Register message handler for regular text messages
    # filters.TEXT matches any text message
    # ~filters.COMMAND excludes commands (so we don't handle /start here)
    application.add_handler(
        MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message)
    )
    
    # Register error handler
    application.add_error_handler(error_handler)
    
    # Start polling
    # This tells the bot to start asking Telegram for updates
    # - polling_interval: Not needed with python-telegram-bot v20+ (uses long polling)
    # - allowed_updates: Specifies what types of updates to receive
    print("✅ Bot is running! Press Ctrl+C to stop.")
    print("📱 Open Telegram and send a message to your bot to test it.\n")
    
    # Start the bot with polling
    # This will block and keep the bot running until Ctrl+C is pressed
    application.run_polling(
        allowed_updates=Update.ALL_TYPES,  # Receive all types of updates
        drop_pending_updates=True  # Ignore messages sent while bot was offline
    )


# ============================================================================
# ENTRY POINT
# ============================================================================

if __name__ == '__main__':
    """
    Entry point of the script
    
    This ensures main() only runs when the script is executed directly,
    not when it's imported as a module.
    """
    main()
