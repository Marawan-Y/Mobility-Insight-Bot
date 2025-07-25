# ───────────────────────────────────────────────────────── app.py ───────────
import os, re, time
from datetime import datetime
from contextlib import contextmanager

import pymysql
import markdown as md
from dotenv import load_dotenv
from flask import Flask, render_template, request, session, flash
import openai
from openai import OpenAI, RateLimitError

# ─── Flask & Jinja Setup ────────────────────────────────────────────────────
load_dotenv()
app = Flask(__name__)
app.secret_key = os.getenv("SECRET_KEY", "change_me")
def render_markdown(text):
    # enable the "tables" (and fenced code, etc.) extensions
    rendered_html = md.markdown(text or "", extensions=["tables", "fenced_code", "nl2br"])
    
    # Add inline CSS directly to the table element
    table_style = 'style="border-collapse: collapse; width: 100%; margin-bottom: 1rem;"'
    th_style = 'style="border: 1px solid #ddd; padding: 8px; text-align: left; background-color: #f2f2f2; font-weight: bold;"'
    td_style = 'style="border: 1px solid #ddd; padding: 8px; text-align: left;"'
    
    # Replace table tags with styled versions
    rendered_html = rendered_html.replace("<table>", f'<table {table_style}>')
    rendered_html = rendered_html.replace("<th>", f'<th {th_style}>')
    rendered_html = rendered_html.replace("<td>", f'<td {td_style}>')
    
    return rendered_html

# Add the filter to your Jinja environment
app.jinja_env.filters["markdown"] = render_markdown
# ─── Database Config ────────────────────────────────────────────────────────
DB_HOST     = os.getenv("DB_HOST", "localhost")
DB_PORT     = int(os.getenv("DB_PORT", 3306))
DB_USER     = os.getenv("DB_USER", "your_user")
DB_PASSWORD = os.getenv("DB_PASSWORD", "your_pass")
DB_NAME     = os.getenv("DB_NAME", "mobility_bot")

# ─── LLM Config ─────────────────────────────────────────────────────────────
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
    openai_client = OpenAI(api_key=OPENAI_API_KEY)

# ─── Database Connection Context Manager ────────────────────────────────────
@contextmanager
def get_db_connection():
    conn = None
    try:
        conn = pymysql.connect(
            host=DB_HOST, port=DB_PORT, user=DB_USER,
            password=DB_PASSWORD, database=DB_NAME,
            charset="utf8mb4"
        )
        yield conn
    except Exception as e:
        if conn:
            conn.rollback()
        raise
    finally:
        if conn:
            conn.close()

# ─── Universal LLM helper (optimized) ──────────────────────────────────────
def call_llm(prompt: str, retries: int = 2, delay: float = 1.0,
             max_tokens: int = 800) -> str:  # Reduced retries and tokens
    for attempt in range(retries):
        try:
            if LLM_PROVIDER == "vertex":
                vertexai.init(project=VERTEX_PROJECT, location=VERTEX_LOCATION)
                model = GenerativeModel(model_name=VERTEX_MODEL)
                return model.generate_content(
                    prompt, temperature=0.5, max_output_tokens=max_tokens
                ).text.strip()
            resp = openai_client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[{"role": "user", "content": prompt}],
                temperature=0.5,
                max_tokens=max_tokens,
                timeout=30  # Add 30 second timeout
            )
            return resp.choices[0].message.content.strip()
        except Exception as e:
            print(f"LLM attempt {attempt+1} failed: {e}")
            if attempt == retries-1:
                return f"Error generating content: {str(e)[:100]}"
            time.sleep(delay)

# ─── LangChain bits (with fallback) ────────────────────────────────────────
try:
    from langchain_openai import ChatOpenAI
    from langchain.chains import LLMChain
    from langchain.prompts import PromptTemplate
    LANGCHAIN_AVAILABLE = True
    llm = ChatOpenAI(temperature=0.7, api_key=OPENAI_API_KEY)
except ImportError:
    try:
        from langchain.chat_models import ChatOpenAI
        from langchain.chains import LLMChain
        from langchain.prompts import PromptTemplate
        LANGCHAIN_AVAILABLE = True
        llm = ChatOpenAI(temperature=0.7)
    except ImportError:
        LANGCHAIN_AVAILABLE = False
        print("LangChain not available, using direct OpenAI calls")

