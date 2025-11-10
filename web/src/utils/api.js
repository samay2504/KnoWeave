/**
 * Production-Ready API Utilities with Token Refresh
 * Handles automatic OAuth token refresh on 401 errors
 */

const API_BASE_URL = process.env.REACT_APP_API_BASE_URL || 'http://localhost:8000';

let isRefreshing = false;
let refreshPromise = null;

/**
 * Refresh OAuth token
 */
async function refreshToken() {
  try {
    const response = await fetch(`${API_BASE_URL}/api/refresh-token`, {
      method: 'POST',
      credentials: 'include', // Important for cookies
    });

    if (response.ok) {
      console.log('✅ Token refreshed successfully');
      return true;
    } else {
      console.warn('⚠️ Token refresh failed');
      return false;
    }
  } catch (error) {
    console.error('❌ Token refresh error:', error);
    return false;
  }
}

/**
 * Fetch with automatic token refresh on 401
 * Drop-in replacement for fetch() with auth handling
 */
export async function fetchWithAuth(url, options = {}) {
  // Ensure credentials are included
  const fetchOptions = {
    ...options,
    credentials: 'include',
  };

  try {
    // First attempt
    let response = await fetch(url, fetchOptions);

    // If 401, try to refresh token and retry
    if (response.status === 401) {
      console.log('🔄 Got 401, attempting token refresh...');

      // Prevent multiple simultaneous refresh attempts
      if (!isRefreshing) {
        isRefreshing = true;
        refreshPromise = refreshToken();
      }

      const refreshSuccess = await refreshPromise;
      isRefreshing = false;
      refreshPromise = null;

      if (refreshSuccess) {
        // Retry original request with refreshed token
        console.log('🔄 Retrying original request with refreshed token...');
        response = await fetch(url, fetchOptions);

        if (response.ok) {
          console.log('✅ Request succeeded after token refresh');
          return response;
        }
      }

      // If refresh failed or retry still got 401, redirect to login
      console.warn('⚠️ Authentication failed, redirecting to login...');
      
      // Clear any stored user data
      localStorage.removeItem('user');
      
      // Redirect to login (only if not already on login page)
      if (!window.location.pathname.includes('/login')) {
        window.location.href = '/login';
      }
      
      throw new Error('Authentication required. Please log in again.');
    }

    return response;
  } catch (error) {
    // Network error or other fetch failure
    console.error('❌ Fetch error:', error);
    throw error;
  }
}

/**
 * Convenience methods for common HTTP verbs
 */
export const api = {
  get: (url, options = {}) =>
    fetchWithAuth(url, { ...options, method: 'GET' }),

  post: (url, data, options = {}) =>
    fetchWithAuth(url, {
      ...options,
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        ...options.headers,
      },
      body: JSON.stringify(data),
    }),

  put: (url, data, options = {}) =>
    fetchWithAuth(url, {
      ...options,
      method: 'PUT',
      headers: {
        'Content-Type': 'application/json',
        ...options.headers,
      },
      body: JSON.stringify(data),
    }),

  delete: (url, options = {}) =>
    fetchWithAuth(url, { ...options, method: 'DELETE' }),
};

export default api;
