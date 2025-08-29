#!/bin/bash

echo "🎵 Setting up Spotify OAuth Web App..."
echo ""

# Check if Python is installed
if ! command -v python3 &> /dev/null; then
    echo "❌ Python 3 is not installed. Please install Python 3.8+ first."
    exit 1
fi

# Check if Node.js is installed
if ! command -v node &> /dev/null; then
    echo "❌ Node.js is not installed. Please install Node.js 16+ first."
    exit 1
fi

# Check if uv is installed
if ! command -v uv &> /dev/null; then
    echo "❌ uv is not installed. Please install uv first:"
    echo "   curl -LsSf https://astral.sh/uv/install.sh | sh"
    exit 1
fi

echo "✅ Prerequisites check passed!"
echo ""

# Setup backend
echo "🔧 Setting up backend..."
cd backend

# Copy environment file if it doesn't exist
if [ ! -f .env ]; then
    cp env.example .env
    echo "📝 Created .env file. Please update it with your Spotify credentials."
fi

# Install dependencies
echo "📦 Installing Python dependencies..."
uv sync

echo "✅ Backend setup complete!"
echo ""

# Setup frontend
echo "🔧 Setting up frontend..."
cd ../frontend

# Install dependencies
echo "📦 Installing Node.js dependencies..."
npm install

echo "✅ Frontend setup complete!"
echo ""

echo "🎉 Setup complete!"
echo ""
echo "📋 Next steps:"
echo "1. Go to https://developer.spotify.com/dashboard"
echo "2. Create a new app"
echo "3. Add 'http://localhost:3000/auth/callback' to Redirect URIs"
echo "4. Update backend/.env with your Client ID and Client Secret"
echo ""
echo "🚀 To run the application:"
echo "  Backend:  cd backend && uv run main.py"
echo "  Frontend: cd frontend && npm run dev"
echo ""
echo "🌐 Open http://localhost:3000 in your browser"
