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

  test('handles successful login initiation', async () => {
    // Mock window.location.href assignment
    const mockLocation = { href: '' };
    Object.defineProperty(window, 'location', {
      value: mockLocation,
      writable: true,
    });

    render(<AuthGoogle />);
    
    const loginButton = screen.getByRole('button', { name: /continue with google/i });
    fireEvent.click(loginButton);

    await waitFor(() => {
      expect(mockLocation.href).toBe('https://accounts.google.com/o/oauth2/v2/auth?client_id=test');
    });
  });

  test('shows loading state during login', async () => {
    render(<AuthGoogle />);
    
    const loginButton = screen.getByRole('button', { name: /continue with google/i });
    fireEvent.click(loginButton);

    // Check if loading spinner appears
    expect(screen.getByRole('button')).toHaveClass('animate-spin');
    expect(screen.getByRole('button')).toBeDisabled();
  });

  test('handles login error', async () => {
    // Override the server response for this test
    server.use(
      rest.get('/auth/google/login', (req, res, ctx) => {
        return res(ctx.status(500), ctx.json({ detail: 'Server error' }));
      })
    );

    render(<AuthGoogle />);
    
    const loginButton = screen.getByRole('button', { name: /continue with google/i });
    fireEvent.click(loginButton);

    await waitFor(() => {
      expect(screen.getByText(/failed to initiate login/i)).toBeInTheDocument();
    });

    // Verify button is re-enabled after error
    expect(loginButton).not.toBeDisabled();
  });

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

  test('responsive design elements', () => {
    render(<AuthGoogle />);
    
  const container = screen.getByTestId('auth-container');
  expect(container).toHaveClass('max-w-md', 'w-full');

  const button = screen.getByRole('button', { name: /continue with google/i });
  expect(button).toHaveClass('w-full');
  });
});
