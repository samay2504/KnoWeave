// Frontend configuration constants
// Matches backend constants for production-grade consistency

export const BACKEND_PORT = 8000;
export const FRONTEND_PORT = 3000;

export const API_CONFIG = {
  BASE_URL: `http://localhost:${BACKEND_PORT}`,
  ENDPOINTS: {
    SESSION: '/api/session',
    PTG: '/api/ptg',
    AGENTS: '/api/agents',
    AUTH: '/api/auth',
  },
  TIMEOUT: 30000, // 30 seconds
};

export const OAUTH_CONFIG = {
  GOOGLE_CLIENT_ID: process.env.REACT_APP_GOOGLE_CLIENT_ID || '',
  REDIRECT_URI: `http://localhost:${FRONTEND_PORT}/auth/callback`,
};

export const AI_MODES = {
  CONSERVATIVE: 'conservative',
  BALANCED: 'balanced', 
  EXPLORATORY: 'exploratory',
  FOCUSED: 'focused',
};

export const DEFAULT_MODE = AI_MODES.BALANCED;

export const AGENT_TYPES = {
  GENERAL: 'general',
  CREATIVE: 'creative',
  ANALYTICAL: 'analytical',
  TECHNICAL: 'technical',
  RESEARCH: 'research',
  WRITING: 'writing',
};

export const UI_CONFIG = {
  TOAST_DURATION: 3000,
  ANIMATION_DURATION: 200,
  DEBOUNCE_DELAY: 300,
};
