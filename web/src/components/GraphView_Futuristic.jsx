import React, { useState, useEffect, useRef, useCallback } from 'react';
import CytoscapeComponent from 'react-cytoscapejs';

const GraphView = ({ sessionId }) => {
  const [graphData, setGraphData] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [selectedNode, setSelectedNode] = useState(null);
  const [searchQuery, setSearchQuery] = useState('');
  const [view, setView] = useState('overview'); // 'overview', 'detailed', 'graph'
  const canvasRef = useRef(null);

  const apiBase = process.env.REACT_APP_API_BASE || '';

  const fetchGraphData = useCallback(async () => {
    if (!sessionId) return;
    
    setLoading(true);
    setError(null);
    
    try {
      const response = await fetch(`${apiBase}/api/session/${sessionId}/snapshot`, {
        credentials: 'include',
      });
      
      if (!response.ok) {
        throw new Error('Failed to fetch graph data');
      }
      
      const data = await response.json();
      setGraphData(data);
    } catch (err) {
      console.error('Error fetching graph data:', err);
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }, [apiBase, sessionId]);

  useEffect(() => {
    fetchGraphData();
  }, [sessionId, fetchGraphData]);

  const handleNodeAction = async (action, nodeId) => {
    if (!sessionId || !nodeId) return;
    
    try {
      const response = await fetch(`${apiBase}/api/session/${sessionId}/node/${nodeId}/${action}`, {
        method: 'POST',
        credentials: 'include',
      });
      
      if (response.ok) {
        fetchGraphData(); // Refresh data
      }
    } catch (err) {
      console.error(`Error performing ${action} on node:`, err);
    }
  };

  // Filter nodes based on search query
  const filteredNodes = graphData?.nodes?.filter(node => 
    !searchQuery || 
    node.title?.toLowerCase().includes(searchQuery.toLowerCase()) ||
    node.text?.toLowerCase().includes(searchQuery.toLowerCase())
  ) || [];

  // Cytoscape graph elements and style
  const cyElements = React.useMemo(() => {
    if (!graphData?.nodes || !graphData?.edges) return [];
    const nodes = graphData.nodes.map(node => ({
      data: {
        id: node.id,
        label: node.title || node.id,
        ...node
      }
    }));
    const edges = graphData.edges.map(edge => ({
      data: {
        id: edge.id || `${edge.source}_${edge.target}`,
        source: edge.source,
        target: edge.target,
        ...edge
      }
    }));
    return [...nodes, ...edges];
  }, [graphData]);

  const cyStyle = [
    {
      selector: 'node',
      style: {
        'background-color': '#f97316',
        'label': 'data(label)',
        'color': '#fff',
        'font-size': 12,
        'text-outline-width': 2,
        'text-outline-color': '#0a0a0a',
        'border-width': 2,
        'border-color': '#fff',
        'width': 24,
        'height': 24,
        'text-valign': 'bottom',
        'text-halign': 'center',
        'font-family': 'Orbitron, monospace',
        'text-background-color': '#0a0a0a',
        'text-background-opacity': 0.7,
        'text-background-padding': 2
      }
    },
    {
      selector: 'node:selected',
      style: {
        'background-color': '#ea580c',
        'border-color': '#f97316',
        'border-width': 4
      }
    },
    {
      selector: 'edge',
      style: {
        'width': 2,
        'line-color': '#f97316',
        'target-arrow-color': '#f97316',
        'target-arrow-shape': 'triangle',
        'curve-style': 'bezier',
        'opacity': 0.8
      }
    }
  ];

  if (loading) {
    return (
      <div className="glass-strong rounded-xl p-6 border-cyber">
        <div className="cyber-pulse">
          <div className="h-4 bg-neon-orange-500/20 rounded w-1/4 mb-4 animate-pulse"></div>
          <div className="space-y-3">
            <div className="h-3 bg-cyber-gray-600/30 rounded animate-pulse"></div>
            <div className="h-3 bg-cyber-gray-600/30 rounded w-5/6 animate-pulse"></div>
            <div className="h-3 bg-cyber-gray-600/30 rounded w-4/6 animate-pulse"></div>
          </div>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="glass-strong rounded-xl p-6 border-cyber">
        <div className="text-red-400 text-center">
          <svg className="w-12 h-12 mx-auto mb-4 animate-pulse" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-2.5L13.732 4c-.77-.833-1.732-.833-2.464 0L4.732 18.5c-.77.833.192 2.5 1.732 2.5z" />
          </svg>
          <p className="mb-4">Error loading graph: {error}</p>
          <button
            onClick={fetchGraphData}
            className="cyber-button px-4 py-2 rounded-lg hover:scale-105 transform transition-all duration-300"
          >
            <svg className="w-4 h-4 inline mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
            </svg>
            Retry
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="glass-strong rounded-xl p-6 border-cyber shadow-cyber">
      <div className="flex items-center justify-between mb-6">
        <h3 className="text-lg font-semibold cyber-heading flex items-center">
          <svg className="w-6 h-6 mr-3 animate-spin text-neon-orange-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 10V3L4 14h7v7l9-11h-7z" />
          </svg>
          Knowledge Graph
        </h3>
        <div className="flex items-center space-x-3">
          {/* View Toggle */}
          <select 
            value={view} 
            onChange={(e) => setView(e.target.value)}
            className="cyber-input px-3 py-1 rounded-lg text-sm border-cyber"
          >
            <option value="overview">Overview</option>
            <option value="detailed">Detailed</option>
            <option value="graph">Graph View</option>
          </select>
          
          {/* Refresh Button */}
          <button
            onClick={fetchGraphData}
            className="cyber-button p-2 rounded-lg hover:scale-110 transform transition-all duration-300"
            title="Refresh graph"
          >
            <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
            </svg>
          </button>
        </div>
      </div>

      {/* Search Box */}
      <div className="mb-6">
        <div className="relative">
          <input
            type="text"
            placeholder="Search nodes by title or content..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="w-full cyber-input rounded-xl p-4 pl-12 text-sm transition-all duration-300 focus:neon-glow"
          />
          <svg className="absolute left-4 top-1/2 transform -translate-y-1/2 w-4 h-4 text-neon-orange-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
          </svg>
        </div>
      </div>
      
      {graphData ? (
        <div className="space-y-6">
          {/* Graph Statistics */}
          <div className="grid grid-cols-2 gap-4 text-sm">
            <div className="p-3 glass rounded-lg border-cyber">
              <span className="cyber-subheading">Session ID:</span>
              <p className="text-white truncate font-mono text-xs mt-1">{graphData.session_id || 'N/A'}</p>
            </div>
            <div className="p-3 glass rounded-lg border-cyber">
              <span className="cyber-subheading">Topic:</span>
              <p className="text-white font-semibold">{graphData.topic || 'N/A'}</p>
            </div>
            {graphData.nodes && (
              <div className="p-3 glass rounded-lg border-cyber">
                <span className="cyber-subheading">Nodes:</span>
                <p className="text-neon-orange-400 font-bold text-lg">{graphData.nodes.length}</p>
              </div>
            )}
            {graphData.edges && (
              <div className="p-3 glass rounded-lg border-cyber">
                <span className="cyber-subheading">Connections:</span>
                <p className="text-neon-orange-400 font-bold text-lg">{graphData.edges.length}</p>
              </div>
            )}
          </div>

          {/* Graph View */}
          {view === 'graph' && (
            <div className="glass rounded-xl p-4 border-cyber">
              <CytoscapeComponent
                elements={cyElements}
                style={{ width: '100%', height: '320px', background: '#0a0a0a', borderRadius: '0.75rem', cursor: 'crosshair' }}
                stylesheet={cyStyle}
                layout={{ name: 'cose', animate: true, fit: true, padding: 30 }}
                cy={cy => {
                  cy.on('tap', 'node', (evt) => {
                    const node = evt.target.data();
                    setSelectedNode(node);
                  });
                  cy.on('tap', (evt) => {
                    if (evt.target === cy) setSelectedNode(null);
                  });
                }}
              />
            </div>
          )}

          {/* Selected Node Details */}
          {selectedNode && (
            <div className="glass-strong rounded-xl p-6 border-cyber neon-glow">
              <h4 className="cyber-subheading mb-4 flex items-center">
                <div className="w-3 h-3 bg-neon-orange-500 rounded-full mr-3 animate-pulse"></div>
                Node Details
              </h4>
              <div className="space-y-3 text-sm">
                <div><span className="cyber-subheading">ID:</span> <span className="text-white font-mono">{selectedNode.id}</span></div>
                <div><span className="cyber-subheading">Title:</span> <span className="text-white">{selectedNode.title}</span></div>
                <div><span className="cyber-subheading">Text:</span> <span className="text-white">{selectedNode.text}</span></div>
                <div><span className="cyber-subheading">Score:</span> <span className="text-neon-orange-400 font-bold">{selectedNode.score}</span></div>
                <div><span className="cyber-subheading">Created:</span> <span className="text-white">{selectedNode.created_at}</span></div>
                <div><span className="cyber-subheading">Last Used:</span> <span className="text-white">{selectedNode.last_used_at}</span></div>
              </div>
              
              {/* Action Buttons */}
              <div className="flex flex-wrap gap-2 mt-6">
                <button
                  onClick={() => handleNodeAction('suggest', selectedNode.id)}
                  className="cyber-button px-4 py-2 rounded-lg text-sm hover:scale-105 transform transition-all duration-300"
                >
                  <svg className="w-4 h-4 inline mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 10V3L4 14h7v7l9-11h-7z" />
                  </svg>
                  Suggest
                </button>
                <button
                  onClick={() => handleNodeAction('accept', selectedNode.id)}
                  className="cyber-button px-4 py-2 rounded-lg text-sm hover:scale-105 transform transition-all duration-300 bg-green-600/20 hover:bg-green-600/40 border-green-500/30"
                >
                  <svg className="w-4 h-4 inline mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
                  </svg>
                  Accept
                </button>
                <button
                  onClick={() => handleNodeAction('backtrack', selectedNode.id)}
                  className="cyber-button px-4 py-2 rounded-lg text-sm hover:scale-105 transform transition-all duration-300 bg-yellow-600/20 hover:bg-yellow-600/40 border-yellow-500/30"
                >
                  <svg className="w-4 h-4 inline mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 14l2-2m0 0l2-2m-2 2l-2-2m2 2l2 2M3 12l6.414 6.414a2 2 0 001.414.586H19a2 2 0 002-2V7a2 2 0 00-2-2h-8.172a2 2 0 00-1.414.586L3 12z" />
                  </svg>
                  Backtrack
                </button>
                <button
                  onClick={() => setSelectedNode(null)}
                  className="cyber-button px-4 py-2 rounded-lg text-sm hover:scale-105 transform transition-all duration-300"
                >
                  Close
                </button>
              </div>
            </div>
          )}

          {/* Nodes List */}
          {view === 'detailed' && filteredNodes.length > 0 && (
            <div>
              <h4 className="cyber-subheading mb-4 flex items-center">
                <svg className="w-5 h-5 mr-2 animate-pulse" fill="currentColor" viewBox="0 0 24 24">
                  <path d="M12 2L2 7l10 5 10-5-10-5zM2 17l10 5 10-5M2 12l10 5 10-5"/>
                </svg>
                Nodes {searchQuery && `(filtered: ${filteredNodes.length})`}
              </h4>
              <div className="space-y-3 max-h-64 overflow-y-auto">
                {filteredNodes.map((node) => (
                  <div 
                    key={node.id} 
                    className="glass rounded-xl p-4 border-cyber cursor-pointer hover:neon-glow transition-all duration-300 group"
                    onClick={() => setSelectedNode(node)}
                  >
                    <p className="text-sm text-white font-medium mb-2 flex items-center">
                      <div className="w-2 h-2 bg-neon-orange-500 rounded-full mr-2 animate-pulse"></div>
                      {node.title || node.id}
                    </p>
                    <p className="text-xs text-cyber-gray-300 mb-3 leading-relaxed">{node.text?.substring(0, 100)}...</p>
                    {node.score && (
                      <div className="mt-3">
                        <div className="w-full bg-cyber-gray-600/30 rounded-full h-2">
                          <div
                            className="bg-gradient-to-r from-neon-orange-500 to-neon-orange-400 h-2 rounded-full transition-all duration-500"
                            style={{ width: `${node.score * 100}%` }}
                          ></div>
                        </div>
                        <span className="text-xs cyber-subheading mt-1 block">
                          Relevance: {Math.round(node.score * 100)}%
                        </span>
                      </div>
                    )}
                  </div>
                ))}
              </div>
            </div>
          )}
          
          {/* Events (Overview) */}
          {view === 'overview' && graphData.events && graphData.events.length > 0 && (
            <div>
              <h4 className="cyber-subheading mb-4 flex items-center">
                <svg className="w-5 h-5 mr-2 animate-pulse" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 10V3L4 14h7v7l9-11h-7z" />
                </svg>
                Recent Events
              </h4>
              <div className="space-y-3">
                {graphData.events.slice(-5).map((event, index) => (
                  <div key={index} className="glass rounded-xl p-4 border-cyber">
                    <p className="text-sm text-white mb-2">{event.summary || event.id}</p>
                    {event.confidence && (
                      <div className="mt-2">
                        <div className="w-full bg-cyber-gray-600/30 rounded-full h-2">
                          <div
                            className="bg-gradient-to-r from-blue-500 to-blue-400 h-2 rounded-full transition-all duration-500"
                            style={{ width: `${event.confidence * 100}%` }}
                          ></div>
                        </div>
                        <span className="text-xs cyber-subheading mt-1 block">
                          Confidence: {Math.round(event.confidence * 100)}%
                        </span>
                      </div>
                    )}
                  </div>
                ))}
              </div>
            </div>
          )}
          
          {/* Characters */}
          {graphData.characters && Object.keys(graphData.characters).length > 0 && (
            <div>
              <h4 className="cyber-subheading mb-4 flex items-center">
                <svg className="w-5 h-5 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M17 20h5v-2a3 3 0 00-5.356-1.857M17 20H7m10 0v-2c0-.656-.126-1.283-.356-1.857M7 20H2v-2a3 3 0 015.356-1.857M7 20v-2c0-.656.126-1.283.356-1.857m0 0a5.002 5.002 0 019.288 0M15 7a3 3 0 11-6 0 3 3 0 016 0zm6 3a2 2 0 11-4 0 2 2 0 014 0zM7 10a2 2 0 11-4 0 2 2 0 014 0z" />
                </svg>
                Characters
              </h4>
              <div className="flex flex-wrap gap-2">
                {Object.keys(graphData.characters).map((character) => (
                  <span
                    key={character}
                    className="px-3 py-2 cyber-button rounded-full text-xs cursor-pointer hover:scale-105 transform transition-all duration-300"
                    title={graphData.characters[character]?.description || character}
                  >
                    {character}
                  </span>
                ))}
              </div>
            </div>
          )}
        </div>
      ) : (
        <div className="text-center py-12">
          <svg className="w-16 h-16 mx-auto mb-4 text-cyber-gray-500 animate-pulse" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9.663 17h4.673M12 3v1m6.364 1.636l-.707.707M21 12h-1M4 12H3m3.343-5.657l-.707-.707m2.828 9.9a5 5 0 117.072 0l-.548.547A3.374 3.374 0 0014 18.469V19a2 2 0 11-4 0v-.531c0-.895-.356-1.754-.988-2.386l-.548-.547z" />
          </svg>
          <p className="cyber-subheading">No graph data available</p>
          <p className="text-sm mt-1 text-cyber-gray-400">Start a session to see your knowledge graph</p>
        </div>
      )}
    </div>
  );
};

export default GraphView;
