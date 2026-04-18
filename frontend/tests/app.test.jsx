import { render, screen } from '@testing-library/react';
import { describe, it, expect } from 'vitest';
import App from '../src/app.jsx';


describe('App', () => {
  it('renderiza sem crashar', async () => {
    render(<App />);
    expect(await screen.findByRole('heading', { name: /agentescala/i })).toBeDefined();
  });
});
