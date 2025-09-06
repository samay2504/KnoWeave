import React from 'react';
import { render, screen, waitFor } from '@testing-library/react';
import '@testing-library/jest-dom';
import { BrowserRouter } from 'react-router-dom';
import { rest } from 'msw';
import { setupServer } from 'msw/node';
import Callback from '../components/Callback';

// Mock react-router-dom hooks
const mockNavigate = jest.fn();
const mockSearchParams = new URLSearchParams();

jest.mock('react-router-dom', () => ({
  ...jest.requireActual('react-router-dom'),
  useNavigate: () => mockNavigate,
  useSearchParams: () => [mockSearchParams]
}));

// Mock server for API calls
const server = setupServer(
  rest.get('/auth/google/callback', (req, res, ctx) => {
    const code = req.url.searchParams.get('code');
    const state = req.url.searchParams.get('state');
    
    if (code === 'valid_code' && state === 'valid_state') {
      return res(
        ctx.json({
          success: true,
          user: {
            id: '123456789',
            email: 'test@example.com',
            name: 'Test User',
            picture: 'https://example.com/avatar.jpg'
          }
        })
      );
    }
    
    return res(
      ctx.status(400),
      ctx.json({ detail: 'Invalid code or state' })
    );
  })
);

beforeAll(() => server.listen());
afterEach(() => {
  server.resetHandlers();
  mockNavigate.mockClear();
  mockSearchParams.delete('code');
  mockSearchParams.delete('state');
  mockSearchParams.delete('error');
  localStorage.clear();
});
afterAll(() => server.close());

const renderCallback = () => {
  return render(
    <BrowserRouter>
      <Callback />
    </BrowserRouter>
  );
};

describe('Callback Component', () => {
  test('shows processing state initially', () => {
    mockSearchParams.set('code', 'valid_code');
    mockSearchParams.set('state', 'valid_state');
    
    renderCallback();
    
    expect(screen.getByText('Completing Sign In')).toBeInTheDocument();
    expect(screen.getByText(/please wait while we process/i)).toBeInTheDocument();
    expect(screen.getByRole('status')).toHaveClass('animate-spin');
  });

  test('handles successful authentication', async () => {
    mockSearchParams.set('code', 'valid_code');
    mockSearchParams.set('state', 'valid_state');
    
    renderCallback();
    
    await waitFor(() => {
      expect(screen.getByText('Success!')).toBeInTheDocument();
    }, { timeout: 3000 });
    
    expect(screen.getByText(/you have been signed in successfully/i)).toBeInTheDocument();
    
    // Check if user data is stored in localStorage
    await waitFor(() => {
      const storedUser = localStorage.getItem('user');
      expect(storedUser).toBeTruthy();
    });
    const userData = JSON.parse(localStorage.getItem('user'));
    expect(userData.email).toBe('test@example.com');

    // Check if navigation occurs after delay
    await waitFor(() => {
      expect(mockNavigate).toHaveBeenCalledWith('/', { replace: true });
    }, { timeout: 2500 });
  });

  test('handles OAuth error parameter', async () => {
    mockSearchParams.set('error', 'access_denied');
    
    renderCallback();
    
    await waitFor(() => {
      expect(screen.getByText('Authentication Failed')).toBeInTheDocument();
    });
    
    expect(screen.getByText(/oauth error: access_denied/i)).toBeInTheDocument();
    
    // Should redirect to login after delay
    await waitFor(() => {
      expect(mockNavigate).toHaveBeenCalledWith('/login', { replace: true });
    }, { timeout: 3500 });
  });

  test('handles missing code parameter', async () => {
    mockSearchParams.set('state', 'valid_state');
    // No code parameter
    
    renderCallback();
    
    await waitFor(() => {
      expect(screen.getByText('Authentication Failed')).toBeInTheDocument();
    });
    
    expect(screen.getByText(/missing code or state parameter/i)).toBeInTheDocument();
  });

  test('handles missing state parameter', async () => {
    mockSearchParams.set('code', 'valid_code');
    // No state parameter
    
    renderCallback();
    
    await waitFor(() => {
      expect(screen.getByText('Authentication Failed')).toBeInTheDocument();
    });
    
    expect(screen.getByText(/missing code or state parameter/i)).toBeInTheDocument();
  });

  test('handles server authentication failure', async () => {
    mockSearchParams.set('code', 'invalid_code');
    mockSearchParams.set('state', 'invalid_state');
    
    renderCallback();
    
    await waitFor(() => {
      expect(screen.getByText('Authentication Failed')).toBeInTheDocument();
    });
    
    expect(screen.getByText(/invalid code or state/i)).toBeInTheDocument();
    
    // Should redirect to login after delay
    await waitFor(() => {
      expect(mockNavigate).toHaveBeenCalledWith('/login', { replace: true });
    }, { timeout: 3500 });
  });

  test('handles network errors', async () => {
    mockSearchParams.set('code', 'valid_code');
    mockSearchParams.set('state', 'valid_state');
    
    // Override server to simulate network error
    server.use(
      rest.get('/auth/google/callback', (req, res, ctx) => {
        return res.networkError('Network error');
      })
    );
    
    renderCallback();
    
    await waitFor(() => {
      expect(screen.getByText('Authentication Failed')).toBeInTheDocument();
    });
    
    expect(screen.getByText(/redirecting to login page/i)).toBeInTheDocument();
  });

  test('proper icon rendering for different states', async () => {
    mockSearchParams.set('code', 'valid_code');
    mockSearchParams.set('state', 'valid_state');
    
    renderCallback();
    
    // Processing state has spinner
    expect(screen.getByRole('status')).toHaveClass('animate-spin');
    
    // Wait for success state
    await waitFor(() => {
      expect(screen.getByText('Success!')).toBeInTheDocument();
    });
    
    // Success state should have checkmark (SVG with specific path)
    const successIcon = screen.getByRole('img', { hidden: true });
    expect(successIcon).toBeInTheDocument();
  });

  test('error state shows correct icon', async () => {
    mockSearchParams.set('error', 'access_denied');
    
    renderCallback();
    
    await waitFor(() => {
      expect(screen.getByText('Authentication Failed')).toBeInTheDocument();
    });
    
    // Error state should have X icon
    const errorIcon = screen.getByRole('img', { hidden: true });
    expect(errorIcon).toBeInTheDocument();
  });
});
