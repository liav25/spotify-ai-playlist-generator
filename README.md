# Mr. DJ

An AI-powered Spotify playlist generator that uses OAuth authentication with React (Vite) frontend and FastAPI backend.

## Features

- Spotify OAuth 2.0 Authorization Code Flow
- User authentication with Spotify
- Create personalized playlists using AI
- Modern React frontend with Vite
- FastAPI backend with proper OAuth handling

## Project Structure

```
test_spotify/
├── frontend/          # React + Vite frontend
├── backend/           # FastAPI backend
├── README.md          # This file
└── .env.example       # Environment variables template
```

## Prerequisites

- Python 3.8+
- Node.js 16+
- Spotify Developer Account

## Setup Instructions

### 1. Spotify App Setup

1. Go to [Spotify Developer Dashboard](https://developer.spotify.com/dashboard)
2. Create a new app
3. Add `http://localhost:3000/auth/callback` to Redirect URIs
4. Note down your Client ID and Client Secret

### 2. Environment Setup

1. Copy `.env.example` to `.env` in the backend directory
2. Fill in your Spotify credentials:
   ```
   SPOTIFY_CLIENT_ID=your_client_id_here
   SPOTIFY_CLIENT_SECRET=your_client_secret_here
   ```

### 3. Backend Setup

```bash
cd backend
uv sync
uv run main.py
```

The backend will run on `http://localhost:8000`

### 4. Frontend Setup

```bash
cd frontend
npm install
npm run dev
```

The frontend will run on `http://localhost:3000`

## Usage

1. Open `http://localhost:3000` in your browser
2. Click "Login with Spotify"
3. Authorize the application
4. You can start creating playlists with Mr. DJ after successful authentication

## API Endpoints

- `GET /auth/login` - Initiates Spotify OAuth flow
- `GET /auth/callback` - Handles OAuth callback
- `GET /api/user` - Returns current user information
- `POST /api/chat` - Chat with Mr. DJ to create playlists

## Technologies Used

- **Frontend**: React 18, Vite, TypeScript
- **Backend**: FastAPI, Python 3.8+
- **Authentication**: Spotify OAuth 2.0
- **Package Manager**: uv (Python), npm (Node.js)
