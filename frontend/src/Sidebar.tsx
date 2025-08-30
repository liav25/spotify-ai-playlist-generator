import React from 'react';
import { useTheme } from './ThemeContext';
import { usePlaylist } from './PlaylistContext';
import PlaylistTrack from './PlaylistTrack';
import './Sidebar.css';


interface SidebarProps {
  user: {
    display_name: string;
    images?: Array<{ url: string }>;
  } | null;
  onNewConversation: () => void;
  onLogout: () => void;
  isMobileOpen?: boolean;
  onMobileClose?: () => void;
}

const Sidebar: React.FC<SidebarProps> = ({ user, onNewConversation, onLogout, isMobileOpen, onMobileClose }) => {
  const { theme, toggleTheme } = useTheme();
  const { currentPlaylist, isLoading } = usePlaylist();
  const [isThemeSwitching, setIsThemeSwitching] = React.useState(false);
  
  const handleThemeToggle = () => {
    setIsThemeSwitching(true);
    toggleTheme();
    
    // Remove the animation class after the animation completes
    setTimeout(() => {
      setIsThemeSwitching(false);
    }, 600);
  };
  
  const formatTotalDuration = (tracks: any[]) => {
    const totalMs = tracks.reduce((sum, track) => sum + track.duration_ms, 0);
    const hours = Math.floor(totalMs / 3600000);
    const minutes = Math.floor((totalMs % 3600000) / 60000);
    
    if (hours > 0) {
      return `${hours}h ${minutes}m`;
    }
    return `${minutes}m`;
  };

  return (
    <div className={`sidebar ${isMobileOpen ? 'mobile-open' : ''}`}>
      <div className="sidebar-header">
        {/* Mobile Close Button */}
        <button 
          className="mobile-close-btn" 
          onClick={onMobileClose}
          aria-label="Close menu"
        >
          <svg viewBox="0 0 24 24" fill="currentColor" className="close-icon">
            <path d="M19 6.41L17.59 5 12 10.59 6.41 5 5 6.41 10.59 12 5 17.59 6.41 19 12 13.41 17.59 19 19 17.59 13.41 12z"/>
          </svg>
        </button>
        <div className="logo-section">
          <div className="logo">
            <svg viewBox="0 0 24 24" fill="currentColor" className="spotify-logo">
              <path d="M12 0C5.4 0 0 5.4 0 12s5.4 12 12 12 12-5.4 12-12S18.66 0 12 0zm5.521 17.34c-.24.359-.66.48-1.021.24-2.82-1.74-6.36-2.101-10.561-1.141-.418.122-.779-.179-.899-.539-.12-.421.18-.78.54-.9 4.56-1.021 8.52-.6 11.64 1.32.42.18.479.659.301 1.02zm1.44-3.3c-.301.42-.841.6-1.262.3-3.239-1.98-8.159-2.58-11.939-1.38-.479.12-1.02-.12-1.14-.6-.12-.48.12-1.021.6-1.141C9.6 9.9 15 10.561 18.72 12.84c.361.181.54.78.241 1.2zm.12-3.36C15.24 8.4 8.82 8.16 5.16 9.301c-.6.179-1.2-.181-1.38-.721-.18-.601.18-1.2.72-1.381 4.26-1.26 11.28-1.02 15.721 1.621.539.3.719 1.02.419 1.56-.299.421-1.02.599-1.559.3z"/>
            </svg>
          </div>
          <h1 className="app-title">Mr. DJ</h1>
        </div>
        
        <div className="sidebar-controls">
          <button 
            className={`theme-toggle-btn ${isThemeSwitching ? 'theme-switching' : ''}`} 
            onClick={handleThemeToggle} 
            title={`Switch to ${theme === 'light' ? 'dark' : 'light'} mode`}
          >
            {theme === 'light' ? (
              // Moon icon for switching to dark mode
              <svg viewBox="0 0 24 24" fill="currentColor" className="theme-icon">
                <path d="M21 12.79A9 9 0 1111.21 3 7 7 0 0021 12.79z"/>
              </svg>
            ) : (
              // Sun icon for switching to light mode
              <svg viewBox="0 0 24 24" fill="currentColor" className="theme-icon">
                <path d="M12 17q-2.075 0-3.537-1.463T7 12q0-2.075 1.463-3.537T12 7q2.075 0 3.537 1.463T17 12q0 2.075-1.463 3.537T12 17ZM2 13q-.425 0-.712-.288T1 12q0-.425.288-.712T2 11h2q.425 0 .713.288T5 12q0 .425-.288.712T4 13H2Zm18 0q-.425 0-.712-.288T19 12q0-.425.288-.712T20 11h2q.425 0 .713.288T23 12q0 .425-.288.712T22 13h-2Zm-8-8q-.425 0-.712-.288T11 4V2q0-.425.288-.712T12 1q.425 0 .713.288T13 2v2q0 .425-.288.712T12 5Zm0 18q-.425 0-.712-.288T11 20v-2q0-.425.288-.712T12 17q.425 0 .713.288T13 18v2q0 .425-.288.712T12 23ZM5.65 7.05 4.575 6q-.3-.275-.3-.7t.275-.7q.275-.3.7-.3t.7.3L7.05 5.65q.275.3.275.7t-.3.7q-.275.275-.687.275t-.688-.3ZM18 19.425l-1.05-1.075q-.275-.3-.275-.712t.275-.688q.275-.3.688-.3t.712.3L19.425 18q.3.275.3.7t-.3.7q-.275.275-.7.275t-.725-.3ZM16.95 7.05q-.3-.275-.3-.687t.3-.688L18.025 4.6q.275-.3.7-.3t.7.3q.3.275.3.7t-.3.725L18.35 7.05q-.3.275-.712.275t-.688-.275ZM4.575 19.425q-.3-.3-.3-.725t.3-.7L5.65 16.95q.275-.275.687-.275t.688.275q.3.3.3.713t-.3.712L6 19.425q-.275.275-.7.275t-.725-.275Z"/>
              </svg>
            )}
          </button>
          
          <button className="new-conversation-btn" onClick={onNewConversation}>
            <svg viewBox="0 0 24 24" fill="currentColor" className="plus-icon">
              <path d="M19 13h-6v6h-2v-6H5v-2h6V5h2v6h6v2z"/>
            </svg>
            New Conversation
          </button>
        </div>
      </div>

      <div className="playlist-section">
        {isLoading ? (
          <div className="playlist-loading">
            <div className="loading-spinner"></div>
            <div className="loading-text">Loading playlist...</div>
          </div>
        ) : currentPlaylist ? (
          <>
            <div className="playlist-header">
              <div className="playlist-cover">
                {currentPlaylist.images && currentPlaylist.images.length > 0 ? (
                  <img 
                    src={currentPlaylist.images[0].url} 
                    alt={`${currentPlaylist.name} cover`}
                    className="playlist-cover-image"
                  />
                ) : (
                  <div className="playlist-cover-placeholder">
                    <svg viewBox="0 0 24 24" fill="currentColor" className="playlist-icon">
                      <path d="M15 6H3v2h12V6zm0 4H3v2h12v-2zM3 16h8v-2H3v2zM17 6v8.18c-.31-.11-.65-.18-1-.18-1.66 0-3 1.34-3 3s1.34 3 3 3 3-1.34 3-3V8h3V6h-5z"/>
                    </svg>
                  </div>
                )}
              </div>
              <div className="playlist-info">
                <h3 className="playlist-title">{currentPlaylist.name}</h3>
                <div className="playlist-stats">
                  {currentPlaylist.tracks.length} songs • {formatTotalDuration(currentPlaylist.tracks)}
                </div>
              </div>
            </div>
            
            <div className="playlist-tracks">
              {currentPlaylist.tracks.map((track, index) => (
                <PlaylistTrack 
                  key={track.id} 
                  track={track} 
                  index={index}
                />
              ))}
            </div>
          </>
        ) : (
          <div className="playlist-empty">
            <div className="empty-state-icon">
              <svg viewBox="0 0 24 24" fill="currentColor" className="music-note-icon">
                <path d="M12 3v10.55c-.59-.34-1.27-.55-2-.55-2.21 0-4 1.79-4 4s1.79 4 4 4 4-1.79 4-4V7h4V3h-6z"/>
              </svg>
            </div>
            <h3>No Active Playlist</h3>
            <p>Create a playlist to see it here with track details and album covers.</p>
          </div>
        )}
      </div>

      {user && (
        <div className="sidebar-footer">
          <div className="user-info">
            <div className="user-avatar-container">
              {user.images && user.images.length > 0 ? (
                <img 
                  src={user.images[0].url} 
                  alt={user.display_name}
                  className="user-avatar"
                />
              ) : (
                <div className="user-avatar-placeholder">
                  {user.display_name.charAt(0).toUpperCase()}
                </div>
              )}
            </div>
            <div className="user-details">
              <div className="user-name">{user.display_name}</div>
              <div className="user-status">Ready to create playlists</div>
            </div>
            <button className="logout-btn" onClick={onLogout} title="Sign out">
              <svg viewBox="0 0 24 24" fill="currentColor" className="logout-icon">
                <path d="M17 7l-1.41 1.41L18.17 11H8v2h10.17l-2.58 2.59L17 17l5-5zM4 5h8V3H4c-1.1 0-2 .9-2 2v14c0 1.1.9 2 2 2h8v-2H4V5z"/>
              </svg>
            </button>
          </div>
        </div>
      )}
    </div>
  );
};

export default Sidebar;