import ReactMarkdown, { type Components } from "react-markdown";
import remarkGfm from "remark-gfm";
import { cn } from "@/lib/utils";

interface MarkdownContentProps {
  children: string;
  className?: string;
}

const components: Components = {
  h1: ({ children }) => <h1 className="text-xl font-bold">{children}</h1>,
  h2: ({ children }) => <h2 className="text-lg font-semibold">{children}</h2>,
  h3: ({ children }) => <h3 className="text-base font-semibold">{children}</h3>,
  h4: ({ children }) => <h4 className="font-semibold">{children}</h4>,
  h5: ({ children }) => <h5 className="font-semibold">{children}</h5>,
  h6: ({ children }) => <h6 className="font-semibold">{children}</h6>,
  p: ({ children }) => <p className="whitespace-pre-line">{children}</p>,
  ul: ({ children }) => <ul className="list-disc space-y-1 pl-6">{children}</ul>,
  ol: ({ children, start }) => <ol start={start} className="list-decimal space-y-1 pl-6">{children}</ol>,
  li: ({ children }) => <li className="[&>p]:my-1 [&>ul]:mt-1 [&>ol]:mt-1">{children}</li>,
  blockquote: ({ children }) => <blockquote className="border-l-4 border-primary/40 pl-4 text-muted-foreground [&>p+p]:mt-2">{children}</blockquote>,
  a: ({ children, href, title }) => href ? <a href={href} title={title} target="_blank" rel="noopener noreferrer" className="text-primary underline underline-offset-2">{children}</a> : <span>{children}</span>,
  code: ({ children, className }) => <code className={cn("rounded bg-muted px-1 py-0.5 font-mono text-xs", className)}>{children}</code>,
  pre: ({ children }) => <pre className="overflow-x-auto rounded-lg bg-muted p-3 [&>code]:block [&>code]:bg-transparent [&>code]:p-0">{children}</pre>,
  table: ({ children }) => <div className="max-w-full overflow-x-auto"><table className="w-full border-collapse text-sm">{children}</table></div>,
  th: ({ children, style }) => <th style={style} className="border bg-muted px-3 py-2 font-semibold">{children}</th>,
  td: ({ children, style }) => <td style={style} className="border px-3 py-2">{children}</td>,
  img: ({ src, alt, title }) => src ? <img src={src} alt={alt ?? ""} title={title} loading="lazy" decoding="async" referrerPolicy="no-referrer" className="max-h-96 max-w-full rounded-lg object-contain" /> : null,
  hr: () => <hr className="border-border" />,
};

export function MarkdownContent({ children, className }: MarkdownContentProps) {
  return <div className={cn("min-w-0 space-y-3 break-words text-sm leading-relaxed", className)}>
    <ReactMarkdown remarkPlugins={[remarkGfm]} skipHtml components={components}>
      {children}
    </ReactMarkdown>
  </div>;
}
