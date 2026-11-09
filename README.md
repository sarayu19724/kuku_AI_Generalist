# Promo Finder — runnable prototype

A small Streamlit app for the Kuku Problem 1 brief. It accepts a ZIP of timestamped screenplay files (`episode-*.txt`), finds 20–60 second candidate windows, ranks them using transparent heuristics, and exports Markdown, CSV and JSON.

## Run locally
```bash
python -m venv .venv
# Windows:
.venv\Scripts\activate
# macOS/Linux:
source .venv/bin/activate
pip install -r requirements.txt
streamlit run app.py
```
Open the local URL printed by Streamlit (usually http://localhost:8501), upload the screenplay ZIP, and click **Find promo moments**.

## Input format
ZIP contains one or more `.txt` files named `episode-*.txt`. Each timestamped event should look like:
```
**CHARACTER:**
Start: (00:12.30) | End: (00:14.10)
Dialogue or action text
```
The parser also supports uppercase labels such as `**ACTION:**` and `**CAMERA:**`.

## What it does
- Parses timestamped dialogue/action/camera events.
- Evaluates candidate windows between 20 and 60 seconds.
- Scores opening hook (first 3.5 s), ending cliffhanger (last 5 s), and standalone readability.
- Flags simple spoiler and graphic-violence keyword risks.
- Ranks candidates and lets an editor inspect transcript windows.
- Exports `promos.md`, `promos.csv`, and `promos.json`.

## Limitations
This is a rule-based prototype, not a validated model. Keyword heuristics can miss visual hooks, misunderstand context, and over-score dramatic language. Risk flags are approximate. It does not inspect actual video, generate edits, or publish promos. An editor must approve every cut. For a new screenplay format, update `parse_episode` in `engine.py`.

## Privacy
The app processes uploaded files locally in the Streamlit process and does not call an external model or upload screenplay text to a third-party API. Keep the source screenplay pack private; do not commit it to a public repository.

## CLI run
```bash
python run.py --pack path/to/screenplays.zip --out outputs
```
The CLI writes ranked Markdown, CSV, JSON and a parsing/quality report.

## Tests
```bash
python -m unittest discover -s tests -v
```
