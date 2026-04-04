'use client';

import { useState, useEffect } from 'react';
import { MainLayout } from '@/components/templates/MainLayout';
import { AgentWorkflowVisualizer, WorkflowNode, WorkflowEdge, WorkflowGraph, NodeStatus } from '@/components/organisms/AgentWorkflowVisualizer';
import { Button } from '@/components/atoms/Button';
import { Badge } from '@/components/atoms/Badge';

// Initial Mock Graph
const initialNodes: WorkflowNode[] = [
  // Stage 0: Trigger
  { id: 'T1', stage: 0, order: 0, type: 'trigger', label: 'User Chat Input', description: 'User asks for blue tents in stock.', status: 'idle' },
  
  // Stage 1: Initial Processing
  { id: 'O1', stage: 1, order: 0, type: 'orchestrator', label: 'Intent Routing', description: 'Fast SLM determines specialist agents needed.', status: 'idle' },
  
  // Stage 2: Specialist Execution (Parallel)
  { id: 'S1', stage: 2, order: 0, type: 'specialist', label: 'Catalog Agent', description: 'Vector search for "blue tents"', status: 'idle' },
  { id: 'S2', stage: 2, order: 1, type: 'specialist', label: 'Inventory Agent', description: 'Checking stock for SKUs', status: 'idle' },
  { id: 'S3', stage: 2, order: 2, type: 'specialist', label: 'CRM Profile', description: 'Checking loyalty points for user', status: 'idle' },

  // Stage 3: Synthesis
  { id: 'O2', stage: 3, order: 0, type: 'orchestrator', label: 'Response Synthesis', description: 'Rich LLM composing human response.', status: 'idle' },
  
  // Stage 4: Output
  { id: 'A1', stage: 4, order: 0, type: 'action', label: 'Chat Render', description: 'Stream response to UI.', status: 'idle' }
];

const initialEdges: WorkflowEdge[] = [
  { source: 'T1', target: 'O1' },
  { source: 'O1', target: 'S1', label: 'extracts keywords' },
  { source: 'O1', target: 'S2', label: 'requests stock' },
  { source: 'O1', target: 'S3', label: 'profile match' },
  // Edges back to Synthesis
  { source: 'S1', target: 'O2', label: 'results: 3 SKUs' },
  { source: 'S2', target: 'O2', label: 'in_stock: true' },
  { source: 'S3', target: 'O2', label: 'gold_tier' },
  // Edges to output
  { source: 'O2', target: 'A1' }
];

export default function WorkflowsPage() {
  const [graph, setGraph] = useState<WorkflowGraph>({ nodes: initialNodes, edges: initialEdges });
  const [isPlaying, setIsPlaying] = useState(false);
  const [step, setStep] = useState(0);

  // Playback Simulation Effect
  useEffect(() => {
    if (!isPlaying) return;

    const timer = setInterval(() => {
      setStep(s => {
        if (s > 6) {
          setIsPlaying(false);
          return s;
        }
        return s + 1;
      });
    }, 1500); // Step every 1.5s

    return () => clearInterval(timer);
  }, [isPlaying]);

  // Update nodes based on timeline step
  useEffect(() => {
    let nodes = [...initialNodes];
    
    // Simple state machine for simulation
    const setStatus = (id: string, status: NodeStatus, metrics?: WorkflowNode['metrics']) => {
      nodes = nodes.map(n => n.id === id ? { ...n, status, metrics } : n);
    };

    if (step === 0) nodes = [...initialNodes]; // Reset

    if (step >= 1) { setStatus('T1', 'success', { latency: '120ms' }); setStatus('O1', 'running'); }
    if (step >= 2) { setStatus('O1', 'success', { tokens: '250', latency: '400ms' }); setStatus('S1', 'running'); setStatus('S2', 'running'); setStatus('S3', 'running'); }
    if (step >= 3) { setStatus('S1', 'success', { latency: '1.2s', tokens: '0' }); setStatus('S2', 'success', { latency: '800ms' }); setStatus('S3', 'success'); setStatus('O2', 'running'); }
    if (step >= 4) { setStatus('O2', 'success', { latency: '2.5s', tokens: '1050' }); setStatus('A1', 'running'); }
    if (step >= 5) { setStatus('A1', 'success'); }

    setGraph({ nodes, edges: initialEdges });
  }, [step]);

  const handleRestart = () => {
    setStep(0);
    setIsPlaying(true);
  };

  return (
    <MainLayout>
      <div className="space-y-6 max-w-[1400px] mx-auto">
        <header className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between border-b pb-6 border-gray-200 dark:border-gray-800">
          <div>
            <h1 className="text-3xl font-extrabold tracking-tight text-gray-900 dark:text-white">
              Agent Workflow Topology
            </h1>
            <p className="mt-2 text-sm text-gray-500 dark:text-gray-400">
              Interactive visualization of agent-to-agent traces, orchestration routes, and latency paths.
            </p>
          </div>
          <div className="flex gap-3 items-center">
            <Badge variant={isPlaying ? 'info' : 'secondary'}>
              {isPlaying ? 'Simulation Running...' : step > 5 ? 'Trace Complete' : 'Idle'}
            </Badge>
            <Button onClick={handleRestart} disabled={isPlaying}>
              {step > 0 ? '▶ Replay Simulation' : '▶ Start Trace Simulation'}
            </Button>
          </div>
        </header>

        {/* The Graph Canvas */}
        <section className="bg-white dark:bg-gray-900 border border-gray-200 dark:border-gray-800 shadow-sm rounded-xl p-4">
          <AgentWorkflowVisualizer graph={graph} />
        </section>

        {/* Detail Panel aligned below */}
        <section className="grid grid-cols-1 md:grid-cols-3 gap-6">
          <div className="md:col-span-2 bg-white dark:bg-gray-800 rounded-xl p-6 border border-gray-200 dark:border-gray-700 shadow-sm">
            <h2 className="text-lg font-semibold mb-4 dark:text-white">Trace Metadata</h2>
            <div className="font-mono text-xs p-4 bg-gray-50 dark:bg-gray-950 rounded-lg text-gray-700 dark:text-gray-300 break-words whitespace-pre-wrap">
              {JSON.stringify({
                trace_id: 'a8b-19cx-9v11-zpe9',
                session_id: '102-cart-user-454',
                start_time: new Date().toISOString(),
                total_duration: step > 4 ? '5.02s' : '...',
                total_tokens: step > 4 ? 1300 : '...',
                status: step > 4 ? 'success' : isPlaying ? 'streaming' : 'pending'
              }, null, 2)}
            </div>
          </div>
          <div className="bg-blue-50 dark:bg-blue-900/20 text-blue-900 dark:text-blue-100 rounded-xl p-6 border border-blue-100 dark:border-blue-800/50 shadow-sm">
            <h2 className="text-lg font-semibold mb-2">Topology Legend</h2>
            <ul className="space-y-3 text-sm mt-4">
              <li className="flex items-center gap-2"><span className="text-amber-500 w-5">⚡</span> External Trigger / Action</li>
              <li className="flex items-center gap-2"><span className="text-purple-500 w-5">⑂</span> Orchestrator / SLM Router</li>
              <li className="flex items-center gap-2"><span className="text-blue-500 w-5">🤖</span> Specialist Leaf Agent</li>
              <li className="flex gap-2 text-xs opacity-75 mt-8 items-start border-t border-blue-200 dark:border-blue-800 pt-4">
                Nodes running in parallel display pulsing borders and compute bounds asynchronously.
              </li>
            </ul>
          </div>
        </section>

      </div>
    </MainLayout>
  );
}
