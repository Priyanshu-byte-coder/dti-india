// Build the Word version of the paper draft from paper/draft.md (+ generated tables).
//   NODE_PATH=<dir with node_modules/docx> node paper/build_docx.js [draft.md] [tables.md] [out.docx]
// Supports the Markdown used in the draft: #/##/### headings, paragraphs, "- " bullets,
// "> " note blocks, pipe tables, ```latex blocks, **bold**, *italic*, `code`, [text](url),
// and <!-- TABLES:1,2 --> markers that pull "## Table N." blocks from the tables file.
const fs = require("fs");
const path = require("path");
const {
  Document, Packer, Paragraph, TextRun, HeadingLevel, Table, TableRow, TableCell, WidthType,
  AlignmentType, ShadingType, BorderStyle, LevelFormat, Footer, PageNumber, TableLayoutType,
} = require("docx");

const [draftPath = "paper/draft.md", tablesPath = "paper/tables_onet.md", outPath = "paper/DTI_paper_draft.docx"] =
  process.argv.slice(2);
const FONT = "Times New Roman";
const PAGE_W = 11906, MARGIN = 1300, CONTENT_W = PAGE_W - 2 * MARGIN; // A4, DXA

// ---------- inline Markdown -> TextRuns ----------
// Escaped characters (e.g. O\*NET) are swapped for private-use placeholders before parsing,
// so they cannot open or close bold/italic spans, and restored when the run is written.
const PROTECT = { "*": "", _: "", "`": "", "[": "", "]": "", "#": "", "|": "", "\\": "" };
const RESTORE = Object.fromEntries(Object.entries(PROTECT).map(([k, v]) => [v, k]));
const protect = (s) => s.replace(/\\([*_`\\[\]#|])/g, (_, c) => PROTECT[c]);
const unescape = (s) => s.replace(/[-]/g, (c) => RESTORE[c]);
function inline(rawText, base = {}) {
  const text = protect(rawText);
  const runs = [];
  const re = /(\*\*[^*]+?\*\*|\*[^*\s][^*]*?\*|`[^`]+`|\[[^\]]+\]\([^)]+\)|\[(?:PENDING[^\]]*|PRELIMINARY[^\]]*|To be [^\]]*|Final wording[^\]]*)\])/g;
  let last = 0, m;
  const push = (t, o = {}) => { if (t) runs.push(new TextRun({ text: unescape(t), font: FONT, ...base, ...o })); };
  while ((m = re.exec(text)) !== null) {
    push(text.slice(last, m.index));
    const tok = m[0];
    if (tok.startsWith("**")) {
      const inner = tok.slice(2, -2);
      if (/^\[(PENDING|PRELIMINARY|To be|Final wording)/.test(inner)) push(inner, { bold: true, highlight: "yellow" });
      else push(inner, { bold: true });
    } else if (tok.startsWith("`")) push(tok.slice(1, -1), { font: "Consolas", size: (base.size || 22) - 2 });
    else if (tok.startsWith("[") && tok.includes("](")) push(tok.slice(1, tok.indexOf("](")));
    else if (tok.startsWith("[")) push(tok, { bold: true, highlight: "yellow" });
    else push(tok.slice(1, -1), { italics: true });
    last = m.index + tok.length;
  }
  push(text.slice(last));
  return runs;
}

// ---------- LaTeX (small subset) -> runs with sub/superscripts ----------
const GREEK = { alpha: "α", beta: "β", gamma: "γ", delta: "δ", lambda: "λ", tau: "τ", epsilon: "ε", sum: "Σ", ln: "ln", text: "" };
function latexRuns(src) {
  let s = src.replace(/\\qquad/g, "     ").replace(/\\,/g, " ").replace(/\\text\{([^}]*)\}/g, "$1")
    .replace(/O\^\*NET/g, "O*NET")
    .replace(/\\(alpha|beta|gamma|delta|lambda|tau|epsilon|sum|ln)(?![a-zA-Z])/g, (_, g) => GREEK[g] + (g === "ln" ? " " : ""))
    .replace(/\^\*/g, "^{*}").replace(/\\-/g, "-");
  const runs = [];
  const re = /([_^])(\{[^}]*\}|.)/g;
  let last = 0, m;
  const add = (t, o = {}) => t && runs.push(new TextRun({ text: t, font: "Cambria Math", size: 24, italics: true, ...o }));
  while ((m = re.exec(s)) !== null) {
    add(s.slice(last, m.index));
    const body = m[2].startsWith("{") ? m[2].slice(1, -1) : m[2];
    add(body, m[1] === "_" ? { subScript: true } : { superScript: true });
    last = m.index + m[0].length;
  }
  add(s.slice(last));
  return runs;
}

