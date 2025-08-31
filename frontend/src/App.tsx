import { useState, useEffect } from 'react'
import './App.css'
import ChatInterface from './ChatInterface'
import Sidebar from './Sidebar'
import AnimatedInstructions from './AnimatedInstructions'
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
  const [user, setUser] = useState<User | null>({
    id: 'anonymous',
    display_name: 'Anonymous User',
    email: 'anonymous@user.com',
    images: []
  })
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    // Skip authentication - go directly to chat
    // Clean up URL if there are any auth-related parameters
    const urlParams = new URLSearchParams(window.location.search)
    if (urlParams.has('token') || urlParams.has('code') || urlParams.has('state')) {
      window.history.replaceState({}, document.title, window.location.pathname)
    }
  }, [])

  const handleLogout = () => {
    // No-op for now - could be used later for clearing conversations
    console.log('Logout clicked - no action needed in service account mode')
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
  const [isMobileSidebarOpen, setIsMobileSidebarOpen] = useState(false)
  
  const handleNewConversation = () => {
    // Reset the conversation thread and clear the current playlist
    chatApi.resetThread()
    setCurrentPlaylist(null)
    // Close mobile sidebar when starting new conversation
    setIsMobileSidebarOpen(false)
  }

  const toggleMobileSidebar = () => {
    setIsMobileSidebarOpen(!isMobileSidebarOpen)
  }

  const closeMobileSidebar = () => {
    setIsMobileSidebarOpen(false)
  }

  return (
    <div className="app">
      {/* Mobile Header */}
      <div className="mobile-header">
        <button 
          className="mobile-menu-btn" 
          onClick={toggleMobileSidebar}
          aria-label="Open menu"
        >
          <svg viewBox="0 0 24 24" fill="currentColor" className="hamburger-icon">
            <path d="M3 18h18v-2H3v2zm0-5h18v-2H3v2zm0-7v2h18V6H3z"/>
          </svg>
        </button>
        
        <div className="mobile-header-center">
          <div className="mobile-logo">
            <svg viewBox="0 0 24 24" fill="currentColor" className="spotify-logo">
              <path d="M12 0C5.4 0 0 5.4 0 12s5.4 12 12 12 12-5.4 12-12S18.66 0 12 0zm5.521 17.34c-.24.359-.66.48-1.021.24-2.82-1.74-6.36-2.101-10.561-1.141-.418.122-.779-.179-.899-.539-.12-.421.18-.78.54-.9 4.56-1.021 8.52-.6 11.64 1.32.42.18.479.659.301 1.02zm1.44-3.3c-.301.42-.841.6-1.262.3-3.239-1.98-8.159-2.58-11.939-1.38-.479.12-1.02-.12-1.14-.6-.12-.48.12-1.021.6-1.141C9.6 9.9 15 10.561 18.72 12.84c.361.181.54.78.241 1.2zm.12-3.36C15.24 8.4 8.82 8.16 5.16 9.301c-.6.179-1.2-.181-1.38-.721-.18-.601.18-1.2.72-1.381 4.26-1.26 11.28-1.02 15.721 1.621.539.3.719 1.02.419 1.56-.299.421-1.02.599-1.559.3z"/>
            </svg>
          </div>
          <h1 className="mobile-app-title">Mr. DJ</h1>
        </div>
        
        <div className="mobile-user-avatar">
          <div className="mobile-avatar-placeholder">
            🎵
          </div>
        </div>
      </div>
      
      {/* Mobile Sidebar Backdrop */}
      {isMobileSidebarOpen && (
        <div className="mobile-sidebar-backdrop" onClick={closeMobileSidebar} />
      )}
      
      <Sidebar 
        user={user}
        onNewConversation={handleNewConversation}
        onLogout={onLogout}
        isMobileOpen={isMobileSidebarOpen}
        onMobileClose={closeMobileSidebar}
      />
      
      <div className="main-content">
        <ChatInterface username={user.display_name} />
      </div>
    </div>
  )
}

export default App