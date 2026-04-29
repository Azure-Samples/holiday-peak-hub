import { resolveCommerceAgentSlot } from '@/components/templates/CommerceAgentLayout';

describe('resolveCommerceAgentSlot', () => {
  it('preserves an explicit primary position', () => {
    const resolved = resolveCommerceAgentSlot({ agentSlug: 'ecommerce-catalog-search', position: 'bottom-right' }, 'primary');

    expect(resolved.position).toBe('bottom-right');
    expect(resolved.facing).toBe('left');
  });

  it('defaults the primary slot to bottom-left', () => {
    const resolved = resolveCommerceAgentSlot({ agentSlug: 'ecommerce-catalog-search' }, 'primary');

    expect(resolved.position).toBe('bottom-left');
    expect(resolved.facing).toBe('right');
  });

  it('defaults side-cast robots to the right-side stack', () => {
    const resolved = resolveCommerceAgentSlot({ agentSlug: 'search-enrichment-agent' }, 'side-cast');

    expect(resolved.position).toBe('bottom-right');
    expect(resolved.facing).toBe('left');
    expect(resolved.scenePeer).toBe('right');
    expect(resolved.className).toContain('xl:bottom-24');
  });
});