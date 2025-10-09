import { useState, useEffect } from 'react'
import './App.css'
import ChatInterface from './ChatInterface'
import Sidebar from './Sidebar'
import { ThemeProvider } from './ThemeContext'
import { PlaylistProvider } from './PlaylistContext'
// Resolve logo URL via Vite so bundler handles it correctly
const appLogoUrl = new URL('../mrdjlogo.svg', import.meta.url).href


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
  const user: User = {
    id: 'anonymous',
    display_name: 'Anonymous User',
    email: 'anonymous@user.com',
    images: []
  }

  useEffect(() => {
    // Skip authentication - go directly to chat
    // Clean up URL if there are any auth-related parameters
    const urlParams = new URLSearchParams(window.location.search)
    if (urlParams.has('token') || urlParams.has('code') || urlParams.has('state')) {
      window.history.replaceState({}, document.title, window.location.pathname)
    }
  }, [])


  return (
    <ThemeProvider>
      <PlaylistProvider>
        <AppContent user={user} />
      </PlaylistProvider>
    </ThemeProvider>
  )
}

function AppContent({ user }: { user: User }) {
  const [isMobileSidebarOpen, setIsMobileSidebarOpen] = useState(false)
  const [hasOpenedSidebar, setHasOpenedSidebar] = useState(false)

  const toggleMobileSidebar = () => {
    setHasOpenedSidebar(true) // Stop pulse animation after first interaction
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
          className={`mobile-menu-btn ${!hasOpenedSidebar ? 'pulse-animation' : ''}`}
          onClick={toggleMobileSidebar}
          aria-label="Show me playlists"
        >
          <svg viewBox="0 0 24 24" fill="currentColor" className="playlist-icon">
            <path d="M15 6H3v2h12V6zm0 4H3v2h12v-2zM3 16h8v-2H3v2zM17 6v8.18c-.31-.11-.65-.18-1-.18-1.66 0-3 1.34-3 3s1.34 3 3 3 3-1.34 3-3V8h3V6h-5z"/>
          </svg>
          <span className="mobile-menu-text">Show me!</span>
        </button>
        
        <div className="mobile-header-center">
          <div className="mobile-logo">
            <img src={appLogoUrl} alt="Mr. DJ logo" className="brand-logo-img" />
          </div>
          <h1 className="mobile-app-title">Mr. DJ</h1>
        </div>
      </div>
      
      {/* Mobile Sidebar Backdrop */}
      {isMobileSidebarOpen && (
        <div className="mobile-sidebar-backdrop" onClick={closeMobileSidebar} />
      )}
      
      <Sidebar 
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
