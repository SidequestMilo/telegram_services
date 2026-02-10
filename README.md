# 🤖 Smart Telegram Bot

A feature-rich Telegram bot with jokes, calculator, and weather capabilities!

## ✨ Features

### 😄 Jokes
Get random programming jokes to brighten your day!

**Examples:**
- "Tell me a joke"
- "Make me laugh"
- "Something funny"

### 🧮 Calculator
Solve mathematical expressions instantly!

**Examples:**
- "Calculate 25 * 4"
- "What is 100 / 5"
- "42 + 58"
- "(10 + 5) * 3"

**Supported operations:**
- Addition: `+`
- Subtraction: `-`
- Multiplication: `*` or `×`
- Division: `/` or `÷`
- Parentheses for order: `()`

### 🌍 Weather
Get current weather information for any city worldwide!

**Examples:**
- "Weather in Delhi"
- "Mumbai temperature"
- "What's the weather in London"

**Shows:**
- Temperature (°C)
- Feels like temperature
- Weather conditions
- Humidity
- Wind speed

## 🚀 Quick Start

### 1. Install Dependencies

```bash
pip3 install -r requirements.txt
```

### 2. Configure Environment Variables

Copy `.env.example` to `.env` and add your tokens:

```bash
cp .env.example .env
```

Edit `.env` and add:
- **TELEGRAM_BOT_TOKEN** (Required) - Get from [@BotFather](https://t.me/BotFather)
- **OPENWEATHER_API_KEY** (Optional) - Get from [OpenWeatherMap](https://openweathermap.org/api)

### 3. Run the Bot

```bash
python3 bot.py
```

## 📝 Commands

- `/start` - Welcome message and feature overview
- `/help` - Detailed help with examples

## 🔧 How It Works

The bot uses keyword detection to understand what you're asking for:

1. **Message received** → Bot analyzes the text
2. **Keywords detected** → Appropriate function is triggered
3. **Response generated** → Reply sent back to you

### Smart Detection Examples

| Your Message | Bot Detects | Action |
|-------------|-------------|---------|
| "Tell me a joke" | Keyword: "joke" | Returns random joke |
| "Calculate 5 + 5" | Keyword: "calculate" | Performs calculation |
| "25 * 4" | Math operators: "*" | Performs calculation |
| "Weather in Delhi" | Keyword: "weather" | Fetches weather data |

## 🌐 Weather API Setup

The weather feature requires a free API key from OpenWeatherMap:

1. Go to [OpenWeatherMap](https://openweathermap.org/api)
2. Sign up for a free account
3. Verify your email
4. Go to API keys section
5. Copy your API key
6. Add it to your `.env` file:
   ```
   OPENWEATHER_API_KEY=your_actual_api_key_here
   ```

**Note:** The weather feature will show a helpful message if the API key is not configured. Other features work without it!

## 📂 Project Structure

```
Lythe/
├── bot.py                    # Main bot code
├── requirements.txt          # Python dependencies
├── .env                      # Your configuration (not in git)
├── .env.example             # Configuration template
├── .gitignore               # Git ignore rules
├── README.md                # This file!
├── BOT_WORKFLOW.md          # Technical workflow documentation
└── POLLING_EXPLAINED.md     # Polling explanation
```

## 🔐 Security

- Never commit your `.env` file to version control
- Keep your bot token and API keys private
- The bot uses secure HTTPS connections
- Calculator safely validates expressions before evaluation

## 🎯 Usage Examples

### Chat Examples

```
You: Tell me a joke
Bot: 😄 Here's a joke for you, Pragun!
     Why do programmers prefer dark mode? Because light attracts bugs! 🐛

You: Calculate 25 * 4
Bot: ✅ 25 * 4 = 100

You: Weather in Delhi
Bot: 🌍 Weather in Delhi, IN
     🌡️ Temperature: 18°C (Feels like 17°C)
     ☁️ Conditions: Clear sky
     💧 Humidity: 62%
     💨 Wind Speed: 3.5 m/s
```

## 🛠️ Troubleshooting

### Bot doesn't respond
- Check if the bot is running (`python3 bot.py`)
- Verify your `TELEGRAM_BOT_TOKEN` is correct in `.env`
- Check internet connection

### Weather doesn't work
- Verify `OPENWEATHER_API_KEY` is in your `.env` file
- Make sure the API key is active (can take a few minutes after signup)
- Check city name spelling

### Calculator error
- Use only numbers and operators: `+`, `-`, `*`, `/`
- Check parentheses are balanced
- Avoid special characters

### Timeout errors
- These are usually temporary network issues
- The bot will continue running
- Try sending your message again

## 📚 Technical Details

- **Language:** Python 3.9+
- **Framework:** python-telegram-bot 20.8
- **API:** OpenWeatherMap API
- **Method:** Long polling (no webhooks needed)

## 🔄 Future Enhancements

Possible features to add:
- Currency conversion
- Language translation
- Reminders and notifications
- To-do list management
- News headlines
- Random facts
- Unit conversions
- AI-powered responses

## 📄 License

This is a learning project. Feel free to use and modify as needed!

## 🤝 Contributing

Want to add features? Feel free to:
1. Fork the project
2. Add new features
3. Test thoroughly
4. Share your improvements!

## 💬 Support

If you encounter issues:
1. Check the troubleshooting section
2. Review the code comments in `bot.py`
3. Read `BOT_WORKFLOW.md` for technical details

---

Made with ❤️ for learning Telegram bot development!
