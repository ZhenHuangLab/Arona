import ReactMarkdown, { type Components } from 'react-markdown';
import remarkBreaks from 'remark-breaks';
import remarkGfm from 'remark-gfm';
import remarkMath from 'remark-math';
import rehypeKatex from 'rehype-katex';
import { cn } from '@/lib/utils';

export interface MarkdownProps {
  content: string;
  className?: string;
}

const IMAGE_EXTENSIONS = [
  '.jpg',
  '.jpeg',
  '.png',
  '.gif',
  '.webp',
  '.bmp',
  '.tif',
  '.tiff',
] as const;

function hasImageExtension(url: string): boolean {
  const clean = url.split(/[?#]/)[0]?.toLowerCase() ?? '';
  return IMAGE_EXTENSIONS.some((ext) => clean.endsWith(ext));
}

function shouldRewriteToFilesEndpoint(src: string): boolean {
  const trimmed = src.trim();
  if (!trimmed) return false;
  const lower = trimmed.toLowerCase();

  // Already an API URL or an external URL.
  if (lower.startsWith('/api/')) return false;
  if (lower.startsWith('http://') || lower.startsWith('https://')) return false;
  if (lower.startsWith('data:image/')) return false;
  if (lower.startsWith('blob:')) return false;

  // Only rewrite likely-image paths.
  return hasImageExtension(trimmed);
}

function toFilesEndpointUrl(src: string): string {
  const trimmed = src.trim();
  const params = new URLSearchParams({ path: trimmed });
  return `/api/files?${params.toString()}`;
}

function normalizeHtmlImgTags(content: string): string {
  // Best-effort conversion of raw HTML <img> tags into Markdown image syntax.
  // We skip fenced code blocks to avoid breaking examples.
  const lines = content.split(/\r?\n/);
  let inFence = false;
  let fenceToken: '```' | '~~~' | null = null;

  const extractAttr = (tag: string, name: string): string | null => {
    const re = new RegExp(
      `${name}\\s*=\\s*("([^"]*)"|'([^']*)'|([^\\s>]+))`,
      'i'
    );
    const m = tag.match(re);
    return (m?.[2] ?? m?.[3] ?? m?.[4] ?? '').trim() || null;
  };

  const convertImgTags = (text: string): string => {
    return text.replace(/<img\b[^>]*>/gi, (tag) => {
      const src = extractAttr(tag, 'src');
      if (!src) return tag;
      const alt = extractAttr(tag, 'alt') ?? '';
      // Escape ']' in alt to avoid breaking Markdown.
      const safeAlt = alt.replace(/]/g, '\\]');
      return `![${safeAlt}](${src})`;
    });
  };

  for (let i = 0; i < lines.length; i += 1) {
    const trimmed = lines[i].trimStart();
    const fenceMatch = trimmed.match(/^(```|~~~)/);
    if (fenceMatch) {
      const token = fenceMatch[1] as '```' | '~~~';
      if (!inFence) {
        inFence = true;
        fenceToken = token;
      } else if (fenceToken === token) {
        inFence = false;
        fenceToken = null;
      }
      continue;
    }

    if (!inFence) {
      lines[i] = convertImgTags(lines[i]);
    }
  }

  return lines.join('\n');
}

function sanitizeUrl(url: string, context: 'image' | 'link'): string {
  const trimmed = url.trim();
  if (!trimmed) return '';

  const lower = trimmed.toLowerCase();

  // Block obvious XSS vectors.
  if (lower.startsWith('javascript:') || lower.startsWith('vbscript:')) return '';

  // For links, don't allow arbitrary data: URLs.
  if (context === 'link' && lower.startsWith('data:')) return '';

  // For images, only allow data:image/*.
  if (context === 'image' && lower.startsWith('data:') && !lower.startsWith('data:image/')) {
    return '';
  }

  return trimmed;
}

/**
 * Safe Markdown renderer.
 *
 * - Uses `react-markdown` (no raw HTML by default) to avoid XSS.
 * - Enables GFM (tables, strikethrough, task lists) and soft line breaks.
 */
export function Markdown({ content, className }: MarkdownProps) {
  const normalized = normalizeHtmlImgTags(content);

  const components: Components = {
    img: ({ src, alt, className: imgClassName, ...props }) => {
      const safeSrc = sanitizeUrl(src ?? '', 'image');
      if (!safeSrc) return null;

      const finalSrc = shouldRewriteToFilesEndpoint(safeSrc)
        ? toFilesEndpointUrl(safeSrc)
        : safeSrc;

      return (
        <img
          {...props}
          src={finalSrc}
          alt={alt ?? ''}
          loading="lazy"
          decoding="async"
          className={cn('max-w-full h-auto rounded-md border border-border/50', imgClassName)}
        />
      );
    },
    a: ({ href, ...props }) => {
      const safeHref = sanitizeUrl(href ?? '', 'link');
      if (!safeHref) return <span {...props} />;

      const isExternal =
        safeHref.startsWith('http://') || safeHref.startsWith('https://');

      return (
        <a
          {...props}
          href={safeHref}
          target={isExternal ? '_blank' : undefined}
          rel={isExternal ? 'noreferrer' : undefined}
        />
      );
    },
  };

  return (
    <div className={cn('markdown', className)}>
      <ReactMarkdown
        remarkPlugins={[remarkGfm, remarkBreaks, remarkMath]}
        rehypePlugins={[rehypeKatex]}
        components={components}
      >
        {normalized}
      </ReactMarkdown>
    </div>
  );
}
