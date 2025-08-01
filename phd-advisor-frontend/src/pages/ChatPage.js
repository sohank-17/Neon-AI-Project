import React, { useState, useEffect, useRef } from 'react';
import { Home, MessageCircle, Reply, X, Sparkles, Users, Settings2, FileText , LogOut} from 'lucide-react';
import EnhancedChatInput from '../components/EnhancedChatInput';
import MessageBubble from '../components/MessageBubble';
import ThinkingIndicator from '../components/ThinkingIndicator';
import SuggestionsPanel from '../components/SuggestionsPanel';
import ThemeToggle from '../components/ThemeToggle';
import ProviderDropdown from '../components/ProviderDropdown';
import ExportButton from '../components/ExportButton';
import Sidebar from '../components/Sidebar';
import { advisors, getAdvisorColors } from '../data/advisors';
import { useTheme } from '../contexts/ThemeContext';
import '../styles/ChatPage.css';
import '../styles/EnhancedChatInput.css';
import AdvisorStatusDropdown from '../components/AdvisorStatusDropdown';

const ChatPage = ({ user, authToken, onNavigateToHome, onSignOut }) => {
  const [messages, setMessages] = useState([]);
  const [isLoading, setIsLoading] = useState(false);
  const [thinkingAdvisors, setThinkingAdvisors] = useState([]);
  const [collectedInfo, setCollectedInfo] = useState({});
  const [replyingTo, setReplyingTo] = useState(null);
  const [currentProvider, setCurrentProvider] = useState('gemini');
  const [isProviderSwitching, setIsProviderSwitching] = useState(false);
  const [uploadedDocuments, setUploadedDocuments] = useState([]);
  const messagesEndRef = useRef(null);
  const { isDark } = useTheme();

  const [currentSessionId, setCurrentSessionId] = useState(null);
  const [currentSessionTitle, setCurrentSessionTitle] = useState('');
  const [isSavingSession, setIsSavingSession] = useState(false);
  const [isLoadingSession, setIsLoadingSession] = useState(false);

  

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages, thinkingAdvisors]);

  useEffect(() => {
    fetchCurrentProvider();
  }, []);

  const fetchCurrentProvider = async () => {
    try {
      const response = await fetch('http://localhost:8000/current-provider');
      if (response.ok) {
        const data = await response.json();
        setCurrentProvider(data.current_provider);
        console.log('Loaded provider:', data.current_provider, 'Available:', data.available_providers);
      }
    } catch (error) {
      console.error('Error fetching current provider:', error);
    }
  };

  

  const handleProviderSwitch = async (newProvider) => {
    if (newProvider === currentProvider || isProviderSwitching) return;

    setIsProviderSwitching(true);
    try {
      const response = await fetch('http://localhost:8000/switch-provider', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          provider: newProvider
        }),
      });

      if (response.ok) {
        const data = await response.json();
        setCurrentProvider(newProvider);
        
        const switchMessage = {
          id: generateMessageId(),
          type: 'system',
          content: `✨ Switched to ${newProvider.charAt(0).toUpperCase() + newProvider.slice(1)} provider. Your advisors are now ready with the new AI model.`,
          timestamp: new Date()
        };
        setMessages(prev => [...prev, switchMessage]);
      } else {
        const error = await response.json();
        console.error('Failed to switch provider:', error);
        const errorMessage = {
          id: generateMessageId(),
          type: 'error',
          content: `Failed to switch to ${newProvider}: ${error.detail || 'Unknown error'}`,
          timestamp: new Date()
        };
        setMessages(prev => [...prev, errorMessage]);
      }
    } catch (error) {
      console.error('Error switching provider:', error);
      const errorMessage = {
        id: generateMessageId(),
        type: 'error',
        content: `Error switching to ${newProvider}. Please try again.`,
        timestamp: new Date()
      };
      setMessages(prev => [...prev, errorMessage]);
    } finally {
      setIsProviderSwitching(false);
    }
  };

  const generateMessageId = () => {
    return Date.now().toString() + Math.random().toString(36).substr(2, 9);
  };

  const createNewSession = async (firstMessage = null) => {
    try {
      const title = firstMessage 
        ? `${firstMessage.substring(0, 30)}...` 
        : `Chat ${new Date().toLocaleDateString()}`;

      const response = await fetch('http://localhost:8000/api/chat-sessions', {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${authToken}`,
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({ title })
      });

      if (response.ok) {
        const newSession = await response.json();
        
        // Update state immediately
        setCurrentSessionId(newSession.id);
        setCurrentSessionTitle(newSession.title);
        
        console.log('MongoDB session created:', newSession.id);
        return newSession.id;
      } else {
        console.error('Failed to create new session');
        return null;
      }
    } catch (error) {
      console.error('Error creating new session:', error);
      return null;
    }
  };


// Load an existing chat session
const loadChatSession = async (sessionId) => {
  if (!sessionId || isLoadingSession) return;
  setIsLoadingSession(true);
  try {
    // Use the new switch-chat endpoint that syncs context
    const response = await fetch('http://localhost:8000/switch-chat', {
      method: 'POST',
      headers: {
        'Authorization': `Bearer ${authToken}`,
        'Content-Type': 'application/json'
      },
      body: JSON.stringify({
        chat_session_id: sessionId
      })
    });

    if (response.ok) {
      const result = await response.json();
      if (result.status === 'success') {
        setCurrentSessionId(sessionId);
        setCurrentSessionTitle(''); // Will be set from MongoDB data
        
        // Load the messages from the synced context
        const formattedMessages = result.context.messages.map(msg => ({
          ...msg,
          timestamp: new Date(msg.timestamp)
        }));
        
        setMessages(formattedMessages);
        setReplyingTo(null);
        setThinkingAdvisors([]);
        
        // Also get the session title from MongoDB
        const sessionResponse = await fetch(`http://localhost:8000/api/chat-sessions/${sessionId}`, {
          headers: {
            'Authorization': `Bearer ${authToken}`,
            'Content-Type': 'application/json'
          }
        });
        if (sessionResponse.ok) {
          const sessionData = await sessionResponse.json();
          setCurrentSessionTitle(sessionData.title);
        }
      }
    }
  } catch (error) {
    console.error('Error loading session:', error);
  } finally {
    setIsLoadingSession(false);
  }
};

