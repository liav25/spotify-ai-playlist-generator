import { PlaylistData } from './PlaylistContext';

export interface ChatMessage {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  timestamp: Date;
}

export interface ChatRequest {
  message: string;
  thread_id?: string;
}

export interface ChatResponse {
  message: string;
  thread_id: string;
  playlist_data?: PlaylistData;
}

export class ChatApi {
  // @ts-ignore - username may be used in future implementations
  private _username: string | null = null;
  private threadId: string | null = null;

  setUsername(username: string) {
    this._username = username;
  }

  private getAuthToken(): string | null {
    return localStorage.getItem('spotify_token');
  }

  async sendMessage(content: string): Promise<{ message: ChatMessage; playlistData?: PlaylistData }> {
    const token = this.getAuthToken();
    if (!token) {
      throw new Error('Authentication required');
    }

    const request: ChatRequest = {
      message: content,
      thread_id: this.threadId || undefined
    };

    try {
      const response = await fetch('/api/chat', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`
        },
        body: JSON.stringify(request)
      });

      if (!response.ok) {
        if (response.status === 401) {
          throw new Error('Authentication expired. Please login again.');
        } else if (response.status === 500) {
          throw new Error('Server error. Please try again later.');
        }
        throw new Error(`HTTP error! status: ${response.status}`);
      }

      const data: ChatResponse = await response.json();
      
      // Store thread_id for future messages
      this.threadId = data.thread_id;

      const assistantMessage: ChatMessage = {
        id: crypto.randomUUID(),
        role: 'assistant',
        content: data.message,
        timestamp: new Date()
      };

      return { 
        message: assistantMessage,
        playlistData: data.playlist_data
      };
    } catch (error) {
      console.error('Chat API error:', error);
      
      if (error instanceof Error) {
        throw error;
      }
      
      throw new Error('Failed to send message. Please try again.');
    }
  }

  async fetchPlaylist(playlistId: string): Promise<PlaylistData | null> {
    const token = this.getAuthToken();
    if (!token) {
      throw new Error('Authentication required');
    }

    try {
      const response = await fetch(`/api/playlist/${playlistId}`, {
        headers: {
          'Authorization': `Bearer ${token}`
        }
      });

      if (!response.ok) {
        if (response.status === 401) {
          throw new Error('Authentication expired. Please login again.');
        } else if (response.status === 404) {
          return null; // Playlist not found
        }
        throw new Error(`HTTP error! status: ${response.status}`);
      }

      const playlistData: PlaylistData = await response.json();
      return playlistData;
    } catch (error) {
      console.error('Playlist fetch error:', error);
      
      if (error instanceof Error) {
        throw error;
      }
      
      throw new Error('Failed to fetch playlist. Please try again.');
    }
  }

  // Reset conversation thread
  resetThread() {
    this.threadId = null;
  }
}

export const chatApi = new ChatApi();