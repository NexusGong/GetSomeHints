import React from 'react';
import './SearchBox.css';

interface SearchBoxProps {
  value: string;
  onChange: (value: string) => void;
  onSearch: () => void;
  placeholder?: string;
  disabled?: boolean;
}

export const SearchBox: React.FC<SearchBoxProps> = ({
  value,
  onChange,
  onSearch,
  placeholder = '输入关键词，多个用逗号分隔...',
  disabled = false,
}) => {
  const handleKeyPress = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && (e.ctrlKey || e.metaKey) && !disabled && value.trim()) {
      e.preventDefault();
      onSearch();
    }
  };

  return (
      <textarea
        value={value}
        onChange={(e) => onChange(e.target.value)}
        onKeyDown={handleKeyPress}
        placeholder={placeholder}
        disabled={disabled}
        className="search-box"
        rows={6}
      />
  );
};
