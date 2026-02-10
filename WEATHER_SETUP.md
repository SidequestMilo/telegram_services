# 🌍 Weather Feature Setup Guide

## What is OpenWeatherMap?

OpenWeatherMap is a free weather API service that provides current weather data for any location worldwide.

## How to Get Your Free API Key

### Step 1: Sign Up
1. Go to [https://openweathermap.org/api](https://openweathermap.org/api)
2. Click "Sign Up" (top right corner)
3. Fill in your details:
   - Username
   - Email
   - Password
4. Agree to terms and click "Create Account"

### Step 2: Verify Email
1. Check your email inbox
2. Click the verification link
3. Your account is now verified!

### Step 3: Get API Key
1. Log in to your OpenWeatherMap account
2. Go to [https://home.openweathermap.org/api_keys](https://home.openweathermap.org/api_keys)
3. You'll see a default API key already created
4. Copy this key (looks like: `a1b2c3d4e5f6g7h8i9j0k1l2m3n4o5p6`)

### Step 4: Add to Your Bot
1. Open your `.env` file
2. Add this line:
   ```
   OPENWEATHER_API_KEY=your_actual_key_here
   ```
3. Replace `your_actual_key_here` with the key you copied
4. Save the file

### Step 5: Wait (Important!)
⏰ **New API keys can take 10-15 minutes to activate**
- Don't worry if it doesn't work immediately
- Wait 10-15 minutes after signup
- Then restart your bot

## Testing the Weather Feature

Once your API key is active, try these commands in your bot:

```
Weather in Delhi
Mumbai temperature
What's the weather in London
```

## Troubleshooting

### "Weather feature is not configured" message
- Make sure the API key is in your `.env` file
- Check for typos in the variable name: `OPENWEATHER_API_KEY`
- Restart the bot after adding the key

### "City not found" error
- Check the spelling of the city name
- Try using just the city name without country
- Some cities may need the country code (e.g., "London, UK")

### "Could not fetch weather data" error
- Check your internet connection
- Make sure API key is active (wait 10-15 minutes after signup)
- Verify the API key is correct in `.env`

## Free Plan Limits

The free OpenWeatherMap plan includes:
- ✅ 60 calls per minute
- ✅ 1,000,000 calls per month
- ✅ Current weather data
- ✅ Worldwide coverage

This is more than enough for personal use!

## Optional: Without Weather API

If you don't want to set up the weather feature:
- The bot will still work perfectly
- Jokes and calculator features work without it
- When someone asks for weather, the bot will show a helpful setup message

## Example .env File

```bash
# Required - Your Telegram bot token
TELEGRAM_BOT_TOKEN=1234567890:ABCdefGHIjklMNOpqrsTUVwxyz

# Optional - For weather feature
OPENWEATHER_API_KEY=a1b2c3d4e5f6g7h8i9j0k1l2m3n4o5p6
```

## Need Help?

- OpenWeatherMap documentation: [https://openweathermap.org/api](https://openweathermap.org/api)
- OpenWeatherMap FAQ: [https://openweathermap.org/faq](https://openweathermap.org/faq)

---

Ready to test? Restart your bot and ask for the weather! 🌤️
