import React from 'react';
import { PlaylistTrack as PlaylistTrackType } from './PlaylistContext';

interface PlaylistTrackProps {
  track: PlaylistTrackType;
  index: number;
}

const PlaylistTrack: React.FC<PlaylistTrackProps> = ({ track, index }) => {
  const formatDuration = (milliseconds: number): string => {
    const minutes = Math.floor(milliseconds / 60000);
    const seconds = Math.floor((milliseconds % 60000) / 1000);
    return `${minutes}:${seconds.toString().padStart(2, '0')}`;
  };

  const handleTrackClick = () => {
    // Open Spotify track if available
    if (track.external_urls.spotify) {
      window.open(track.external_urls.spotify, '_blank');
    }
  };

  return (
    <div 
      className="playlist-track-item"
      onClick={handleTrackClick}
    >
      <div className="track-index">
        {index + 1}
      </div>
      
      <div className="track-album-cover">
        {track.album_cover ? (
          <img 
            src={track.album_cover} 
            alt={`${track.album} cover`}
            className="album-cover-image"
            loading="lazy"
          />
        ) : (
          <div className="album-cover-placeholder">
            <svg viewBox="0 0 24 24" fill="currentColor" className="music-note-icon">
              <path d="M12 3v10.55c-.59-.34-1.27-.55-2-.55-2.21 0-4 1.79-4 4s1.79 4 4 4 4-1.79 4-4V7h4V3h-6z"/>
            </svg>
          </div>
        )}
      </div>

      <div className="track-info">
        <div className="track-name" title={track.name}>
          {track.name}
        </div>
        <div className="track-artist" title={track.artist}>
          {track.artist}
        </div>
      </div>

      <div className="track-duration">
        {formatDuration(track.duration_ms)}
      </div>
    </div>
  );
};

export default PlaylistTrack;