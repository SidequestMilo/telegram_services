
#!/bin/bash
# 🚀 Telegram Gateway Deployment Script

# 1. Stop existing containers
echo "Stopping existing containers..."
docker-compose down

# 2. Pull latest changes (optional, uncomment if using git)
# git pull origin main

# 3. Check for .env file
if [ ! -f .env ]; then
    echo "⚠️  .env file not found! creating from example..."
    if [ -f .env.example ]; then
        cp .env.example .env
        echo "✅ Created .env. Please edit it with your secrets!"
        exit 1
    else
        echo "❌ .env.example missing. Please create .env manually."
        exit 1
    fi
fi

# 4. Build and Start
echo "Building and starting services..."
docker-compose up -d --build

# 5. Show Status
echo "✅ Deployment complete! Services are running."
docker-compose ps
