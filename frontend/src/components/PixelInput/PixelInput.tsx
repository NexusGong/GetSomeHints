import React from 'react';
import './PixelInput.css';

interface PixelInputProps {
  value: string;
  onChange: (value: string) => void;
  placeholder?: string;
  disabled?: boolean;
  type?: 'text' | 'password' | 'email' | 'number';
  className?: string;
  onKeyPress?: (e: React.KeyboardEvent) => void;
}

export const PixelInput: React.FC<PixelInputProps> = ({
  value,
  onChange,
  placeholder,
  disabled = false,
  type = 'text',
  className = '',
  onKeyPress,
}) => {
  return (
    <input
      type={type}
      className={`pixel-input ${className}`}
      value={value}
      onChange={(e) => onChange(e.target.value)}
      placeholder={placeholder}
      disabled={disabled}
      onKeyPress={onKeyPress}
    />
  );
};
