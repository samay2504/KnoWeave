import { useState, useEffect } from 'react';
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
  const updateMode = async (newMode, config = null) => {
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
  };

  /**
   * Generate prompt using current mode
   */
  const generatePrompt = async (userPrompt, agentType = 'general') => {
    setIsLoading(true);
    setError(null);

    try {
      const response = await fetch(`${API_BASE}/ptg/generate`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          user_prompt: userPrompt,
          agent_type: agentType,
          mode: currentMode,
          mode_config: modeConfig,
        }),
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
      const response = await fetch(`${API_BASE}/session/modes`);
      
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
  }, [initialMode]);

  return {
    currentMode,
    modeConfig,
    isLoading,
    error,
    updateMode,
    generatePrompt,
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
      const response = await fetch(`${API_BASE}/session/create`, {
        method: 'POST',
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
      const response = await fetch(`${API_BASE}/session/${targetSessionId}`);
      
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
