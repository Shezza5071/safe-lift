"""Load official manual handling guidance into Cortex Search (H4H.APP.GUIDANCE_SEARCH).

PDFs are parsed in Snowflake with AI_PARSE_DOCUMENT; HTML pages are stripped to text locally.
Run: .venv/bin/python load_guidance.py <download_dir>   (one-off, rerunnable)
"""
import html
import re
import sys
from pathlib import Path

import snowflake.connector

SOURCES = {  # file in download_dir -> citation label
    "model-cop-hazardous-manual-tasks.pdf": "Safe Work Australia, Model Code of Practice: Hazardous manual tasks (2018)",
    "swa_lifting.html": "Safe Work Australia, Lifting, pushing and pulling (manual tasks)",
    "nsw_aged_care.html": "SafeWork NSW, Aged care",
    "vic_transferring.html": "WorkSafe Victoria, Transferring people safely",
}


def html_text(path):
    raw = path.read_text(errors="ignore")
    raw = re.sub(r"(?is)<(script|style|nav|header|footer)[^>]*>.*?</\1>", " ", raw)
    main = re.search(r"(?is)<main[^>]*>(.*?)</main>", raw)
    text = html.unescape(re.sub(r"<[^>]+>", " ", main.group(1) if main else raw))
    return re.sub(r"\s+", " ", text).strip()


def chunks(text, size=1200, overlap=150):
    return [text[i:i + size] for i in range(0, len(text), size - overlap) if len(text[i:i + size]) > 200]


def main(src_dir):
    c = snowflake.connector.connect(connection_name="main").cursor()
    c.execute("create or replace table H4H.APP.GUIDANCE_CHUNKS (source string, chunk string)")
    c.execute("""create stage if not exists H4H.APP.GUIDANCE_STAGE
                 encryption=(type='SNOWFLAKE_SSE') directory=(enable=true)""")
    for name, label in SOURCES.items():
        f = Path(src_dir) / name
        if not f.exists():
            print("skip (missing)", name)
            continue
        if f.suffix == ".pdf":
            c.execute(f"put file://{f} @H4H.APP.GUIDANCE_STAGE overwrite=true auto_compress=false")
            c.execute("alter stage H4H.APP.GUIDANCE_STAGE refresh")
            c.execute(f"""insert into H4H.APP.GUIDANCE_CHUNKS
              select %s, value::string from table(flatten(
                snowflake.cortex.split_text_recursive_character(
                  ai_parse_document(to_file('@H4H.APP.GUIDANCE_STAGE', '{name}'), {{'mode': 'LAYOUT'}}):content::string,
                  'markdown', 1200, 150)))""", (label,))
        else:
            c.executemany("insert into H4H.APP.GUIDANCE_CHUNKS values (%s, %s)",
                          [(label, ch) for ch in chunks(html_text(f))])
        print(name, c.execute("select count(*) from H4H.APP.GUIDANCE_CHUNKS where source=%s", (label,)).fetchone()[0])
    c.execute("""create or replace cortex search service H4H.APP.GUIDANCE_SEARCH on chunk attributes source
                 warehouse=COMPUTE_WH target_lag='1 day' as select source, chunk from H4H.APP.GUIDANCE_CHUNKS""")
    print("GUIDANCE_SEARCH ready")


if __name__ == "__main__":
    main(sys.argv[1])
