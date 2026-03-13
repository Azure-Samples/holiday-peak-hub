import '@testing-library/jest-dom';

if (!process.env.NEXT_PUBLIC_STRIPE_PUBLISHABLE_KEY) {
	process.env.NEXT_PUBLIC_STRIPE_PUBLISHABLE_KEY = 'pk_test_checkout';
}

if (!(global as any).crypto?.subtle) {
	const { webcrypto } = require('crypto');
	Object.defineProperty(global, 'crypto', {
		value: webcrypto,
		configurable: true,
	});
}

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

if (!window.matchMedia) {
	Object.defineProperty(window, 'matchMedia', {
		writable: true,
		value: (query: string) => ({
			matches: false,
			media: query,
			onchange: null,
			addListener: jest.fn(),
			removeListener: jest.fn(),
			addEventListener: jest.fn(),
			removeEventListener: jest.fn(),
			dispatchEvent: jest.fn(),
		}),
	});
}

jest.mock('@stripe/stripe-js', () => ({
	__esModule: true,
	loadStripe: jest.fn(async () => ({
		confirmPayment: jest.fn(async () => ({ error: null })),
	})),
}), { virtual: true });

jest.mock('@stripe/react-stripe-js', () => ({
	__esModule: true,
	Elements: ({ children }: any) => React.createElement('div', { 'data-testid': 'stripe-elements' }, children),
	PaymentElement: () => React.createElement('div', { 'data-testid': 'payment-element' }),
	useStripe: () => ({
		confirmPayment: jest.fn(async () => ({ error: null })),
	}),
	useElements: () => ({}),
}), { virtual: true });
