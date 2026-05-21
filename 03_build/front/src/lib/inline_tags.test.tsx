import { render } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { InlineTags } from "@/lib/inline_tags";

function html(text: string | null | undefined): string {
  const { container } = render(<InlineTags text={text} />);
  return container.innerHTML;
}

describe("renderInlineTags (Tier-0 §10)", () => {
  it("renders <num> as mono ink-primary", () => {
    const out = html("<num>2 risk-tagged Cases</num>");
    expect(out).toContain("font-mono");
    expect(out).toContain("2 risk-tagged Cases");
  });

  it("renders <bad> as risk-high color", () => {
    expect(html("<bad>vendor-consolidation</bad>")).toContain("text-risk-high-fg");
  });

  it("renders <good> as risk-low color", () => {
    expect(html("<good>replacement delivered</good>")).toContain("text-risk-low-fg");
  });

  it("renders <quote> as italic quote color", () => {
    const out = html('<quote>"cut vendor count by 20%"</quote>');
    expect(out).toContain("italic");
    expect(out).toContain("text-ink-quote");
  });

  it("renders <em> as italic ink-primary", () => {
    const out = html("<em>EBR is Thursday</em>");
    expect(out).toContain("italic");
    expect(out).toContain("text-ink-primary");
  });

  it("escapes non-whitelist tags (no injection)", () => {
    const out = html('<script>alert(1)</script> and <b>bold</b>');
    // Angle brackets must be escaped to entities; no live <script>/<b> elements.
    expect(out).not.toContain("<script>");
    expect(out).not.toContain("<b>");
    expect(out).toContain("&lt;script&gt;");
    expect(out).toContain("&lt;b&gt;");
  });

  it("preserves plain text around tags", () => {
    const out = html("Open <num>2</num> cases before <em>Thursday</em>.");
    expect(out).toContain("Open ");
    expect(out).toContain(" cases before ");
    expect(out).toContain(".");
  });

  it("handles stray/unbalanced close tag as literal text", () => {
    const out = html("trailing </num> tag");
    expect(out).toContain("&lt;/num&gt;");
  });

  it("returns empty for null/empty input", () => {
    expect(html(null)).toBe("");
    expect(html("")).toBe("");
  });
});
