import React, { useState, useEffect, useRef, useCallback } from 'react';

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
      // Use the new graph endpoint instead of snapshot
      const response = await fetch(`${apiBase}/api/session/${sessionId}/graph`, {
        credentials: 'include',
      });
      
      if (!response.ok) {
        throw new Error('Failed to fetch graph data');
      }
      
      const data = await response.json();
      
      // Transform data to expected format
      const transformedData = {
        nodes: data.nodes || [],
        edges: data.edges || [],
        timestamp: data.timestamp
      };
      
      setGraphData(transformedData);
      console.log('📊 Graph data loaded:', transformedData);
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

  // Filter nodes based on search query
  const filteredNodes = graphData?.nodes?.filter(node => 
    !searchQuery || 
    node.title?.toLowerCase().includes(searchQuery.toLowerCase()) ||
    node.text?.toLowerCase().includes(searchQuery.toLowerCase())
  ) || [];

  // Canvas drawing for graph visualization
  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas || !graphData?.nodes || view !== 'graph') return;
    
    const ctx = canvas.getContext('2d');
    const rect = canvas.getBoundingClientRect();
    canvas.width = rect.width;
    canvas.height = rect.height;
    
    // Clear canvas with cyber background
    ctx.fillStyle = '#0a0a0a';
    ctx.fillRect(0, 0, canvas.width, canvas.height);
    
    // Draw cyber grid
    ctx.strokeStyle = 'rgba(249, 115, 22, 0.05)';
    ctx.lineWidth = 1;
    const gridSize = 20;
    
    for (let x = 0; x < canvas.width; x += gridSize) {
      ctx.beginPath();
      ctx.moveTo(x, 0);
      ctx.lineTo(x, canvas.height);
      ctx.stroke();
    }
    
    for (let y = 0; y < canvas.height; y += gridSize) {
      ctx.beginPath();
      ctx.moveTo(0, y);
      ctx.lineTo(canvas.width, y);
      ctx.stroke();
    }

    // Position nodes in a circle with some randomness
    if (graphData.nodes.length > 0) {
      const centerX = canvas.width / 2;
      const centerY = canvas.height / 2;
      const radius = Math.min(canvas.width, canvas.height) / 3;
      
      graphData.nodes.forEach((node, index) => {
        const angle = (index / graphData.nodes.length) * 2 * Math.PI;
        node.x = centerX + Math.cos(angle) * radius + (Math.random() - 0.5) * 50;
        node.y = centerY + Math.sin(angle) * radius + (Math.random() - 0.5) * 50;
      });
    }

    // Draw edges with neon glow
    if (graphData.edges) {
      graphData.edges.forEach(edge => {
        const source = graphData.nodes.find(n => n.id === edge.source);
        const target = graphData.nodes.find(n => n.id === edge.target);
        
        if (source && target) {
          // Glow effect
          ctx.strokeStyle = 'rgba(249, 115, 22, 0.3)';
          ctx.lineWidth = 3;
          ctx.beginPath();
          ctx.moveTo(source.x, source.y);
          ctx.lineTo(target.x, target.y);
          ctx.stroke();
          
          // Main line
          ctx.strokeStyle = 'rgba(249, 115, 22, 0.8)';
          ctx.lineWidth = 1;
          ctx.beginPath();
          ctx.moveTo(source.x, source.y);
          ctx.lineTo(target.x, target.y);
          ctx.stroke();
        }
      });
    }

    // Draw nodes with neon effect
    if (graphData.nodes) {
      graphData.nodes.forEach((node) => {
        // Outer glow
        const gradient = ctx.createRadialGradient(node.x, node.y, 5, node.x, node.y, 20);
        gradient.addColorStop(0, node.id === selectedNode?.id ? 'rgba(249, 115, 22, 0.8)' : 'rgba(249, 115, 22, 0.4)');
        gradient.addColorStop(1, 'rgba(249, 115, 22, 0)');
        ctx.fillStyle = gradient;
        ctx.beginPath();
        ctx.arc(node.x, node.y, 20, 0, 2 * Math.PI);
        ctx.fill();
        
        // Main node
        ctx.fillStyle = node.id === selectedNode?.id ? '#f97316' : '#ea580c';
        ctx.beginPath();
        ctx.arc(node.x, node.y, 8, 0, 2 * Math.PI);
        ctx.fill();
        
        // Node border
        ctx.strokeStyle = '#ffffff';
        ctx.lineWidth = 1;
        ctx.beginPath();
        ctx.arc(node.x, node.y, 8, 0, 2 * Math.PI);
        ctx.stroke();
        
        // Draw node labels with cyber font
        ctx.fillStyle = '#ffffff';
        ctx.font = '12px Orbitron, monospace';
        ctx.textAlign = 'center';
        ctx.shadowColor = 'rgba(249, 115, 22, 0.8)';
        ctx.shadowBlur = 5;
        ctx.fillText(node.title?.substring(0, 10) || node.id, node.x, node.y + 25);
        ctx.shadowBlur = 0;
      });
    }
  }, [view, graphData, selectedNode]);

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
              <span className="cyber-subheading">Nodes:</span>
              <p className="text-neon-orange-400 font-bold text-lg">{graphData.nodes?.length || 0}</p>
            </div>
            <div className="p-3 glass rounded-lg border-cyber">
              <span className="cyber-subheading">Connections:</span>
              <p className="text-neon-orange-400 font-bold text-lg">{graphData.edges?.length || 0}</p>
            </div>
          </div>

          {/* Graph View */}
          {view === 'graph' && (
            <div className="glass rounded-xl p-4 border-cyber">
              <canvas
                ref={canvasRef}
                className="w-full h-80 rounded-lg cursor-crosshair"
                onClick={(e) => {
                  const rect = e.target.getBoundingClientRect();
                  const x = e.clientX - rect.left;
                  const y = e.clientY - rect.top;
                  
                  // Find clicked node
                  const clickedNode = graphData.nodes?.find(node => {
                    const distance = Math.sqrt((node.x - x) ** 2 + (node.y - y) ** 2);
                    return distance <= 10;
                  });
                  
                  setSelectedNode(clickedNode || null);
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
                <div><span className="cyber-subheading">Type:</span> <span className="text-white capitalize">{selectedNode.type}</span></div>
                <div><span className="cyber-subheading">Title:</span> <span className="text-white">{selectedNode.title}</span></div>
                {selectedNode.text && <div><span className="cyber-subheading">Content:</span> <span className="text-white">{selectedNode.text}</span></div>}
                {selectedNode.actor && <div><span className="cyber-subheading">Actor:</span> <span className="text-white">{selectedNode.actor}</span></div>}
                {selectedNode.confidence && <div><span className="cyber-subheading">Confidence:</span> <span className="text-neon-orange-400 font-bold">{Math.round(selectedNode.confidence * 100)}%</span></div>}
              </div>
              
              {/* Action Buttons */}
              <div className="flex flex-wrap gap-2 mt-6">
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
                      <div className={`w-2 h-2 ${node.type === 'character' ? 'bg-blue-500' : 'bg-neon-orange-500'} rounded-full mr-2 animate-pulse`}></div>
                      {node.title || node.id}
                    </p>
                    <p className="text-xs text-cyber-gray-300 mb-3 leading-relaxed">{node.text?.substring(0, 100)}...</p>
                    {node.confidence && (
                      <div className="mt-3">
                        <div className="w-full bg-cyber-gray-600/30 rounded-full h-2">
                          <div
                            className="bg-gradient-to-r from-neon-orange-500 to-neon-orange-400 h-2 rounded-full transition-all duration-500"
                            style={{ width: `${node.confidence * 100}%` }}
                          ></div>
                        </div>
                        <span className="text-xs cyber-subheading mt-1 block">
                          Confidence: {Math.round(node.confidence * 100)}%
                        </span>
                      </div>
                    )}
                  </div>
                ))}
              </div>
            </div>
          )}
          
          {/* Overview */}
          {view === 'overview' && filteredNodes.length > 0 && (
            <div>
              <h4 className="cyber-subheading mb-4 flex items-center">
                <svg className="w-5 h-5 mr-2 animate-pulse" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 10V3L4 14h7v7l9-11h-7z" />
                </svg>
                Recent Nodes
              </h4>
              <div className="space-y-3">
                {filteredNodes.slice(-5).map((node) => (
                  <div key={node.id} className="glass rounded-xl p-4 border-cyber cursor-pointer hover:neon-glow" onClick={() => setSelectedNode(node)}>
                    <p className="text-sm text-white mb-2 flex items-center">
                      <span className={`px-2 py-1 rounded text-xs mr-2 ${node.type === 'character' ? 'bg-blue-500/20' : 'bg-orange-500/20'}`}>{node.type}</span>
                      {node.title || node.id}
                    </p>
                    {node.confidence && (
                      <div className="mt-2">
                        <div className="w-full bg-cyber-gray-600/30 rounded-full h-2">
                          <div
                            className="bg-gradient-to-r from-blue-500 to-blue-400 h-2 rounded-full transition-all duration-500"
                            style={{ width: `${node.confidence * 100}%` }}
                          ></div>
                        </div>
                        <span className="text-xs cyber-subheading mt-1 block">
                          Confidence: {Math.round(node.confidence * 100)}%
                        </span>
                      </div>
                    )}
                  </div>
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
