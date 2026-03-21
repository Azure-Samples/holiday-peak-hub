import React from 'react';
import { fireEvent, render, screen } from '@testing-library/react';
import { Alert } from '../../components/molecules/Alert';
import { Modal } from '../../components/molecules/Modal';
import { Badge } from '../../components/atoms/Badge';
import { Button } from '../../components/atoms/Button';
import { Input } from '../../components/atoms/Input';

describe('atoms and molecules', () => {
  it('renders button loading state and disables interaction', () => {
    const onClick = jest.fn();

    render(
      <Button onClick={onClick} loading>
        Save
      </Button>,
    );

    const button = screen.getByRole('button', { name: 'Save' });
    expect(button).toBeDisabled();

    fireEvent.click(button);
    expect(onClick).not.toHaveBeenCalled();
  });

  it('renders controlled input and dispatches change events', () => {
    const onChange = jest.fn();

    render(
      <Input
        ariaLabel="Search"
        value=""
        onChange={onChange}
        prefix={<span>$</span>}
        suffix={<span>USD</span>}
      />,
    );

    const input = screen.getByLabelText('Search');
    fireEvent.change(input, { target: { value: '19.99' } });

    expect(onChange).toHaveBeenCalledTimes(1);
  });

  it('renders badge variants and supports dot mode', () => {
    const { rerender } = render(<Badge variant="success">ok</Badge>);
    expect(screen.getByText('ok')).toBeInTheDocument();

    rerender(
      <Badge dot ariaLabel="status dot">
        1
      </Badge>,
    );
    expect(screen.getByLabelText('status dot')).toBeInTheDocument();
  });

  it('dismisses alert and calls callback', () => {
    const onDismiss = jest.fn();

    render(
      <Alert title="Heads up" onDismiss={onDismiss}>
        Check this.
      </Alert>,
    );

    fireEvent.click(screen.getByRole('button', { name: 'Dismiss alert' }));
    expect(onDismiss).toHaveBeenCalledTimes(1);
    expect(screen.queryByRole('alert')).not.toBeInTheDocument();
  });

  it('renders modal content and closes from close button', () => {
    const onClose = jest.fn();

    render(
      <Modal isOpen onClose={onClose} title="Edit item">
        <p>Modal content</p>
      </Modal>,
    );

    expect(screen.getByText('Modal content')).toBeInTheDocument();
    fireEvent.click(screen.getByRole('button', { name: 'Close modal' }));
    expect(onClose).toHaveBeenCalledTimes(1);
  });
});
