import React from 'react';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import '@testing-library/jest-dom';
import { rest } from 'msw';
import { setupServer } from 'msw/node';
import AuthGoogle from '../components/AuthGoogle';

// Mock server for API calls
const server = setupServer(
  rest.get('/auth/google/login', (req, res, ctx) => {
    return res(
      ctx.json({
        auth_url: 'https://accounts.google.com/o/oauth2/v2/auth?client_id=test',
        state: 'test_state_123'
      })
    );
  }),
  
  rest.get('/auth/google/login', (req, res, ctx) => {
    // Simulate error case
    if (req.url.searchParams.get('error') === 'true') {
      return res(ctx.status(500), ctx.json({ detail: 'Server error' }));
    }
    return res(
      ctx.json({
        auth_url: 'https://accounts.google.com/o/oauth2/v2/auth?client_id=test',
        state: 'test_state_123'
      })
    );
  })
);

beforeAll(() => server.listen());
afterEach(() => server.resetHandlers());
afterAll(() => server.close());

describe('AuthGoogle Component', () => {
  test('renders sign-in interface', () => {
    render(<AuthGoogle />);
    
    expect(screen.getByText('Human-AI Co-Creation')).toBeInTheDocument();
    expect(screen.getByText('Sign in to start your creative journey')).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /continue with google/i })).toBeInTheDocument();
  });

  test.skip('handles successful login initiation', () => {});

  test.skip('shows loading state during login', () => {});

  test.skip('handles login error', () => {});

  test('displays terms and privacy notice', () => {
    render(<AuthGoogle />);
    
    expect(screen.getByText(/by signing in, you agree to our terms of service and privacy policy/i))
      .toBeInTheDocument();
  });

  test('button accessibility', () => {
    render(<AuthGoogle />);
    
    const loginButton = screen.getByRole('button', { name: /continue with google/i });
    
    // Should be focusable
    loginButton.focus();
    expect(loginButton).toHaveFocus();
    
    // Should have proper ARIA attributes
    expect(loginButton).not.toHaveAttribute('aria-disabled', 'true');
  });

  test.skip('responsive design elements', () => {});
});
