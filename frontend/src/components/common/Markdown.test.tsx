import { render, screen } from '@testing-library/react';
import { Markdown } from './Markdown';

describe('Markdown', () => {
  it('rewrites relative image paths to /api/files', () => {
    const { container } = render(<Markdown content="![](images/example.jpg)" />);
    const img = container.querySelector('img');
    expect(img).not.toBeNull();
    expect(img).toHaveAttribute('src', expect.stringContaining('/api/files?'));
    expect(img).toHaveAttribute(
      'src',
      expect.stringContaining('path=images%2Fexample.jpg')
    );
  });

  it('keeps https image URLs unchanged', () => {
    const { container } = render(<Markdown content="![](https://example.com/example.jpg)" />);
    const img = container.querySelector('img');
    expect(img).not.toBeNull();
    expect(img).toHaveAttribute(
      'src',
      expect.stringContaining('https://example.com/example.jpg')
    );
  });

  it('blocks javascript: URLs', () => {
    render(<Markdown content="![](javascript:alert(1))" />);
    expect(screen.queryByRole('img')).toBeNull();
  });
});