# ─── Utility ----------------------------------------------------------------
def split_trend_blocks(raw_md: str):
    """Return (titles:list, blocks:list) given markdown with 'Trend Title: '"""
    matches = list(re.finditer(r"(?mi)^.*?trend title:\s*(.+)$", raw_md))
    titles, blocks = [], []
    for i, m in enumerate(matches):
        titles.append(m.group(1).strip())
        start = m.end()
        end   = matches[i+1].start() if i+1 < len(matches) else len(raw_md)
        blocks.append(raw_md[start:end].strip())
    return titles, blocks

def extract_confidence_score(block: str) -> float:
    """Extract confidence score from trend block"""
    m = re.search(r"Confidence\s*Score:\s*([0-9.]+)", block, re.IGNORECASE)
    return float(m.group(1)) if m else 0.5

# ─── Autonomous validation helper (simplified) ─────────────────────────────
def autonomous_trend_validation(trend_block: str) -> str:
    # Simplified validation to speed up
    v_prompt = f"Rate this trend 1-10 for market viability:\n{trend_block[:200]}..."
    return call_llm(v_prompt, max_tokens=100)

# ─── Enhanced generate_trends() with structured scouting ──────────────────
def generate_trends(uc: str, sec: str, dem: str) -> str:
    print(f"DEBUG: Starting generate_trends with uc='{uc}', sec='{sec}', dem='{dem}'")
    
    if not uc or not sec or not dem:
        print("DEBUG: Missing input parameters")
        return "Error: Missing input parameters"
    
    print("DEBUG: Creating structured prompt for trend generation")
    
    # Enhanced prompt for better structured output
    prompt_text = f"""Generate exactly 3 comprehensive mobility disruptive Technologies for:
- **Use-case**: {uc}
- **Sector**: {sec}
- **Demand**: {dem}

For each technology, provide the following structured format:

Technology Title: [Compelling and specific trend name]

Confidence Score: [0.1-1.0]

**Confidence Justification:**
- **Market Evidence**: [supporting market data/signals]
- **Technology Readiness**: [current technology maturity]
- **Novelty**: [how novel or innovative this technology is]
- **Industry Adoption**: [adoption indicators]
- **Risk Factors**: [key uncertainties or challenges]

**Description:**
[2-3 sentences describing the technology and its significance]

**Market Impact:**
- **Market Size**: [estimated market opportunity]
- **Timeline**: [expected timeline for mainstream adoption]
- **Key Drivers**: [primary forces driving this trend]

**Value Proposition:**
[Clear value proposition for Schaeffler and customers]

**Key Players:**
[List 3-4 major companies/organizations involved]

**Implementation Readiness:**
- **Technical Feasibility**: [assessment of technical requirements]
- **Market Readiness**: [assessment of market conditions]
- **Competitive Advantage**: [potential advantages for Schaeffler]

---

Make each trend distinct and actionable with realistic confidence scores based on current market conditions."""

    print(f"DEBUG: Created enhanced prompt")
    
    try:
        print("DEBUG: Attempting OpenAI call...")
        
        if not OPENAI_API_KEY:
            print("DEBUG: No OpenAI API key found!")
            return generate_fallback_trends(uc, sec, dem)
        
        result = call_llm(prompt_text, max_tokens=1200)  # Increased for detailed output
        print(f"DEBUG: OpenAI call successful, got: {len(result)} characters")
        
        if not result or len(result.strip()) < 50:
            print("DEBUG: Empty or very short result from OpenAI")
            return generate_fallback_trends(uc, sec, dem)
            
        return result
        
    except Exception as e:
        print(f"DEBUG: OpenAI call failed: {str(e)}")
        return generate_fallback_trends(uc, sec, dem)

