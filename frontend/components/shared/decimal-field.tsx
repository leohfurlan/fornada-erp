"use client";

import { useState, type InputHTMLAttributes } from 'react';

export function DecimalField({ value, places = 3, ...props }: Omit<InputHTMLAttributes<HTMLInputElement>, 'value'> & {value: string; places?: number}) {
  const [focused, setFocused] = useState(false);
  const number = Number(value.replace(',', '.'));
  const display = value && Number.isFinite(number)
    ? new Intl.NumberFormat('pt-BR', {useGrouping: false, maximumFractionDigits: places}).format(number)
    : value;
  return <input {...props} value={focused ? value.replace('.', ',') : display}
    onFocus={event => {setFocused(true); props.onFocus?.(event);}}
    onBlur={event => {setFocused(false); props.onBlur?.(event);}} />;
}
