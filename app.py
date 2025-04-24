import os
import re
import time
import pymysql
import markdown
from dotenv import load_dotenv
from flask import (
    Flask, render_template, request,
    session, redirect, url_for, flash
)

# ─── Load environment ─────────────────────────────────────────────────────────
load_dotenv()
app = Flask(__name__)
app.secret_key = os.getenv("SECRET_KEY", "change_me")

# ─── Database config ───────────────────────────────────────────────────────────
DB_HOST     = os.getenv("DB_HOST", "localhost")
DB_PORT     = int(os.getenv("DB_PORT", 3306))
DB_USER     = os.getenv("DB_USER", "your_user")
DB_PASSWORD = os.getenv("DB_PASSWORD", "your_pass")
DB_NAME     = os.getenv("DB_NAME", "mobility_bot")  # or your actual DB

# ─── LLM config ────────────────────────────────────────────────────────────────
LLM_PROVIDER    = os.getenv("LLM_PROVIDER", "openai").lower()
OPENAI_API_KEY  = os.getenv("OPENAI_API_KEY")
VERTEX_PROJECT  = os.getenv("VERTEX_PROJECT")
VERTEX_LOCATION = os.getenv("VERTEX_LOCATION", "us-central1")
VERTEX_MODEL    = os.getenv("VERTEX_MODEL", "gemini-1.0-pro")

if LLM_PROVIDER == "vertex":
    import vertexai
    try:
        from vertexai.preview.generative_models import GenerativeModel
    except ImportError:
        from vertexai.generative_models import GenerativeModel
else:
    from openai import OpenAI
    openai_client = OpenAI(api_key=OPENAI_API_KEY)

def call_llm(prompt, max_retries=3, delay=1.0, max_tokens=1500):
    for attempt in range(max_retries):
        try:
            if LLM_PROVIDER == "vertex":
                vertexai.init(project=VERTEX_PROJECT, location=VERTEX_LOCATION)
                model = GenerativeModel(model_name=VERTEX_MODEL)
                return model.generate_content(
                    prompt,
                    temperature=0.5,
                    max_output_tokens=max_tokens
                ).text.strip()
            else:
                resp = openai_client.chat.completions.create(
                    model="gpt-4-turbo",
                    messages=[{"role":"user","content":prompt}],
                    temperature=0.5,
                    max_tokens=max_tokens
                )
                return resp.choices[0].message.content.strip()
        except Exception as e:
            txt = str(e).lower()
            if any(code in txt for code in ("429", "rate limit", "quota")):
                time.sleep(delay)
                delay *= 2
                continue
            raise
    raise RuntimeError("LLM unavailable after retries")

# ─── Utility to split out exactly 3 trend blocks ──────────────────────────────
def split_trend_blocks(raw_md: str):
    matches = list(re.finditer(r"(?mi)^.*?trend title:\s*(.+)$", raw_md))
    titles, contents = [], []
    for idx, m in enumerate(matches):
        titles.append(m.group(1).strip())
        start = m.end()
        end = matches[idx+1].start() if idx+1 < len(matches) else len(raw_md)
        contents.append(raw_md[start:end].strip())
    return titles, contents

# ─── Step 1: ask the LLM for 3 trends ────────────────────────────────────────────
def generate_trends(use_case, sector, demand):
    prompt = (
        f"You are an expert in mobility technology. The user demand is in **{use_case}** / **{sector}**: “{demand}”.\n\n"
        "Provide **exactly 3** trend solutions. Each must start with “Trend Title: <title>” "
        "then Description:, Relevance / Impact:, Value Proposition:, Key Players:.\n"
        "Return them in Markdown."
    )
    return call_llm(prompt)

# ─── Steps 2–4: assessment, radar, PESTEL ───────────────────────────────────────
def assess_trend(title, block_md):
    prompt = (
        f"## Comprehensive Trend Assessment for “{title}”\n\n"
        f"{block_md}\n\n"
        "Rate 1–10 in a Markdown table for: Impact, Disruptive Potential, Uncertainty, Market Size, "
        "KPIs, Revenue Potential, Competitive Edge, Ease of Implementation, Scalability, Sustainability."
    )
    return call_llm(prompt)

def radar_positioning(title, assess_md):
    prompt = (
        f"{assess_md}\n\n"
        f"## Radar Positioning for “{title}”\n"
        "Classify as **ACT**, **PREPARE**, or **WATCH** and justify briefly."
    )
    return call_llm(prompt, max_tokens=300)

