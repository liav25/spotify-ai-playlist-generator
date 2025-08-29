export interface ChatMessage {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  timestamp: Date;
}

export interface ChatResponse {
  message: ChatMessage;
}

export class MockChatApi {
  private username: string | null = null;

  setUsername(username: string) {
    this.username = username;
  }

  async sendMessage(_content: string): Promise<ChatResponse> {
    const delay = Math.random() * 500 + 300;
    
    await new Promise(resolve => setTimeout(resolve, delay));

    const response: ChatMessage = {
      id: crypto.randomUUID(),
      role: 'assistant',
      content: `Hello ${this.username || 'User'}`,
      timestamp: new Date()
    };

    return { message: response };
  }
}

export const mockChatApi = new MockChatApi();