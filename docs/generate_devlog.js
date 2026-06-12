const {
  Document, Packer, Paragraph, TextRun, Table, TableRow, TableCell,
  HeadingLevel, AlignmentType, BorderStyle, WidthType, ShadingType,
  LevelFormat, PageNumber, Header, Footer, ExternalHyperlink,
} = require("docx");
const fs = require("fs");

const CONTENT_WIDTH = 9360; // US Letter, 1" margins
const COL1 = 2200;
const COL2 = CONTENT_WIDTH - COL1;

const border = { style: BorderStyle.SINGLE, size: 1, color: "DDDDDD" };
const borders = { top: border, bottom: border, left: border, right: border };

function h1(text) {
  return new Paragraph({
    heading: HeadingLevel.HEADING_1,
    spacing: { before: 360, after: 120 },
    children: [new TextRun({ text, bold: true, size: 36, font: "Arial", color: "1F4E79" })],
  });
}

function h2(text) {
  return new Paragraph({
    heading: HeadingLevel.HEADING_2,
    spacing: { before: 280, after: 80 },
    children: [new TextRun({ text, bold: true, size: 28, font: "Arial", color: "2E75B6" })],
  });
}

function h3(text) {
  return new Paragraph({
    heading: HeadingLevel.HEADING_3,
    spacing: { before: 200, after: 60 },
    children: [new TextRun({ text, bold: true, size: 24, font: "Arial", color: "404040" })],
  });
}

function p(text, opts = {}) {
  return new Paragraph({
    spacing: { before: 60, after: 60 },
    children: [new TextRun({ text, size: 22, font: "Arial", ...opts })],
  });
}

function bullet(text, bold_prefix = "") {
  return new Paragraph({
    numbering: { reference: "bullets", level: 0 },
    spacing: { before: 40, after: 40 },
    children: [
      ...(bold_prefix ? [new TextRun({ text: bold_prefix + " ", bold: true, size: 22, font: "Arial" })] : []),
      new TextRun({ text, size: 22, font: "Arial" }),
    ],
  });
}

function code(text) {
  return new Paragraph({
    spacing: { before: 60, after: 60 },
    indent: { left: 720 },
    children: [new TextRun({ text, size: 20, font: "Courier New", color: "C7254E" })],
  });
}

function codeBlock(lines) {
  return lines.map(line =>
    new Paragraph({
      spacing: { before: 20, after: 20 },
      indent: { left: 720 },
      shading: { type: ShadingType.CLEAR, fill: "F5F5F5" },
      children: [new TextRun({ text: line, size: 18, font: "Courier New", color: "2C3E50" })],
    })
  );
}

function divider() {
  return new Paragraph({
    spacing: { before: 160, after: 160 },
    border: { bottom: { style: BorderStyle.SINGLE, size: 4, color: "2E75B6", space: 1 } },
    children: [],
  });
}

function infoTable(rows) {
  return new Table({
    width: { size: CONTENT_WIDTH, type: WidthType.DXA },
    columnWidths: [COL1, COL2],
    rows: rows.map(([label, value]) =>
      new TableRow({
        children: [
          new TableCell({
            borders,
            width: { size: COL1, type: WidthType.DXA },
            shading: { type: ShadingType.CLEAR, fill: "EBF3FA" },
            margins: { top: 80, bottom: 80, left: 120, right: 120 },
            children: [new Paragraph({ children: [new TextRun({ text: label, bold: true, size: 20, font: "Arial" })] })],
          }),
          new TableCell({
            borders,
            width: { size: COL2, type: WidthType.DXA },
            margins: { top: 80, bottom: 80, left: 120, right: 120 },
            children: [new Paragraph({ children: [new TextRun({ text: value, size: 20, font: "Arial" })] })],
          }),
        ],
      })
    ),
  });
}