def generate_fallback_trends(uc: str, sec: str, dem: str) -> str:
    """Generate enhanced fallback trends with full structure"""
    print("DEBUG: Generating enhanced fallback trends")
    return f"""Trend Title: AI-Enhanced {uc}

Confidence Score: 0.7

**Confidence Justification:**
- **Market Evidence**: Growing investment in AI solutions across {sec} sector
- **Technology Readiness**: Core AI technologies are mature and deployable
- **Industry Adoption**: Early adopters showing positive results
- **Risk Factors**: Integration complexity and regulatory considerations

**Description:**
Artificial intelligence integration is transforming {uc} applications in the {sec} sector to meet growing {dem}. This trend represents a significant shift towards intelligent, adaptive systems.

**Market Impact:**
- **Market Size**: Multi-billion dollar opportunity in AI-enabled {sec}
- **Timeline**: 3-5 years for mainstream adoption
- **Key Drivers**: Efficiency demands, cost reduction, performance optimization

**Value Proposition:**
Enhanced performance, predictive capabilities, and operational efficiency for {uc} applications.

**Key Players:**
- Technology leaders in AI/ML platforms
- {sec} industry incumbents
- Automotive suppliers
- Software solution providers

**Implementation Readiness:**
- **Technical Feasibility**: High - leveraging existing AI frameworks
- **Market Readiness**: Medium - early adoption phase
- **Competitive Advantage**: Strong potential through early market entry

---

Trend Title: Sustainable {sec} Innovation

Confidence Score: 0.8

**Confidence Justification:**
- **Market Evidence**: Regulatory pressure and consumer demand for sustainability
- **Technology Readiness**: Green technologies increasingly viable
- **Industry Adoption**: Industry-wide sustainability commitments
- **Risk Factors**: Higher initial costs and technology transitions

**Description:**
Environmental sustainability is driving new approaches to {dem} within the {sec} industry. Companies are prioritizing eco-friendly solutions and circular economy principles.

**Market Impact:**
- **Market Size**: Rapidly growing green technology market
- **Timeline**: 2-4 years for significant market presence
- **Key Drivers**: Regulatory requirements, ESG mandates, consumer preferences

**Value Proposition:**
Reduced environmental impact, regulatory compliance, and brand differentiation.

**Key Players:**
- Green technology startups
- Established {sec} manufacturers
- Environmental technology providers
- Government agencies and regulators

**Implementation Readiness:**
- **Technical Feasibility**: High - proven sustainable technologies available
- **Market Readiness**: High - strong market demand
- **Competitive Advantage**: Excellent opportunity for sustainability leadership

---

Trend Title: Smart Infrastructure for {uc}

Confidence Score: 0.6

**Confidence Justification:**
- **Market Evidence**: Infrastructure modernization initiatives globally
- **Technology Readiness**: IoT and connectivity technologies mature
- **Industry Adoption**: Pilot projects showing promising results
- **Risk Factors**: High infrastructure investment requirements and long deployment cycles

**Description:**
Intelligent infrastructure development is supporting {dem} requirements in the {sec} sector. This includes connected systems, real-time monitoring, and adaptive infrastructure.

**Market Impact:**
- **Market Size**: Significant public and private infrastructure investment
- **Timeline**: 5-7 years for widespread deployment
- **Key Drivers**: Urban growth, efficiency needs, technology convergence

**Value Proposition:**
Optimized resource utilization, predictive maintenance, and enhanced user experience.

**Key Players:**
- Infrastructure technology companies
- Government agencies
- Telecommunications providers
- System integrators

**Implementation Readiness:**
- **Technical Feasibility**: Medium - requires coordinated technology integration
- **Market Readiness**: Medium - dependent on infrastructure investment cycles
- **Competitive Advantage**: Good potential through strategic partnerships"""

# ─── Enhanced prompt wrappers with structured formatting ──────────────────
def assess_trend(title, block):
    p = f"""## Comprehensive Trend Assessment for "{title}"

{block}

Please provide a structured assessment in the following format:

| Category | Rating (1-10) | Justification |
|----------|---------------|---------------|
| Impact | [score] | [brief explanation] |
| Disruptive Potential | [score] | [brief explanation] |
| Uncertainty | [score] | [brief explanation] |
| Market Size | [score] | [brief explanation] |
| KPIs (Key Performance Indicators) | [score] | [brief explanation] |
| Revenue Potential | [score] | [brief explanation] |
| Competitive Edge | [score] | [brief explanation] |
| Ease of Implementation | [score] | [brief explanation] |
| Scalability | [score] | [brief explanation] |
| Sustainability | [score] | [brief explanation] |

## Summary
Provide a 2-3 sentence overall assessment of this trend's potential."""
    return call_llm(p, max_tokens=800)

def radar_positioning(title, assessment):
    p = f"""{assessment}

## Radar Positioning for "{title}"

**Classification:** [ACT/PREPARE/WATCH]

**Justification:**
- **ACT**: If the trend requires immediate action due to high impact and readiness
- **PREPARE**: If the trend shows promise but needs preparation and monitoring  
- **WATCH**: If the trend is early-stage or uncertain but worth tracking

**Recommended Timeline:** [timeframe]
**Key Action Items:** [list 2-3 specific actions]"""
    return call_llm(p, max_tokens=400)

