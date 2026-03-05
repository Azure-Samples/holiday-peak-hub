import '@testing-library/jest-dom';

const React = require('react');

jest.mock('@/components/atoms/ThemeToggle', () => ({
	ThemeToggle: () => React.createElement('div', { 'data-testid': 'theme-toggle' }),
}));

jest.mock('@/components/atoms/Chart', () => ({
  Chart: () => React.createElement('div', { 'data-testid': 'mock-chart' }),
}));

jest.mock('next/image', () => ({
	__esModule: true,
	default: (props: any) => {
		const { fill, priority, ...rest } = props;
		return React.createElement('img', { alt: props.alt || '', ...rest });
	},
}));

jest.mock('next/link', () => ({
	__esModule: true,
	default: ({ href, children, ...rest }: any) =>
		React.createElement('a', { href, ...rest }, children),
}));
