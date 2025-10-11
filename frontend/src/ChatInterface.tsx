import React, { useEffect, useState, useRef } from 'react';
import ReactMarkdown from 'react-markdown';
import { chatApi, ChatMessage, ToolCallEvent } from './chatApi';
import { usePlaylist } from './PlaylistContext';
import './ChatInterface.css';
// Resolve logo URL via Vite so bundler handles it correctly
const appLogoUrl = new URL('../mrdjlogo.svg', import.meta.url).href
const tavilyLogoUrl = new URL('../tavily_logo.png', import.meta.url).href

interface ChatInterfaceProps {
  username: string;
}

type PresetOption = {
  title: string;
  icon: string;
  description: string;
  predefinedResponse?: string;
};

const ChatInterface: React.FC<ChatInterfaceProps> = ({ username }) => {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [inputValue, setInputValue] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const { setCurrentPlaylist } = usePlaylist();
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const skipNextScrollRef = useRef(false);
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
    if (skipNextScrollRef.current) {
      skipNextScrollRef.current = false;
      return;
    }
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


  const sendStreamingMessage = async (content: string) => {
    setIsLoading(true);
    // Reset tool call indicator

    let statusMessageId: string | null = null;
    let toolMessageId: string | null = null;
    let currentToolLabel = '';
    let hasToolActivity = false;
    let pendingStatusMessage: string | null = null;
    const toolActivities: Array<{ id: string; label: string; status: ToolMessageStatus }> = [];

    const updateStatusMessage = (nextContent: string) => {
      if (!statusMessageId) return;
      const messageId = statusMessageId;
      setMessages(prev =>
        prev.map(message =>
          message.id === messageId
            ? {
                ...message,
                content: nextContent,
                timestamp: new Date()
              }
            : message
        )
      );
    };

    type ToolMessageStatus = 'active' | 'completed' | 'error';

    const ensureStatusMessage = (content: string) => {
      if (!statusMessageId) {
        statusMessageId = crypto.randomUUID();
        const statusChatMessage: ChatMessage = {
          id: statusMessageId,
          role: 'assistant',
          content,
          timestamp: new Date(),
          metadata: {
            type: 'status'
          }
        };
        setMessages(prev => [...prev, statusChatMessage]);
      } else {
        updateStatusMessage(content);
      }
    };

    const syncToolMessage = (status: ToolMessageStatus) => {
      const latestLabel = toolActivities.length > 0
        ? toolActivities[toolActivities.length - 1].label
        : currentToolLabel || 'Tool activity';
      const activitiesSnapshot = toolActivities.map(activity => ({ ...activity }));

      if (!toolMessageId) {
        toolMessageId = crypto.randomUUID();
        const toolChatMessage: ChatMessage = {
          id: toolMessageId,
          role: 'assistant',
          content: latestLabel,
          timestamp: new Date(),
          metadata: {
            type: 'tool',
            status,
            expanded: true,
            toolActivities: activitiesSnapshot
          }
        };
        setMessages(prev => [...prev, toolChatMessage]);
      } else {
        const messageId = toolMessageId;
        setMessages(prev =>
          prev.map(message =>
            message.id === messageId
              ? {
                  ...message,
                  content: latestLabel,
                  timestamp: new Date(),
                  metadata: {
                    ...(message.metadata || {}),
                    type: 'tool',
                    status,
                    expanded: message.metadata?.expanded ?? true,
                    toolActivities: activitiesSnapshot
                  }
                }
              : message
          )
        );
      }
    };

    const collapseToolPanel = () => {
      if (!toolMessageId) return;
      const messageId = toolMessageId;
      setMessages(prev =>
        prev.map(message =>
          message.id === messageId
            ? {
                ...message,
                metadata: {
                  ...(message.metadata || {}),
                  type: 'tool',
                  expanded: false,
                  status: (message.metadata && message.metadata.status) || 'completed',
                  toolActivities: message.metadata?.toolActivities || []
                }
              }
            : message
        )
      );
    };

    const handleToolEvent = (event: ToolCallEvent) => {
      if (event.type === 'status') {
        if (!event.message) {
          return;
        }

        if (!hasToolActivity) {
          pendingStatusMessage = event.message;
        } else {
          ensureStatusMessage(event.message);
        }
      } else if (event.type === 'tool_start') {
        if (!event.message) {
          return;
        }

        hasToolActivity = true;

        if (pendingStatusMessage) {
          ensureStatusMessage(pendingStatusMessage);
          pendingStatusMessage = null;
        }

        const lastActivity = toolActivities[toolActivities.length - 1];

        if (!(lastActivity && lastActivity.label === event.message)) {
          const activity = {
            id: crypto.randomUUID(),
            label: event.message,
            status: 'active' as ToolMessageStatus
          };
          toolActivities.push(activity);
          currentToolLabel = activity.label;
        } else {
          lastActivity.status = 'active';
          currentToolLabel = lastActivity.label;
        }
        syncToolMessage('active');
      } else if (event.type === 'tool_end') {
        for (let i = toolActivities.length - 1; i >= 0; i -= 1) {
          if (toolActivities[i].status === 'active') {
            toolActivities[i] = {
              ...toolActivities[i],
              status: 'completed'
            };
            break;
          }
        }

        const hasActive = toolActivities.some(activity => activity.status === 'active');
        if (toolActivities.length > 0) {
          currentToolLabel = toolActivities[toolActivities.length - 1].label;
        }
        syncToolMessage(hasActive ? 'active' : 'completed');
      }
    };

    const markToolError = () => {
      if (toolActivities.length === 0) {
        return;
      }
      const lastIndex = toolActivities.length - 1;
      toolActivities[lastIndex] = {
        ...toolActivities[lastIndex],
        status: 'error'
      };
      currentToolLabel = toolActivities[lastIndex].label;
      syncToolMessage('error');
    };

    try {
      const response = await chatApi.sendMessageWithStreaming(content, handleToolEvent);

      if (statusMessageId) {
        updateStatusMessage('✅ Finished processing your request.');
      }

      if (toolActivities.length > 0) {
        for (let i = 0; i < toolActivities.length; i += 1) {
          if (toolActivities[i].status === 'active') {
            toolActivities[i] = {
              ...toolActivities[i],
              status: 'completed'
            };
          }
        }
        syncToolMessage('completed');
      }
      pendingStatusMessage = null;

      setMessages(prev => [...prev, response.message]);

      if (toolActivities.length > 0) {
        collapseToolPanel();
      }

      if (response.playlistData) {
        setCurrentPlaylist(response.playlistData);

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
          }, 2000);
        }
      }
    } catch (error) {
      console.error('Error sending message:', error);

      if (statusMessageId) {
        updateStatusMessage('⚠️ There was a problem processing your request.');
      }

      if (toolActivities.length > 0) {
        markToolError();
      }
      pendingStatusMessage = null;

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

  const handleSendMessage = async () => {
    if (!inputValue.trim() || isLoading) return;

    const messageContent = inputValue;

    const userMessage: ChatMessage = {
      id: crypto.randomUUID(),
      role: 'user',
      content: messageContent,
      timestamp: new Date()
    };

    setMessages(prev => [...prev, userMessage]);
    setInputValue('');

    await sendStreamingMessage(messageContent);
  };

  const handleKeyPress = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSendMessage();
    }
  };

  const handlePresetClick = async (preset: PresetOption) => {
    if (isLoading) return;

    const userMessage: ChatMessage = {
      id: crypto.randomUUID(),
      role: 'user',
      content: preset.description,
      timestamp: new Date()
    };

    if (preset.predefinedResponse) {
      const assistantMessage: ChatMessage = {
        id: crypto.randomUUID(),
        role: 'assistant',
        content: preset.predefinedResponse,
        timestamp: new Date()
      };

      setMessages(prev => [...prev, userMessage, assistantMessage]);
      return;
    }

    setMessages(prev => [...prev, userMessage]);
    await sendStreamingMessage(preset.description);
  };

  const handleToggleToolMessage = (messageId: string) => {
    skipNextScrollRef.current = true;
    setMessages(prev =>
      prev.map(message =>
        message.id === messageId
          ? {
              ...message,
              metadata: {
                ...(message.metadata || { type: 'tool' }),
                expanded: !(message.metadata?.expanded ?? true)
              }
            }
          : message
      )
    );
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

  const formatListItemText = (text: string): string => {
    const separators = [' — ', ' – ', ' - ', ' –', ' —', ' -'];
    for (const separator of separators) {
      const index = text.indexOf(separator);
      if (index > 0) {
        const name = text.slice(0, index).trim();
        const description = text.slice(index + separator.length).trim();
        if (name && description) {
          return `${name}: ${description}`;
        }
      }
    }
    return text;
  };

  const containsTavilyReference = (text: string): boolean =>
    text.includes('Tavily');

  const renderInlineTavilyLogo = () => (
    <img
      src={tavilyLogoUrl}
      alt="Tavily logo"
      className="inline-tool-logo"
    />
  );

  const renderToolCallLabel = (label: string): React.ReactNode => {
    if (containsTavilyReference(label)) {
      const parts = label.split('Tavily');
      const renderedParts = [];
      for (let i = 0; i < parts.length; i += 1) {
        if (i > 0) {
          renderedParts.push(
            <React.Fragment key={`tavily-${i}`}>
              Tavily
              {renderInlineTavilyLogo()}
            </React.Fragment>
          );
        }
        if (parts[i]) {
          renderedParts.push(
            <React.Fragment key={`text-${i}`}>{parts[i]}</React.Fragment>
          );
        }
      }
      return renderedParts;
    }
    return label;
  };


  const WHAT_CAN_YOU_DO_RESPONSE =
    "Hey there! I'm Mr. DJ 🎧, your AI playlist curator ready to spin custom mixes from mellow study sessions to sweaty workouts. Share the mood, occasion, or artists you love and I'll blend Spotify insights with audio features for a smooth flow. I can whip up sunrise chillouts, HIIT boosters, nostalgic 90s sing-alongs, or globe-trotting discovery journeys. Try prompts like:\n• “Build a 30-minute indie pop warm-up for my morning run.”\n• “Curate a lo-fi beats playlist for late-night studying.”\n• “Give me soulful brunch vibes with a sprinkle of neo-soul classics.”\nJust drop the vibe and I'll start mixing!";

  const presetOptions: PresetOption[] = [
    {
      title: "What can you do?",
      icon: "❓",
      description: "What can you do?",
      predefinedResponse: WHAT_CAN_YOU_DO_RESPONSE
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
                onClick={() => handlePresetClick(preset)}
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
          {messages.map((message) => {
            const isToolMessage = message.metadata?.type === 'tool';
            const toolActivities = isToolMessage ? (message.metadata?.toolActivities || []) : [];
            const expanded = isToolMessage ? (message.metadata?.expanded ?? true) : false;
            const toolStatus = isToolMessage ? (message.metadata?.status || 'active') : 'active';
            const latestActivity = toolActivities.length > 0 ? toolActivities[toolActivities.length - 1] : null;

            return (
              <div
                key={message.id}
                className={`message ${message.role === 'user' ? 'user-message' : 'assistant-message'}`}
                data-testid="chat-message"
              >
                <div className={`message-bubble ${isToolMessage ? 'tool-call-bubble' : ''}`}>
                  <div className="message-content">
                    {isToolMessage ? (
                      <div className={`tool-call-message ${toolStatus} ${expanded ? 'expanded' : 'collapsed'}`}>
                        <button
                          type="button"
                          className="tool-call-toggle"
                          onClick={() => handleToggleToolMessage(message.id)}
                          aria-expanded={expanded}
                        >
                          <span className="tool-call-prefix">Tool Calls</span>
                          <span className="tool-call-toggle-icon" aria-hidden="true" />
                        </button>

                        {!expanded && latestActivity && (
                          <div className="tool-call-summary">
                            <span className="tool-call-label">{renderToolCallLabel(latestActivity.label)}</span>
                            {toolStatus === 'active' && (
                              <span className="tool-call-dots">
                                <span></span>
                                <span></span>
                                <span></span>
                              </span>
                            )}
                            {toolStatus === 'completed' && (
                              <span className="tool-call-status-icon">✅ Done</span>
                            )}
                            {toolStatus === 'error' && (
                              <span className="tool-call-status-icon error">⚠️ Error</span>
                            )}
                          </div>
                        )}

                        {expanded && (
                          <ul className="tool-call-list">
                            {toolActivities.map((activity) => (
                              <li key={activity.id} className={`tool-call-item ${activity.status}`}>
                                <span className="tool-call-item-label">{renderToolCallLabel(activity.label)}</span>
                                {activity.status === 'active' ? (
                                  <span className="tool-call-dots">
                                    <span></span>
                                    <span></span>
                                    <span></span>
                                  </span>
                                ) : activity.status === 'completed' ? (
                                  <span className="tool-call-item-status success">✅ Done</span>
                                ) : (
                                  <span className="tool-call-item-status error">⚠️ Error</span>
                                )}
                              </li>
                            ))}
                          </ul>
                        )}
                      </div>
                    ) : message.role === 'assistant' ? (
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
                          const formattedText = formatListItemText(textContent);
                          const shouldAppendLogo = containsTavilyReference(textContent);
                          return (
                            <li 
                              dir={getTextDirection(textContent)}
                              style={{ textAlign: getTextDirection(textContent) === 'rtl' ? 'right' : 'left' }}
                            >
                              {formattedText}
                              {shouldAppendLogo && (
                                <>
                                  {' '}
                                  {renderInlineTavilyLogo()}
                                </>
                              )}
                            </li>
                          );
                        },
                        p: ({ children }) => {
                          const textContent = extractTextContent(children);
                          const shouldAppendLogo = containsTavilyReference(textContent);
                          return (
                            <p 
                              dir={getTextDirection(textContent)}
                              style={{ textAlign: getTextDirection(textContent) === 'rtl' ? 'right' : 'left' }}
                            >
                              {children}
                              {shouldAppendLogo && (
                                <>
                                  {' '}
                                  {renderInlineTavilyLogo()}
                                </>
                              )}
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
            );
          })}

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
