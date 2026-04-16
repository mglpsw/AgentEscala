import { render, screen } from '@testing-library/react';
import { describe, it, expect } from 'vitest';
import App from '../src/app.jsx';


describe('App', () => {
  it('renderiza sem crashar', () => {
    render(<App />);
    // Espera encontrar algum texto padrão do app
    expect(screen.getByText(/escala|login|bem-vindo/i)).toBeDefined();
  });
});
