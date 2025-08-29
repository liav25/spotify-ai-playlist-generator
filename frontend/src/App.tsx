import { useState, useEffect } from 'react'
import './App.css'
import ChatInterface from './ChatInterface'
import Sidebar from './Sidebar'
import { ThemeProvider } from './ThemeContext'
import { PlaylistProvider, usePlaylist } from './PlaylistContext'
import { chatApi } from './chatApi'

// Get API base URL for auth endpoints
const getApiBaseUrl = (): string => {
  const apiUrl = import.meta.env.VITE_API_URL;
  const isProd = import.meta.env.PROD;
  
  if (apiUrl && isProd) {
    return apiUrl;
  }
  // In development, use relative URLs with proxy
  return '';
};

interface User {
  id: string
  display_name: string
  email?: string
  images?: Array<{
    url: string
    height: number
    width: number
  }>
}

function App() {
  const [user, setUser] = useState<User | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    // Check for token in URL parameters (after OAuth callback)
    const urlParams = new URLSearchParams(window.location.search)
    const token = urlParams.get('token')
    
    if (token) {
      // Store token in localStorage
      localStorage.setItem('spotify_token', token)
      
      // Clean up URL
      window.history.replaceState({}, document.title, window.location.pathname)
      
      // Fetch user data
      fetchUserData(token)
    } else {
      // Check if we have a stored token
      const storedToken = localStorage.getItem('spotify_token')
      if (storedToken) {
        fetchUserData(storedToken)
      }
    }
  }, [])

  const fetchUserData = async (token: string) => {
    setLoading(true)
    setError(null)
    
    try {
      const response = await fetch('/api/user', {
        headers: {
          'Authorization': `Bearer ${token}`
        }
      })
      
      if (response.ok) {
        const userData = await response.json()
        setUser(userData)
      } else {
        // Token might be expired, remove it
        localStorage.removeItem('spotify_token')
        setError('Authentication failed. Please login again.')
      }
    } catch (err) {
      console.error('Error fetching user data:', err)
      setError('Failed to fetch user data')
    } finally {
      setLoading(false)
    }
  }

  const handleLogin = () => {
    setLoading(true)
    setError(null)
    
    // Redirect to backend OAuth endpoint
    const apiBaseUrl = getApiBaseUrl()
    window.location.href = `${apiBaseUrl}/auth/login`
  }

  const handleLogout = () => {
    localStorage.removeItem('spotify_token')
    setUser(null)
    setError(null)
  }

  if (loading) {
    return (
      <ThemeProvider>
        <PlaylistProvider>
          <div className="app loading-state">
            <div className="loading-container">
              <div className="loading-content">
                <div className="spinner"></div>
                <div className="loading-text">Loading PlaylistAI...</div>
              </div>
            </div>
          </div>
        </PlaylistProvider>
      </ThemeProvider>
    )
  }

  if (!user) {
    return (
      <ThemeProvider>
        <PlaylistProvider>
          <div className="app login-state">
            <div className="login-container">
              <div className="login-content">
                {error && (
                  <div className="error">
                    <p>{error}</p>
                    <button onClick={handleLogout}>Try Again</button>
                  </div>
                )}
                
                <div className="login-section">
                  <div className="login-header">
                    <div className="logo">
                      <svg viewBox="0 0 24 24" fill="currentColor" className="spotify-logo">
                        <path d="M12 0C5.4 0 0 5.4 0 12s5.4 12 12 12 12-5.4 12-12S18.66 0 12 0zm5.521 17.34c-.24.359-.66.48-1.021.24-2.82-1.74-6.36-2.101-10.561-1.141-.418.122-.779-.179-.899-.539-.12-.421.18-.78.54-.9 4.56-1.021 8.52-.6 11.64 1.32.42.18.479.659.301 1.02zm1.44-3.3c-.301.42-.841.6-1.262.3-3.239-1.98-8.159-2.58-11.939-1.38-.479.12-1.02-.12-1.14-.6-.12-.48.12-1.021.6-1.141C9.6 9.9 15 10.561 18.72 12.84c.361.181.54.78.241 1.2zm.12-3.36C15.24 8.4 8.82 8.16 5.16 9.301c-.6.179-1.2-.181-1.38-.721-.18-.601.18-1.2.72-1.381 4.26-1.26 11.28-1.02 15.721 1.621.539.3.719 1.02.419 1.56-.299.421-1.02.599-1.559.3z"/>
                      </svg>
                    </div>
                    <h1>PlaylistAI</h1>
                  </div>
                  
                  <p>Connect your Spotify account to start creating personalized playlists with AI assistance</p>
                  
                  <button onClick={handleLogin} className="spotify-login-btn">
                    <svg 
                      viewBox="0 0 24 24" 
                      width="24" 
                      height="24" 
                      fill="currentColor"
                      className="spotify-icon"
                    >
                      <path d="M12 0C5.4 0 0 5.4 0 12s5.4 12 12 12 12-5.4 12-12S18.66 0 12 0zm5.521 17.34c-.24.359-.66.48-1.021.24-2.82-1.74-6.36-2.101-10.561-1.141-.418.122-.779-.179-.899-.539-.12-.421.18-.78.54-.9 4.56-1.021 8.52-.6 11.64 1.32.42.18.479.659.301 1.02zm1.44-3.3c-.301.42-.841.6-1.262.3-3.239-1.98-8.159-2.58-11.939-1.38-.479.12-1.02-.12-1.14-.6-.12-.48.12-1.021.6-1.141C9.6 9.9 15 10.561 18.72 12.84c.361.181.54.78.241 1.2zm.12-3.36C15.24 8.4 8.82 8.16 5.16 9.301c-.6.179-1.2-.181-1.38-.721-.18-.601.18-1.2.72-1.381 4.26-1.26 11.28-1.02 15.721 1.621.539.3.719 1.02.419 1.56-.299.421-1.02.599-1.559.3z"/>
                    </svg>
                    Connect to Spotify
                  </button>
                </div>
              </div>
            </div>
          </div>
        </PlaylistProvider>
      </ThemeProvider>
    )
  }

  return (
    <ThemeProvider>
      <PlaylistProvider>
        <AppContent user={user} onLogout={handleLogout} />
      </PlaylistProvider>
    </ThemeProvider>
  )
}

function AppContent({ user, onLogout }: { user: User; onLogout: () => void }) {
  const { setCurrentPlaylist } = usePlaylist()
  
  const handleNewConversation = () => {
    // Reset the conversation thread and clear the current playlist
    chatApi.resetThread()
    setCurrentPlaylist(null)
  }

  return (
    <div className="app">
      <Sidebar 
        user={user}
        onNewConversation={handleNewConversation}
        onLogout={onLogout}
      />
      
      <div className="main-content">
        <ChatInterface username={user.display_name} />
      </div>
    </div>
  )
}

export default App