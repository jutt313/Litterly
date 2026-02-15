# Litterly

AI-powered product data enrichment pipeline for e-commerce. Upload raw product data, and Litterly will search the web, scrape product pages, merge data from multiple sources, and generate Shopify-ready product listings with professional copywriting — all automatically.

Built for sellers importing Japanese products to international markets via Shopify + Matrixify.

## What It Does

1. **Upload** a CSV, JSON, or Excel file with your raw product data
2. **Litterly searches** the web (DuckDuckGo) for each product on Amazon Japan, Rakuten, and vendor sites
3. **Scrapes** matched product pages for specs, images, ingredients, certifications, reviews
4. **Merges** data from all sources into one complete product profile
5. **Generates copywriting** — 15 Shopify sections including title, description, USPs, benefits, features, ingredients, product story, and more
6. **Exports** a Matrixify-compatible CSV ready to import into Shopify

## Features

- 4 LLM providers: DeepSeek, OpenAI, Claude, Gemini (pluggable — use any or all)
- 1-20 parallel workers for batch processing
- Real-time progress via WebSocket
- Live CSV download while job is running
- Built-in AI chat assistant ("Litterly") to help diagnose errors and inspect output
- Everything stored locally on your machine
- Dark-themed web UI

## Screenshots

> Coming soon

---

## Setup — Mac

### Prerequisites

- Python 3.10 or newer
- Node.js 18 or newer
- Git

If you don't have them, install with Homebrew:

```bash
# Install Homebrew (if you don't have it)
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"

# Install Python, Node.js, and Git
brew install python node git
```

### Step 1: Clone the repo

```bash
git clone https://github.com/jutt313/Litterly.git
cd Litterly
```

### Step 2: Set up the backend

```bash
# Create a virtual environment
python3 -m venv .venv

# Activate it
source .venv/bin/activate

# Install Python dependencies
pip install -r requirements.txt
```

### Step 3: Add your API keys

```bash
# Copy the example env file
cp .env.example .env
```

Open `.env` in any text editor and add at least one API key:

```
# You only need ONE of these — pick whichever you have:
DEEPSEEK_API_KEY=your-key-here
OPENAI_API_KEY=your-key-here
ANTHROPIC_API_KEY=your-key-here
GEMINI_API_KEY=your-key-here
```

Where to get API keys:
- **DeepSeek** (cheapest): https://platform.deepseek.com/api_keys
- **OpenAI**: https://platform.openai.com/api-keys
- **Claude**: https://console.anthropic.com/
- **Gemini**: https://aistudio.google.com/apikey

### Step 4: Set up the frontend

```bash
cd frontend
npm install
cd ..
```

### Step 5: Run Litterly

Open **two terminal windows**.

**Terminal 1 — Backend:**

```bash
cd Litterly
source .venv/bin/activate
python -m uvicorn backend.main:app --host 0.0.0.0 --port 8000 --reload
```

**Terminal 2 — Frontend:**

```bash
cd Litterly/frontend
npm run dev
```

### Step 6: Open in browser

Go to **http://localhost:3000**

---

## Setup — Windows

### Prerequisites

- Python 3.10 or newer — download from https://www.python.org/downloads/
  - **Important:** Check "Add Python to PATH" during installation
- Node.js 18 or newer — download from https://nodejs.org/
- Git — download from https://git-scm.com/download/win

### Step 1: Clone the repo

Open **Command Prompt** or **PowerShell**:

```cmd
git clone https://github.com/jutt313/Litterly.git
cd Litterly
```

### Step 2: Set up the backend

```cmd
# Create a virtual environment
python -m venv .venv

# Activate it
.venv\Scripts\activate

# Install Python dependencies
pip install -r requirements.txt
```

### Step 3: Add your API keys

```cmd
# Copy the example env file
copy .env.example .env
```

Open `.env` with Notepad and add at least one API key:

```
DEEPSEEK_API_KEY=your-key-here
```