def pestel_driver(title, block):
    p = f"""{block}

## PESTEL Trend Radar for "{title}"

**Primary Driver:** [Political/Economic/Social/Technological/Ecological/Legal]

**Justification:**
[Explain why this is the primary driver]

**Secondary Factors:**
- **Political**: [impact level and description]
- **Economic**: [impact level and description]  
- **Social**: [impact level and description]
- **Technological**: [impact level and description]
- **Ecological**: [impact level and description]
- **Legal**: [impact level and description]"""
    return call_llm(p, max_tokens=500)

def market_ready_solution(title, block):
    p = f"""{block}

## Path to Market-Ready Services and Products for "{title}"

Please structure the implementation roadmap as follows:

### 1. Technology Integration
- **Current Capabilities**: [assessment]
- **Required Technologies**: [list]
- **Integration Approach**: [strategy]

### 2. Product Development  
- **Product Concept**: [description]
- **Key Features**: [list]
- **Development Timeline**: [timeframe]

### 3. Service Design
- **Service Model**: [description]
- **Customer Journey**: [key touchpoints]
- **Value Proposition**: [core benefits]

### 4. Market Analysis
- **Target Segments**: [primary customers]
- **Market Size**: [estimation]
- **Competitive Landscape**: [key players]

### 5. Regulatory Compliance
- **Key Regulations**: [applicable standards]
- **Compliance Strategy**: [approach]
- **Risk Mitigation**: [measures]

### 6. Manufacturing & Production
- **Production Requirements**: [capabilities needed]
- **Supply Chain**: [key considerations]
- **Quality Standards**: [requirements]

### 7. Launch Strategy
- **Go-to-Market**: [approach]
- **Marketing Strategy**: [key channels]
- **Success Metrics**: [KPIs]"""
    return call_llm(p, max_tokens=1200)

def partners_navigation(title, block):
    p = f"""{block}

## Strategic Partners for "{title}"

Please provide a structured partner analysis:

| Partner Type | Organization | Role/Expertise | Strategic Value | Collaboration Model |
|--------------|--------------|----------------|-----------------|-------------------|
| Technology Provider | [Company Name] | [Specific expertise] | [Value to Schaeffler] | [Partnership approach] |
| Infrastructure Partner | [Company Name] | [Specific expertise] | [Value to Schaeffler] | [Partnership approach] |
| Market/Customer Partner | [Company Name] | [Specific expertise] | [Value to Schaeffler] | [Partnership approach] |
| Academic/Research Partner | [Institution Name] | [Specific expertise] | [Value to Schaeffler] | [Partnership approach] |
| Regulatory/Standards Partner | [Organization Name] | [Specific expertise] | [Value to Schaeffler] | [Partnership approach] |

## Partnership Strategy
- **Primary Partnership Priority**: [most critical partnership]
- **Timeline for Engagement**: [recommended approach]
- **Risk Mitigation**: [partnership risk considerations]"""
    return call_llm(p, max_tokens=800)

# ─── DB helper --------------------------------------------------------------
def save_to_db(uc, sec, dem, trends_md, sel, ass, rad,
               pes, msol, prts, titles=None, blocks=None):
    """Save to database with proper confidence score extraction"""
    confidence_score = None
    
    # Extract confidence score from selected trend
    if titles and blocks and sel in titles:
        idx = titles.index(sel)
        if idx < len(blocks):
            confidence_score = extract_confidence_score(blocks[idx])
    
    try:
        with get_db_connection() as conn:
            cur = conn.cursor()
            cur.execute("""
                INSERT INTO trend_queries (
                  use_case, sector, demand, selected_trend,
                  trend_solutions, trend_assessment, radar_positioning,
                  pestel_tag, market_solution, partners, confidence_score
                ) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
            """, (uc, sec, dem, sel, trends_md, ass, rad, pes,
                  msol, prts, confidence_score))
            conn.commit()
    except Exception as e:
        print(f"Database error saving trend query: {e}")
        flash("Error saving to database", "error")

