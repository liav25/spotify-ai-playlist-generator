import React, { createContext, useContext, useState, ReactNode } from 'react';

export interface PlaylistTrack {
  id: string;
  name: string;
  artist: string;
  album: string;
  uri: string;
  duration_ms: number;
  popularity: number;
  album_cover?: string;
  preview_url?: string;
  external_urls: Record<string, string>;
}

export interface PlaylistData {
  id: string;
  name: string;
  description: string;
  public: boolean;
  collaborative: boolean;
  total_tracks: number;
  owner: string;
  tracks: PlaylistTrack[];
  images: Array<{ url: string; height: number; width: number }>;
}

interface PlaylistContextType {
  currentPlaylist: PlaylistData | null;
  setCurrentPlaylist: (playlist: PlaylistData | null) => void;
  isLoading: boolean;
  setIsLoading: (loading: boolean) => void;
}

const PlaylistContext = createContext<PlaylistContextType | undefined>(undefined);

export const usePlaylist = () => {
  const context = useContext(PlaylistContext);
  if (context === undefined) {
    throw new Error('usePlaylist must be used within a PlaylistProvider');
  }
  return context;
};

interface PlaylistProviderProps {
  children: ReactNode;
}

export const PlaylistProvider: React.FC<PlaylistProviderProps> = ({ children }) => {
  const [currentPlaylist, setCurrentPlaylist] = useState<PlaylistData | null>(null);
  const [isLoading, setIsLoading] = useState(false);

  return (
    <PlaylistContext.Provider
      value={{
        currentPlaylist,
        setCurrentPlaylist,
        isLoading,
        setIsLoading,
      }}
    >
      {children}
    </PlaylistContext.Provider>
  );
};