import { render, screen } from '@testing-library/react';
import { describe, it, expect } from 'vitest';
import App from '../src/app.jsx';


describe('App', () => {
  it('renderiza sem crashar', () => {
    render(<App />);
    expect(screen.getByRole('heading', { name: /agentescala/i })).toBeDefined();
  });
});
