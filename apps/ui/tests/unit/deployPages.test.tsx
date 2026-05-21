import { render, screen } from '@testing-library/react';
import '@testing-library/jest-dom';
import DeployCatalogPage from '../../app/(deploy)/deploy/catalog/page';
import DeployConfigurePage from '../../app/(deploy)/deploy/configure/page';
import DeployPreflightPage from '../../app/(deploy)/deploy/preflight/page';
import DeployTrackPage from '../../app/(deploy)/deploy/track/[id]/page';

/**
 * Pin the deploy-portal page composition order from Epic #1039.
 * Each page must show the preview banner FIRST so users cannot miss
 * "this is a preview path" before any action.
 */

describe('/deploy/catalog (#1028)', () => {
  beforeEach(() => {
    render(<DeployCatalogPage />);
  });

  it('renders the preview banner above the hero', () => {
    expect(screen.getByTestId('deploy-catalog-preview-banner')).toBeInTheDocument();
  });

  it('renders the catalog hero', () => {
    expect(screen.getByTestId('deploy-catalog-hero')).toBeInTheDocument();
  });

  it('renders the agent picker', () => {
    expect(screen.getByTestId('deploy-catalog-picker')).toBeInTheDocument();
  });

  it('lists every domain with the agent fieldset', () => {
    const picker = screen.getByTestId('deploy-catalog-picker');
    for (const k of ['crm', 'ecommerce', 'inventory', 'logistics', 'product-management', 'search', 'truth']) {
      expect(picker.querySelector(`fieldset[data-domain-key="${k}"]`)).toBeInTheDocument();
    }
  });
});

describe('/deploy/configure (#1029)', () => {
  beforeEach(() => {
    render(<DeployConfigurePage />);
  });

  it('renders the preview banner above the hero', () => {
    expect(screen.getByTestId('deploy-configure-preview-banner')).toBeInTheDocument();
  });

  it('renders the configure hero', () => {
    expect(screen.getByTestId('deploy-configure-hero')).toBeInTheDocument();
  });

  it('renders the configure form with the required fields', () => {
    const form = screen.getByTestId('deploy-configure-form');
    expect(form.querySelector('input[name="tenantId"]')).toBeInTheDocument();
    expect(form.querySelector('input[name="subscriptionId"]')).toBeInTheDocument();
    expect(form.querySelector('input[name="resourceGroup"]')).toBeInTheDocument();
    expect(form.querySelector('select[name="location"]')).toBeInTheDocument();
  });

  it('region select includes westeurope, eastus2, brazilsouth', () => {
    const form = screen.getByTestId('deploy-configure-form');
    const opts = Array.from(form.querySelectorAll('select[name="location"] option')).map((o) => o.getAttribute('value'));
    expect(opts).toEqual(expect.arrayContaining(['westeurope', 'eastus2', 'brazilsouth']));
  });
});

describe('/deploy/preflight (#1030)', () => {
  beforeEach(() => {
    render(<DeployPreflightPage />);
  });

  it('renders the preview banner above the hero', () => {
    expect(screen.getByTestId('deploy-preflight-preview-banner')).toBeInTheDocument();
  });

  it('renders the preflight hero', () => {
    expect(screen.getByTestId('deploy-preflight-hero')).toBeInTheDocument();
  });

  it('renders the preflight panel with mock checks', () => {
    expect(screen.getByTestId('deploy-preflight-panel')).toBeInTheDocument();
  });
});

describe('/deploy/track/[id] (#1032)', () => {
  beforeEach(async () => {
    const ui = await DeployTrackPage({ params: Promise.resolve({ id: 'preview' }) });
    render(ui);
  });

  it('renders the preview banner above the hero', () => {
    expect(screen.getByTestId('deploy-track-preview-banner')).toBeInTheDocument();
  });

  it('renders the track hero', () => {
    expect(screen.getByTestId('deploy-track-hero')).toBeInTheDocument();
  });

  it('renders the track panel', () => {
    expect(screen.getByTestId('deploy-track-panel')).toBeInTheDocument();
  });

  it('shows Clean-up-now as the PRIMARY action (Epic #1039 hard rule)', () => {
    const panel = screen.getByTestId('deploy-track-panel');
    expect(panel.querySelector('a[data-track-cleanup]')).toBeInTheDocument();
  });

  it('shows Delete-this-deployment as a secondary action', () => {
    const panel = screen.getByTestId('deploy-track-panel');
    expect(panel.querySelector('a[data-track-delete]')).toBeInTheDocument();
  });

  it('surfaces the 30-day retention window', () => {
    expect(screen.getByText(/30 d \(then purged\)/)).toBeInTheDocument();
  });
});
