import type { ReactNode } from 'react'
import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'

/**
 * Render Markdown (GitHub-flavoured: real tables, lists, bold, code, headings)
 * styled with the Nightfall tokens, RTL-friendly. Used for assistant answers so
 * they read as formatted text/tables instead of raw `## ** | |` syntax.
 */
export function Markdown({ children }: { children: string }) {
  return (
    <div className="wm-md flex flex-col gap-space-sm text-on-surface">
      <ReactMarkdown
        remarkPlugins={[remarkGfm]}
        components={{
          h1: ({ children }) => <h1 className="font-headline-1 text-headline-1 text-primary mt-space-sm">{children}</h1>,
          h2: ({ children }) => <h2 className="font-headline-1 text-headline-1 text-primary mt-space-sm">{children}</h2>,
          h3: ({ children }) => <h3 className="font-headline-2 text-headline-2 text-primary mt-space-xs">{children}</h3>,
          h4: ({ children }) => <h4 className="font-body-medium text-body-medium text-on-surface">{children}</h4>,
          p: ({ children }) => <p className="font-body text-body leading-relaxed">{children}</p>,
          strong: ({ children }) => <strong className="font-body-medium text-on-surface">{children}</strong>,
          em: ({ children }) => <em className="italic">{children}</em>,
          ul: ({ children }) => <ul className="list-disc ps-space-lg flex flex-col gap-space-xs marker:text-outline">{children}</ul>,
          ol: ({ children }) => <ol className="list-decimal ps-space-lg flex flex-col gap-space-xs marker:text-outline">{children}</ol>,
          li: ({ children }) => <li className="font-body text-body leading-relaxed">{children}</li>,
          a: ({ href, children }) => (
            <a href={href} className="text-primary underline underline-offset-2 hover:text-tertiary break-words">{children}</a>
          ),
          blockquote: ({ children }) => (
            <blockquote className="border-s-4 border-surface-container-high ps-space-md text-on-surface-variant">{children}</blockquote>
          ),
          hr: () => <hr className="border-surface-container-high my-space-xs" />,
          code: ({ className, children }: { className?: string; children?: ReactNode }) => {
            const block = (className ?? '').includes('language-')
            if (block) {
              return (
                <pre className="overflow-x-auto rounded-xl bg-surface-container-low p-space-md" dir="ltr">
                  <code className="font-mono-body text-mono-body text-on-surface">{children}</code>
                </pre>
              )
            }
            return <code className="font-mono-body text-mono-body rounded bg-surface-container-low px-1 py-0.5" dir="ltr">{children}</code>
          },
          table: ({ children }) => (
            <div className="overflow-x-auto rounded-xl border border-surface-container-high">
              <table className="w-full border-collapse text-body">{children}</table>
            </div>
          ),
          thead: ({ children }) => <thead className="bg-surface-container">{children}</thead>,
          th: ({ children }) => (
            <th className="border-b border-surface-container-high px-space-md py-space-sm text-start font-body-medium text-primary">{children}</th>
          ),
          td: ({ children }) => (
            <td className="border-b border-surface-container-high px-space-md py-space-sm text-start align-top">{children}</td>
          ),
        }}
      >
        {children}
      </ReactMarkdown>
    </div>
  )
}
