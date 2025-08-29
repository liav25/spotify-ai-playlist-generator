import React, { useEffect, useState, useRef } from 'react';
import { chatApi, ChatMessage } from './chatApi';
import { usePlaylist } from './PlaylistContext';
import './ChatInterface.css';

interface ChatInterfaceProps {
  username: string;
}

const ChatInterface: React.FC<ChatInterfaceProps> = ({ username }) => {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [inputValue, setInputValue] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const { setCurrentPlaylist } = usePlaylist();
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  // Auto-scroll to bottom when new messages arrive
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  useEffect(() => {
    chatApi.setUsername(username);
    // Add welcome message when chat interface loads
    const welcomeMessage: ChatMessage = {
      id: crypto.randomUUID(),
      role: 'assistant',
      content: `Hi ${username}! I'm your AI music assistant. I can help you create amazing playlists based on your preferences, mood, or any specific requirements you have in mind.\n\nTry asking me something like:\n• \"Create a chill indie playlist for studying\"\n• \"Make an upbeat workout mix\"\n• \"Generate a road trip playlist with 90s hits\"\n\nWhat kind of playlist would you like to create today?`,
      timestamp: new Date()
    };
    setMessages([welcomeMessage]);
  }, [username]);

  // Auto-resize textarea
  const adjustTextareaHeight = () => {
    const textarea = textareaRef.current;
    if (textarea) {
      textarea.style.height = 'auto';
      textarea.style.height = `${Math.min(textarea.scrollHeight, 120)}px`;
    }
  };

  useEffect(() => {
    adjustTextareaHeight();
  }, [inputValue]);

  const handleSendMessage = async () => {
    if (!inputValue.trim() || isLoading) return;

    const userMessage: ChatMessage = {
      id: crypto.randomUUID(),
      role: 'user',
      content: inputValue,
      timestamp: new Date()
    };

    setMessages(prev => [...prev, userMessage]);
    setInputValue('');
    setIsLoading(true);

    try {
      const response = await chatApi.sendMessage(inputValue);
      setMessages(prev => [...prev, response.message]);
      
      // Update playlist if provided
      if (response.playlistData) {
        setCurrentPlaylist(response.playlistData);
      }
    } catch (error) {
      console.error('Error sending message:', error);
      
      const errorMessage: ChatMessage = {
        id: crypto.randomUUID(),
        role: 'assistant',
        content: `I'm sorry, I encountered an error while processing your request. ${error instanceof Error ? error.message : 'Please try again or check your connection.'}`,
        timestamp: new Date()
      };
      setMessages(prev => [...prev, errorMessage]);
    } finally {
      setIsLoading(false);
    }
  };

  const handleKeyPress = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSendMessage();
    }
  };

  const handlePresetClick = (title: string) => {
    setInputValue(title);
    if (textareaRef.current) {
      textareaRef.current.focus();
    }
  };


  const presetOptions = [
    {
      title: "Create a workout playlist",
      icon: "🏃",
      description: "High-energy tracks for your fitness routine"
    },
    {
      title: "Make a chill evening playlist", 
      icon: "🌙",
      description: "Relaxing tunes for winding down"
    },
    {
      title: "Road trip music mix",
      icon: "🚗", 
      description: "Perfect songs for long drives"
    }
  ];

  return (
    <div className="chat-interface">
      {messages.length === 1 && messages[0].role === 'assistant' ? (
        // Show welcome state with preset cards
        <div className="welcome-container">
          <div className="welcome-header">
            <div className="welcome-icon">
              <svg viewBox="0 0 24 24" fill="currentColor" className="spotify-logo">
                <path d="M12 0C5.4 0 0 5.4 0 12s5.4 12 12 12 12-5.4 12-12S18.66 0 12 0zm5.521 17.34c-.24.359-.66.48-1.021.24-2.82-1.74-6.36-2.101-10.561-1.141-.418.122-.779-.179-.899-.539-.12-.421.18-.78.54-.9 4.56-1.021 8.52-.6 11.64 1.32.42.18.479.659.301 1.02zm1.44-3.3c-.301.42-.841.6-1.262.3-3.239-1.98-8.159-2.58-11.939-1.38-.479.12-1.02-.12-1.14-.6-.12-.48.12-1.021.6-1.141C9.6 9.9 15 10.561 18.72 12.84c.361.181.54.78.241 1.2zm.12-3.36C15.24 8.4 8.82 8.16 5.16 9.301c-.6.179-1.2-.181-1.38-.721-.18-.601.18-1.2.72-1.381 4.26-1.26 11.28-1.02 15.721 1.621.539.3.719 1.02.419 1.56-.299.421-1.02.599-1.559.3z"/>
              </svg>
            </div>
            <h1>Welcome to PlaylistAI</h1>
            <p>I'm your AI playlist curator. Tell me what you're in the mood for, and I'll create the perfect playlist for you on Spotify.</p>
          </div>
          
          <div className="preset-cards">
            {presetOptions.map((preset, index) => (
              <div
                key={index}
                className="preset-card"
                onClick={() => handlePresetClick(preset.title)}
              >
                <div className="preset-icon">{preset.icon}</div>
                <div className="preset-content">
                  <h3>{preset.title}</h3>
                  <p>{preset.description}</p>
                </div>
              </div>
            ))}
          </div>
        </div>
      ) : (
        // Show regular chat messages
        <div className="messages-container">
          {messages.map((message) => (
            <div
              key={message.id}
              className={`message ${message.role === 'user' ? 'user-message' : 'assistant-message'}`}
            >
              <div className="message-bubble">
                <div className="message-content">
                  {message.content.split('\n').map((line, index) => (
                    <div key={index} className="message-line">
                      {line || '\u00A0'}
                    </div>
                  ))}
                </div>
              </div>
            </div>
          ))}
          
          {/* Typing Indicator */}
          {isLoading && (
            <div className="message assistant-message typing-indicator">
              <div className="message-bubble">
                <span>Thinking</span>
                <div className="typing-dots">
                  <span></span>
                  <span></span>
                  <span></span>
                </div>
              </div>
            </div>
          )}
          
          <div ref={messagesEndRef} />
        </div>
      )}

      {/* Input Area */}
      <div className="input-area">
        <div className="input-container">
          <div className="input-wrapper">
            <textarea
              ref={textareaRef}
              className="message-input"
              value={inputValue}
              onChange={(e) => setInputValue(e.target.value)}
              onKeyPress={handleKeyPress}
              placeholder="Tell me what kind of playlist you want..."
              disabled={isLoading}
              rows={1}
            />
            <button
              className="send-button"
              onClick={handleSendMessage}
              disabled={!inputValue.trim() || isLoading}
              aria-label="Send message"
            >
              <svg viewBox="0 0 24 24" fill="currentColor">
                <path d="M2.01 21L23 12 2.01 3 2 10l15 2-15 2z"/>
              </svg>
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};

export default ChatInterface;