// ---------- blocks ----------
const thin = { style: BorderStyle.SINGLE, size: 4, color: "999999" };
function mdTable(lines) {
  const rows = lines.filter((l) => !/^\|\s*-+/.test(l.replace(/\|/g, "|").replace(/:/g, "")) && !/^\|(\s*-+\s*\|)+\s*$/.test(l))
    .map((l) => l.trim().replace(/^\||\|$/g, "").split("|").map((c) => c.trim()));
  const ncol = rows[0].length;
  // width from the body cells; headers may wrap onto two or three lines
  const lens = Array.from({ length: ncol }, (_, j) => Math.max(
    ...rows.slice(1).map((r) => Math.min((r[j] || "").length, 45)), Math.ceil((rows[0][j] || "").length / 2.5), 4));
  const total = lens.reduce((a, b) => a + b, 0);
  const widths = lens.map((x) => Math.floor((CONTENT_W * x) / total));
  widths[widths.length - 1] += CONTENT_W - widths.reduce((a, b) => a + b, 0);
  const size = ncol >= 7 ? 15 : 17;
  return new Table({
    width: { size: CONTENT_W, type: WidthType.DXA }, columnWidths: widths, layout: TableLayoutType.FIXED,
    rows: rows.map((r, i) => new TableRow({
      tableHeader: i === 0,
      children: widths.map((w, j) => new TableCell({
        width: { size: w, type: WidthType.DXA },
        borders: { top: thin, bottom: thin, left: thin, right: thin },
        shading: i === 0 ? { type: ShadingType.CLEAR, fill: "E7ECF2", color: "auto" } : undefined,
        margins: { top: 40, bottom: 40, left: 70, right: 70 },
        children: [new Paragraph({ children: inline(r[j] || "", { size, bold: i === 0 }) })],
      })),
    })),
  });
}

