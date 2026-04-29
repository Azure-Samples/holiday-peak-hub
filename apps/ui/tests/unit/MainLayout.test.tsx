import React from 'react';
import { fireEvent, render, screen } from '@testing-library/react';
import { MainLayout } from '../../components/templates/MainLayout';

const push = jest.fn();

jest.mock('next/navigation', () => ({
  useRouter: () => ({
    push,
  }),
}));

jest.mock('../../components/organisms/Navigation', () => ({
  Navigation: ({ onSearch }: { onSearch?: (query: string) => void }) => (
    <div>
      <input
        aria-label="Search products"
        placeholder="Search products..."
        onKeyDown={(event) => {
          if (event.key === 'Enter') {
            onSearch?.((event.target as HTMLInputElement).value);
          }
        }}
      />
    </div>
  ),
}));

describe('MainLayout', () => {
  beforeEach(() => {
    push.mockClear();
  });

  it('routes search queries to /search', () => {
    render(
      <MainLayout>
        <div>Content</div>
      </MainLayout>
    );

    const input = screen.getByPlaceholderText('Search products...');
    fireEvent.change(input, { target: { value: 'boots' } });
    fireEvent.keyDown(input, { key: 'Enter', code: 'Enter' });

    expect(push).toHaveBeenCalledWith('/search?q=boots');
  });

  it('routes empty searches to the search page', () => {
    render(
      <MainLayout>
        <div>Content</div>
      </MainLayout>
    );

    const input = screen.getByPlaceholderText('Search products...');
    fireEvent.change(input, { target: { value: '   ' } });
    fireEvent.keyDown(input, { key: 'Enter', code: 'Enter' });

    expect(push).toHaveBeenCalledWith('/search');
  });
});
