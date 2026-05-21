/*
 * SPEC-035 — inline-tag voice renderer (Tier-0 §10). TypeScript port of
 * rm-intelligence-agent/src/render_demo.py `tokenize`. The whitelist is EXACT:
 * <num> <bad> <good> <quote> <em>. Anything not on the whitelist is rendered as
 * literal text (React escapes text nodes by default) — we NEVER use
 * dangerouslySetInnerHTML, so stray markup/HTML in agent prose cannot inject.
 *
 *   <num>2 risk-tagged Cases</num> → JetBrains Mono, ink-primary
 *   <bad>vendor-consolidation</bad> → risk-high color
 *   <good>replacement delivered</good> → risk-low color
 *   <quote>"…"</quote> → Inter italic, quote color (slate-700)
 *   <em>EBR is Thursday</em> → Inter italic, ink-primary
 */
import { Fragment, type ReactNode } from "react";

export type InlineTag = "num" | "bad" | "good" | "quote" | "em";

const TAG_CLASS: Record<InlineTag, string> = {
  num: "font-mono text-ink-primary tabular-nums",
  bad: "text-risk-high-fg",
  good: "text-risk-low-fg",
  quote: "italic text-ink-quote",
  em: "italic text-ink-primary",
};

const ALLOWED = new Set<string>(["num", "bad", "good", "quote", "em"]);
// Matches an opening or closing whitelist tag; everything else is literal text.
const TAG_RE = /<(\/?)(num|bad|good|quote|em)>/g;

interface Frame {
  tag: InlineTag | null; // null = root
  children: ReactNode[];
}

/**
 * Parse inline-tag prose into React nodes. Stack-based so balanced tags nest
 * correctly; unbalanced/unknown tags degrade to escaped literal text.
 */
export function renderInlineTags(text: string | null | undefined): ReactNode[] {
  if (!text) return [];
  const root: Frame = { tag: null, children: [] };
  const stack: Frame[] = [root];
  const top = () => stack[stack.length - 1];

  let pos = 0;
  let key = 0;
  const pushText = (s: string) => {
    if (s) top().children.push(<Fragment key={key++}>{s}</Fragment>);
  };

  let m: RegExpExecArray | null;
  TAG_RE.lastIndex = 0;
  while ((m = TAG_RE.exec(text)) !== null) {
    pushText(text.slice(pos, m.index));
    pos = TAG_RE.lastIndex;
    const closing = m[1] === "/";
    const tag = m[2] as InlineTag;
    if (!ALLOWED.has(tag)) {
      pushText(m[0]); // defensive; regex already constrains
      continue;
    }
    if (!closing) {
      stack.push({ tag, children: [] });
    } else if (stack.length > 1 && top().tag === tag) {
      const frame = stack.pop()!;
      top().children.push(
        <span key={key++} className={TAG_CLASS[frame.tag as InlineTag]}>
          {frame.children}
        </span>,
      );
    } else {
      // Stray/unbalanced close tag → render literally (escaped).
      pushText(m[0]);
    }
  }
  pushText(text.slice(pos));

  // Any unclosed frames: flatten their collected children into the parent
  // (don't drop content; just lose the styling on the malformed segment).
  while (stack.length > 1) {
    const frame = stack.pop()!;
    top().children.push(<Fragment key={key++}>{frame.children}</Fragment>);
  }
  return root.children;
}

/** Convenience component. */
export function InlineTags({ text }: { text: string | null | undefined }) {
  return <>{renderInlineTags(text)}</>;
}
