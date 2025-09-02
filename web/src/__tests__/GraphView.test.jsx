import React from 'react';
import { render, screen, waitFor, fireEvent } from '@testing-library/react';
import { jest } from '@jest/globals';
import '@testing-library/jest-dom';
import GraphView from '../GraphView';

// Mock fetch globally
const mockFetch = jest.fn();
global.fetch = mockFetch;

describe('GraphView Component', () => {
  const mockSessionId = 'test-session-123';
  
  beforeEach(() => {
    mockFetch.mockClear();
  });

  it('renders loading state initially', () => {
    mockFetch.mockImplementation(() => new Promise(() => {})); // Never resolves
    
    render(<GraphView sessionId={mockSessionId} />);
    
    expect(screen.getByText(/loading/i)).toBeInTheDocument();
  });

  it('renders error state when API call fails', async () => {
    mockFetch.mockRejectedValue(new Error('Network error'));
    
    render(<GraphView sessionId={mockSessionId} />);
    
    await waitFor(() => {
      expect(screen.getByText(/error loading graph/i)).toBeInTheDocument();
    });
    
    expect(screen.getByText(/network error/i)).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /retry/i })).toBeInTheDocument();
  });

  it('renders graph data when API call succeeds', async () => {
    const mockGraphData = {
      session_id: mockSessionId,
      topic: 'Test Story',
      events: [
        { id: 'event1', summary: 'Story begins', confidence: 0.9 },
        { id: 'event2', summary: 'Plot develops', confidence: 0.8 }
      ],
      characters: {
        hero: { name: 'Hero', description: 'Main character' },
        villain: { name: 'Villain', description: 'Antagonist' }
      },
      nodes: [
        { id: 'node1', title: 'Beginning', text: 'Once upon a time', score: 0.9 },
        { id: 'node2', title: 'Middle', text: 'Plot development', score: 0.8 }
      ],
      edges: [
        { from: 'node1', to: 'node2', relationship: 'leads_to' }
      ]
    };

    mockFetch.mockResolvedValue({
      ok: true,
      json: async () => mockGraphData
    });

    render(<GraphView sessionId={mockSessionId} />);

    await waitFor(() => {
      expect(screen.getByText('Knowledge Graph')).toBeInTheDocument();
    });

    expect(screen.getByText(mockSessionId)).toBeInTheDocument();
    expect(screen.getByText('Test Story')).toBeInTheDocument();
    expect(screen.getByText(/story begins/i)).toBeInTheDocument();
    expect(screen.getByText(/plot develops/i)).toBeInTheDocument();
    expect(screen.getByText('hero')).toBeInTheDocument();
    expect(screen.getByText('villain')).toBeInTheDocument();
  });

  it('handles refresh functionality', async () => {
    const mockGraphData = {
      session_id: mockSessionId,
      topic: 'Test Story',
      events: []
    };

    mockFetch.mockResolvedValue({
      ok: true,
      json: async () => mockGraphData
    });

    render(<GraphView sessionId={mockSessionId} />);

    await waitFor(() => {
      expect(screen.getByText('Knowledge Graph')).toBeInTheDocument();
    });

    // Find and click refresh button
    const refreshButton = screen.getByRole('button');
    fireEvent.click(refreshButton);

    // Verify fetch was called again
    expect(mockFetch).toHaveBeenCalledTimes(2);
  });

  it('calls correct API endpoint with session ID', async () => {
    mockFetch.mockResolvedValue({
      ok: true,
      json: async () => ({ session_id: mockSessionId })
    });

    render(<GraphView sessionId={mockSessionId} />);

    await waitFor(() => {
      expect(mockFetch).toHaveBeenCalledWith(
        `/api/session/${mockSessionId}/snapshot`,
        { credentials: 'include' }
      );
    });
  });

  it('handles non-ok response status', async () => {
    mockFetch.mockResolvedValue({
      ok: false,
      status: 404
    });

    render(<GraphView sessionId={mockSessionId} />);

    await waitFor(() => {
      expect(screen.getByText(/error loading graph/i)).toBeInTheDocument();
    });
  });

  it('shows empty state when no graph data', async () => {
    mockFetch.mockResolvedValue({
      ok: true,
      json: async () => null
    });

    render(<GraphView sessionId={mockSessionId} />);

    await waitFor(() => {
      expect(screen.getByText(/no graph data available/i)).toBeInTheDocument();
    });
    
    expect(screen.getByText(/start a session to see your knowledge graph/i)).toBeInTheDocument();
  });

  it('does not fetch when sessionId is not provided', () => {
    render(<GraphView sessionId={null} />);
    
    expect(mockFetch).not.toHaveBeenCalled();
  });
});