Where to get API keys:
- **DeepSeek** (cheapest): https://platform.deepseek.com/api_keys
- **OpenAI**: https://platform.openai.com/api-keys
- **Claude**: https://console.anthropic.com/
- **Gemini**: https://aistudio.google.com/apikey

### Step 4: Set up the frontend

```cmd
cd frontend
npm install
cd ..
```

### Step 5: Run Litterly

Open **two terminal windows**.

**Terminal 1 — Backend:**

```cmd
cd Litterly
.venv\Scripts\activate
python -m uvicorn backend.main:app --host 0.0.0.0 --port 8000 --reload
```

**Terminal 2 — Frontend:**

```cmd
cd Litterly\frontend
npm run dev
```

### Step 6: Open in browser

Go to **http://localhost:3000**

---

## How to Use

1. Open **http://localhost:3000** in your browser
2. Go to **Settings** and verify your API key is configured
3. Go to **Dashboard** and upload a CSV/JSON/Excel file with your product data
4. Click on the job to open it
5. Choose your **LLM provider** and **number of workers** (1-20)
6. Click **Start Pipeline**
7. Watch real-time progress — each product goes through 6 stages
8. Download the **Live CSV** while running, or **Final CSV** when done
9. Click the chat bubble to ask **Litterly** about your job status, errors, or output data
10. Import the CSV into Shopify using Matrixify

## Input CSV Format

Your CSV needs at minimum a `Title` column. These columns are automatically detected:

| Column | Purpose |
|--------|---------|
| Title | Product name (required) |
| Vendor / Brand | Brand name |
| Body HTML / Description | Existing product description |
| Image Src | Product image URL |
| Variant Price | Product price |
| Variant SKU | Product SKU |
| Tags | Product tags |
| Handle | URL slug |

Any additional columns are preserved as extra data and passed to the pipeline.

## Output

The output is a Matrixify-compatible CSV with these columns:

- **Handle, Title, Body HTML, Vendor, Tags, Status** — Core Shopify fields
- **Variant SKU, Variant Price, Variant Weight** — Variant data (preserved from input)
- **Image Src, Image Alt Text** — Product images
- **6 USP metafields** — `Metafield: custom.usp1` through `usp6`
- **12 section metafields** — specifications, who_is_this_for, benefits, features, what's_inside, how_to_use, product_story, ingredients, certifications, about_brand, shipping, sold_in_stores

All metafields use Shopify's `rich_text_field` JSON format, ready for direct Matrixify import.

## The 6-Agent Pipeline

| # | Agent | What It Does | Uses LLM? |
|---|-------|-------------|-----------|
| 1 | Ingestion | Reads CSV/JSON/Excel, maps columns | No |
| 2 | Matcher | Searches DuckDuckGo, AI verifies matches | Yes |
| 3 | Extractor | Scrapes matched pages for data | Yes |
| 4 | Merger | Merges data from all sources | Yes |
| 5 | Copywriter | Generates 15 Shopify sections | Yes |
| 6 | Exporter | Formats for Matrixify CSV | No |

## Tech Stack

- **Backend:** Python, FastAPI, Pydantic
- **Frontend:** React 19, Vite, Axios
- **LLMs:** DeepSeek, OpenAI, Claude, Gemini
- **Search:** DuckDuckGo (free, no API key needed)
- **Scraping:** httpx, BeautifulSoup
- **Real-time:** WebSocket

## Troubleshooting

**"Upload stuck at Uploading..."**
- Make sure the backend is running on port 8000

**"Chat says error"**
- Check that at least one API key is configured in Settings
- Check the backend terminal for error details

**"No products found in CSV"**
- Make sure your CSV has a `Title` column
- Supported formats: CSV, JSON, Excel (.xlsx, .xls)

**"Products failing at matching stage"**
- Product titles might be too vague — use specific names with brand
- DuckDuckGo might be rate limiting — reduce worker count to 2-3

**Windows: "python not found"**
- Make sure Python is added to PATH (reinstall and check the box)
- Try using `python3` instead of `python`

## License

MIT
