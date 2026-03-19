import React from 'react';
import { render, screen } from '@testing-library/react';
import { AgentHealthCard } from '../../components/admin/AgentHealthCard';
import { TraceTimeline } from '../../components/admin/TraceTimeline';
import { TraceWaterfall } from '../../components/admin/TraceWaterfall';
import { ModelUsageTable } from '../../components/admin/ModelUsageTable';
import { EvaluationTrendChart } from '../../components/admin/EvaluationTrendChart';
import { EvaluationComparisonTable } from '../../components/admin/EvaluationComparisonTable';

describe('agent activity components', () => {
  it('renders agent health card metrics', () => {
    render(
      <AgentHealthCard
        metric={{
          id: 'a1',
          label: 'Search Agent',
          status: 'healthy',
          latency_ms: 95,
          error_rate: 0.012,
          throughput_rpm: 23,
          updated_at: '2026-03-19T11:30:00Z',
        }}
      />
    );

    expect(screen.getByText('Search Agent')).toBeInTheDocument();
    expect(screen.getByLabelText('Search Agent status healthy')).toBeInTheDocument();
    expect(screen.getByText('95 ms')).toBeInTheDocument();
  });

  it('renders trace timeline and waterfall spans', () => {
    const spans = [
      {
        span_id: 'root',
        parent_span_id: null,
        name: 'root span',
        service: 'search-agent',
        status: 'ok' as const,
        started_at: '2026-03-19T11:00:00Z',
        ended_at: '2026-03-19T11:00:00.200Z',
        duration_ms: 200,
      },
      {
        span_id: 'child',
        parent_span_id: 'root',
        name: 'child span',
        service: 'llm-agent',
        status: 'warning' as const,
        started_at: '2026-03-19T11:00:00.050Z',
        ended_at: '2026-03-19T11:00:00.180Z',
        duration_ms: 130,
      },
    ];

    const { rerender } = render(<TraceTimeline spans={spans} />);
    expect(screen.getByText('root span')).toBeInTheDocument();
    expect(screen.getByText('child span')).toBeInTheDocument();

    rerender(<TraceWaterfall spans={spans} />);
    expect(screen.getByLabelText('Trace timing waterfall')).toBeInTheDocument();
  });

  it('renders model usage table with SLM vs LLM split', () => {
    render(
      <ModelUsageTable
        rows={[
          {
            model_name: 'mini-fast',
            model_tier: 'slm',
            requests: 100,
            input_tokens: 1000,
            output_tokens: 500,
            total_tokens: 1500,
            avg_latency_ms: 70,
            cost_usd: 1.2,
          },
          {
            model_name: 'pro-rich',
            model_tier: 'llm',
            requests: 40,
            input_tokens: 2000,
            output_tokens: 1200,
            total_tokens: 3200,
            avg_latency_ms: 220,
            cost_usd: 7.8,
          },
        ]}
      />
    );

    expect(screen.getByText('mini-fast')).toBeInTheDocument();
    expect(screen.getByText('slm')).toBeInTheDocument();
    expect(screen.getByText('llm')).toBeInTheDocument();
  });

  it('renders evaluation trend empty-state and comparison rows', () => {
    const { rerender } = render(<EvaluationTrendChart trends={[]} />);
    expect(screen.getByText('No evaluation trend data available.')).toBeInTheDocument();

    rerender(
      <EvaluationComparisonTable
        rows={[
          {
            model_name: 'mini-fast',
            model_tier: 'slm',
            dataset: 'retrieval-v1',
            score: 0.91,
            pass_rate: 0.97,
            avg_latency_ms: 80,
            cost_per_1k_tokens: 0.01,
          },
        ]}
      />
    );

    expect(screen.getByText('retrieval-v1')).toBeInTheDocument();
    expect(screen.getByText('0.910')).toBeInTheDocument();
  });
});