// Save a message to the current session
const saveMessageToSession = async (message) => {
  if (!currentSessionId || !authToken) return;

  try {
    await fetch(`http://localhost:8000/api/chat-sessions/${currentSessionId}/messages`, {
      method: 'POST',
      headers: {
        'Authorization': `Bearer ${authToken}`,
        'Content-Type': 'application/json'
      },
      body: JSON.stringify({
        session_id: currentSessionId,
        message: {
          ...message,
          timestamp: message.timestamp.toISOString()
        }
      })
    });
  } catch (error) {
    console.error('Error saving message to session:', error);
  }
};

// Update session title based on first message
const updateSessionTitle = async (sessionId, newTitle) => {
  if (!sessionId || !authToken) return;

  try {
    await fetch(`http://localhost:8000/api/chat-sessions/${sessionId}`, {
      method: 'PUT',
      headers: {
        'Authorization': `Bearer ${authToken}`,
        'Content-Type': 'application/json'
      },
      body: JSON.stringify({ title: newTitle })
    });
    setCurrentSessionTitle(newTitle);
  } catch (error) {
    console.error('Error updating session title:', error);
  }
};

// Handle selecting a session from sidebar
const handleSelectSession = async (sessionId) => {
  if (sessionId === currentSessionId) return;
  await loadChatSession(sessionId);
};

