import React, { useEffect, useState, useRef } from 'react';
import ReactMarkdown from 'react-markdown';
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
    // Start with empty messages - no welcome message
    setMessages([]);
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
        
        // If this is a newly created playlist with no tracks, 
        // fetch the updated playlist data after a short delay to get any tracks that were added
        if (response.playlistData.tracks.length === 0) {
          setTimeout(async () => {
            try {
              const updatedPlaylist = await chatApi.fetchPlaylist(response.playlistData!.id);
              if (updatedPlaylist && updatedPlaylist.tracks.length > 0) {
                setCurrentPlaylist(updatedPlaylist);
              }
            } catch (error) {
              console.warn('Failed to fetch updated playlist:', error);
            }
          }, 2000); // Wait 2 seconds for tracks to be added
        }
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

  const handlePresetClick = (description: string) => {
    setInputValue(description);
    if (textareaRef.current) {
      textareaRef.current.focus();
    }
  };

  // Function to detect if text contains Hebrew characters
  const containsHebrew = (text: string): boolean => {
    const hebrewRegex = /[\u0590-\u05FF]/;
    return hebrewRegex.test(text);
  };

  // Function to determine text direction
  const getTextDirection = (text: string): 'rtl' | 'ltr' => {
    return containsHebrew(text) ? 'rtl' : 'ltr';
  };

  // Extract text content from React children
  const extractTextContent = (children: React.ReactNode): string => {
    if (typeof children === 'string') return children;
    if (typeof children === 'number') return children.toString();
    if (Array.isArray(children)) {
      return children.map(extractTextContent).join('');
    }
    if (children && typeof children === 'object' && 'props' in children) {
      return extractTextContent((children as any).props.children);
    }
    return children?.toString() || '';
  };


  const presetOptions = [
    {
      title: "Create a workout playlist",
      icon: "🏃",
      description: "I need energizing music to fuel my workouts and keep me motivated during exercise. Please create a high-tempo playlist with upbeat songs that will help me maintain intensity and push through challenging sets. Include genres like electronic, hip-hop, rock, or pop with strong beats and motivational lyrics. The playlist should flow well from warm-up to peak intensity tracks."
    },
    {
      title: "Make a chill evening playlist", 
      icon: "🌙",
      description: "I want to unwind after a long day with soothing, relaxing music that helps me transition into evening mode. Create a mellow playlist perfect for reading, cooking dinner, or simply decompressing at home. Focus on acoustic, indie, ambient, or soft pop tracks with calm vocals and gentle instrumentation. The mood should be peaceful and contemplative, helping me slow down and relax."
    },
    {
      title: "Road trip music mix",
      icon: "🚗", 
      description: "I'm planning a road trip and need the perfect soundtrack for hours of driving with friends or family. Create an engaging playlist that captures the spirit of adventure and keeps energy levels up during long stretches of highway. Include classic rock, indie favorites, sing-along anthems, and feel-good hits that everyone can enjoy. The songs should evoke feelings of freedom, wanderlust, and the joy of the open road."
    }
  ];

  return (
    <div className="chat-interface" data-testid="chat-interface">
      {messages.length === 0 ? (
        // Show welcome state with preset cards when no messages
        <div className="welcome-container">
          <div className="welcome-header">
            <div className="welcome-icon">
              <svg viewBox="0 0 24 24" fill="currentColor" className="spotify-logo">
                <path d="M12 0C5.4 0 0 5.4 0 12s5.4 12 12 12 12-5.4 12-12S18.66 0 12 0zm5.521 17.34c-.24.359-.66.48-1.021.24-2.82-1.74-6.36-2.101-10.561-1.141-.418.122-.779-.179-.899-.539-.12-.421.18-.78.54-.9 4.56-1.021 8.52-.6 11.64 1.32.42.18.479.659.301 1.02zm1.44-3.3c-.301.42-.841.6-1.262.3-3.239-1.98-8.159-2.58-11.939-1.38-.479.12-1.02-.12-1.14-.6-.12-.48.12-1.021.6-1.141C9.6 9.9 15 10.561 18.72 12.84c.361.181.54.78.241 1.2zm.12-3.36C15.24 8.4 8.82 8.16 5.16 9.301c-.6.179-1.2-.181-1.38-.721-.18-.601.18-1.2.72-1.381 4.26-1.26 11.28-1.02 15.721 1.621.539.3.719 1.02.419 1.56-.299.421-1.02.599-1.559.3z"/>
              </svg>
            </div>
            <h1>Welcome to Mr. DJ</h1>
            <p>I'm your AI playlist curator. Tell me what you're in the mood for, and I'll create the perfect playlist for you on Spotify. <strong>No login required!</strong></p>
          </div>
          
          <div className="preset-cards">
            {presetOptions.map((preset, index) => (
              <div
                key={index}
                className="preset-card"
                onClick={() => handlePresetClick(preset.description)}
              >
                <div className="preset-icon">{preset.icon}</div>
                <div className="preset-content">
                  <h3>{preset.title}</h3>
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
              data-testid="chat-message"
            >
              <div className="message-bubble">
                <div className="message-content">
                  {message.role === 'assistant' ? (
                    <ReactMarkdown
                      components={{
                        a: ({ href, children }) => (
                          <a 
                            href={href} 
                            target="_blank" 
                            rel="noopener noreferrer"
                            className="message-link"
                          >
                            {children}
                          </a>
                        ),
                        img: () => null, // Hide images to keep track lists clean
                        li: ({ children }) => {
                          const textContent = extractTextContent(children);
                          return (
                            <li 
                              dir={getTextDirection(textContent)}
                              style={{ textAlign: getTextDirection(textContent) === 'rtl' ? 'right' : 'left' }}
                            >
                              {children}
                            </li>
                          );
                        },
                        p: ({ children }) => {
                          const textContent = extractTextContent(children);
                          return (
                            <p 
                              dir={getTextDirection(textContent)}
                              style={{ textAlign: getTextDirection(textContent) === 'rtl' ? 'right' : 'left' }}
                            >
                              {children}
                            </p>
                          );
                        },
                        h1: ({ children }) => {
                          const textContent = extractTextContent(children);
                          return (
                            <h1 
                              dir={getTextDirection(textContent)}
                              style={{ textAlign: getTextDirection(textContent) === 'rtl' ? 'right' : 'left' }}
                            >
                              {children}
                            </h1>
                          );
                        },
                        h2: ({ children }) => {
                          const textContent = extractTextContent(children);
                          return (
                            <h2 
                              dir={getTextDirection(textContent)}
                              style={{ textAlign: getTextDirection(textContent) === 'rtl' ? 'right' : 'left' }}
                            >
                              {children}
                            </h2>
                          );
                        },
                        h3: ({ children }) => {
                          const textContent = extractTextContent(children);
                          return (
                            <h3 
                              dir={getTextDirection(textContent)}
                              style={{ textAlign: getTextDirection(textContent) === 'rtl' ? 'right' : 'left' }}
                            >
                              {children}
                            </h3>
                          );
                        }
                      }}
                    >
                      {message.content}
                    </ReactMarkdown>
                  ) : (
                    message.content.split('\n').map((line, index) => (
                      <div 
                        key={index} 
                        className="message-line"
                        dir={getTextDirection(line)}
                        style={{ textAlign: getTextDirection(line) === 'rtl' ? 'right' : 'left' }}
                      >
                        {line || '\u00A0'}
                      </div>
                    ))
                  )}
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
          <textarea
            ref={textareaRef}
            className="message-input"
            value={inputValue}
            onChange={(e) => setInputValue(e.target.value)}
            onKeyPress={handleKeyPress}
            placeholder="Tell me what kind of playlist you want..."
            disabled={isLoading}
            rows={1}
            data-testid="chat-input"
          />
          <button
            className="send-button"
            onClick={handleSendMessage}
            disabled={!inputValue.trim() || isLoading}
            aria-label="Send message"
            data-testid="send-button"
          >
            <svg viewBox="0 0 24 24" fill="currentColor">
              <path d="M2.01 21L23 12 2.01 3 2 10l15 2-15 2z"/>
            </svg>
          </button>
        </div>
      </div>
    </div>
  );
};

export default ChatInterface;