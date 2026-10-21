import { fireEvent, render, screen } from '@testing-library/react';
import { expect, it, vi } from 'vitest';
import { DecimalField } from '@/components/shared/decimal-field';

it('formats the display while preserving the exact value for editing', () => {
  const onChange = vi.fn();
  render(<DecimalField aria-label="Quantidade" value="1.23456789" onChange={onChange} />);
  const input = screen.getByLabelText('Quantidade');
  expect(input).toHaveValue('1,235');
  fireEvent.focus(input);
  expect(input).toHaveValue('1,23456789');
  fireEvent.blur(input);
  expect(input).toHaveValue('1,235');
  expect(onChange).not.toHaveBeenCalled();
});

it('removes padding and keeps an empty field empty', () => {
  const view = render(<DecimalField aria-label="Quantidade" value="120.0000" />);
  expect(screen.getByLabelText('Quantidade')).toHaveValue('120');
  view.rerender(<DecimalField aria-label="Quantidade" value="" />);
  expect(screen.getByLabelText('Quantidade')).toHaveValue('');
});
