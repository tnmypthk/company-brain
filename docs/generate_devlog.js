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
        children: [new TextRun({ text: "Stack: Python 3.9 • Claude API (Sonnet 4.6 + Opus 4.8) • ChromaDB • Streamlit • Slack & Google APIs", size: 20, font: "Arial", color: "888888" })],
      }),
      divider(),

      // ── PROJECT OVERVIEW ──────────────────────────────────────────────────
      h1("Project Overview"),
      p("Company Brain is a portfolio project inspired by YC's RFS. The goal is to ingest company knowledge from Slack, Gmail, Google Drive, and uploaded files, extract structured process knowledge using a multi-agent Claude API pipeline, store it in ChromaDB, and present it via a Streamlit dashboard. (The original plan named CrewAI for the agent layer; in practice the agents are plain Claude API calls, so that dependency was dropped — see Day 6.)"),
      new Paragraph({ spacing: { before: 120, after: 60 }, children: [] }),
      infoTable([
        ["Inspiration", "YC Request for Startups — knowledge management category"],
        ["Goal", "Ship a working demo, learn by building"],
        ["Days 1–2", "Ingestion pipeline: Drive, Gmail, file upload, ChromaDB, Streamlit UI"],
        ["Day 3", "Claude API skills extractor + YAML skills files"],
        ["Day 4", "Slack ingestion + validator agent (2-agent pipeline)"],
        ["Day 5", "Synthesized answers with source citations"],
        ["Day 6 / 6.5", "Streamlit Cloud deployment, central config.yaml, UI polish"],
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

      // ══════════════════════════════════════════════════════════════════════
      // DAY 3
      // ══════════════════════════════════════════════════════════════════════
      h1("Day 3 — Claude API Skills File Generator"),
      p("Date: 2026-06-12", { color: "888888", italics: true }),
      p("Goal: Add the generation half of RAG. Days 1–2 built retrieval (finding relevant chunks); Day 3 sends those chunks to the Claude API and reasons over them — turning raw search into structured, reusable process documentation."),

      h2("1. agents/extractor.py — Chunks to Structured Process"),
      p("The extractor retrieves the top-N chunks for a topic, sends them to Claude, and gets back a structured process definition: process name, owner, trigger, ordered steps, edge cases, sources, and a confidence rating."),
      h3("Why structured JSON, not prose?"),
      p("The next step writes a YAML skills file. If Claude returns a paragraph, you have to parse it — fragile. If it returns JSON matching a known schema, you can validate it and write it directly. This 'structured output' pattern is one of the most important prompt-engineering techniques."),
      h3("Why split the system and user prompt?"),
      p("The system prompt defines Claude's role and the output contract — it's stable across every call, so Anthropic caches it. The user prompt carries the per-request payload (the topic and the retrieved chunks). Keeping the contract in the system prompt means it isn't restated, and isn't competing with thousands of context tokens for attention."),
      h3("Why claude-sonnet-4-6?"),
      p("Sonnet balances capability and cost well for structured extraction. The harder reasoning job (critiquing the draft) gets a stronger model on Day 4."),

      h2("2. agents/skills_writer.py — Dict to YAML"),
      p("Converts the extractor's dict into a human-readable YAML file in skills/. Keys are written in a deliberate reading order — what → who → why → how → exceptions → provenance — rather than yaml.dump's default alphabetical order, which would put 'confidence' before 'steps' and read wrong."),
      p("YAML over JSON because a skills file is meant to be reviewed, corrected, and committed by a human. YAML reads like a document; JSON's brackets and escaping make manual editing error-prone."),

      h2("3. Skills Tab in the Dashboard"),
      p("A topic input, a generate button, a YAML preview, and a save button. The catch: Streamlit re-runs the whole script on every interaction, so the generated result is held in st.session_state — without it, clicking 'Save' would lose the result from the 'Generate' click and re-trigger the expensive API call."),

      h2("Day 3 — What Was Tested"),
      bullet("extract_process() — generated a structured skills file from ingested chunks with sensible steps and confidence"),
      bullet("skills_writer — dict serialized to ordered YAML and saved to skills/"),
      bullet("Skills tab — generate → preview → save round-trip works without re-calling the API on save"),

      divider(),

      // ══════════════════════════════════════════════════════════════════════
      // DAY 4
      // ══════════════════════════════════════════════════════════════════════
      h1("Day 4 — Slack Ingestion & the 2-Agent Pipeline"),
      p("Date: 2026-06-12", { color: "888888", italics: true }),
      p("Goal: Add Slack as a fourth ingestion source, and add a second Claude agent that reviews the extractor's output — turning a single generation step into a generator-critic pipeline."),

      h2("1. ingestion/slack.py — Channel Transcripts"),
      p("Pulls messages from named channels via slack_sdk, resolves author IDs to names, and stores each channel as one chronological transcript tagged 'slack:{channel}'."),
      h3("Why a transcript, not one chunk per message?"),
      p("Slack messages are tiny — often under ten words ('sounds good!', '+1'). A chunk per message would fill ChromaDB with thousands of near-meaningless embeddings. Concatenating a channel's messages chronologically and chunking the transcript keeps a question and its answer in the same chunk, which is what makes retrieval useful."),
      h3("One users_list call, cached"),
      p("Messages reference authors by ID (U0123ABC). Calling users_info per message would be one API call per author per message. A single paginated users_list up front maps every ID to a display name."),
      h3("Public-channel scope fallback"),
      p("Listing private channels needs the optional groups:read scope. Rather than requiring it, the code asks for public + private and, if Slack rejects it with missing_scope, retries public-only — so the minimal three-scope token works out of the box."),

      h2("2. agents/validator.py — The Critic"),
      p("A second Claude agent (Opus 4.8) takes the extractor's draft and returns an improved version with a validation_notes field: are the steps actually executable? Are the edge cases realistic? Is the owner identifiable? Is the confidence honest?"),
      h3("Why two agents instead of one bigger prompt?"),
      p("A model reviewing its own output in the same context tends to defend its mistakes — the reasoning that produced a vague step is still in context. A critic with a fresh context containing only the draft reads it the way a new employee would: 'could I actually follow this?' This is the generator-critic (reflection) pattern."),
      h3("Cheap generator, strong critic"),
      p("Extraction is mostly mechanical restructuring, so it runs on Sonnet. Critique benefits from stronger reasoning, so it runs on Opus 4.8. Splitting the models is the classic cost/quality trade."),

      h2("3. Structured Outputs — Contract in the API, Not the Prompt"),
      p("Day 3's extractor asked for JSON in the prompt ('respond with ONLY valid JSON') and parsed the result. That broke the first time Claude wrapped its JSON in markdown fences. The fix: output_config.format with a JSON schema, which makes the API guarantee schema-valid output. The contract moves from a prompt suggestion to an enforced constraint — no fence-stripping, no missing-key checks. Both agents were upgraded to use it."),
      p("A second latent bug surfaced at the same time: the extractor's max_tokens was 1024, just above the failed response's size — a slightly longer process would have truncated the JSON mid-object. Raised to 4096."),

      h2("4. Dashboard — Side-by-Side Review"),
      p("The Skills tab now runs extractor → validator and shows the draft and the improved version side by side, with the validator's notes in an expander. Seeing what changed — and whether confidence went up or down — is how a human builds trust in the pipeline. A confidence drop is a feature: it means the validator caught the draft overselling its sourcing."),

      h2("Day 4 — What Was Tested"),
      bullet("Slack ingestion — channel transcript stored, public-scope fallback verified after a missing_scope error"),
      bullet("validate_process() — live run demoted a weak draft's confidence from high to low and rewrote vague steps"),
      bullet("Structured outputs — markdown-fence parse failure eliminated; extractor re-ran cleanly on the topic that broke it"),

      divider(),

      // ══════════════════════════════════════════════════════════════════════
      // DAY 5
      // ══════════════════════════════════════════════════════════════════════
      h1("Day 5 — Synthesized Answers with Citations"),
      p("Date: 2026-06-12", { color: "888888", italics: true }),
      p("Goal: Upgrade the Query tab from raw chunk retrieval to a synthesized, cited answer — the third Claude agent, and the feature that makes the product feel like an assistant rather than a search box."),

      h2("1. agents/answerer.py — Cited RAG Q&A"),
      p("Retrieves the top-8 chunks, sends them to Claude as 'Company Brain', and returns a prose answer grounded only in the provided context, with sources cited by name. Returns the chunks too, so the UI can show the evidence under the answer."),
      h3("Why the citation rule lives in the SYSTEM prompt, not the user prompt"),
      p("This was the day's key lesson, and it has four reasons:"),
      bullet("Attention. In RAG the user turn is ~95% pasted context — eight chunks of text with the question at the end. An instruction buried in that wall competes with thousands of tokens and gets lost in the middle. The system prompt is read with priority every time.", "Authority:"),
      bullet("'Cite your sources' is part of who the agent is — it applies to every question. The user prompt is the per-request payload. Permanent behavior belongs in the system prompt.", "Contract vs payload:"),
      bullet("Retrieved chunks are untrusted text. An ingested email could contain 'ignore previous instructions.' Instructions in the system channel are far harder for user-channel content to override.", "Injection resistance:"),
      bullet("The system prompt is byte-identical across queries, so it forms a stable, cacheable prefix.", "Caching:"),

      h2("2. Query Tab — Two Modes"),
      p("A toggle: 'Get Answer' (synthesis with a 'show source chunks' expander) and 'Raw chunks' (the original Day 1 view). Raw view stays first-class because it's the debugging tool — when an answer looks wrong, the first question is 'what did retrieval actually feed the model?'"),
      h3("The most important test: honest refusal"),
      p("Retrieval always returns the nearest chunks — there's no threshold below which it returns nothing. Asked 'what about football?' against a knowledge base with no football content, the model was handed eight unrelated chunks and still said the knowledge base doesn't cover it, listing what IS covered, rather than hallucinating. A RAG system that confidently makes things up on out-of-scope questions is worse than no system; this refusal is the trust foundation."),

      h2("3. README"),
      p("Wrote the project README with YC RFS framing, a Mermaid architecture diagram (sources → chunker → ChromaDB → three agents → outputs), run instructions, a tech-stack table, and a roadmap."),

      h2("Day 5 — What Was Tested"),
      bullet("answer_question() — cited answer synthesized live from Slack-sourced chunks with inline source names"),
      bullet("Mode toggle — Get Answer and Raw chunks both render; source-chunks expander works"),
      bullet("Out-of-scope refusal — model declined to answer a topic absent from the knowledge base"),

      divider(),

      // ══════════════════════════════════════════════════════════════════════
      // DAY 6 + 6.5
      // ══════════════════════════════════════════════════════════════════════
      h1("Day 6 & 6.5 — Deployment, Config & UI Polish"),
      p("Date: 2026-06-26", { color: "888888", italics: true }),
      p("Goal: Make the app deployable to Streamlit Cloud, move tunable settings out of code, and polish the UI from a dev tool into something that reads like a product."),

      h2("1. Secrets — st.secrets vs os.getenv"),
      p("Local dev keeps secrets in a .env file read by python-dotenv into the environment (os.getenv). Streamlit Cloud has no .env — it exposes secrets only via st.secrets. Code using just one of these works in one place and silently fails in the other (and the CLI has no Streamlit runtime at all)."),
      p("utils/config.py:get_secret() resolves both: Streamlit secrets first, then the environment. One helper, used everywhere, so all four agents/ingestors share the same logic."),
      h3("Why Google OAuth is fundamentally different on a server"),
      p("Anthropic and Slack keys are static bearer tokens — a string you attach to a request, easy to move into any secrets manager. Google OAuth is an interaction model: flow.run_local_server() opens a browser for consent and writes token.json to disk. A headless server has no browser and an ephemeral disk, and the OAuth client is registered as a 'Desktop app' (localhost redirect). So Drive/Gmail are gated to local-only with a clear notice, rather than hanging the request."),

      h2("2. Deployment Config"),
      bullet(".streamlit/config.toml — dark theme, 200MB upload limit"),
      bullet(".streamlit/secrets.toml.example — committable template; the real secrets.toml is gitignored"),
      bullet("requirements.txt — every dependency pinned for reproducible builds"),
      bullet("crewai removed — it was never imported (the agents are plain Claude API calls) and its 0.5.0 pin caps at Python 3.9, which would break the Cloud build"),

      h2("3. config.yaml — Central Tunables"),
      p("Models per agent, max_tokens, chunk sizes/overlap per source, retrieval counts, and the vector-store settings were hardcoded and scattered across files. They now live in one config.yaml, loaded once via get_config(). Tuning a model or a chunk size is a one-line YAML edit, not a hunt through code. Secrets deliberately stay out of it — those are credentials, not configuration."),

      h2("4. UI Polish (Day 6.5)"),
      bullet("A CSS layer: bordered metric cards, cleaner tabs, source-type badges (gmail/slack/drive/file), confidence chips (green/yellow/red)"),
      bullet("A hero row of live metrics: Total Sources, Total Chunks, Skills Generated"),
      bullet("Stats tab — a source grid with type icons, cleaned names, and count badges"),
      bullet("Skills library — styled cards with confidence chip, owner, and date"),
      bullet("Query — the synthesized answer in a left-accented card"),
      bullet("Empty states when the knowledge base has no chunks"),
      bullet("A unified indigo accent (primaryColor) so sliders, tabs, and buttons match the badges instead of Streamlit's default red"),

      h2("Day 6 / 6.5 — What Was Tested"),
      bullet("get_secret() — resolves from .env locally and falls through correctly when st.secrets is absent; CLI import path intact"),
      bullet("config.yaml — values verified flowing into agents, ingestion, storage, and the dashboard"),
      bullet("App runs end-to-end via Streamlit's AppTest with no exceptions; deployed-server path shows the Google local-only notice"),

      divider(),

      // ── RUNNING THE PROJECT ───────────────────────────────────────────────
      h1("Running the Project"),
      h2("Prerequisites"),
      bullet("Python 3.9, virtualenv at cb-env/"),
      bullet("ANTHROPIC_API_KEY in .env (or Streamlit Cloud secrets) — required for all three agents"),
      bullet("credentials.json from Google Cloud Console (OAuth Desktop app) — optional, for Drive/Gmail (local only)"),
      bullet("SLACK_BOT_TOKEN with channels:read, channels:history, users:read — optional, for Slack ingestion"),
      bullet("Tunables (models, chunk sizes, retrieval counts) live in config.yaml — no code changes to adjust them"),

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
        ["config.yaml", "Central tunables — models, chunk sizes, retrieval counts, vector store"],
        ["utils/config.py", "get_secret() + get_config() + running_on_cloud() — secrets and settings"],
        ["ingestion/chunker.py", "Word-based overlapping text chunker"],
        ["ingestion/file_upload.py", "PDF + DOCX parser — path and bytes variants"],
        ["ingestion/drive.py", "Google Drive OAuth2 connector (local only)"],
        ["ingestion/gmail.py", "Gmail connector — MIME parsing, reply stripping (local only)"],
        ["ingestion/slack.py", "Slack connector — channel transcripts via slack_sdk"],
        ["ingestion/csv_ingest.py", "CSV row-to-prose converter for structured data"],
        ["storage/chroma.py", "ChromaDB wrapper — upsert, cosine query, stats"],
        ["agents/extractor.py", "Claude agent — chunks to structured process JSON"],
        ["agents/validator.py", "Claude agent (Opus) — reviews and improves the draft"],
        ["agents/answerer.py", "Claude agent — cited Q&A synthesis"],
        ["agents/skills_writer.py", "Writes process dicts to YAML skills files"],
        ["dashboard/app.py", "Streamlit UI — Ingest / Query / Skills / Stats tabs"],
        ["ingest.py", "CLI entry point for all ingestion commands"],
        ["run_dashboard.sh", "Launch script — sets PYTHONPATH correctly"],
      ]),

      divider(),

      // ── WEEK 1 COMPLETE ───────────────────────────────────────────────────
      h1("Week 1 Complete — What Shipped & What's Next"),
      p("The original four-week plan compressed into Week 1. The app is feature-complete, deployable, and documented."),
      h2("Shipped"),
      bullet("Four ingestion sources — file upload, Google Drive, Gmail, Slack — all funneling into one chunker and ChromaDB"),
      bullet("Synthesized Q&A with source citations, plus a raw-chunk debugging view"),
      bullet("A 2-agent skills pipeline (extractor → validator) producing reviewed YAML process docs"),
      bullet("API-enforced structured outputs on both extraction agents"),
      bullet("Streamlit Cloud deployment readiness, central config.yaml, and a polished product UI"),
      h2("What's Next"),
      bullet("Thread-aware Slack ingestion (conversations_replies)"),
      bullet("Re-ranking retrieved chunks before synthesis (cross-encoder or LLM re-rank)"),
      bullet("A hosted vector store so a deployed instance persists across restarts"),
      bullet("Authentication + per-tenant isolation — the path toward a small SaaS"),
      p("As a portfolio piece, it's in a shippable state: ingest from four sources, ask a question and get a cited answer, generate a process doc and watch a second agent critique it."),

      new Paragraph({ spacing: { before: 240, after: 0 }, children: [] }),
    ],
  }],
});

Packer.toBuffer(doc).then(buffer => {
  fs.writeFileSync("company_brain_devlog.docx", buffer);
  console.log("Created: docs/company_brain_devlog.docx");

});
