import os
import re
import time
import pymysql
import markdown as md
from dotenv import load_dotenv
from flask import Flask, render_template, request, session, flash

# ─── Flask & Jinja Setup ────────────────────────────────────────────────────
load_dotenv()
app = Flask(__name__)
app.secret_key = os.getenv("SECRET_KEY", "change_me")
app.jinja_env.filters["markdown"] = md.markdown  # allow {{ text|markdown }}

# ─── Database Config ─────────────────────────────────────────────────────────
DB_HOST     = os.getenv("DB_HOST", "localhost")
DB_PORT     = int(os.getenv("DB_PORT", 3306))
DB_USER     = os.getenv("DB_USER", "your_user")
DB_PASSWORD = os.getenv("DB_PASSWORD", "your_pass")
DB_NAME     = os.getenv("DB_NAME", "mobility_bot")

# ─── LLM Config ──────────────────────────────────────────────────────────────
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

def call_llm(prompt, retries=3, delay=1.0, max_tokens=1500):
    for _ in range(retries):
        try:
            if LLM_PROVIDER == "vertex":
                vertexai.init(project=VERTEX_PROJECT, location=VERTEX_LOCATION)
                model = GenerativeModel(model_name=VERTEX_MODEL)
                return model.generate_content(
                    prompt, temperature=0.5, max_output_tokens=max_tokens
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
            if any(code in str(e).lower() for code in ("429","rate limit","quota")):
                time.sleep(delay)
                delay *= 2
                continue
            raise
    raise RuntimeError("LLM unavailable after retries")

def split_trend_blocks(raw_md):
    matches = list(re.finditer(r"(?mi)^.*?trend title:\s*(.+)$", raw_md))
    titles, blocks = [], []
    for i,m in enumerate(matches):
        titles.append(m.group(1).strip())
        start = m.end()
        end = matches[i+1].start() if i+1 < len(matches) else len(raw_md)
        blocks.append(raw_md[start:end].strip())
    return titles, blocks

# ─── Prompt wrappers ─────────────────────────────────────────────────────────
def generate_trends(uc, sec, dem):
    p = (f"You are an expert in mobility tech. Demand in **{uc}** / **{sec}**: “{dem}”.\n\n"
         "Provide **exactly 3** trends. Each must start “Trend Title: <title>” then "
         "Description:, Relevance / Impact:, Value Proposition:, Key Players:.\nReturn in Markdown.")
    return call_llm(p)

def assess_trend(title, block):
    p = (
        f"## Comprehensive Trend Assessment for “{title}”\n\n{block}\n\n"
        "Rate 1–10 in a Markdown table for: Impact, Disruptive Potential, Uncertainty, Market Size, "
        "KPIs, Revenue Potential, Competitive Edge, Ease of Implementation, Scalability, Sustainability."
    )
    return call_llm(p)

def radar_positioning(title, assessment):
    p = (f"{assessment}\n\n## Radar Positioning for “{title}”\n"
         "Classify as **ACT**, **PREPARE**, or **WATCH** and justify briefly.")
    return call_llm(p, max_tokens=300)

def pestel_driver(title, block):
    p = (f"{block}\n\n## PESTEL Trend Radar for “{title}”\n"
         "Identify the primary driver (Political/Economic/Social/Technological/Ecological/Legal) and justify.")
    return call_llm(p, max_tokens=300)

def market_ready_solution(title, block):
    p = (f"{block}\n\n## Path to Market-Ready Services and Products for “{title}”\n"
         "Define implementation steps at Schaeffler: Technology Integration, Product Development, "
         "Service Design, Market Analysis, Regulatory Compliance, Manufacturing & Production, Launch Strategy.")
    return call_llm(p, max_tokens=900)

def partners_navigation(title, block):
    p = (
        f"{block}\n\n"
        f"## Identifying Key Partners for “{title}”\n\n"
        "Return a table with these three columns in this exact order:\n"
        "  1. Partner Type\n"
        "  2. Organization\n"
        "  3. Role/Expertise\n\n"
        "List each partner on its own row.  Do **not** include any narrative or extra text—just the table."
    )
    return call_llm(p, max_tokens=600)

def save_to_db(uc, sec, dem, trends_md, sel, ass, rad, pes, msol, prts):
    conn = pymysql.connect(host=DB_HOST, port=DB_PORT,
                           user=DB_USER, password=DB_PASSWORD,
                           database=DB_NAME, charset="utf8mb4")
    cur = conn.cursor()
    cur.execute("""
        INSERT INTO trend_queries (
            use_case, sector, demand, selected_trend,
            trend_solutions, trend_assessment, radar_positioning,
            pestel_tag, market_solution, partners
        ) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
    """, (uc, sec, dem, sel, trends_md, ass, rad, pes, msol, prts))
    conn.commit()
    cur.close()
    conn.close()

# ─── Main chat route ─────────────────────────────────────────────────────────
@app.route("/", methods=["GET","POST"])
def chat():
    if request.method == "GET":
        session.clear()
        session["step"] = "identification"
        return render_template("index.html", step="identification")

    step = session.get("step")

    # Phase 1 → Identification
    if step == "identification":
        uc  = request.form.get("use_case")
        sec = request.form.get("sector")
        dem = request.form.get("demand","").strip()
        if not (uc and sec and dem):
            flash("Please fill in Use-case, Sector & Demand.", "warning")
            return render_template("index.html", step="identification")
        raw         = generate_trends(uc, sec, dem)
        titles, blocks = split_trend_blocks(raw)
        # build full Markdown blob
        trends_md = "\n\n".join(f"### Trend {i+1}: {t}\n{blocks[i]}"
                               for i,t in enumerate(titles))
        session.update({
            "step":             "scouting",
            "use_case":         uc,
            "sector":           sec,
            "demand":           dem,
            "titles":           titles,
            "blocks":           blocks,
            "trends_md":        trends_md,
            "remaining_trends": titles.copy(),
            "validation_results": {}
        })
        return render_template("index.html", step="scouting")

    # Phase 2 → Scouting (choose & either Validate or Implement)
    if step == "scouting":
        idx_str = request.form.get("selected_trend_idx","")
        action  = request.form.get("action","")
        if not (idx_str.isdigit() and action in ("validate","implement")):
            flash("Pick one trend and click Validate or Implement.", "warning")
            return render_template("index.html", step="scouting")
        idx = int(idx_str)
        rem = session["remaining_trends"]
        if idx<0 or idx>=len(rem):
            flash("Select a valid trend index.", "warning")
            return render_template("index.html", step="scouting")

        sel   = rem.pop(idx)
        block = session["blocks"][ session["titles"].index(sel) ]
        session["selected_trend"] = sel

        if action == "validate":
            ass = assess_trend(sel, block)
            rad = radar_positioning(sel, ass)
            pes = pestel_driver(sel, block)
            session["validation_results"][sel] = {
                "assessment": ass, "radar": rad, "pestel": pes
            }
            session["step"] = "validation"
            return render_template("index.html", step="validation")

        # direct implementation
        msol = market_ready_solution(sel, block)
        prts = partners_navigation(sel, block)
        save_to_db(
            session["use_case"], session["sector"], session["demand"],
            session["trends_md"], sel, "", "", "", msol, prts
        )
        session["market_solution"] = msol
        session["partners"]        = prts
        session["step"]            = "implementation"
        return render_template("index.html", step="implementation")

    # Phase 3 → Validation (after a validation prompt)
    if step == "validation":
        action = request.form.get("action","")
        sel    = session["selected_trend"]
        block  = session["blocks"][ session["titles"].index(sel) ]
        if action == "validate_more":
            session["step"] = "scouting"
            return render_template("index.html", step="scouting")

        # proceed to implementation
        msol = market_ready_solution(sel, block)
        prts = partners_navigation(sel, block)
        # save with existing validation results
        vr = session["validation_results"][sel]
        save_to_db(
            session["use_case"], session["sector"], session["demand"],
            session["trends_md"], sel,
            vr["assessment"], vr["radar"], vr["pestel"],
            msol, prts
        )
        session["market_solution"] = msol
        session["partners"]        = prts
        session["step"]            = "implementation"
        return render_template("index.html", step="implementation")

    # fallback
    session["step"] = "identification"
    return render_template("index.html", step="identification")

if __name__ == "__main__":
    app.run(debug=True)