def pestel_driver(title, block_md):
    prompt = (
        f"{block_md}\n\n"
        f"## PESTEL Trend Radar for “{title}”\n"
        "Identify the primary driver (Political/Economic/Social/Technological/Ecological/Legal) and justify."
    )
    return call_llm(prompt, max_tokens=300)

# ─── Save full conversation to MySQL ────────────────────────────────────────────
def save_to_db(uc, sec, dem, trends_md, sel, ass_md, rad_md, pes_md):
    conn = pymysql.connect(
        host=DB_HOST, port=DB_PORT,
        user=DB_USER, password=DB_PASSWORD,
        database=DB_NAME, charset="utf8mb4"
    )
    cur = conn.cursor()
    # ← UPDATED COLUMN NAMES TO MATCH YOUR SCHEMA
    cur.execute("""
        INSERT INTO trend_queries (
            use_case,
            sector,
            demand,
            selected_trend,
            trend_solutions,
            trend_assessment,
            radar_positioning,
            pestel_tag
        ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
    """, (uc, sec, dem, sel, trends_md, ass_md, rad_md, pes_md))
    conn.commit()
    cur.close()
    conn.close()

# ─── The chat endpoint ─────────────────────────────────────────────────────────
@app.route("/", methods=["GET","POST"])
def chat():
    # ---- debug prints ----
    print("=== NEW REQUEST ===")
    print("Method:", request.method)
    print("Form data:", dict(request.form))
    print("Session keys:", list(session.keys()))
    print("LLM_PROVIDER:", LLM_PROVIDER)
    if LLM_PROVIDER == "vertex":
        print("Vertex project/model:", VERTEX_PROJECT, VERTEX_MODEL)
    else:
        print("OpenAI key OK?", bool(OPENAI_API_KEY))

    # GET → clear & show form
    if request.method == "GET":
        session.clear()
        return render_template("index.html", step1_done=False)

    # STEP 1: capture the three inputs
    if not session.get("step1_done"):
        uc  = request.form.get("use_case","").strip()
        sec = request.form.get("sector","").strip()
        dem = request.form.get("demand","").strip()
        if not (uc and sec and dem):
            flash("Please fill in Use-case, Sector & Demand.","warning")
            return redirect(url_for("chat"))

        try:
            raw_md = generate_trends(uc, sec, dem)
        except Exception as e:
            print("LLM Error:", e)
            flash("Error generating trends; please try again later.","danger")
            return redirect(url_for("chat"))

        titles, blocks = split_trend_blocks(raw_md)

        # rebuild with proper numbering
        clean_md = ""
        for i, t in enumerate(titles, start=1):
            clean_md += f"### Trend {i}: {t}\n{blocks[i-1]}\n\n"

        session.update({
            "step1_done": True,
            "use_case": uc,
            "sector": sec,
            "demand": dem,
            "titles": titles,
            "blocks": blocks,
            "trends_md": clean_md
        })

        return render_template(
            "index.html",
            step1_done=True,
            trends=markdown.markdown(clean_md),
            titles=titles,
            selected=None
        )

    # STEP 2+: user picks one trend title
    titles   = session["titles"]
    blocks   = session["blocks"]
    clean_md = session["trends_md"]
    sel      = request.form.get("selected_trend")

    if sel not in titles:
        flash("Select one of the three trends to dive deeper.","warning")
        return render_template(
            "index.html",
            step1_done=True,
            trends=markdown.markdown(clean_md),
            titles=titles,
            selected=None
        )

    idx      = titles.index(sel)
    block_md = blocks[idx]

    # Steps 2–4 in one go
    ass_md = assess_trend(sel, block_md)
    rad_md = radar_positioning(sel, ass_md)
    pes_md = pestel_driver(sel, block_md)

    # persist
    save_to_db(
        session["use_case"],
        session["sector"],
        session["demand"],
        clean_md,
        sel,
        ass_md,
        rad_md,
        pes_md
    )

    return render_template(
        "index.html",
        step1_done=True,
        trends=markdown.markdown(clean_md),
        titles=titles,
        selected=sel,
        assessment=markdown.markdown(ass_md),
        radar=markdown.markdown(rad_md),
        pestel=markdown.markdown(pes_md)
    )

if __name__ == "__main__":
    app.run(debug=True)
