import { resolvePersona, isPersona } from '@/lib/persona/types';

describe('lib/persona/types', () => {
  describe('isPersona', () => {
    it.each([
      ['retailer', true],
      ['builder', true],
      ['deploy', false],
      ['', false],
      [undefined, false],
      [null, false],
      ['Retailer', false],
      [' retailer', false],
    ])('isPersona(%j) === %j', (input, expected) => {
      expect(isPersona(input)).toBe(expected);
    });
  });

  describe('resolvePersona — query param wins for sharable links', () => {
    it('returns query value when query is a valid persona', () => {
      expect(resolvePersona('builder', 'retailer')).toBe('retailer');
    });

    it('returns cookie value when query is missing', () => {
      expect(resolvePersona('retailer', undefined)).toBe('retailer');
    });

    it('returns cookie value when query is invalid', () => {
      expect(resolvePersona('builder', 'unknown')).toBe('builder');
    });

    it('returns null when both are missing', () => {
      expect(resolvePersona(undefined, undefined)).toBeNull();
    });

    it('returns null when both are invalid', () => {
      expect(resolvePersona('weasel', 'penguin')).toBeNull();
    });

    it('returns query value even when cookie is invalid', () => {
      expect(resolvePersona('weasel', 'builder')).toBe('builder');
    });
  });
});
