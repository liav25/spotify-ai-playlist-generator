import { PlaylistData } from './PlaylistContext';

export interface ChatMessageMetadata {
  type?: 'tool' | 'status';
  status?: 'active' | 'completed' | 'error';
  expanded?: boolean;
  toolActivities?: Array<{
    id: string;
    label: string;
    status: 'active' | 'completed' | 'error';
  }>;
}

export interface ChatMessage {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  timestamp: Date;
  metadata?: ChatMessageMetadata;
}

export interface ChatRequest {
  message: string;
  thread_id?: string;
  ultrathink?: boolean;
}

export interface ChatResponse {
  message: string;
  thread_id: string;
  playlist_data?: PlaylistData;
}

export interface ToolCallEvent {
  type: 'tool_start' | 'tool_end' | 'status' | 'complete' | 'error';
  tool?: string;
  message: string;
  thread_id?: string;
  playlist_data?: PlaylistData;
}

export type ToolCallCallback = (event: ToolCallEvent) => void;

// Get API base URL - use environment variable in production, fallback to relative URLs
const getApiBaseUrl = (): string => {
  // In production, VITE_API_URL will be set by Render
  const apiUrl = import.meta.env.VITE_API_URL;
  const isProd = import.meta.env.PROD;
  
  if (apiUrl && isProd) {
    return apiUrl;
  }
  // In development, use relative URLs with proxy
  return '';
};

const normalizePlaylistData = (
  playlist?: PlaylistData | null
): PlaylistData | undefined => {
  if (!playlist) {
    return undefined;
  }

  const tracks = Array.isArray(playlist.tracks)
    ? playlist.tracks.map(track => ({
        ...track,
        external_urls: track.external_urls || {}
      }))
    : [];

  return {
    ...playlist,
    tracks,
    images: playlist.images || [],
    external_urls: playlist.external_urls || {},
  };
};

export class ChatApi {
  // @ts-ignore - username may be used in future implementations
  private _username: string | null = null;
  private threadId: string | null = null;
  private apiBaseUrl: string = getApiBaseUrl();
  private ultrathinkEnabled = false;

  setUsername(username: string) {
    this._username = username;
  }

  setUltrathinkEnabled(enabled: boolean) {
    this.ultrathinkEnabled = enabled;
  }

  getUltrathinkEnabled(): boolean {
    return this.ultrathinkEnabled;
  }

  private getAuthToken(): string | null {
    return localStorage.getItem('spotify_token');
  }

  async sendMessage(content: string): Promise<{ message: ChatMessage; playlistData?: PlaylistData }> {
    const token = this.getAuthToken();
    
    const request: ChatRequest = {
      message: content,
      thread_id: this.threadId || undefined
    };

    if (this.ultrathinkEnabled) {
      request.ultrathink = true;
    }

    const headers: Record<string, string> = {
      'Content-Type': 'application/json'
    };
    
    // Only add Authorization header if token exists (for optional user auth)
    if (token) {
      headers['Authorization'] = `Bearer ${token}`;
    }

    try {
      const response = await fetch(`${this.apiBaseUrl}/api/chat`, {
        method: 'POST',
        headers,
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
        playlistData: normalizePlaylistData(data.playlist_data)
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
      const response = await fetch(`${this.apiBaseUrl}/api/playlist/${playlistId}`, {
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
      return normalizePlaylistData(playlistData) || null;
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

  async sendMessageWithStreaming(
    content: string,
    onToolCall: ToolCallCallback
  ): Promise<{ message: ChatMessage; playlistData?: PlaylistData }> {
    const token = this.getAuthToken();

    const request: ChatRequest = {
      message: content,
      thread_id: this.threadId || undefined
    };

    if (this.ultrathinkEnabled) {
      request.ultrathink = true;
    }

    const headers: Record<string, string> = {
      'Content-Type': 'application/json'
    };

    if (token) {
      headers['Authorization'] = `Bearer ${token}`;
    }

    try {
      const response = await fetch(`${this.apiBaseUrl}/api/chat/stream`, {
        method: 'POST',
        headers,
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

      const reader = response.body?.getReader();
      const decoder = new TextDecoder();
      let finalMessage = '';
      let finalThreadId = this.threadId || '';
      let finalPlaylistData: PlaylistData | undefined;
      let sseBuffer = '';

      if (!reader) {
        throw new Error('Failed to get response reader');
      }

      const processEventChunk = (eventChunk: string) => {
        const dataLines = eventChunk
          .split('\n')
          .filter(line => line.startsWith('data:'));

        if (dataLines.length === 0) {
          return;
        }

        const payload = dataLines
          .map(line => line.slice(5).trimStart())
          .join('\n');

        if (!payload) {
          return;
        }

        try {
          const event: ToolCallEvent = JSON.parse(payload);
          console.log('Received SSE event:', event);

          if (event.type === 'tool_start' || event.type === 'status') {
            onToolCall(event);
          } else if (event.type === 'tool_end') {
            onToolCall(event);
          } else if (event.type === 'complete') {
            console.log('Received complete event with message:', event.message);
            finalMessage = event.message;
            finalThreadId = event.thread_id || finalThreadId;
            finalPlaylistData = event.playlist_data;
          } else if (event.type === 'error') {
            throw new Error(event.message);
          }
        } catch (parseError) {
          console.warn('Failed to parse SSE event payload:', payload, parseError);
        }
      };

      try {
        while (true) {
          const { done, value } = await reader.read();

          if (done) {
            console.log('Stream completed');
            break;
          }

          sseBuffer += decoder.decode(value, { stream: true });

          const eventChunks = sseBuffer.split('\n\n');
          sseBuffer = eventChunks.pop() ?? '';

          for (const eventChunk of eventChunks) {
            processEventChunk(eventChunk);
          }
        }
      } finally {
        if (sseBuffer.trim().length > 0) {
          processEventChunk(sseBuffer);
        }
        reader.releaseLock();
      }

      console.log('Final message:', finalMessage);
      console.log('Final thread ID:', finalThreadId);

      // Store thread_id for future messages
      this.threadId = finalThreadId;

      const assistantMessage: ChatMessage = {
        id: crypto.randomUUID(),
        role: 'assistant',
        content: finalMessage,
        timestamp: new Date()
      };

      return {
        message: assistantMessage,
        playlistData: normalizePlaylistData(finalPlaylistData)
      };
    } catch (error) {
      console.error('Streaming chat API error:', error);

      if (error instanceof Error) {
        throw error;
      }

      throw new Error('Failed to send message. Please try again.');
    }
  }
}

export const chatApi = new ChatApi();
