import React, { useState, useEffect, useCallback } from 'react';
import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom';
import Navbar from './components/Navbar';
import AuthGoogle from './components/AuthGoogle';
import Callback from './components/Callback';
import GraphView from './components/GraphView';
import HealthCheck from './components/HealthCheck_Production';
import ModeSelector from './components/ModeSelector';
import DomainSelector from './components/DomainSelector';
import { useAIMode, useSession } from './hooks/useAIMode';
import { DEFAULT_MODE, API_CONFIG, DEFAULT_DOMAIN } from './config/constants';
import { fetchWithAuth } from './utils/api';
import './index.css';

const API_BASE_URL = API_CONFIG.BASE_URL;

// Dashboard component with mode selection and domain support
const Dashboard = ({ user }) => {
  const [currentSessionId, setCurrentSessionId] = useState(null);
  const [storyContent, setStoryContent] = useState('');
  const [isEditing, setIsEditing] = useState(false);
  const [generatedPrompt, setGeneratedPrompt] = useState('');
  const [isGenerating, setIsGenerating] = useState(false);
  const [currentDomain, setCurrentDomain] = useState(DEFAULT_DOMAIN);
  const [isDomainDetectionEnabled, setIsDomainDetectionEnabled] = useState(true);
  const [sessionError, setSessionError] = useState(null);
  const [isInitializing, setIsInitializing] = useState(true);
  const [analytics, setAnalytics] = useState(null);
  const [loadingAnalytics, setLoadingAnalytics] = useState(false);

  // Use custom hooks for AI mode and session management
  const {
    currentMode,
    updateMode,
    detectDomain,
    isLoading: modeLoading,
    error: modeError,
    clearError
  } = useAIMode(DEFAULT_MODE);

  const {
  sessionId,
  isSessionActive,
  createSession
  } = useSession();

  // Initialize session on mount with retry logic
  useEffect(() => {
    const initSession = async () => {
      if (!user) {
        setIsInitializing(false);
        return;
      }

      setIsInitializing(true);
      setSessionError(null);
      
      // Retry logic for session creation
      const maxRetries = 3;
      let retryCount = 0;
      let lastError = null;
      
      while (retryCount < maxRetries) {
        try {
          console.log(`🔄 Initializing session (attempt ${retryCount + 1}/${maxRetries})...`);
          
          const result = await createSession({
            user_id: user?.id || user?.email || 'anonymous',
            topic: 'story',
            topic_descriptor: 'Creative writing session',
            initial_content: '',
            policy: undefined
          });
          
          if (result && result.session_id) {
            setCurrentSessionId(result.session_id);
            console.log('✅ Session initialized:', result.session_id);
            setIsInitializing(false);
            return; // Success!
          }
          
          throw new Error('Session creation returned no session_id');
          
        } catch (err) {
          lastError = err;
          retryCount++;
          console.warn(`❌ Session init attempt ${retryCount} failed:`, err.message);
          
          if (retryCount < maxRetries) {
            // Exponential backoff: 1s, 2s, 4s
            // eslint-disable-next-line no-loop-func
            await new Promise(resolve => setTimeout(resolve, 1000 * Math.pow(2, retryCount - 1)));
          }
        }
      }
      
      // All retries failed
      console.error('💥 Session initialization failed after all retries');
      setSessionError(`Failed to create session: ${lastError?.message || 'Unknown error'}. Please refresh the page.`);
      setIsInitializing(false);
    };

    if (!isSessionActive && user) {
      initSession();
    } else if (isSessionActive && sessionId) {
      // Use existing session
      setCurrentSessionId(sessionId);
      setIsInitializing(false);
    } else if (!user) {
      setIsInitializing(false);
    }
  }, [isSessionActive, user, sessionId, createSession]);

  /**
   * Fetch real-time analytics data from backend
   */
  const fetchAnalytics = useCallback(async () => {
    const activeSessionId = currentSessionId || sessionId;
    if (!activeSessionId) return;

    setLoadingAnalytics(true);
    try {
      const response = await fetchWithAuth(`${API_BASE_URL}/api/session/${activeSessionId}/analytics`, {
        method: 'GET',
        headers: { 'Content-Type': 'application/json' }
      });

      if (response.ok) {
        const data = await response.json();
        setAnalytics(data);
        console.log('📊 Analytics loaded:', data);
      } else {
        console.warn('⚠️ Failed to fetch analytics:', response.status);
      }
    } catch (error) {
      console.error('❌ Analytics fetch error:', error);
    } finally {
      setLoadingAnalytics(false);
    }
  }, [currentSessionId, sessionId]);

  /**
   * Load analytics when session is ready and periodically refresh
   */
  useEffect(() => {
    if (currentSessionId || sessionId) {
      fetchAnalytics();
      
      // Refresh analytics every 30 seconds
      const interval = setInterval(fetchAnalytics, 30000);
      return () => clearInterval(interval);
    }
  }, [currentSessionId, sessionId, fetchAnalytics]);

  /**
   * Handle domain change from selector
   */
  const handleDomainChange = async (newDomain, domainConfig) => {
    try {
      // PRODUCTION FIX: Skip if domain hasn't changed
      if (currentDomain === newDomain) {
        console.debug('⚡ Domain unchanged, skipping update');
        return;
      }
      
      setCurrentDomain(newDomain);
      
      // Notify backend of domain change for session tracking
      if (sessionId) {
        try {
          await fetchWithAuth(`${API_BASE_URL}/api/session/${sessionId}/domain`, {
            method: 'PUT',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ 
              domain: newDomain,
              isAIDetected: domainConfig?.isAIDetected || false,
              confidence: domainConfig?.confidence
            })
          });
        } catch (backendErr) {
          console.warn('Backend domain update failed (non-critical):', backendErr);
        }
      }
      
      // Auto-switch to preferred mode for domain
      if (domainConfig && domainConfig.preferredMode && domainConfig.preferredMode !== currentMode) {
        const activeSessionId = currentSessionId || sessionId;
        await updateMode(domainConfig.preferredMode, null, activeSessionId);
      }
      
      console.log(`Domain changed to: ${newDomain}`, domainConfig?.isAIDetected ? '(AI detected)' : '(manual)');
    } catch (err) {
      console.error('Failed to update domain:', err);
    }
  };

  /**
   * Handle mode change from selector
   */
  const handleModeChange = async (newMode, modeConfig) => {
    try {
      const activeSessionId = currentSessionId || sessionId;
      await updateMode(newMode, modeConfig, activeSessionId);
      console.log(`Mode changed to: ${newMode}`);
    } catch (err) {
      console.error('Failed to update mode:', err);
    }
  };

  /**
   * Handle save - persist current content to session
   */
  const handleSave = async () => {
    if (!sessionId && !currentSessionId) {
      console.warn('Cannot save: No active session');
      setSessionError('⚠️ Session not initialized. Please wait or refresh the page.');
      return;
    }

    const activeSessionId = currentSessionId || sessionId;
    const contentToSave = storyContent.trim();

    try {
      console.log(`💾 Saving session: ${activeSessionId}`);
      
      const response = await fetchWithAuth(`${API_BASE_URL}/api/session/${activeSessionId}/save`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          content: contentToSave,
          domain: currentDomain || 'story',
          metadata: {
            word_count: contentToSave.split(/\s+/).length,
            char_count: contentToSave.length,
            last_saved: new Date().toISOString()
          }
        })
      });

      if (!response.ok) {
        const errorText = await response.text();
        console.error('❌ Save request failed:', response.status, errorText);
        throw new Error(`Save failed (${response.status}): ${errorText}`);
      }

      const result = await response.json();
      console.log('✅ Session saved successfully:', result);
      
      // Show success feedback
      setGeneratedPrompt(`✅ Session saved successfully!\n\n📝 Content: ${result.content_length} characters\n⏰ Saved at: ${new Date(result.timestamp).toLocaleTimeString()}`);
      
      // Clear success message after 3 seconds
      setTimeout(() => {
        if (generatedPrompt.startsWith('✅ Session saved')) {
          setGeneratedPrompt('');
        }
      }, 3000);
      
    } catch (err) {
      console.error('💥 Save error:', err);
      setSessionError(err.message || 'Failed to save session. Please try again.');
    }
  };

  /**
   * Auto-detect domain from user input
   * Currently disabled - domain detection happens via explicit user selection
   */
  // eslint-disable-next-line no-unused-vars
  const handleDomainDetection = async (text) => {
    if (!isDomainDetectionEnabled || !text.trim()) return;

    try {
      const detection = await detectDomain(text);
      if (detection && detection.topic_family && detection.topic_family !== currentDomain) {
        const confidence = detection.domain_confidence || 0;
        if (confidence > 0.5) {
          setCurrentDomain(detection.topic_family);
          console.log(`Auto-detected domain: ${detection.topic_family} (confidence: ${confidence})`);
        }
      }
    } catch (err) {
      console.error('Domain detection failed:', err);
    }
  };

  /**
   * Handle AI suggestion request with production-ready error handling
   */
  const handleSuggest = async () => {
    // Validation checks
    if (!sessionId && !currentSessionId) {
      console.warn('Cannot suggest: No active session');
      setGeneratedPrompt('⚠️ Session not initialized. Please wait or refresh the page.');
      return;
    }

    const activeSessionId = currentSessionId || sessionId;
    const contentToUse = storyContent.trim();
    
    if (!contentToUse || contentToUse.length < 10) {
      console.warn('Cannot suggest: Story content too short');
      setGeneratedPrompt('💡 Please write at least 10 characters of content before requesting suggestions.');
      return;
    }

    setIsGenerating(true);
    clearError();
    setGeneratedPrompt(''); // Clear previous suggestions

    try {
      console.log(`🚀 Sending suggestion request for session: ${activeSessionId}`);
      
      // Use the production-grade invoke_suggest endpoint instead of suggestion_signal
      const response = await fetchWithAuth(`${API_BASE_URL}/api/session/${activeSessionId}/invoke_suggest`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          mode: 'on_demand', // Valid SuggestionMode enum value
          options: {
            topic: currentDomain || 'story',
            context: contentToUse,
            max_branches: 3
          },
          constraints: {}
        })
      });

      if (!response.ok) {
        const errorText = await response.text();
        console.error('❌ Suggestion request failed:', response.status, errorText);
        
        if (response.status === 404) {
          throw new Error('Session not found. Please refresh the page to create a new session.');
        } else if (response.status === 401) {
          throw new Error('Authentication required. Please log in again.');
        } else if (response.status === 500) {
          throw new Error('Server error. Our team has been notified. Please try again in a moment.');
        }
        
        throw new Error(`Suggestion failed (${response.status}): ${errorText}`);
      }

      const result = await response.json();
      console.log('📥 Suggestion response:', result);
      
      // Handle SuggestionsResponse structure: { session_id, projections: {}, metadata: {}, status }
      if (result.status === 'ok' || result.status === 'success') {
        const projections = result.projections || {};
        const projectionsList = Object.values(projections).filter(p => p != null);
        
        if (projectionsList.length > 0) {
          console.log(`✅ Suggestions received: ${projectionsList.length} options`);
          
          // PRODUCTION FIX: Clean markdown formatting - remove **, *, -, etc.
          const cleanMarkdown = (text) => {
            return text
              .replace(/\*\*(.*?)\*\*/g, '$1')  // Remove **bold**
              .replace(/\*(.*?)\*/g, '$1')      // Remove *italic*
              .replace(/^[-*+]\s/gm, '')        // Remove list markers at line start
              .replace(/^#+\s/gm, '')           // Remove headers
              .replace(/`(.*?)`/g, '$1')        // Remove `code`
              .replace(/\[(.*?)\]\(.*?\)/g, '$1') // Remove [links](url)
              .trim();
          };
          
          // Intelligently format projections with clean output
          const projectionsText = projectionsList
            .map((p, i) => {
              // Extract content intelligently
              let title = cleanMarkdown(p.title || `Option ${i + 1}`);
              let content = cleanMarkdown(
                p.paragraph || p.content || p.text || p.suggestion || ''
              );
              
              // If content is empty, try to extract from nested structure
              if (!content && typeof p === 'object') {
                content = cleanMarkdown(
                  p.content?.paragraph || p.content?.text || ''
                );
              }
              
              // Pretty print without markdown
              if (content) {
                return `${title}\n\n${content}`;
              } else {
                return title;
              }
            })
            .join('\n\n━━━━━━━━━━━━━━━━━━━━━━\n\n');  // Clean divider
          
          setGeneratedPrompt(`✨ AI Suggestions:\n\n${projectionsText}`);
        } else {
          console.warn('No projections in response');
          setGeneratedPrompt('💡 No suggestions available at this time. Try adding more content or changing the mode.');
        }
        
        // Fetch updated graph in background
        try {
          const graphResponse = await fetchWithAuth(`${API_BASE_URL}/api/session/${activeSessionId}/snapshot`, {
            method: 'GET',
            headers: { 'Content-Type': 'application/json' }
          });
          
          if (graphResponse.ok) {
            const snapshotData = await graphResponse.json();
            console.log('📊 Graph updated:', snapshotData);
            // Trigger analytics refresh
            fetchAnalytics();
          }
        } catch (graphError) {
          console.warn('⚠️ Failed to fetch updated graph (non-critical):', graphError);
        }
        
      } else if (result.status === 'suggestion_triggered') {
        console.log('✅ Suggestion triggered:', result.reason);
        setGeneratedPrompt(`✅ Suggestion process started: ${result.reason}\n\nThe AI agents are analyzing your content. Please try again in a moment.`);
        
      } else if (result.status === 'suggestion_skipped') {
        console.log('ℹ️ Suggestion skipped:', result.reason);
        setGeneratedPrompt(`ℹ️ Suggestion not triggered: ${result.reason}\n\nTry writing more content or changing your writing style.`);
        
      } else {
        // Unexpected response format
        console.warn('⚠️ Unexpected response format:', result);
        setGeneratedPrompt('⚠️ Received an unexpected response. Please try again.');
      }
      
    } catch (error) {
      console.error('❌ Suggestion failed:', error);
      
      // User-friendly error messages
      const errorMessage = error.message || 'An unexpected error occurred';
      setGeneratedPrompt(`❌ Error: ${errorMessage}\n\nPlease try again or contact support if the issue persists.`);
      
      // Also set error through existing error system if available
      if (typeof modeError !== 'undefined') {
        // Use the existing error handling system
        console.error('Setting mode error:', errorMessage);
      }
      
    } finally {
      setIsGenerating(false);
    }
  };

  return (
    <div className="min-h-screen bg-cyber-black cyber-grid">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        
        {/* Session Error Alert */}
        {sessionError && (
          <div className="mb-6 p-4 bg-red-900/50 border border-red-500/30 rounded-lg">
            <div className="flex items-center">
              <svg className="w-6 h-6 text-red-400 mr-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-1.96-1.333-2.731 0L3.732 16c-.77 1.333.192 3 1.732 3z" />
              </svg>
              <div>
                <h3 className="text-lg font-semibold text-red-300 mb-1">Session Error</h3>
                <p className="text-sm text-red-200">{sessionError}</p>
              </div>
            </div>
            <button
              onClick={() => window.location.reload()}
              className="mt-3 cyber-button px-4 py-2 rounded-lg text-sm"
            >
              Refresh Page
            </button>
          </div>
        )}
        
        {/* Initialization Loading State */}
        {isInitializing && !sessionError && (
          <div className="mb-6 p-4 bg-blue-900/30 border border-blue-500/30 rounded-lg">
            <div className="flex items-center">
              <div className="animate-spin rounded-full h-5 w-5 border-b-2 border-blue-400 mr-3"></div>
              <p className="text-blue-300">Initializing your creative session...</p>
            </div>
          </div>
        )}
        
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
          {/* Left Panel - Story Editor */}
          <div className="lg:col-span-2 space-y-6">
            <div className="glass-strong rounded-2xl p-8 shadow-cyber liquid-morph">
              <div className="flex items-center justify-between mb-6">
                <h2 className="text-2xl font-bold cyber-heading">
                  AI Story Co-Creation Studio
                </h2>
                <div className="flex items-center space-x-3">
                  <button 
                    onClick={handleSuggest}
                    disabled={
                      isGenerating || 
                      isInitializing || 
                      sessionError ||
                      !((currentSessionId || sessionId) && storyContent && storyContent.trim().length >= 10)
                    }
                    className="cyber-button px-4 py-2 rounded-lg font-medium transition-all duration-300 disabled:opacity-50 disabled:cursor-not-allowed"
                    title={
                      isInitializing ? "Initializing session..." :
                      sessionError ? "Session error - please refresh" :
                      !storyContent || storyContent.trim().length < 10 ? "Write at least 10 characters first" :
                      !(currentSessionId || sessionId) ? "Waiting for session..." :
                      "Get AI suggestions for your story"
                    }
                  >
                    <svg className="w-5 h-5 inline mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 10V3L4 14h7v7l9-11h-7z" />
                    </svg>
                    {isGenerating ? 'Suggesting...' : isInitializing ? 'Initializing...' : 'Suggest'}
                  </button>
                  <button 
                    onClick={handleSave}
                    disabled={
                      isInitializing || 
                      sessionError ||
                      !((currentSessionId || sessionId) && storyContent && storyContent.trim().length > 0)
                    }
                    className="cyber-button px-4 py-2 rounded-lg font-medium transition-all duration-300 disabled:opacity-50 disabled:cursor-not-allowed"
                    title={
                      isInitializing ? "Initializing session..." :
                      sessionError ? "Session error - please refresh" :
                      !storyContent || storyContent.trim().length === 0 ? "No content to save" :
                      !(currentSessionId || sessionId) ? "Waiting for session..." :
                      "Save current content to session"
                    }
                  >
                    <svg className="w-5 h-5 inline mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 7H5a2 2 0 00-2 2v9a2 2 0 002 2h14a2 2 0 002-2V9a2 2 0 00-2-2h-3m-1 4l-3-3m0 0l-3 3m3-3v12" />
                    </svg>
                    Save
                  </button>
                </div>
              </div>
              
              {/* Story Editor */}
              <div className="relative">
                <div className="absolute inset-0 bg-gradient-to-r from-neon-orange-500/5 to-transparent rounded-xl"></div>
                <textarea
                  value={storyContent}
                  onChange={(e) => setStoryContent(e.target.value)}
                  onFocus={() => setIsEditing(true)}
                  onBlur={() => setIsEditing(false)}
                  placeholder="Start writing your story here... The AI will help you create something amazing. Write at least 10 characters, then click 'Suggest' for AI assistance."
                  className={`relative z-10 w-full h-96 cyber-input rounded-xl p-6 text-lg leading-relaxed resize-none transition-all duration-300 ${
                    isEditing ? 'neon-glow' : ''
                  }`}
                  disabled={isInitializing || sessionError}
                />
                
                {/* Writing Stats */}
                <div className="flex justify-between items-center mt-4 text-sm text-cyber-gray-300">
                  <div className="flex space-x-6">
                    <span>Words: <span className="neon-text font-semibold">{storyContent.split(' ').filter(word => word.length > 0).length}</span></span>
                    <span>Characters: <span className="neon-text font-semibold">{storyContent.length}</span></span>
                  </div>
                  <div className="flex items-center space-x-2">
                    <div className="w-2 h-2 bg-neon-orange-500 rounded-full animate-pulse"></div>
                    <span className="cyber-subheading">Ready</span>
                  </div>
                </div>
              </div>
            </div>
            
            {/* Mode Selection and PTG Panel */}
            <div className="glass-strong rounded-2xl p-6 shadow-cyber">
              <h3 className="text-lg font-semibold cyber-heading mb-6 flex items-center">
                <svg className="w-6 h-6 mr-3 animate-pulse" fill="currentColor" viewBox="0 0 24 24">
                  <path d="M12 2L2 7l10 5 10-5-10-5zM2 17l10 5 10-5M2 12l10 5 10-5"/>
                </svg>
                Content Domain & AI Mode
              </h3>

              {/* Domain Selector */}
              <div className="mb-6">
                <DomainSelector
                  currentDomain={currentDomain}
                  onDomainChange={handleDomainChange}
                  disabled={modeLoading}
                  userInput={storyContent}
                  autoDetect={isDomainDetectionEnabled}
                  className="cyber-input"
                />
              </div>

              {/* Mode Selector */}
              <div className="mb-6">
                <ModeSelector
                  currentMode={currentMode}
                  onModeChange={handleModeChange}
                  disabled={modeLoading}
                  currentDomain={currentDomain}
                  userInput={storyContent}
                  autoDetect={isDomainDetectionEnabled}
                  className="cyber-input"
                />
              </div>

              {/* Domain Detection Toggle */}
              <div className="mb-4">
                <label className="flex items-center space-x-3 text-sm text-gray-400">
                  <input
                    type="checkbox"
                    checked={isDomainDetectionEnabled}
                    onChange={(e) => setIsDomainDetectionEnabled(e.target.checked)}
                    className="h-4 w-4 text-blue-600 rounded border-gray-300"
                  />
                  <span>Auto-detect content domain from input</span>
                </label>
              </div>

              {/* AI Suggestions Display - Populated by Suggest button */}
              {generatedPrompt && (
                <div className="glass rounded-xl p-4 border-cyber mt-4">
                  <div className="flex items-center justify-between mb-2">
                    <span className="text-sm font-medium cyber-subheading">AI Suggestions</span>
                    <span className="text-xs px-2 py-1 bg-neon-orange-500/20 text-neon-orange-300 rounded-full">
                      Mode: {currentMode}
                    </span>
                  </div>
                  <div className="bg-gray-900/50 rounded-lg p-3 mb-3">
                    <pre className="whitespace-pre-wrap text-sm text-white font-mono">
                      {generatedPrompt}
                    </pre>
                  </div>
                  <button
                    onClick={() => navigator.clipboard.writeText(generatedPrompt)}
                    className="cyber-button px-3 py-1 text-xs rounded"
                  >
                    Copy
                  </button>
                </div>
              )}

              {/* Error Display */}
              {modeError && (
                <div className="mt-4 p-3 bg-red-900/50 border border-red-500/30 rounded-lg">
                  <p className="text-sm text-red-300">{modeError}</p>
                  <button
                    onClick={clearError}
                    className="mt-2 text-xs text-red-400 hover:text-red-200"
                  >
                    Dismiss
                  </button>
                </div>
              )}
            </div>
          </div>
          
          {/* Right Panel - Knowledge Graph & Session Info */}
          <div className="space-y-6">
            {/* Knowledge Graph */}
            <div className="glass-strong rounded-2xl overflow-hidden shadow-cyber">
              <GraphView sessionId={currentSessionId} />
            </div>
            
            {/* Character & Fact Check Panel */}
            <div className="glass-strong rounded-2xl p-6 shadow-cyber liquid-morph-alt">
              <h3 className="text-lg font-semibold cyber-heading mb-4 flex items-center">
                <div className="w-3 h-3 bg-neon-orange-500 rounded-full mr-3 animate-glow"></div>
                Story Analytics
              </h3>
              <div className="space-y-4">
                <div className="p-4 glass rounded-xl">
                  <h4 className="text-sm font-medium cyber-subheading mb-2">Fact Check Status</h4>
                  {loadingAnalytics ? (
                    <div className="animate-pulse">
                      <div className="h-4 bg-cyber-gray-600/30 rounded w-3/4"></div>
                    </div>
                  ) : analytics?.fact_check ? (
                    <div className="flex items-center text-sm">
                      <svg className={`w-4 h-4 mr-2 ${analytics.fact_check.percentage === 100 ? 'text-green-400' : 'text-yellow-400'}`} fill="currentColor" viewBox="0 0 20 20">
                        <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clipRule="evenodd" />
                      </svg>
                      <span className={`${analytics.fact_check.percentage === 100 ? 'text-green-400' : 'text-yellow-400'} font-semibold`}>
                        {analytics.fact_check.verified}/{analytics.fact_check.total} facts verified ({Math.round(analytics.fact_check.percentage)}%)
                      </span>
                    </div>
                  ) : (
                    <div className="flex items-center text-sm">
                      <svg className="w-4 h-4 mr-2 text-green-400" fill="currentColor" viewBox="0 0 20 20">
                        <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clipRule="evenodd" />
                      </svg>
                      <span className="text-green-400 font-semibold">All facts verified</span>
                    </div>
                  )}
                </div>
                <div className="p-4 glass rounded-xl">
                  <h4 className="text-sm font-medium cyber-subheading mb-2">Character Profiles</h4>
                  {loadingAnalytics ? (
                    <div className="animate-pulse space-y-2">
                      <div className="h-3 bg-cyber-gray-600/30 rounded"></div>
                      <div className="h-3 bg-cyber-gray-600/30 rounded w-5/6"></div>
                    </div>
                  ) : analytics?.characters && analytics.characters.length > 0 ? (
                    <div className="space-y-2 text-sm text-white">
                      {analytics.characters.slice(0, 3).map((char, idx) => (
                        <div key={idx} className="flex items-center">
                          <div className={`w-2 h-2 ${idx === 0 ? 'bg-neon-orange-500' : 'bg-blue-400'} rounded-full mr-2 animate-pulse`}></div>
                          <span className="truncate">
                            {char.name}: {char.consistency}
                            {char.traits.length > 0 && ` (${char.traits.slice(0, 2).join(', ')})`}
                          </span>
                        </div>
                      ))}
                      {analytics.characters.length > 3 && (
                        <div className="text-xs text-cyber-gray-300 mt-1">
                          +{analytics.characters.length - 3} more characters
                        </div>
                      )}
                    </div>
                  ) : (
                    <div className="space-y-2 text-sm text-white">
                      <div className="flex items-center">
                        <div className="w-2 h-2 bg-cyber-gray-500 rounded-full mr-2"></div>
                        No characters detected yet
                      </div>
                    </div>
                  )}
                </div>
              </div>
            </div>

            {/* Session Control Panel */}
            <div className="glass-strong rounded-2xl p-6 shadow-cyber">
              <h3 className="text-lg font-semibold cyber-heading mb-4 flex items-center">
                <svg className="w-5 h-5 mr-3 animate-spin text-neon-orange-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.065 2.572c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.572 1.065c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.065-2.572c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z" />
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
                </svg>
                Session Control
              </h3>
              <div className="space-y-4">
                <div className="grid grid-cols-2 gap-3 text-sm">
                  <div className="p-3 glass rounded-lg border-cyber">
                    <div className="cyber-subheading text-xs mb-1">Mode</div>
                    <div className="text-white font-semibold capitalize">{currentMode || 'Balanced'}</div>
                  </div>
                  <div className="p-3 glass rounded-lg border-cyber">
                    <div className="cyber-subheading text-xs mb-1">Topic</div>
                    <div className="text-white font-semibold capitalize">{currentDomain || 'Story'}</div>
                  </div>
                  <div className="p-3 glass rounded-lg border-cyber">
                    <div className="cyber-subheading text-xs mb-1">Word Count</div>
                    <div className="text-white font-semibold">
                      {analytics?.story_metrics?.word_count || storyContent.split(' ').filter(word => word.length > 0).length}
                    </div>
                  </div>
                  <div className="p-3 glass rounded-lg border-cyber">
                    <div className="cyber-subheading text-xs mb-1">Events</div>
                    <div className="text-white font-semibold">
                      {analytics?.story_metrics?.event_count || 0}
                    </div>
                  </div>
                </div>
              </div>
            </div>
            
            {/* System Health */}
            <div className="glass-strong rounded-2xl overflow-hidden shadow-cyber">
              <HealthCheck />
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

// Protected Route component
const ProtectedRoute = ({ children, user }) => {
  if (!user) {
    return <Navigate to="/login" replace />;
  }
  return children;
};

function App() {
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);

  // Check authentication status on app load
  useEffect(() => {
    const checkAuth = async () => {
      try {
        // Check localStorage first
        const storedUser = localStorage.getItem('user');
        if (storedUser) {
          setUser(JSON.parse(storedUser));
        }

        // Verify with backend
        const response = await fetch(`${API_BASE_URL}/api/me`, {
          credentials: 'include',
        });

        if (response.ok) {
          const userData = await response.json();
          setUser(userData);
          localStorage.setItem('user', JSON.stringify(userData));
        } else {
          // 401 is expected when not logged in - don't log as error
          if (response.status !== 401) {
            console.warn(`Auth check returned ${response.status}`);
          }
          // Clear invalid stored data
          localStorage.removeItem('user');
          setUser(null);
        }
      } catch (error) {
        // Network errors are worth logging
        console.error('Auth check network error:', error);
        localStorage.removeItem('user');
        setUser(null);
      } finally {
        setLoading(false);
      }
    };

    checkAuth();
  }, []);

  const handleSignOut = async () => {
    try {
      await fetch('/auth/logout', {
        method: 'POST',
        credentials: 'include',
      });
    } catch (error) {
      console.error('Sign out error:', error);
    } finally {
      localStorage.removeItem('user');
      setUser(null);
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-screen bg-gray-900">
        <div className="animate-spin rounded-full h-16 w-16 border-b-2 border-blue-500"></div>
      </div>
    );
  }

  return (
    <Router>
      <div className="App">
        {user && <Navbar user={user} onSignOut={handleSignOut} />}
        
        <Routes>
          <Route 
            path="/login" 
            element={user ? <Navigate to="/" replace /> : <AuthGoogle />} 
          />
          <Route 
            path="/auth/callback" 
            element={<Callback />} 
          />
          <Route 
            path="/" 
            element={
              <ProtectedRoute user={user}>
                <Dashboard user={user} />
              </ProtectedRoute>
            } 
          />
          <Route 
            path="*" 
            element={<Navigate to={user ? "/" : "/login"} replace />} 
          />
        </Routes>
      </div>
    </Router>
  );
}

export default App;
