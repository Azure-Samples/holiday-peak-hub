import React from 'react';
import { render, screen } from '@testing-library/react';

jest.mock('recharts', () => {
  const ReactLib = jest.requireActual<typeof import('react')>('react');

  const passthrough =
    (name: string) =>
    ({
      children,
      tickLine: _tickLine,
      iconType: _iconType,
      wrapperStyle: _wrapperStyle,
      nameKey: _nameKey,
      innerRadius: _innerRadius,
      label: _label,
      verticalAlign: _verticalAlign,
      ...props
    }: {
      children?: React.ReactNode;
      tickLine?: unknown;
      iconType?: unknown;
      wrapperStyle?: unknown;
      nameKey?: unknown;
      innerRadius?: unknown;
      label?: unknown;
      verticalAlign?: unknown;
    }) => ReactLib.createElement('div', { 'data-testid': name, ...props }, children);

  return {
    ResponsiveContainer: passthrough('ResponsiveContainer'),
    LineChart: passthrough('LineChart'),
    BarChart: passthrough('BarChart'),
    AreaChart: passthrough('AreaChart'),
    PieChart: passthrough('PieChart'),
    Line: passthrough('Line'),
    Bar: passthrough('Bar'),
    Area: passthrough('Area'),
    Pie: passthrough('Pie'),
    Cell: passthrough('Cell'),
    XAxis: passthrough('XAxis'),
    YAxis: passthrough('YAxis'),
    CartesianGrid: passthrough('CartesianGrid'),
    Tooltip: passthrough('Tooltip'),
    Legend: passthrough('Legend'),
  };
});

import { Chart } from '../../components/atoms/Chart';

describe('Chart', () => {
  it('renders cartesian chart series', () => {
    render(
      <Chart
        type="line"
        data={[{ name: 'Jan', value: 10 }]}
        series={[{ dataKey: 'value', color: '#0ea5e9' }]}
      />,
    );

    expect(screen.getByTestId('LineChart')).toBeInTheDocument();
    expect(screen.getByTestId('Line')).toBeInTheDocument();
  });

  it('renders donut chart', () => {
    render(
      <Chart
        type="donut"
        data={[{ name: 'A', value: 40 }]}
        series={[{ dataKey: 'value', color: '#22c55e' }]}
        innerRadius={55}
      />,
    );

    expect(screen.getByTestId('PieChart')).toBeInTheDocument();
    expect(screen.getByTestId('Pie')).toBeInTheDocument();
  });
});
