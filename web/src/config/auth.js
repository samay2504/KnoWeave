/**
 * Authentication configuration for production readiness
 */

const AUTH_CONFIG = {
  // Timeout settings
  OAUTH_TIMEOUT: 30000, // 30 seconds
  TOKEN_REFRESH_BUFFER: 300000, // 5 minutes before expiry
  
  // Retry settings
  MAX_RETRIES: 2,
  RETRY_DELAY: 1000, // 1 second
  
  // Cookie settings
  COOKIE_MAX_AGE: 300, // 5 minutes for OAuth state
  
  // Error messages
  ERRORS: {
    TIMEOUT: 'The request timed out. Please check your connection and try again.',
    EXPIRED: 'Your session has expired. Please sign in again.',
    NETWORK: 'Network error. Please check your connection and try again.',
    SERVER: 'Server error. Please try again later.',
    GENERIC: 'Authentication failed. Please try again.',
  },
  
  // Development vs Production settings
  IS_PRODUCTION: process.env.NODE_ENV === 'production',
  
  // OAuth settings
  OAUTH: {
    SCOPES: ['openid', 'email', 'profile'],
    PROMPT: process.env.NODE_ENV === 'production' ? 'select_account' : 'consent',
    ACCESS_TYPE: 'offline',
  }
};

export default AUTH_CONFIG;