// Handle creating new chat from sidebar
const handleNewChat = async (sessionId = null) => {
  if (sessionId) {
    // Loading existing session
    await loadChatSession(sessionId);
    return; // Return early for existing session loading
  } else {
    // Creating completely new chat with fresh context
    try {
      // Step 1: Reset memory session
      const response = await fetch('http://localhost:8000/new-chat', {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${authToken}`,
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({
          title: `Chat ${new Date().toLocaleDateString()}`
        })
      });

      if (response.ok) {
        const result = await response.json();
        if (result.status === 'success') {
          // Step 2: Immediately create MongoDB session
          const newSessionId = await createNewSession(`Chat ${new Date().toLocaleDateString()}`);
          
          if (newSessionId) {
            // Reset all state to fresh with the new session
            setMessages([]);
            setCurrentSessionId(newSessionId); // Set the new session ID immediately
            setCurrentSessionTitle(`Chat ${new Date().toLocaleDateString()}`);
            setReplyingTo(null);
            setThinkingAdvisors([]);
            setUploadedDocuments([]);
            
            console.log('New chat created with MongoDB session:', newSessionId);
            
            // Wait a bit to ensure state has updated
            await new Promise(resolve => setTimeout(resolve, 100));
            return newSessionId; // Return the session ID for the sidebar
          } else {
            throw new Error('Failed to create MongoDB session');
          }
        } else {
          throw new Error('Failed to create memory session');
        }
      } else {
        throw new Error(`HTTP error: ${response.status}`);
      }
    } catch (error) {
      console.error('Error creating new chat:', error);
      
      // Fallback to local reset
      setMessages([]);
      setCurrentSessionId(null);
      setCurrentSessionTitle('');
      setReplyingTo(null);
      setThinkingAdvisors([]);
      setUploadedDocuments([]);
      
      // Re-throw the error so the sidebar knows something went wrong
      throw error;
    }
  }
};

  

  const handleFileUploaded = async (fileInfo) => {
  const documentMessage = {
    id: generateMessageId(),
    type: 'document_upload',
    content: `Document uploaded: ${fileInfo.name}`,
    timestamp: new Date()
  };
  
  setMessages(prev => [...prev, documentMessage]);
  setUploadedDocuments(prev => [...prev, fileInfo]);
  
  // Save document upload message to database if we have a current session
  if (currentSessionId) {
    await saveMessageToSession(documentMessage);
  }
};

  const handleSendMessage = async (inputMessage) => {
    if (!inputMessage.trim()) return;

    // Create user message
    const userMessage = {
      id: generateMessageId(),
      type: 'user',
      content: inputMessage,
      timestamp: new Date()
    };

    // Add to local state immediately
    setMessages(prev => [...prev, userMessage]);

    // Create new session if we don't have one
    let sessionId = currentSessionId;
    if (!sessionId) {
      sessionId = await createNewSession(inputMessage);
      if (!sessionId) {
        console.error('Failed to create session');
        return;
      }
    }

    // Save user message to database
    await saveMessageToSession(userMessage);

    // Update session title if this is the first message and title is generic
    if (messages.length === 0 && currentSessionTitle.includes('Chat ')) {
      const newTitle = inputMessage.length > 30 
        ? `${inputMessage.substring(0, 30)}...` 
        : inputMessage;
      await updateSessionTitle(sessionId, newTitle);
    }

    // Set loading state
    setIsLoading(true);
    setThinkingAdvisors(['system']);

    try {
      const response = await fetch('http://localhost:8000/chat-sequential', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${authToken}`,
        },
        body: JSON.stringify({
          user_input: inputMessage,
          response_length: 'medium',
          chat_session_id: currentSessionId // Include current session ID
        }),
      });

      if (!response.ok) {
        throw new Error(`HTTP error! Status: ${response.status}`);
      }

      const data = await response.json();

      // Handle clarification needed case
      if (data.type === 'clarification_needed') {
        const clarificationMessage = {
          id: generateMessageId(),
          type: 'clarification',
          content: data.message,
          suggestions: data.suggestions || [],
          timestamp: new Date()
        };

        setMessages(prev => [...prev, clarificationMessage]);
        await saveMessageToSession(clarificationMessage);

      } else if (data.type === 'sequential_responses' && data.responses) {
        // Handle normal advisor responses
        const advisorMessages = data.responses.map((advisor) => ({
          id: generateMessageId(),
          type: 'advisor',
          advisorId: advisor.persona_id,
          advisorName: advisor.persona,
          content: advisor.response,
          timestamp: new Date()
        }));

        setMessages(prev => [...prev, ...advisorMessages]);

        // Save each advisor message to database
        for (const advisorMessage of advisorMessages) {
          await saveMessageToSession(advisorMessage);
        }

      } else if (data.type === 'error') {
        const errorMessage = {
          id: generateMessageId(),
          type: 'error',
          content: data.responses?.[0]?.response || 'An error occurred. Please try again.',
          timestamp: new Date()
        };
        setMessages(prev => [...prev, errorMessage]);
        await saveMessageToSession(errorMessage);
      }

    } catch (error) {
      console.error('Error sending message:', error);
      const errorMessage = {
        id: generateMessageId(),
        type: 'error',
        content: 'Sorry, I encountered an error. Please try again.',
        timestamp: new Date()
      };
      setMessages(prev => [...prev, errorMessage]);
      await saveMessageToSession(errorMessage);
    }

    setIsLoading(false);
    setThinkingAdvisors([]);
    setReplyingTo(null);
  };

  const handleReplyToAdvisor = async (inputMessage, replyContext) => {
  // Ensure we have a session before proceeding
  let sessionId = currentSessionId;
  if (!sessionId) {
    sessionId = await createNewSession(inputMessage);
    if (!sessionId) {
      console.error('Failed to create session for reply');
      return;
    }
  }

  const replyMessage = {
    id: generateMessageId(),
    type: 'user',
    content: inputMessage,
    replyTo: {
      advisorId: replyContext.advisorId,
      advisorName: replyContext.advisorName,
      messageId: replyContext.messageId
    },
    timestamp: new Date()
  };

  setMessages(prev => [...prev, replyMessage]);
  
  // Save reply message to database with explicit session ID
  await saveMessageToSession(replyMessage, sessionId);
  
  setIsLoading(true);
  setThinkingAdvisors([replyContext.advisorId]);

  try {
    const response = await fetch('http://localhost:8000/reply-to-advisor', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${authToken}`,
      },
      body: JSON.stringify({
        user_input: inputMessage,
        advisor_id: replyContext.advisorId,
        original_message_id: replyContext.messageId,
        chat_session_id: sessionId // Use confirmed session ID
      }),
    });

    if (!response.ok) {
      throw new Error(`HTTP error! Status: ${response.status}`);
    }

    const data = await response.json();

    if (data.type === 'advisor_reply') {
      const replyResponseMessage = {
        id: generateMessageId(),
        type: 'advisor',
        advisorId: data.persona_id,
        advisorName: data.persona,
        content: data.response,
        isReply: true,
        timestamp: new Date()
      };
      setMessages(prev => [...prev, replyResponseMessage]);
      
      // Save advisor reply to database
      await saveMessageToSession(replyResponseMessage, sessionId);
    }

  } catch (error) {
    console.error('Error replying to advisor:', error);
    const errorMessage = {
      id: generateMessageId(),
      type: 'error',
      content: 'Sorry, I encountered an error with your reply. Please try again.',
      timestamp: new Date()
    };
    setMessages(prev => [...prev, errorMessage]);
    
    // Save error message to database
    await saveMessageToSession(errorMessage, sessionId);
  }

  setIsLoading(false);
  setThinkingAdvisors([]);
};

  const handleCopyMessage = (messageId, content) => {
    // Optional: Show a toast notification or add to message history
    console.log(`Copied message ${messageId}: ${content.substring(0, 50)}...`);
  };

  const handleExpandMessage = async (messageId, advisorId) => {
    const advisor = advisors[advisorId];
    if (!advisor) return;

    const originalMessage = messages.find(msg => msg.id === messageId);
    if (!originalMessage) return;

    const expandPrompt = `Please expand on your previous response: "${originalMessage.content.substring(0, 100)}..." Provide more detail and depth.`;
    
    const expandMessage = {
      id: generateMessageId(),
      type: 'user',
      content: expandPrompt,
      timestamp: new Date(),
      isExpandRequest: true,
      expandsMessageId: messageId
    };
    setMessages(prev => [...prev, expandMessage]);
    
    // Save expand request to database
    await saveMessageToSession(expandMessage);
    
    setIsLoading(true);
    setThinkingAdvisors([advisorId]);

    try {
      const response = await fetch(`http://localhost:8000/chat/${advisorId}`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${authToken}`,
        },
        body: JSON.stringify({
          user_input: expandPrompt,
          response_length: 'long'
        }),
      });

      if (!response.ok) {
        throw new Error(`HTTP error! Status: ${response.status}`);
      }

      const data = await response.json();

      if (data.persona && data.response) {
        const expandedMessage = {
          id: generateMessageId(),
          type: 'advisor',
          advisorId: advisorId,
          advisorName: advisor.name,
          content: data.response,
          isExpansion: true,
          expandsMessageId: messageId,
          timestamp: new Date()
        };
        setMessages(prev => [...prev, expandedMessage]);
        
        // Save expanded response to database
        await saveMessageToSession(expandedMessage);
      } else {
        const errorMessage = {
          id: generateMessageId(),
          type: 'error',
          content: 'Sorry, I received an unexpected response format. Please try again.',
          timestamp: new Date()
        };
        setMessages(prev => [...prev, errorMessage]);
        
        // Save error message to database
        await saveMessageToSession(errorMessage);
      }

    } catch (error) {
      console.error('Error expanding message:', error);
      const errorMessage = {
        id: generateMessageId(),
        type: 'error',
        content: 'Sorry, I encountered an error while expanding the message. Please try again.',
        timestamp: new Date()
      };
      setMessages(prev => [...prev, errorMessage]);
      
      // Save error message to database
      await saveMessageToSession(errorMessage);
    }

    setIsLoading(false);
    setThinkingAdvisors([]);
  };

  const handleReplyToMessage = (message) => {
    const advisor = advisors[message.advisorId];
    setReplyingTo({
      advisorId: message.advisorId,
      messageId: message.id,
      advisorName: advisor.name
    });
  };

  const handleMessageClick = (message) => {
    if (message.type === 'advisor') {
      const advisor = advisors[message.advisorId];
      setReplyingTo({
        advisorId: message.advisorId,
        messageId: message.id,
        advisorName: advisor.name
      });
    }
  };

  const handleInputSubmit = async (inputMessage) => {
  if (replyingTo) {
    // This is a reply to a specific message
    await handleReplyToAdvisor(inputMessage, replyingTo);
  } else {
    // This is a regular message
    await handleSendMessage(inputMessage);
  }
};

  const cancelReply = () => {
    setReplyingTo(null);
  };

  const [isSidebarCollapsed, setIsSidebarCollapsed] = useState(false);

  const handleSidebarToggle = (isCollapsed) => {
    setIsSidebarCollapsed(isCollapsed);
  };

  const hasMessages = messages.length > 0;
  const hasConversationMessages = messages.filter(m => m.type !== 'system' && m.type !== 'document_upload').length > 0;

  return (
    <div className="chat-page-with-sidebar">
      {/* Sidebar Component */}
      <Sidebar 
        user={user}
        currentSessionId={currentSessionId}
        onSelectSession={handleSelectSession}
        onNewChat={handleNewChat}
        onSignOut={onSignOut}
        authToken={authToken}
        onSidebarToggle={handleSidebarToggle}
      />
      
      <div className={`main-chat-area ${isSidebarCollapsed ? 'sidebar-collapsed' : ''}`}>
        <div className="modern-chat-page">
          {/* Floating Header */}
          <div className="floating-header">
            <div className="header-left">
              <button onClick={onNavigateToHome} className="modern-home-btn">
                <Home size={20} />
              </button>
              <div className="header-brand">
                <div className="brand-icon">
                  <Users size={24} />
                </div>
                <div className="brand-text">
                  <h1>PhD Advisory</h1>
                  <p>AI-Powered Academic Guidance</p>
                </div>
              </div>
            </div>
            
            <div className="header-right">
              <AdvisorStatusDropdown 
                advisors={advisors}
                thinkingAdvisors={thinkingAdvisors}
                getAdvisorColors={getAdvisorColors}
                isDark={isDark}
              />
              
              <div className="header-controls">
                {/* Add session title display */}
                {currentSessionTitle && (
                  <div className="session-title-display">
                    <span>{currentSessionTitle}</span>
                  </div>
                )}
                
                {/* Optional: Add header sign out button */}
                <button 
                  className="header-signout-btn"
                  onClick={onSignOut}
                  title="Sign Out"
                >
                  <LogOut size={16} />
                </button>
                
                {/* Export Button */}
                <ExportButton 
                  hasMessages={hasConversationMessages} 
                  currentSessionId={currentSessionId}
                  authToken={authToken}
                />
                
                {/* Provider Dropdown */}
                <ProviderDropdown 
                  currentProvider={currentProvider}
                  onProviderChange={handleProviderSwitch}
                  isLoading={isProviderSwitching}
                />
                
                {/* Theme Toggle */}
                <ThemeToggle />
              </div>
            </div>
          </div>

          {/* Main Content */}
          <div className="chat-content">
            {!hasMessages ? (
              <div className="welcome-state">
                <SuggestionsPanel onSuggestionClick={handleSendMessage} />
              </div>
            ) : (
              <div className="messages-container">
                {/* Add loading session indicator */}
                {isLoadingSession && (
                  <div className="loading-session">
                    <div className="loading-spinner"></div>
                    <span>Loading chat session...</span>
                  </div>
                )}
                
                <div className="messages-list">
                  <div className="messages-scroll">
                    {messages.map((message) => (
                      <div key={message.id}>
                        {message.type === 'user' && (
                          <div className="user-message-container">
                            <div className="user-message">
                              {message.replyTo && (
                                <div className="reply-indicator">
                                  <Reply size={12} />
                                  <span>Reply to {message.replyTo.advisorName}</span>
                                </div>
                              )}
                              <p>{message.content}</p>
                            </div>
                          </div>
                        )}

                        {message.type === 'advisor' && (
                          <MessageBubble
                            message={message}
                            onReply={handleReplyToMessage}
                            onExpand={handleExpandMessage}
                            onClick={handleMessageClick}
                            showReplyButton={true}
                          />
                        )}

                        {message.type === 'error' && (
                          <div className="error-message-container">
                            <div className="error-message">
                              <p>{message.content}</p>
                            </div>
                          </div>
                        )}

                        {message.type === 'system' && (
                          <div className="system-message-container">
                            <div className="system-message">
                              <p>{message.content}</p>
                            </div>
                          </div>
                        )}

                        {message.type === 'document_upload' && (
                          <div className="system-message-container">
                            <div className="system-message document-upload">
                              <FileText size={16} />
                              <p>{message.content}</p>
                            </div>
                          </div>
                        )}

                        {message.type === 'clarification' && (
                          <div className="clarification-message-container">
                            <div className="clarification-message">
                              <div className="clarification-header">
                                <MessageCircle size={16} />
                                <span>I need a bit more information</span>
                              </div>
                              <p>{message.content}</p>
                              
                              {message.suggestions && message.suggestions.length > 0 && (
                                <div className="clarification-suggestions">
                                  <p className="suggestions-label">Here are some ways you could be more specific:</p>
                                  <div className="suggestions-list">
                                    {message.suggestions.map((suggestion, index) => (
                                      <button
                                        key={index}
                                        className="suggestion-button"
                                        onClick={() => handleSendMessage(suggestion)}
                                      >
                                        {suggestion}
                                      </button>
                                    ))}
                                  </div>
                                </div>
                              )}
                            </div>
                          </div>
                        )}

                        
                      </div>
                    ))}

                    {thinkingAdvisors.includes('system') && (
                      <div className="orchestrator-thinking">
                        <div className="thinking-bubble">
                          <MessageCircle size={20} />
                        </div>
                        <div className="thinking-content">
                          <span className="thinking-label">Orchestrator is thinking...</span>
                          <div className="thinking-animation">
                            <div className="dot"></div>
                            <div className="dot"></div>
                            <div className="dot"></div>
                          </div>
                        </div>
                      </div>
                    )}
                    
                    {thinkingAdvisors.filter(id => id !== 'system').map(advisorId => (
                      <ThinkingIndicator key={advisorId} advisorId={advisorId} />
                    ))}

                    <div ref={messagesEndRef} />
                  </div>
                </div>
              </div>
            )}
          </div>

          <div className="floating-input-area">
            {replyingTo && (
              <div className="reply-banner">
                <div className="reply-info">
                  <Reply size={16} />
                  <span>Replying to <strong>{replyingTo.advisorName}</strong></span>
                </div>
                <button onClick={cancelReply} className="cancel-reply">
                  <X size={16} />
                </button>
              </div>
            )}
            
            <EnhancedChatInput 
              onSendMessage={handleInputSubmit}
              onFileUploaded={handleFileUploaded}
              uploadedDocuments={uploadedDocuments}
              isLoading={isLoading}
              authToken={authToken}
              placeholder={
                replyingTo 
                  ? `Reply to ${replyingTo.advisorName}...`
                  : "Ask your advisors anything about your PhD journey..."
              }
            />
          </div>
        </div>
      </div>
    </div>
  );
};

export default ChatPage;