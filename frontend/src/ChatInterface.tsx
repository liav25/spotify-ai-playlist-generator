import React, { useEffect, useState, useRef } from 'react';
import ReactMarkdown from 'react-markdown';
import { chatApi, ChatMessage } from './chatApi';
import { usePlaylist } from './PlaylistContext';
import './ChatInterface.css';
// Resolve logo URL via Vite so bundler handles it correctly
const appLogoUrl = new URL('../mrdjlogo.svg', import.meta.url).href

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
  const [windowWidth, setWindowWidth] = useState<number>(() => (
    typeof window !== 'undefined' ? window.innerWidth : 1024
  ));

  useEffect(() => {
    if (typeof window === 'undefined') return;

    const handleResize = () => {
      setWindowWidth(window.innerWidth);
    };

    handleResize();
    window.addEventListener('resize', handleResize);
    return () => window.removeEventListener('resize', handleResize);
  }, []);

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

  const handlePresetClick = async (description: string) => {
    if (isLoading) return;

    const userMessage: ChatMessage = {
      id: crypto.randomUUID(),
      role: 'user',
      content: description,
      timestamp: new Date()
    };

    setMessages(prev => [...prev, userMessage]);
    setIsLoading(true);

    try {
      const response = await chatApi.sendMessage(description);
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
      title: "What can you do?",
      icon: "❓",
      description: "What can you do?"
    },
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

  const getMaxVisiblePresets = (width: number) => {
    if (width >= 1024) return presetOptions.length;
    if (width >= 768) return 3;
    if (width >= 600) return 2;
    return 1;
  };

  const maxVisiblePresets = getMaxVisiblePresets(windowWidth);
  const discoveryPreset = presetOptions.find(preset => preset.title === "What can you do?");
  const secondaryPresets = presetOptions.filter(preset => preset.title !== "What can you do?");

  const visiblePresetOptions = discoveryPreset
    ? maxVisiblePresets <= 0
      ? []
      : [discoveryPreset, ...secondaryPresets.slice(0, maxVisiblePresets - 1)]
    : presetOptions.slice(0, maxVisiblePresets);

  return (
    <div className="chat-interface" data-testid="chat-interface">
      {/* Buy me a coffee button - only visible during conversations */}
      {messages.length > 0 && (
        <div className="buy-me-coffee-widget">
          <a 
            href="https://www.buymeacoffee.com/liav25" 
            target="_blank" 
            rel="noopener noreferrer"
            className="bmc-button"
          >
            <img 
              src="https://cdn.buymeacoffee.com/buttons/v2/default-yellow.png" 
              alt="Buy Me A Coffee" 
              className="bmc-button-image"
            />
          </a>
        </div>
      )}
      {messages.length === 0 ? (
        // Show welcome state with preset cards when no messages
        <div className="welcome-container">
          <div className="welcome-header">
            <div className="welcome-icon">
              <img src={appLogoUrl} alt="Mr. DJ logo" className="welcome-logo" />
            </div>
            <h1>Hi, I'm Mr. DJ</h1>
            <div className="main-description">
              <p>Your AI DJ that can generate a personalized playlist just for you on Spotify.</p>
            </div>
            
            <div className="how-it-works">
              <h3>How it works:</h3>
              <ol className="steps-list">
                <li>Tell me your mood, genre, or activity</li>
                <li>I'll create the perfect playlist for you!</li>
                <li>Your playlist gets created on Spotify</li>
              </ol>
              <p className="call-to-action">Ready to discover your next favorite playlist? <strong>Start chatting below!</strong></p>
            </div>
          </div>
          
          <div className="preset-cards">
            {visiblePresetOptions.map((preset, index) => (
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
                <span>Thinking... This will take only 1 minute...</span>
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
            onKeyDown={handleKeyPress}
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
