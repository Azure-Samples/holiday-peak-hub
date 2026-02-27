import '@testing-library/jest-dom';

const React = require('react');

jest.mock('@/components/atoms/ThemeToggle', () => ({
	ThemeToggle: () => React.createElement('div', { 'data-testid': 'theme-toggle' }),
}));

jest.mock('next/image', () => ({
	__esModule: true,
	default: (props: any) => React.createElement('img', { alt: props.alt || '', ...props }),
}));

jest.mock('next/link', () => ({
	__esModule: true,
	default: ({ href, children, ...rest }: any) =>
		React.createElement('a', { href, ...rest }, children),
}));
