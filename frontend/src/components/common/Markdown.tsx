import ReactMarkdown from 'react-markdown';
import remarkBreaks from 'remark-breaks';
import remarkGfm from 'remark-gfm';
import remarkMath from 'remark-math';
import rehypeKatex from 'rehype-katex';
import { cn } from '@/lib/utils';

export interface MarkdownProps {
  content: string;
  className?: string;
}

/**
 * Safe Markdown renderer.
 *
 * - Uses `react-markdown` (no raw HTML by default) to avoid XSS.
 * - Enables GFM (tables, strikethrough, task lists) and soft line breaks.
 */
export function Markdown({ content, className }: MarkdownProps) {
  return (
    <div className={cn('markdown', className)}>
      <ReactMarkdown
        remarkPlugins={[remarkGfm, remarkBreaks, remarkMath]}
        rehypePlugins={[rehypeKatex]}
      >
        {content}
      </ReactMarkdown>
    </div>
  );
}
