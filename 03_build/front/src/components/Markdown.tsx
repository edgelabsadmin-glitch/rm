/*
 * Lightweight markdown renderer for chat/assistant messages — no dependency.
 * Handles the subset LLMs actually emit: **bold** / __bold__, `code`, "- "/"* "
 * bullet lists, "#/##/###" headings, and paragraph/line breaks. Everything is a
 * React text node (auto-escaped) — never dangerouslySetInnerHTML.
 */
import { Fragment, type ReactNode } from "react";
import { cn } from "@/lib/utils";

const INLINE = /(\*\*[^*]+\*\*|__[^_]+__|`[^`]+`)/g;

function renderInline(s: string): ReactNode[] {
  return s.split(INLINE).map((p, i) => {
    if ((p.startsWith("**") && p.endsWith("**")) || (p.startsWith("__") && p.endsWith("__"))) {
      return (
        <strong key={i} className="font-semibold">
          {p.slice(2, -2)}
        </strong>
      );
    }
    if (p.startsWith("`") && p.endsWith("`") && p.length > 2) {
      return (
        <code key={i} className="rounded bg-black/5 px-1 py-0.5 font-mono text-[0.85em]">
          {p.slice(1, -1)}
        </code>
      );
    }
    return <Fragment key={i}>{p}</Fragment>;
  });
}

export function Markdown({ text, className }: { text: string; className?: string }) {
  const lines = text.split("\n");
  const blocks: ReactNode[] = [];
  let bullets: ReactNode[] = [];

  const flushBullets = (key: string) => {
    if (bullets.length) {
      blocks.push(
        <ul key={key} className="my-1 list-disc space-y-1 pl-5">
          {bullets.map((b, i) => (
            <li key={i}>{b}</li>
          ))}
        </ul>,
      );
      bullets = [];
    }
  };

  lines.forEach((line, i) => {
    const bullet = line.match(/^\s*[-*]\s+(.*)$/);
    if (bullet) {
      bullets.push(renderInline(bullet[1]));
      return;
    }
    flushBullets(`ul-${i}`);
    if (line.trim() === "") {
      blocks.push(<div key={`sp-${i}`} className="h-2" />);
      return;
    }
    const heading = line.match(/^\s*#{1,3}\s+(.*)$/);
    if (heading) {
      blocks.push(
        <p key={i} className="font-semibold">
          {renderInline(heading[1])}
        </p>,
      );
      return;
    }
    blocks.push(
      <p key={i} className="break-words">
        {renderInline(line)}
      </p>,
    );
  });
  flushBullets("ul-end");

  return <div className={cn("space-y-1", className)}>{blocks}</div>;
}