const doc = new Document({
  numbering: {
    config: [
      {
        reference: "bullets",
        levels: [{ level: 0, format: LevelFormat.BULLET, text: "•", alignment: AlignmentType.LEFT,
          style: { paragraph: { indent: { left: 720, hanging: 360 } } } }],
      },
    ],
  },
  styles: {
    default: { document: { run: { font: "Arial", size: 22 } } },
    paragraphStyles: [
      { id: "Heading1", name: "Heading 1", basedOn: "Normal", next: "Normal", quickFormat: true,
        run: { size: 36, bold: true, font: "Arial", color: "1F4E79" },
        paragraph: { spacing: { before: 360, after: 120 }, outlineLevel: 0 } },
      { id: "Heading2", name: "Heading 2", basedOn: "Normal", next: "Normal", quickFormat: true,
        run: { size: 28, bold: true, font: "Arial", color: "2E75B6" },
        paragraph: { spacing: { before: 280, after: 80 }, outlineLevel: 1 } },
      { id: "Heading3", name: "Heading 3", basedOn: "Normal", next: "Normal", quickFormat: true,
        run: { size: 24, bold: true, font: "Arial", color: "404040" },
        paragraph: { spacing: { before: 200, after: 60 }, outlineLevel: 2 } },
    ],
  },
  sections: [{
    properties: {
      page: {
        size: { width: 12240, height: 15840 },
        margin: { top: 1440, right: 1440, bottom: 1440, left: 1440 },
      },
    },
    headers: {
      default: new Header({
        children: [new Paragraph({
          border: { bottom: { style: BorderStyle.SINGLE, size: 4, color: "2E75B6", space: 4 } },
          children: [
            new TextRun({ text: "Company Brain — Developer Log", bold: true, size: 20, font: "Arial", color: "2E75B6" }),
            new TextRun({ text: "   |   Portfolio Project", size: 20, font: "Arial", color: "888888" }),
          ],
        })],
      }),
    },
    footers: {
      default: new Footer({
        children: [new Paragraph({
          alignment: AlignmentType.CENTER,
          border: { top: { style: BorderStyle.SINGLE, size: 4, color: "DDDDDD", space: 4 } },
          children: [
            new TextRun({ text: "Page ", size: 18, font: "Arial", color: "888888" }),
            new TextRun({ children: [PageNumber.CURRENT], size: 18, font: "Arial", color: "888888" }),
          ],
        })],
      }),
    },
    children: [

      // ── COVER ─────────────────────────────────────────────────────────────
      new Paragraph({
        spacing: { before: 480, after: 120 },
        children: [new TextRun({ text: "Company Brain", bold: true, size: 64, font: "Arial", color: "1F4E79" })],
      }),
      new Paragraph({
        spacing: { before: 0, after: 80 },
        children: [new TextRun({ text: "Developer Log — Week 1", size: 32, font: "Arial", color: "2E75B6" })],
      }),
      new Paragraph({
        spacing: { before: 0, after: 40 },
        children: [new TextRun({ text: "Tanmay Pathak  |  June 2026", size: 22, font: "Arial", color: "666666" })],
      }),
      new Paragraph({
        spacing: { before: 0, after: 400 },
        children: [new TextRun({ text: "Stack: Python 3.9 • CrewAI • Claude API • ChromaDB • Streamlit • Google APIs", size: 20, font: "Arial", color: "888888" })],
      }),
      divider(),

      // ── PROJECT OVERVIEW ──────────────────────────────────────────────────
      h1("Project Overview"),
      p("Company Brain is a portfolio project inspired by YC's RFS. The goal is to ingest company knowledge from Slack, Gmail, and Google Drive, extract structured process knowledge using the Claude API and CrewAI, store it in ChromaDB, and present it via a Streamlit dashboard."),
      new Paragraph({ spacing: { before: 120, after: 60 }, children: [] }),
      infoTable([
        ["Inspiration", "YC Request for Startups — knowledge management category"],
        ["Goal", "Ship a working demo in 4 weeks, learn by building"],
        ["Week 1", "Ingestion pipeline: Drive, Gmail, file upload, ChromaDB, Streamlit UI"],
        ["Week 2", "CrewAI agents + Claude API for RAG-based answers"],
        ["Week 3", "Streamlit dashboard polish, source filtering, session memory"],
        ["Week 4", "Slack ingestion, final demo prep, portfolio write-up"],
      ]),
      new Paragraph({ spacing: { before: 120, after: 60 }, children: [] }),
      divider(),

      // ══════════════════════════════════════════════════════════════════════
      // DAY 1
      // ══════════════════════════════════════════════════════════════════════
      h1("Day 1 — Ingestion Pipeline & Project Structure"),
      p("Date: 2026-06-10", { color: "888888", italics: true }),
      p("Goal: Set up the full project folder structure, create requirements.txt, and build the data ingestion module — Google Drive + file upload (PDF/DOCX), chunking, embedding, and ChromaDB storage."),

      // Folder structure
      h2("1. Project Structure"),
      p("The project is split into vertical slices. Each folder owns one layer of the system so any layer can be replaced without touching the others."),
      ...codeBlock([
        "company-brain/",
        "  ingestion/        ← getting data in (Drive, Gmail, files, CSV)",
        "  storage/          ← ChromaDB wrapper",
        "  agents/           ← CrewAI agents (Week 2)",
        "  dashboard/        ← Streamlit UI (Week 2+)",
        "  utils/            ← shared helpers",
        "  data/chroma/      ← local vector DB files (git-ignored)",
        "  ingest.py         ← CLI entry point",
        "  requirements.txt",
      ]),
      p("Why this structure? Separation of concerns. When Slack ingestion is added in Week 4, it's one new file in ingestion/ — nothing else changes."),

      // Chunker
      h2("2. ingestion/chunker.py — Text Chunking"),
      p("The chunker splits a long text into overlapping word-based windows before embedding."),
      h3("Why chunk at all?"),
      p("LLMs and vector databases work best on focused units of meaning. A 50-page document as one blob produces a useless embedding — it averages everything into noise. Chunks of ~500 words keep semantic focus while staying large enough to hold paragraph-level context."),
      h3("Why overlap?"),
      p("If a key sentence sits at a chunk boundary, neither chunk captures it fully. An overlap of 50 words ensures boundary content appears in at least one chunk's complete context."),
      h3("Why word-based (not character-based)?"),
      p("Embedding models have token limits (~512 tokens). Tokens track words far more closely than characters — a 500-word chunk is roughly 650 tokens, safely within limits."),
      ...codeBlock([
        "def chunk_text(text, source, chunk_size=500, overlap=50):",
        "    words = text.split()",
        "    start = 0",
        "    while start < len(words):",
        "        end = min(start + chunk_size, len(words))",
        "        # overlap: next chunk re-uses the last 50 words",
        "        start += chunk_size - overlap",
      ]),

      // File upload
      h2("3. ingestion/file_upload.py — PDF & DOCX Parsing"),
      p("Two entry points are provided for the same job:"),
      bullet("ingest_file(path) — takes a file path, used by the CLI", ""),
      bullet("ingest_file_bytes(content, filename) — takes raw bytes, used by Streamlit's file_uploader which gives bytes not a path", ""),
      p("Both converge on the same chunk_text() call. Text is extracted first (PDF via PyPDF2, DOCX via python-docx), then chunked. Converting to plain text once keeps all downstream steps format-agnostic."),

      // Drive
      h2("4. ingestion/drive.py — Google Drive Connector"),
      p("Connects to Google Drive via OAuth2 and ingests Docs, Sheets, PDFs, and DOCX files."),
      h3("Auth flow"),
      p("On first run, a browser tab opens for OAuth authorization. The token is saved to token.json so subsequent runs are silent. credentials.json is the app identity downloaded from Google Cloud Console."),
      h3("Google Docs vs downloadable files"),
      p("Google Docs have no download URL — they exist in Google's internal format. The export API converts them to plain text on the fly. PDFs and DOCX files are downloaded as binary and passed to file_upload.ingest_file_bytes()."),
      h3("Sheets (CSV export)"),
      p("Sheets are exported as CSV. Raw CSV numbers are meaningless to an embedding model, so they are handled by a separate csv_ingest.py module that converts each row into a readable English sentence before chunking (see Day 2)."),

      // ChromaDB
      h2("5. storage/chroma.py — ChromaDB Wrapper"),
      p("ChromaDB is a local-first vector database that runs in-process with zero infrastructure. All data lives in data/chroma/ on disk."),
      h3("Why a wrapper?"),
      p("Direct ChromaDB calls scattered across the codebase would require every caller to know the collection name, embedding function, and ID scheme. Centralizing these in one file means one change propagates everywhere."),
      h3("Embeddings"),
      p("The sentence-transformers library (all-MiniLM-L6-v2 model) generates embeddings locally — no API cost per chunk, works offline. Anthropic's Claude API is a generation model, not an embeddings endpoint, so a separate library is used."),
      h3("upsert() not add()"),
      p("Chunk IDs are deterministic: \"{source}::chunk_{index}\". Running ingestion twice on the same file produces the same IDs. upsert() updates if the ID exists, inserts if not — so re-ingestion is safe. add() would crash with a duplicate ID error."),
      h3("Cosine distance"),
      p("Cosine distance measures the angle between two vectors (0 = identical meaning, 2 = opposite). It's better than Euclidean (L2) distance for text because it captures meaning direction, not word frequency magnitude."),
      ...codeBlock([
        "collection = client.get_or_create_collection(",
        "    name='company_brain',",
        "    embedding_function=SentenceTransformerEmbeddingFunction('all-MiniLM-L6-v2'),",
        "    metadata={'hnsw:space': 'cosine'},",
        ")",
      ]),

      // CLI
      h2("6. ingest.py — CLI Entry Point"),
      p("A thin router that parses sys.argv and delegates to the real modules. Keeping it thin means business logic lives in ingestion/ and storage/, not tangled with argument parsing."),
      ...codeBlock([
        "python ingest.py file path/to/doc.pdf",
        "python ingest.py drive <file_id>",
        "python ingest.py folder <folder_id>",
        "python ingest.py gmail 30",
        "python ingest.py stats",
        'python ingest.py query "how do we handle escalations"',
      ]),

      h2("Day 1 — What Was Tested"),
      bullet("chunk_text() — word splitting and overlap verified"),
      bullet("store_chunks() + query() — fake process docs embedded, queried, results returned with distance ~0.4"),
      bullet("ingest_file() — resume PDF parsed, 1 chunk stored (resume is under 500 words)"),
      bullet("ingest.py stats — collection count, model name, DB path all correct"),

      divider(),

      // ══════════════════════════════════════════════════════════════════════
      // DAY 2
      // ══════════════════════════════════════════════════════════════════════
      h1("Day 2 — Streamlit Dashboard, Gmail & CSV Ingestion"),
      p("Date: 2026-06-11", { color: "888888", italics: true }),
      p("Goal: Add Gmail ingestion, a natural language query function with source attribution, and update the Streamlit dashboard with an 'Ask the Brain' interface."),

      // Dashboard
      h2("1. dashboard/app.py — Streamlit UI"),
      p("Three tabs built into one file:"),
      infoTable([
        ["Ingest tab", "Drag & drop PDF/DOCX files. Google Drive file/folder ID input. Gmail ingest with sliders for days and max emails."],
        ["Query tab", "Text input for natural language questions. Results ranked by semantic similarity with relevance % and expandable chunk previews."],
        ["Stats tab", "Total chunk count, embedding model, and a per-source breakdown showing how many chunks came from each document or email."],
      ]),
      new Paragraph({ spacing: { before: 120, after: 60 }, children: [] }),
      h3("Key design decision — relevance percentage"),
      p("Cosine distance (0=identical, 2=opposite) is converted to a 0-100% relevance score: relevance = max(0, (1 - distance) * 100). This reads more naturally to a non-technical audience than raw distance numbers."),
      h3("PYTHONPATH fix"),
      p("Streamlit's working directory is the file's location, not the project root. Running it directly breaks imports like 'from ingestion.file_upload import ...'. The fix is a launcher script that sets PYTHONPATH before starting Streamlit:"),
      ...codeBlock([
        "# run_dashboard.sh",
        'cd "$(dirname "$0")"',
        'PYTHONPATH="$(pwd)" cb-env/bin/streamlit run dashboard/app.py',
      ]),

      // Gmail
      h2("2. ingestion/gmail.py — Gmail Connector"),
      p("Pulls emails from the last N days, extracts subject + sender + body, and chunks them into ChromaDB with source metadata tagged as 'gmail:{subject}'."),
      h3("Auth"),
      p("Reuses credentials.json from the Drive setup. Gmail requires an additional OAuth scope (gmail.readonly). The SCOPES list in gmail.py includes both Drive and Gmail scopes, so token.json is updated on the next auth flow to cover both."),
      h3("_decode_body() — MIME tree walking"),
      p("Gmail stores email bodies as a tree of MIME parts (text/plain, text/html, attachments, nested multipart containers). The function walks the tree recursively and collects only text/plain leaves, skipping HTML which is full of tag noise."),
      h3("_clean_body() — reply chain stripping"),
      p("Without cleanup, a 10-reply thread re-embeds the full quoted history in every chunk — 90% duplicate content. Lines starting with '>' (quoted replies) and 'On ... wrote:' headers are stripped so each chunk contains only new content."),
      h3("Self-identifying chunks"),
      p("The email header (From, Subject, Date) is prepended to every chunk from that email. This means any retrieved chunk is self-contained — you always know who sent it and why, even if you get chunk 3 of 5 from a long email thread."),
      ...codeBlock([
        "header = f'Email from: {sender}\\nSubject: {subject}\\nDate: {date}\\n---\\n'",
        "full_text = header + body",
        "# Every chunk from this email starts with the header context",
      ]),
      h3("chunk_size=300 for emails"),
      p("Emails are shorter and more focused than documents. Smaller chunks (300 words vs 500 for docs) give more precise retrieval — a relevant sentence is less likely to be diluted by surrounding off-topic content."),

      // CSV
      h2("3. ingestion/csv_ingest.py — Structured Data to Prose"),
      p("This module solves a fundamental RAG problem: raw CSV numbers have no semantic meaning for an embedding model."),
      h3("The problem"),
      p("A fraud detection row like '121958,-2.28,1600.89,0,Low' produced near-zero relevance (distance ~0.95) against any natural language query. The model had nothing to embed."),
      h3("The solution"),
      p("Convert each row to an English sentence before chunking. A schema-aware converter maps column names to readable text:"),
      ...codeBlock([
        "# Before: raw CSV row",
        '"121958,-2.28,1600.89,0,Low"',
        "",
        "# After: prose sentence",
        '"Transaction at time 121958 of $1600.89 was classified as non-fraud',
        ' (confidence: 17.9%). Risk level: Low."',
      ]),
      p("After this change, query distance dropped from ~0.95 to ~0.34 — a dramatic improvement in retrieval quality."),
      h3("Schema registry"),
      p("A _CONVERTERS dict maps keywords in the source name to converter functions. 'fraud' in the filename triggers _fraud_row_to_text(). Unknown schemas fall back to a generic 'key: value, key: value' format. New schemas can be added without touching existing code."),
      h3("rows_per_chunk=20"),
      p("Each chunk holds 20 row-sentences. This keeps chunks focused while staying within embedding token limits. max_rows=500 prevents accidentally ingesting a million-row dataset in a portfolio demo."),

      // DB utils
      h2("4. utils/db_utils.py — Database Management"),
      p("Utility functions for managing the ChromaDB collection:"),
      bullet("list_sources() — print all ingested sources with chunk counts"),
      bullet("delete_source(source) — remove all chunks from a specific source by name"),
      bullet("nuke() — delete everything in the collection"),
      p("These were essential for Day 2 debugging: the fake test data from Day 1 was polluting query results. delete_source() removed it without touching real ingested content."),

      // Duplicate ID fix
      h2("5. Bug Fix — Duplicate Email IDs"),
      p("Multiple emails sharing the same subject (e.g. 'Security alert') caused a ChromaDB DuplicateIDError because chunk IDs were built from the source name alone."),
      p("Fix: use the Gmail message ID (a unique string per email from the API) as the primary key component instead of the subject:"),
      ...codeBlock([
        "# Before (breaks on duplicate subjects):",
        'id = f"{source}::chunk_{chunk_index}"',
        "",
        "# After (unique per email):",
        'id = f"{email_id}::chunk_{chunk_index}"',
      ]),

      // Day 2 test results
      h2("Day 2 — What Was Tested"),
      bullet("File upload via Streamlit — PDF ingested through drag & drop, chunks stored"),
      bullet("Google Drive Sheets — credit card fraud dataset ingested, CSV rows converted to prose"),
      bullet("Query relevance improvement — distance 0.95 → 0.34 after CSV prose conversion"),
      bullet("Gmail — 15 emails ingested from tpsnowflake1611@gmail.com demo account"),
      bullet("Stats tab — sources listed with per-source chunk counts"),
      bullet("Duplicate email ID bug — fixed with Gmail message ID as chunk key"),

      divider(),

      // ── RUNNING THE PROJECT ───────────────────────────────────────────────
      h1("Running the Project"),
      h2("Prerequisites"),
      bullet("Python 3.9, virtualenv at cb-env/"),
      bullet("credentials.json from Google Cloud Console (OAuth Desktop app)"),
      bullet("Gmail API + Google Drive API enabled in the Cloud project"),
      bullet("tpsnowflake1611@gmail.com added as test user in OAuth consent screen"),

      h2("Daily Startup"),
      ...codeBlock([
        "cd ~/company-brain",
        "source cb-env/bin/activate",
        "",
        "# Start the dashboard",
        "./run_dashboard.sh",
        "",
        "# Or use the CLI",
        "python ingest.py gmail 90",
        'python ingest.py query "customer escalation process"',
        "python ingest.py stats",
      ]),

      h2("Key Files"),
      infoTable([
        ["ingestion/chunker.py", "Word-based overlapping text chunker (500w, 50w overlap)"],
        ["ingestion/file_upload.py", "PDF + DOCX parser — path and bytes variants"],
        ["ingestion/drive.py", "Google Drive OAuth2 connector"],
        ["ingestion/gmail.py", "Gmail connector — MIME parsing, reply stripping"],
        ["ingestion/csv_ingest.py", "CSV row-to-prose converter for structured data"],
        ["storage/chroma.py", "ChromaDB wrapper — upsert, cosine query, stats"],
        ["utils/db_utils.py", "DB management: list, delete, nuke sources"],
        ["dashboard/app.py", "Streamlit UI — Ingest / Query / Stats tabs"],
        ["ingest.py", "CLI entry point for all ingestion commands"],
        ["run_dashboard.sh", "Launch script — sets PYTHONPATH correctly"],
      ]),

      divider(),

      // ── NEXT ──────────────────────────────────────────────────────────────
      h1("Up Next — Day 3"),
      p("Wire the Claude API into the Query tab to transform raw chunk retrieval into actual answers (RAG generation step)."),
      bullet("utils/claude_rag.py — take top-5 chunks + user question, send to Claude API, return a synthesized answer"),
      bullet("Update Query tab — show Claude's answer above the raw chunks"),
      bullet("Add source citations in the answer — 'According to [drive:onboarding_doc], ...'"),
      p("This is the step that makes the product feel like a real AI assistant rather than a search engine."),

      new Paragraph({ spacing: { before: 240, after: 0 }, children: [] }),
    ],
  }],
});

Packer.toBuffer(doc).then(buffer => {
  fs.writeFileSync("company_brain_devlog.docx", buffer);
  console.log("Created: docs/company_brain_devlog.docx");

});
