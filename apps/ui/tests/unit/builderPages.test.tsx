import { render, screen } from '@testing-library/react';
import '@testing-library/jest-dom';
import BuilderArchitecturePage from '../../app/(builder)/builders/architecture/page';
import BuilderAdrsPage from '../../app/(builder)/builders/adrs/page';
import BuilderPatternsPage from '../../app/(builder)/builders/patterns/page';
import BuilderTelemetryPage from '../../app/(builder)/builders/telemetry/page';
import EnablementIndexPage from '../../app/(builder)/builders/enablement/page';

describe('/builders/architecture (#1047)', () => {
  beforeEach(() => render(<BuilderArchitecturePage />));

  it('renders the architecture hero', () => {
    expect(screen.getByTestId('builder-architecture-hero')).toBeInTheDocument();
  });

  it('renders the architecture registry table', () => {
    expect(screen.getByTestId('builder-architecture-table')).toBeInTheDocument();
  });
});

describe('/builders/adrs (#1048)', () => {
  beforeEach(() => render(<BuilderAdrsPage />));

  it('renders the ADRs hero', () => {
    expect(screen.getByTestId('builder-adrs-hero')).toBeInTheDocument();
  });

  it('renders the ADR registry table', () => {
    expect(screen.getByTestId('builder-adrs-table')).toBeInTheDocument();
  });
});

describe('/builders/patterns (#1049)', () => {
  beforeEach(() => render(<BuilderPatternsPage />));

  it('renders the patterns hero', () => {
    expect(screen.getByTestId('builder-patterns-hero')).toBeInTheDocument();
  });

  it('renders the locked pattern set', () => {
    const table = screen.getByTestId('builder-patterns-table');
    const expected = [
      'modular-monolith',
      'mcp-only-a2a',
      'agc-canary',
      'three-tier-memory',
      'otel-contract',
      'dual-design-tokens',
    ];
    for (const k of expected) {
      expect(table.querySelector(`[data-row-key="${k}"]`)).toBeInTheDocument();
    }
  });
});

describe('/builders/telemetry (#1050)', () => {
  beforeEach(() => render(<BuilderTelemetryPage />));

  it('renders the telemetry hero', () => {
    expect(screen.getByTestId('builder-telemetry-hero')).toBeInTheDocument();
  });

  it('renders the unmissable demo-data banner', () => {
    const embed = screen.getByTestId('builder-telemetry-embed');
    const banner = embed.querySelector('[data-demo-banner]');
    expect(banner).toBeInTheDocument();
    expect(banner?.textContent).toMatch(/PUBLIC DEMO ONLY/);
    expect(banner?.textContent).toMatch(/Latency to truth/);
  });

  it('renders the placeholder when no workbook URL is configured', () => {
    const embed = screen.getByTestId('builder-telemetry-embed');
    expect(embed.getAttribute('data-has-workbook')).toBe('false');
    expect(embed.querySelector('[data-placeholder]')).toBeInTheDocument();
  });
});

describe('/builders/enablement (#1051 #1052)', () => {
  beforeEach(() => render(<EnablementIndexPage />));

  it('renders the enablement hero', () => {
    expect(screen.getByTestId('enablement-index-hero')).toBeInTheDocument();
  });

  it('renders the enablement table (empty state allowed when no live assets)', () => {
    expect(screen.getByTestId('enablement-index-table')).toBeInTheDocument();
  });
});
