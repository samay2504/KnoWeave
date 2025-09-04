/**
 * Authentication utilities with retry logic and better error handling
 */

import AUTH_CONFIG from '../config/auth';

/**
 * Sleep utility for retry delays
 */
const sleep = (ms) => new Promise(resolve => setTimeout(resolve, ms));

/**
 * Enhanced fetch with retry logic and timeout handling
 */
export const authFetch = async (url, options = {}, retries = AUTH_CONFIG.MAX_RETRIES) => {
  const controller = new AbortController();
  const timeoutId = setTimeout(() => controller.abort(), AUTH_CONFIG.OAUTH_TIMEOUT);

  try {
    const response = await fetch(url, {
      ...options,
      signal: controller.signal,
      headers: {
        'Accept': 'application/json',
        'Content-Type': 'application/json',
        ...options.headers,
      },
    });

    clearTimeout(timeoutId);
    return response;
  } catch (error) {
    clearTimeout(timeoutId);
    
    // If we have retries left and it's a network error, retry
    if (retries > 0 && (error.name === 'AbortError' || error.name === 'TypeError')) {
      console.log(`Request failed, retrying... (${AUTH_CONFIG.MAX_RETRIES - retries + 1}/${AUTH_CONFIG.MAX_RETRIES})`);
      await sleep(AUTH_CONFIG.RETRY_DELAY);
      return authFetch(url, options, retries - 1);
    }
    
    // Transform error for better UX
    if (error.name === 'AbortError') {
      throw new Error(AUTH_CONFIG.ERRORS.TIMEOUT);
    } else if (error.name === 'TypeError') {
      throw new Error(AUTH_CONFIG.ERRORS.NETWORK);
    }
    
    throw error;
  }
};

/**
 * Parse authentication errors for user-friendly messages
 */
export const parseAuthError = (error, response = null) => {
  if (!error) return AUTH_CONFIG.ERRORS.GENERIC;
  
  const message = error.message || error.detail || error;
  
  // Check for specific error patterns
  if (message.includes('expired') || message.includes('invalid_grant')) {
    return AUTH_CONFIG.ERRORS.EXPIRED;
  }
  
  if (message.includes('timeout') || message.includes('ETIMEDOUT')) {
    return AUTH_CONFIG.ERRORS.TIMEOUT;
  }
  
  if (message.includes('network') || message.includes('fetch')) {
    return AUTH_CONFIG.ERRORS.NETWORK;
  }
  
  if (response && response.status >= 500) {
    return AUTH_CONFIG.ERRORS.SERVER;
  }
  
  // Return the original message if it's user-friendly, otherwise generic
  if (typeof message === 'string' && message.length < 200) {
    return message;
  }
  
  return AUTH_CONFIG.ERRORS.GENERIC;
};

/**
 * Validate OAuth state parameter
 */
export const validateOAuthState = (receivedState, expectedState) => {
  if (!receivedState || !expectedState) {
    return false;
  }
  
  return receivedState === expectedState;
};

/**
 * Check if we're in a development environment
 */
export const isDevelopment = () => process.env.NODE_ENV === 'development';

/**
 * Get appropriate error redirect URL
 */
export const getErrorRedirectUrl = (error) => {
  const params = new URLSearchParams({
    error: 'auth_failed',
    message: parseAuthError(error)
  });
  
  return `/login?${params.toString()}`;
};