function loadTables(file) {
  const out = {};
  if (!fs.existsSync(file)) return out;
  const parts = fs.readFileSync(file, "utf8").split(/\n(?=## Table )/);
  for (const p of parts) {
    const m = p.match(/^## Table (\d+)\./);
    if (m) out[m[1]] = p;
  }
  return out;
}

const children = [];
const para = (text, opts = {}) => children.push(new Paragraph({ spacing: { after: 120, line: 288 }, children: inline(text), ...opts }));

function render(md, { insideTables = false } = {}) {
  const lines = md.replace(/\r/g, "").split("\n");
  let i = 0;
  while (i < lines.length) {
    const line = lines[i];
    const t = line.trim();
    if (!t || t === "---") { i++; continue; }
    const tm = t.match(/^<!--\s*TABLES:([\d,\s]+)-->/);
    if (tm) {
      for (const n of tm[1].split(",").map((x) => x.trim()).filter(Boolean)) if (TABLES[n]) render(TABLES[n], { insideTables: true });
      i++; continue;
    }
    if (t.startsWith("<!--")) { i++; continue; }
    if (t.startsWith("```")) {
      const body = [];
      i++;
      while (i < lines.length && !lines[i].trim().startsWith("```")) body.push(lines[i++]);
      i++;
      children.push(new Paragraph({ alignment: AlignmentType.CENTER, spacing: { before: 120, after: 160 }, children: latexRuns(body.join(" ")) }));
      continue;
    }
    if (t.startsWith("|")) {
      const block = [];
      while (i < lines.length && lines[i].trim().startsWith("|")) block.push(lines[i++].trim());
      children.push(mdTable(block));
      children.push(new Paragraph({ spacing: { after: 80 }, children: [] }));
      continue;
    }
    const h = t.match(/^(#{1,3})\s+(.*)$/);
    if (h) {
      const level = h[1].length;
      if (level === 1 && !insideTables) {
        children.push(new Paragraph({ alignment: AlignmentType.CENTER, spacing: { after: 200 }, children: inline(h[2], { bold: true, size: 32 }) }));
      } else if (insideTables || level === 3) {
        children.push(new Paragraph({ heading: HeadingLevel.HEADING_2, spacing: { before: 200, after: 100 }, children: inline(h[2]) }));
      } else {
        children.push(new Paragraph({ heading: HeadingLevel.HEADING_1, spacing: { before: 280, after: 120 }, children: inline(h[2]) }));
      }
      i++; continue;
    }
    if (t.startsWith(">")) {
      const block = [];
      while (i < lines.length && lines[i].trim().startsWith(">")) block.push(lines[i++].trim().replace(/^>\s?/, ""));
      children.push(new Paragraph({
        shading: { type: ShadingType.CLEAR, fill: "FFF4CE", color: "auto" },
        border: { left: { style: BorderStyle.SINGLE, size: 18, color: "C9A227", space: 8 } },
        spacing: { before: 120, after: 200, line: 276 }, children: inline(block.join(" "), { size: 21 }),
      }));
      continue;
    }
    if (/^[-*]\s+/.test(t)) {
      while (i < lines.length && /^[-*]\s+/.test(lines[i].trim())) {
        children.push(new Paragraph({ numbering: { reference: "bullets", level: 0 }, spacing: { after: 60, line: 276 },
          children: inline(lines[i].trim().replace(/^[-*]\s+/, "")) }));
        i++;
      }
      continue;
    }
    const buf = [t];
    i++;
    while (i < lines.length && lines[i].trim() && !/^(#|\||>|```|[-*]\s|<!--)/.test(lines[i].trim())) buf.push(lines[i++].trim());
    const text = buf.join(" ");
    if (/^\*Working draft|^\*\(As submitted/.test(text)) para(text, { alignment: AlignmentType.LEFT });
    else if (/^(Anuja Nair|Gunjan Anand)/.test(text)) para(text, { alignment: AlignmentType.CENTER });
    else para(text, { alignment: AlignmentType.JUSTIFIED });
  }
}

const TABLES = loadTables(tablesPath);
render(fs.readFileSync(draftPath, "utf8"));

const doc = new Document({
  creator: "DTI project", title: "Digital Task Intensity of Indian Occupations — working draft",
  styles: {
    default: { document: { run: { font: FONT, size: 22 } } },
    paragraphStyles: [
      { id: "Heading1", name: "Heading 1", basedOn: "Normal", next: "Normal", quickFormat: true,
        run: { font: FONT, size: 28, bold: true, color: "1F3864" }, paragraph: { outlineLevel: 0 } },
      { id: "Heading2", name: "Heading 2", basedOn: "Normal", next: "Normal", quickFormat: true,
        run: { font: FONT, size: 24, bold: true, color: "2F5496" }, paragraph: { outlineLevel: 1 } },
    ],
  },
  numbering: { config: [{ reference: "bullets", levels: [{ level: 0, format: LevelFormat.BULLET, text: "•", alignment: AlignmentType.LEFT,
    style: { paragraph: { indent: { left: 540, hanging: 270 } } } }] }] },
  sections: [{
    properties: { page: { size: { width: PAGE_W, height: 16838 }, margin: { top: 1300, bottom: 1300, left: MARGIN, right: MARGIN } } },
    footers: { default: new Footer({ children: [new Paragraph({ alignment: AlignmentType.CENTER,
      children: [new TextRun({ children: ["Working draft — ", PageNumber.CURRENT], font: FONT, size: 18, color: "666666" })] })] }) },
    children,
  }],
});
Packer.toBuffer(doc).then((buf) => { fs.writeFileSync(outPath, buf); console.log(`wrote ${outPath} (${children.length} blocks, ${Object.keys(TABLES).length} tables available)`); });
