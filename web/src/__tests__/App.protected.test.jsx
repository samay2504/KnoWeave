import React from 'react';
import { render, screen } from '@testing-library/react';
import '@testing-library/jest-dom';
import { rest } from 'msw';
import { setupServer } from 'msw/node';
import App from '../App';

// Mock server for API calls
const server = setupServer(
  rest.get('/api/me', (req, res, ctx) => {
    const authCookie = req.headers.get('cookie');
    
    if (authCookie && authCookie.includes('auth_token=valid_token')) {
      return res(
        ctx.json({
          id: '123456789',
          email: 'test@example.com',
          name: 'Test User'
        })
      );
    }
    
    return res(ctx.status(401), ctx.json({ detail: 'Not authenticated' }));
  }),
  
  rest.post('/auth/logout', (req, res, ctx) => {
    return res(ctx.json({ success: true, message: 'Logged out successfully' }));
  })
);

beforeAll(() => server.listen());
afterEach(() => {
  server.resetHandlers();
  localStorage.clear();
});
afterAll(() => server.close());

// Mock fetch to include cookies
const originalFetch = global.fetch;
beforeAll(() => {
  global.fetch = jest.fn((url, options = {}) => {
    // Simulate cookie inclusion for credential requests
    if (options.credentials === 'include') {
      const mockToken = localStorage.getItem('mockAuthToken');
      if (mockToken) {
        options.headers = {
          ...options.headers,
          'cookie': `auth_token=${mockToken}`
        };
      }
    }
    return originalFetch(url, options);
  });
});

afterAll(() => {
  global.fetch = originalFetch;
});

describe('App Component Protected Routes', () => {
  test('redirects to login when unauthenticated', async () => {
    render(<App />);
    
    // Should show loading initially
    expect(screen.getByRole('status')).toHaveClass('animate-spin');
    
    // After auth check, should redirect to login
    await screen.findByText('Human-AI Co-Creation');
    expect(screen.getByText('Sign in to start your creative journey')).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /continue with google/i })).toBeInTheDocument();
  });

  test('shows dashboard when authenticated', async () => {
    // Mock valid authentication
    localStorage.setItem('user', JSON.stringify({
      id: '123456789',
      email: 'test@example.com',
      name: 'Test User'
    }));
    localStorage.setItem('mockAuthToken', 'valid_token');
    
    render(<App />);
    
    // Should show loading initially
    expect(screen.getByRole('status')).toHaveClass('animate-spin');
    
    // After auth verification, should show dashboard
    await screen.findByText('Story Editor');
    expect(screen.getByText('Suggestions')).toBeInTheDocument();
    expect(screen.getByText('Knowledge Graph')).toBeInTheDocument();
    
    // Should show navbar with user info
    expect(screen.getByText('Test User')).toBeInTheDocument();
  });

  test('handles authentication verification failure', async () => {
    // Set invalid stored data
    localStorage.setItem('user', JSON.stringify({
      id: '123456789',
      email: 'test@example.com',
      name: 'Test User'
    }));
    localStorage.setItem('mockAuthToken', 'invalid_token');
    
    render(<App />);
    
    // Should show loading initially
    expect(screen.getByRole('status')).toHaveClass('animate-spin');
    
    // After failed verification, should clear data and show login
    await screen.findByText('Sign in to start your creative journey');
    
    // Local storage should be cleared
    expect(localStorage.getItem('user')).toBeNull();
  });

  test('navbar sign out functionality', async () => {
    // Mock authenticated state
    localStorage.setItem('user', JSON.stringify({
      id: '123456789',
      email: 'test@example.com',
      name: 'Test User'
    }));
    localStorage.setItem('mockAuthToken', 'valid_token');
    
    render(<App />);
    
    // Wait for dashboard to load
    await screen.findByText('Story Editor');
    
    // Find and click user menu
    const userButton = screen.getByRole('button', { name: /test user/i });
    userButton.click();
    
    // Find and click sign out
    const signOutButton = await screen.findByText('Sign out');
    signOutButton.click();
    
    // Should redirect to login and clear storage
    await screen.findByText('Sign in to start your creative journey');
    expect(localStorage.getItem('user')).toBeNull();
  });

  test('protected route redirects work correctly', async () => {
    render(<App />);
    
    // Initially should show loading
    expect(screen.getByRole('status')).toHaveClass('animate-spin');
    
    // Should redirect to login for unauthenticated user
    await screen.findByText('Sign in to start your creative journey');
    
    // The URL should reflect the login page
    expect(window.location.pathname).toBe('/');
  });

  test('dashboard components render correctly when authenticated', async () => {
    // Mock authenticated state
    localStorage.setItem('user', JSON.stringify({
      id: '123456789',
      email: 'test@example.com',
      name: 'Test User'
    }));
    localStorage.setItem('mockAuthToken', 'valid_token');
    
    render(<App />);
    
    // Wait for dashboard
    await screen.findByText('Story Editor');
    
    // Check main dashboard elements
    expect(screen.getByText('Suggest')).toBeInTheDocument();
    expect(screen.getByText('Save')).toBeInTheDocument();
    expect(screen.getByPlaceholderText('Start writing your story here...')).toBeInTheDocument();
    
    // Check suggestion cards
    expect(screen.getByText('Option 1')).toBeInTheDocument();
    expect(screen.getByText('Option 2')).toBeInTheDocument();
    expect(screen.getByText('Option 3')).toBeInTheDocument();
    
    // Check right panel
    expect(screen.getByText('Knowledge Graph')).toBeInTheDocument();
    expect(screen.getByText('Session Info')).toBeInTheDocument();
    expect(screen.getByText('Mode:')).toBeInTheDocument();
    expect(screen.getByText('Balanced')).toBeInTheDocument();
  });

  test('loading state displays correctly', () => {
    render(<App />);
    
    const loadingSpinner = screen.getByRole('status');
    expect(loadingSpinner).toHaveClass('animate-spin');
    expect(loadingSpinner).toHaveClass('rounded-full');
    expect(loadingSpinner).toHaveClass('border-b-2');
    expect(loadingSpinner).toHaveClass('border-blue-500');
  });
});
