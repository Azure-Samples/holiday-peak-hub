import React from 'react';
import { render, screen } from '@testing-library/react';
import { DataTable } from '../../components/organisms/DataTable';

type Row = {
  id: string;
  name: string;
  metrics: {
    score: number;
  };
};

describe('DataTable', () => {
  const rows: Row[] = [
    { id: '1', name: 'Alpha', metrics: { score: 85 } },
    { id: '2', name: 'Beta', metrics: { score: 72 } },
  ];

  it('renders loading and empty states', () => {
    const { rerender } = render(<DataTable<Row> loading data={[]} columns={[]} />);
    expect(screen.getByText('Loading...')).toBeInTheDocument();

    rerender(<DataTable<Row> data={[]} columns={[]} emptyMessage="No rows" />);
    expect(screen.getByText('No rows')).toBeInTheDocument();
  });

  it('renders nested accessor values and custom cell renderers', () => {
    render(
      <DataTable<Row>
        data={rows}
        columns={[
          { header: 'Name', accessor: 'name' },
          {
            header: 'Score',
            accessor: 'metrics.score',
            render: (value) => <span>{value}%</span>,
            align: 'right',
          },
        ]}
      />, 
    );

    expect(screen.getByText('Alpha')).toBeInTheDocument();
    expect(screen.getByText('85%')).toBeInTheDocument();
    expect(screen.getByText('72%')).toBeInTheDocument();
  });
});
