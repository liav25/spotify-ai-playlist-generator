#!/usr/bin/env python3
"""
Entry point for the Spotify AI Playlist Generator backend
"""

import uvicorn
from app.main import app

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000, reload=True)