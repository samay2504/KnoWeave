import { useState, useEffect, useCallback } from 'react';
import { BACKEND_PORT } from '../config/constants';

/**
 * Custom hook for managing AI interaction modes
 * Integrates with backend PTG system for mode-specific prompt generation
 */
export const useAIMode = (initialMode = 'balanced') => {
  const [currentMode, setCurrentMode] = useState(initialMode);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState(null);
  const [modeConfig, setModeConfig] = useState(null);

  // Backend API endpoint using global constants
  const API_BASE = `http://localhost:${BACKEND_PORT}/api`;

  /**
   * Update the current AI mode and sync with backend
   */
  const updateMode = useCallback(async (newMode, config = null) => {
    setIsLoading(true);
    setError(null);

    try {
      // Update local state
      setCurrentMode(newMode);
      if (config) {
        setModeConfig(config);
      }

      // Sync with backend PTG system
      const response = await fetch(`${API_BASE}/session/mode`, {
        method: 'POST',
        credentials: 'include', // Include cookies for auth
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          mode: newMode,
          config: config,
        }),
      });

      if (!response.ok) {
        throw new Error(`Failed to update mode: ${response.statusText}`);
      }

      const result = await response.json();
      
      // Store any updated configuration from backend
      if (result.config) {
        setModeConfig(result.config);
      }

      return result;
    } catch (err) {
      console.error('Error updating AI mode:', err);
      setError(err.message);
      throw err;
    } finally {
      setIsLoading(false);
    }
  }, [API_BASE]);

  /**
   * Generate prompt using current mode with domain support
   */
  const generatePrompt = async (userPrompt, agentType = 'general', options = {}) => {
    setIsLoading(true);
    setError(null);

    try {
      const requestBody = {
        user_prompt: userPrompt,
        agent_type: agentType,
        mode: currentMode,
        mode_config: modeConfig,
        // Support for topic-agnostic functionality
        topic: options.topic || userPrompt,
        topic_descriptor: options.topic_descriptor || `User request: ${userPrompt}`,
        topic_family: options.topic_family,
        topic_role: options.topic_role,
        topic_goal: options.topic_goal,
        context_chunks: options.context_chunks || [],
      };

  const response = await fetch(`${API_BASE}/ptg/generate`.replace('/api/ptg', '/api/ptg'), {
        method: 'POST',
        credentials: 'include', // Include cookies for auth
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(requestBody),
      });

      if (!response.ok) {
        throw new Error(`Failed to generate prompt: ${response.statusText}`);
      }

      const result = await response.json();
      return result;
    } catch (err) {
      console.error('Error generating prompt:', err);
      setError(err.message);
      throw err;
    } finally {
      setIsLoading(false);
    }
  };

  /**
   * Get available modes from backend
   */
  const getAvailableModes = async () => {
    try {
      const response = await fetch(`${API_BASE}/session/modes`, {
        credentials: 'include', // Include cookies for auth
      });
      
      if (!response.ok) {
        throw new Error(`Failed to fetch modes: ${response.statusText}`);
      }

      const result = await response.json();
      return result.modes || [];
    } catch (err) {
      console.error('Error fetching available modes:', err);
      return [];
    }
  };

  /**
   * Initialize mode configuration on mount
   */
  useEffect(() => {
    const initializeMode = async () => {
      try {
        await updateMode(initialMode);
      } catch (err) {
        console.warn('Failed to initialize mode:', err);
      }
    };

    initializeMode();
  }, [initialMode, updateMode]);

  // PRODUCTION FIX: Client-side cache to prevent redundant API calls
  const [domainCache] = useState(new Map()); // Cache: text → {result, timestamp}

  /**
   * Detect domain from user input text
   */
  const detectDomain = async (text) => {
    // PRODUCTION FIX: Check cache first (5-minute TTL)
    const cacheKey = text.trim().substring(0, 500);
    const cached = domainCache.get(cacheKey);
    if (cached && Date.now() - cached.timestamp < 300000) {
      console.log('✅ Domain detection cache hit');
      return cached.result;
    }

    setIsLoading(true);
    setError(null);

    try {
      const response = await fetch(`${API_BASE}/api/agents/perception/detect-domain`, {
        method: 'POST',
        credentials: 'include', // Include cookies for auth
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          text: text,
        }),
      });

      if (!response.ok) {
        throw new Error(`Failed to detect domain: ${response.statusText}`);
      }

      const result = await response.json();
      
      // PRODUCTION FIX: Cache successful result
      domainCache.set(cacheKey, { result, timestamp: Date.now() });
      // Limit cache size to 50 entries
      if (domainCache.size > 50) {
        const firstKey = domainCache.keys().next().value;
        domainCache.delete(firstKey);
      }
      
      return result;
    } catch (err) {
      console.error('Error detecting domain:', err);
      setError(err.message);
      return { topic_family: 'story', confidence: 0.0 }; // Fallback
    } finally {
      setIsLoading(false);
    }
  };

  return {
    currentMode,
    modeConfig,
    isLoading,
    error,
    updateMode,
    generatePrompt,
    detectDomain,
    getAvailableModes,
    clearError: () => setError(null),
  };
};

/**
 * Custom hook for session management
 * Handles user sessions and mode persistence
 */
export const useSession = () => {
  const [sessionId, setSessionId] = useState(null);
  const [isSessionActive, setIsSessionActive] = useState(false);
  const [sessionData, setSessionData] = useState(null);

  const API_BASE = `http://localhost:${BACKEND_PORT}/api`;

  /**
   * Create a new session
   */
  const createSession = async (userData = {}) => {
    try {
  const response = await fetch(`${API_BASE}/session/new`, {
        method: 'POST',
        credentials: 'include', // Include cookies for auth
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(userData),
      });

      if (!response.ok) {
        throw new Error(`Failed to create session: ${response.statusText}`);
      }

      const result = await response.json();
      setSessionId(result.session_id);
      setIsSessionActive(true);
      setSessionData(result);

      return result;
    } catch (err) {
      console.error('Error creating session:', err);
      throw err;
    }
  };

  /**
   * Get current session data
   */
  const getSession = async (sessionIdOverride = null) => {
    const targetSessionId = sessionIdOverride || sessionId;
    
    if (!targetSessionId) {
      return null;
    }

    try {
      const response = await fetch(`${API_BASE}/session/${targetSessionId}`, {
        credentials: 'include', // Include cookies for auth
      });
      
      if (!response.ok) {
        if (response.status === 404) {
          setIsSessionActive(false);
          return null;
        }
        throw new Error(`Failed to get session: ${response.statusText}`);
      }

      const result = await response.json();
      setSessionData(result);
      setIsSessionActive(true);

      return result;
    } catch (err) {
      console.error('Error getting session:', err);
      throw err;
    }
  };

  /**
   * End current session
   */
  const endSession = async () => {
    if (!sessionId) {
      return;
    }

    try {
      await fetch(`${API_BASE}/session/${sessionId}/end`, {
        method: 'POST',
        credentials: 'include', // Include cookies for auth
      });
    } catch (err) {
      console.error('Error ending session:', err);
    } finally {
      setSessionId(null);
      setIsSessionActive(false);
      setSessionData(null);
    }
  };

  return {
    sessionId,
    isSessionActive,
    sessionData,
    createSession,
    getSession,
    endSession,
  };
};
