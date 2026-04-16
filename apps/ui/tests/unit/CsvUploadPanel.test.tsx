import React from 'react';
import { render, screen, fireEvent } from '@testing-library/react';
import { CsvUploadPanel } from '../../components/enrichment/CsvUploadPanel';

// Mock Card to a simple wrapper so tests focus on CsvUploadPanel logic
jest.mock('@/components/molecules/Card', () => ({
  Card: ({ children, className }: { children: React.ReactNode; className?: string }) =>
    React.createElement('div', { 'data-testid': 'card', className }, children),
}));

describe('CsvUploadPanel', () => {
  it('renders collapsed by default', () => {
    render(<CsvUploadPanel />);
    expect(screen.getByRole('button', { name: /demo: upload products/i })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /demo: upload products/i })).toHaveAttribute('aria-expanded', 'false');
    expect(screen.queryByLabelText(/select csv file/i)).not.toBeInTheDocument();
  });

  it('expands on click', () => {
    render(<CsvUploadPanel />);
    const toggle = screen.getByRole('button', { name: /demo: upload products/i });
    fireEvent.click(toggle);
    expect(toggle).toHaveAttribute('aria-expanded', 'true');
    expect(screen.getByLabelText(/select csv file/i)).toBeInTheDocument();
  });

  it('file input accepts only .csv', () => {
    render(<CsvUploadPanel />);
    fireEvent.click(screen.getByRole('button', { name: /demo: upload products/i }));
    const input = screen.getByLabelText(/select csv file/i) as HTMLInputElement;
    expect(input.accept).toBe('.csv');
  });

  it('upload button is disabled when no file selected', () => {
    render(<CsvUploadPanel />);
    fireEvent.click(screen.getByRole('button', { name: /demo: upload products/i }));
    const uploadBtn = screen.getByRole('button', { name: /upload & trigger pipeline/i });
    expect(uploadBtn).toBeDisabled();
  });

  it('upload button is enabled when file selected', () => {
    render(<CsvUploadPanel />);
    fireEvent.click(screen.getByRole('button', { name: /demo: upload products/i }));
    const input = screen.getByLabelText(/select csv file/i);
    const file = new File(['sku,title\nSKU1,Product 1'], 'products.csv', { type: 'text/csv' });
    fireEvent.change(input, { target: { files: [file] } });
    const uploadBtn = screen.getByRole('button', { name: /upload & trigger pipeline/i });
    expect(uploadBtn).toBeEnabled();
  });

  it('shows file name and size after selection', () => {
    render(<CsvUploadPanel />);
    fireEvent.click(screen.getByRole('button', { name: /demo: upload products/i }));
    const input = screen.getByLabelText(/select csv file/i);
    const content = 'sku,title\nSKU1,Product 1';
    const file = new File([content], 'products.csv', { type: 'text/csv' });
    fireEvent.change(input, { target: { files: [file] } });
    expect(screen.getByText('products.csv')).toBeInTheDocument();
    expect(screen.getByText(/KB/)).toBeInTheDocument();
  });
});