# ─── Main chat route  (updated with better error handling) -----------------
@app.route("/", methods=["GET", "POST"])
def chat():
    print(f"DEBUG: Request method: {request.method}")
    
    if request.method == "GET":
        print("DEBUG: GET request - clearing session")
        session.clear()
        session["step"] = "identification"
        return render_template("index.html", step="identification")

    print(f"DEBUG: POST request received")
    print(f"DEBUG: Form data: {request.form}")
    print(f"DEBUG: Session step: {session.get('step', 'none')}")

    step = session.get("step")

    try:
        # ------------- Phase 1  Identification ----------------------------------
        if step == "identification":
            uc  = request.form.get("use_case", "").strip()
            sec = request.form.get("sector", "").strip()
            dem = request.form.get("demand", "").strip()
            
            print(f"DEBUG: Received form data - uc='{uc}', sec='{sec}', dem='{dem}'")
            
            if not (uc and sec and dem):
                print("DEBUG: Form validation failed - missing fields")
                flash("Please fill in Use-case, Sector & Demand.", "warning")
                return render_template("index.html", step="identification")

            print("DEBUG: Form validation passed, calling generate_trends...")
            raw = generate_trends(uc, sec, dem)
            print(f"DEBUG: generate_trends returned: {len(raw) if raw else 0} characters")
            
            if not raw or len(raw.strip()) < 10:
                print("DEBUG: Empty or minimal response from generate_trends")
                raw = generate_fallback_trends(uc, sec, dem)
            
            titles, blocks = split_trend_blocks(raw)
            print(f"DEBUG: Split result - {len(titles)} titles, {len(blocks)} blocks")
            
            trends_md = "\n\n".join(f"### Trend {i+1}: {t}\n{blocks[i]}"
                                   for i, t in enumerate(titles))
            
            print(f"DEBUG: Final trends_md length: {len(trends_md)}")

            session.update({
                "step": "scouting",
                "use_case": uc, "sector": sec, "demand": dem,
                "titles": titles, "blocks": blocks, "trends_md": trends_md,
                "remaining_trends": titles.copy(), "validation_results": {}
            })
            
            print("DEBUG: Session updated, rendering scouting template")
            return render_template("index.html", step="scouting")

        # ------------- Phase 2  Scouting ---------------------------------------
        elif step == "scouting":
            idx_str = request.form.get("selected_trend_idx", "")
            action  = request.form.get("action", "")
            
            if not (idx_str.isdigit() and action in ("validate", "implement")):
                flash("Pick one trend and click Validate or Implement.", "warning")
                return render_template("index.html", step="scouting")

            idx = int(idx_str)
            rem = session.get("remaining_trends", [])
            
            if idx < 0 or idx >= len(rem):
                flash("Select a valid trend index.", "warning")
                return render_template("index.html", step="scouting")

            sel   = rem.pop(idx)
            titles = session.get("titles", [])
            blocks = session.get("blocks", [])
            
            if sel not in titles:
                flash("Selected trend not found.", "error")
                return render_template("index.html", step="scouting")
                
            block = blocks[titles.index(sel)]
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
            save_to_db(session["use_case"], session["sector"], session["demand"],
                       session["trends_md"], sel, "", "", "",
                       msol, prts, titles, blocks)
            session["market_solution"] = msol
            session["partners"]        = prts
            session["step"]            = "implementation"
            return render_template("index.html", step="implementation")

        # ------------- Phase 3  Validation --------------------------------------
        elif step == "validation":
            action = request.form.get("action", "")
            sel    = session.get("selected_trend", "")
            titles = session.get("titles", [])
            blocks = session.get("blocks", [])
            
            if not sel or sel not in titles:
                flash("No trend selected for validation.", "error")
                session["step"] = "scouting"
                return render_template("index.html", step="scouting")
                
            block = blocks[titles.index(sel)]

            if action == "validate_more":
                session["step"] = "scouting"
                return render_template("index.html", step="scouting")

            # proceed → implementation
            msol = market_ready_solution(sel, block)
            prts = partners_navigation(sel, block)
            vr   = session["validation_results"].get(sel, {})
            save_to_db(session["use_case"], session["sector"], session["demand"],
                       session["trends_md"], sel,
                       vr.get("assessment", ""), vr.get("radar", ""), vr.get("pestel", ""),
                       msol, prts, titles, blocks)
            session["market_solution"] = msol
            session["partners"]        = prts
            session["step"]            = "implementation"
            return render_template("index.html", step="implementation")

    except Exception as e:
        print(f"ERROR in chat route: {e}")
        import traceback
        traceback.print_exc()
        flash(f"An error occurred: {str(e)}", "error")
        session["step"] = "identification"
        return render_template("index.html", step="identification")

    # Fallback → reset
    session["step"] = "identification"
    return render_template("index.html", step="identification")
# ─────────────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    app.run(debug=True)