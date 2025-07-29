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
from markupsafe import Markup

# ─── Flask & Jinja Setup ────────────────────────────────────────────────────
load_dotenv()
app = Flask(__name__)
app.secret_key = os.getenv("SECRET_KEY", "change_me")

def render_markdown(text):
    """Enhanced markdown renderer with better table formatting"""
    if not text:
        return ""
    
    # Convert markdown to HTML with extensions
    rendered_html = md.markdown(text, extensions=["tables", "fenced_code", "nl2br", "extra"])
    
    # Enhanced table styling
    table_style = '''style="border-collapse: collapse; width: 100%; margin: 1.5rem 0; 
                     box-shadow: 0 2px 4px rgba(0,0,0,0.1); border-radius: 8px; overflow: hidden;"'''
    thead_style = 'style="background-color: #00B140; color: white;"'
    th_style = '''style="border: 1px solid #ddd; padding: 12px 15px; text-align: left; 
                  font-weight: 600; letter-spacing: 0.5px;"'''
    td_style = '''style="border: 1px solid #ddd; padding: 10px 15px; text-align: left; 
                  background-color: white;"'''
    tr_even_style = 'style="background-color: #f8f9fa;"'
    
    # Apply enhanced styles
    rendered_html = rendered_html.replace("<table>", f'<table class="trend-table" {table_style}>')
    rendered_html = rendered_html.replace("<thead>", f'<thead {thead_style}>')
    rendered_html = rendered_html.replace("<th>", f'<th {th_style}>')
    rendered_html = rendered_html.replace("<td>", f'<td {td_style}>')
    
    # Add alternating row colors
    rendered_html = re.sub(r'<tr>(?=.*?<td)', lambda m: '<tr class="even-row">' if m.start() % 2 == 0 else '<tr>', rendered_html)
    
    # Format headers with Schaeffler green
    rendered_html = re.sub(r'<h2>(.*?)</h2>', r'<h2 style="color: #00B140; border-bottom: 2px solid #00B140; padding-bottom: 0.5rem; margin-top: 2rem;">\1</h2>', rendered_html)
    rendered_html = re.sub(r'<h3>(.*?)</h3>', r'<h3 style="color: #003826; margin-top: 1.5rem;">\1</h3>', rendered_html)
    rendered_html = re.sub(r'<h4>(.*?)</h4>', r'<h4 style="color: #00B140; margin-top: 1rem;">\1</h4>', rendered_html)
    
    # Format lists with better spacing
    rendered_html = re.sub(r'<ul>', r'<ul style="margin: 1rem 0; padding-left: 2rem;">', rendered_html)
    rendered_html = re.sub(r'<li>', r'<li style="margin: 0.5rem 0; line-height: 1.6;">', rendered_html)
    
    # Format strong text with Schaeffler green
    rendered_html = re.sub(r'<strong>(.*?)</strong>', r'<strong style="color: #003826; font-weight: 600;">\1</strong>', rendered_html)
    
    # Add container divs for better structure
    rendered_html = f'<div class="rendered-content" style="font-family: -apple-system, BlinkMacSystemFont, \'Segoe UI\', Roboto, sans-serif; line-height: 1.8; color: #2c3e50;">{rendered_html}</div>'
    
    return Markup(rendered_html)

# Add the filter to Jinja environment
app.jinja_env.filters["markdown"] = render_markdown

# ─── User Feedback Configuration ───────────────────────────────────────────
FEEDBACK_FORM_URL = os.getenv("FEEDBACK_FORM_URL", "https://docs.google.com/forms/d/e/1FAIpQLSfT5gGcFuzE_9O1Vca545YmJ83wwzDy-4ZEoerhILOuyNmKWw/viewform?usp=header")

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

# ─── Universal LLM helper (optimized with better prompting) ─────────────────
def call_llm(prompt: str, retries: int = 2, delay: float = 1.0,
             max_tokens: int = 2000) -> str:  # Increased max_tokens
    for attempt in range(retries):
        try:
            if LLM_PROVIDER == "vertex":
                vertexai.init(project=VERTEX_PROJECT, location=VERTEX_LOCATION)
                model = GenerativeModel(model_name=VERTEX_MODEL)
                return model.generate_content(
                    prompt, temperature=0.3, max_output_tokens=max_tokens  # Lower temperature
                ).text.strip()
            
            # Enhanced system prompt for better responses
            system_prompt = """You are a Schaeffler strategic innovation analyst with deep expertise in motion technology, precision components, mechatronics, and thermal management. 

CRITICAL INSTRUCTIONS:
1. ALWAYS provide complete, detailed answers - never cut off mid-sentence
2. FILL ALL PLACEHOLDERS with specific, realistic values and examples
3. Use actual numbers, dates, companies, and specifications
4. Base your responses on Schaeffler's actual capabilities and the mobility industry
5. Format tables properly with complete data in all cells
6. Never repeat the prompt back - only provide the requested analysis"""

            resp = openai_client.chat.completions.create(
                model="gpt-3.5-turbo",
                # model="gpt-4" if "gpt-4" in os.getenv("OPENAI_MODEL", "gpt-3.5-turbo") else "gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.3,  # Lower temperature for consistency
                max_tokens=max_tokens,
                timeout=60  # Increased timeout
            )
            return resp.choices[0].message.content.strip()
        except Exception as e:
            print(f"LLM attempt {attempt+1} failed: {e}")
            if attempt == retries-1:
                return f"Error generating content: {str(e)[:100]}"
            time.sleep(delay)

# ─── Utility Functions ──────────────────────────────────────────────────────
def split_trend_blocks(raw_md: str):
    """Return (titles:list, blocks:list) given markdown with 'Technology Title: '"""
    matches = list(re.finditer(r"(?mi)^.*?technology title:\s*(.+)$", raw_md))
    titles, blocks = [], []
    for i, m in enumerate(matches):
        titles.append(m.group(1).strip())
        start = m.end()
        end = matches[i+1].start() if i+1 < len(matches) else len(raw_md)
        blocks.append(raw_md[start:end].strip())
    return titles, blocks

def extract_confidence_score(block: str) -> float:
    """Extract confidence score from trend block"""
    m = re.search(r"Confidence\s*Score:\s*([0-9.]+)", block, re.IGNORECASE)
    return float(m.group(1)) if m else 0.5

# ─── Enhanced assessment with fixed prompting ───────────────────────────────
def assess_trend(title, block):
    # More explicit prompt to ensure complete responses
    p = f"""## Strategic Technology Assessment for "{title}"

Based on the following technology description, provide a COMPLETE assessment using Schaeffler's Innovation-to-Business (P³) framework:

{block}

INSTRUCTIONS: Create a comprehensive assessment with the following EXACT structure. Fill EVERY field with specific, realistic data:

### Assessment Matrix

Create a table with these EXACT columns and fill ALL cells with specific values:
- Assessment Dimension (exact dimensions listed below)
- Score (1-10) - provide actual numbers
- Strategic Justification - specific reasons related to Schaeffler
- Action Items - concrete next steps

REQUIRED Assessment Dimensions (use these EXACTLY):
1. Motion Technology Impact
2. Disruptive Potential
3. Technology Uncertainty
4. Market Opportunity (TAM)
5. Synergy with Vitesco
6. Sustainability Impact
7. Customer Value Creation
8. Manufacturing Readiness
9. Partnership Ecosystem
10. ROI Potential

### Executive Summary

Provide ALL of the following with SPECIFIC values:
- Strategic Recommendation: [GO or NO-GO with clear reasoning]
- Priority Level: [Critical/High/Medium/Low with justification]
- Investment Range: [€X-Y million over Z years - use real numbers]
- Expected Returns: [Specific revenue and timeline]

### Risk Mitigation Strategy

List specific strategies for:
- Technical Risks: [Concrete mitigation approaches]
- Market Risks: [Specific hedging strategies]
- Competitive Risks: [Clear defensive positioning]

Remember: Fill ALL placeholders with realistic, specific values. Do NOT leave any [brackets] unfilled."""
    
    result = call_llm(p, max_tokens=2000)
    return result

# ─── Enhanced radar positioning ─────────────────────────────────────────────
def radar_positioning(title, assessment):
    p = f"""Based on this assessment:
{assessment}

## Technology Radar Positioning for "{title}"

Provide a COMPLETE radar positioning analysis:

### Radar Classification
Choose ONE classification and explain: ACT / PREPARE / WATCH

### Horizon Mapping
Create a table with:
- Horizon 1 (1-3 years): List 3 specific opportunities
- Horizon 2 (3-7 years): List 3 specific innovations
- Horizon 3 (7+ years): List 3 breakthrough possibilities

### Action Framework
Based on your classification, provide:

**90-Day Action Plan**: List 3 specific milestones with dates
**Resource Allocation**: Specify teams, budget (use real numbers), facilities
**Success Metrics**: List 5 concrete KPIs with target values

### Implementation Timeline
Create a table showing:
- Q1-Q2: Immediate actions (list 3)
- Q3-Q4: Medium-term milestones (list 3)
- Year 2+: Long-term objectives (list 3)

### Key Success Factors
List and explain 3 critical enablers with specific details.

Fill ALL sections with concrete, specific information. No placeholders."""
    
    return call_llm(p, max_tokens=1500)

# ─── Fixed innovation classification ────────────────────────────────────────
def relation_criteria(title, block):
    p = f"""Analyze this technology for Schaeffler:

{block}

## Strategic Innovation Classification for "{title}"

### Innovation Classification Matrix

Classify into ONE quadrant and explain:
- EXPLOIT: Incremental improvements to existing technologies
- EXTEND: New technologies in existing markets  
- DISRUPTIVE: Existing tech creating new markets
- RADICAL: Breakthrough tech for emerging ecosystems

### Technology Assessment
Rate 1-10 and explain:
- Technology Novelty for Schaeffler: [score] - [explanation]
- Current Capabilities: [list 3 specific Schaeffler technologies]
- Technology Gaps: [list 3 specific gaps]
- Development Path: [Build/Buy/Partner/Acquire - explain choice]

### Market Assessment  
Rate 1-10 and explain:
- Market Maturity: [score] - [explanation]
- Customer Readiness: [Early Adopters/Early Majority/Late Majority]
- Market Development Needs: [list 3 specific needs]
- Competitive Position: [explain first-mover vs fast-follower]

### Implementation Roadmap
Provide specific details for each phase:

**Phase 1 - Validation (Months 1-6)**
- Technical Milestones: [list 3 specific deliverables]
- Budget: €[X] million (use realistic number)
- Go/No-Go Criteria: [list 3 specific metrics]

**Phase 2 - Development (Months 7-18)**  
- Development Goals: [list 3 specific objectives]
- Budget: €[Y] million (use realistic number)
- Scale-Up Triggers: [list 3 specific signals]

**Phase 3 - Commercialization (Months 19+)**
- Production Plans: [specify facilities and capacity]
- Budget: €[Z] million (use realistic number)  
- Revenue Target: €[A] million by year [B]

### Strategic Recommendation
Provide a clear, actionable recommendation with specific next steps.

Use real numbers and specific details throughout. No placeholders."""
    
    return call_llm(p, max_tokens=1800)

# ─── Fixed market ready solution ────────────────────────────────────────────
def market_ready_solution(title, block, sec):
    # Completely restructured prompt for better results
    p = f"""Create a comprehensive implementation roadmap for "{title}" in the {sec} sector.

Technology context:
{block}

PROVIDE A COMPLETE ROADMAP WITH THESE EXACT SECTIONS:

## 1. Core Technology Architecture

### Technology Stack (create a detailed table)
List 3 enabling technologies with:
- Technology name (be specific)
- Purpose (how it enables the solution)
- Impact (measurable benefit)
- Specifications (technical details)

### Detailed Specifications
For EACH technology provide:
- Strategic purpose
- Performance metrics (use numbers)
- Integration requirements
- Compliance standards

## 2. Schaeffler Implementation Requirements

### Competency Matrix (create a table)
Show how Schaeffler leverages:
- Precision Engineering: tolerances, methods
- Mechatronics: sensor specs, control systems
- Thermal Management: heat dissipation, efficiency
- Advanced Materials: specific materials, treatments

## 3. System Architecture

Describe:
- Hardware components (list 5+ specific parts)
- Software platform (OS, frameworks, security)
- Testing requirements (temperature ranges, cycles)
- Integration points (protocols, standards)

## 4. Manufacturing Strategy

### Production Network (create a table)
List facilities:
- Europe: [city], [capacity], [role]
- Americas: [city], [capacity], [role]
- Asia: [city], [capacity], [role]
- Timeline for each location

## 5. Development Timeline

### Milestones (create a Gantt-style table)
Show phases from Q1 2025 through 2027+:
- Concept validation
- Prototype testing
- Customer trials
- Industrialization
- Volume production

## 6. Business Case

### Financial Projections (create a detailed table)
5-year projection with:
- Revenue by year (use realistic numbers)
- Investment required (R&D, CapEx, OpEx)
- ROI calculation
- Break-even point

## 7. Risk Management

### Risk Matrix (create a table)
For each risk type:
- Probability (Low/Med/High)
- Impact (1-5 scale)
- Mitigation strategy
- Contingency plan

## 8. Success Metrics

List 10 specific KPIs with target values for:
- Year 1 milestones
- Long-term goals
- Market penetration
- Financial performance

USE SPECIFIC NUMBERS, REAL LOCATIONS, AND CONCRETE DETAILS THROUGHOUT.
NO PLACEHOLDERS OR BRACKETS."""
    
    return call_llm(p, max_tokens=2500)

# ─── Fixed partners navigation ──────────────────────────────────────────────
def partners_navigation(title, block):
    p = f"""Create a strategic partnership plan for "{title}".

Context:
{block}

PROVIDE A COMPLETE PARTNERSHIP STRATEGY:

## Strategic Partner Analysis

### Partner Matrix (create a detailed table)
Include 5 partner types with:
- Partner Type (Technology/Infrastructure/Market/Academic/Regulatory)
- Organization Name (use real companies)
- Core Expertise (specific capabilities)
- Strategic Value (how they help Schaeffler)
- Collaboration Model (JV/License/Alliance)
- Priority (High/Medium/Low)

## Detailed Partner Profiles

### Technology Partners
Profile 2 specific partners:
- Company name and background
- Specific technologies they bring
- Previous collaboration examples
- Proposed partnership structure
- Expected outcomes with timeline

### Market Partners  
Profile 2 specific partners:
- OEM or customer name
- Market position and reach
- Innovation track record
- Co-development opportunities
- Revenue potential (use numbers)

## Partner Selection Criteria

### Evaluation Matrix (create a table)
Show criteria with weights:
- Strategic Alignment (25%)
- Technical Capability (30%)
- Market Position (20%)
- Financial Stability (15%)
- Cultural Fit (10%)

## Implementation Strategy

### Phase 1: Engagement (Months 1-3)
List specific actions:
- Executive meetings
- Technical assessments
- Legal frameworks
- Pilot projects

### Phase 2: Execution (Months 4-12)
List specific activities:
- R&D initiatives
- Resource allocation
- Milestone tracking
- Performance reviews

## Risk Mitigation

### Partnership Risks (create a table)
For each risk:
- Risk type
- Impact level
- Mitigation strategy
- Contingency plan

## Governance Framework

Describe:
- Committee structure
- Meeting cadence
- Decision rights
- Success metrics
- Communication protocols

USE REAL COMPANY NAMES AND SPECIFIC DETAILS. NO GENERIC PLACEHOLDERS."""
    
    return call_llm(p, max_tokens=2000)

# ─── Database helper with better error handling ─────────────────────────────
def save_to_db(uc, sec, dem, trends_md, sel, ass, rad,
               rel, msol, prts, titles=None, blocks=None):
    """Save to database with proper confidence score extraction and session ID"""
    confidence_score = None
    
    # Extract confidence score from selected trend
    if titles and blocks and sel in titles:
        idx = titles.index(sel)
        if idx < len(blocks):
            confidence_score = extract_confidence_score(blocks[idx])
    
    # Generate session ID for feedback tracking
    session_id = session.get('session_id', None)
    if not session_id:
        session_id = f"session_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{os.urandom(4).hex()}"
        session['session_id'] = session_id
    
    try:
        with get_db_connection() as conn:
            cur = conn.cursor()
            
            # First check if table exists and create if not
            cur.execute("""
                CREATE TABLE IF NOT EXISTS trend_queries (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    use_case VARCHAR(255),
                    sector VARCHAR(255),
                    demand TEXT,
                    selected_trend VARCHAR(255),
                    trend_solutions TEXT,
                    trend_assessment TEXT,
                    radar_positioning TEXT,
                    pestel_tag TEXT,
                    market_solution TEXT,
                    partners TEXT,
                    confidence_score FLOAT,
                    session_id VARCHAR(100),
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
            """)
            
            # Insert the data
            cur.execute("""
                INSERT INTO trend_queries (
                    use_case, sector, demand, selected_trend,
                    trend_solutions, trend_assessment, radar_positioning,
                    pestel_tag, market_solution, partners, confidence_score,
                    session_id
                ) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
            """, (uc, sec, dem, sel, trends_md, ass, rad, rel,
                  msol, prts, confidence_score, session_id))
            conn.commit()
            print(f"Successfully saved to database with session_id: {session_id}")
    except Exception as e:
        print(f"Database error: {e}")
        print(f"Error type: {type(e).__name__}")
        # Don't flash error to user, just log it
        # Continue execution even if database fails

# ─── Generate trends with better structure ──────────────────────────────────
def generate_trends(uc: str, sec: str, dem: str) -> str:
    print(f"DEBUG: Starting generate_trends with uc='{uc}', sec='{sec}', dem='{dem}'")
    
    if not uc or not sec or not dem:
        print("DEBUG: Missing input parameters")
        return "Error: Missing input parameters"
    
    # Enhanced prompt with clearer instructions
    prompt_text = f"""Generate exactly 3 mobility disruptive technologies for Schaeffler.

Context:
- Use-case: {uc}
- Sector: {sec}  
- Demand: {dem}

For EACH of the 3 technologies, provide:

Technology Title: [Specific name - be creative and specific]

Confidence Score: [0.7-0.9 - use decimals]

**Strategic Alignment with Schaeffler:**
- Motion Technology Fit: [Specific product families: Guide/Transmit/Control/Generate/Power/Drive/Energize/Sustain Motion]
- Division Relevance: [E-Mobility/Powertrain & Chassis/Vehicle Lifetime Solutions/Bearings & Industrial]
- Core Competency: [Precision components/Mechatronics/Thermal management/Advanced materials]

**Confidence Justification:**
- Market Evidence: [Use specific numbers - market size in €, CAGR %]
- Technology Readiness Level: [1-9 with explanation]
- Regulatory Readiness: [Specific standards like ISO 26262]
- Industry Adoption: [Name specific OEMs]
- Risk Factors: [2-3 specific challenges]

**Description:**
[2-3 sentences on transformative potential]

**Market Impact Analysis:**
- Timeline: [Specific milestones for 12mo/36mo/60mo]
- Regional Priorities: [Europe/Americas/Asia-Pacific/China]
- Key Drivers: [List 3-4 specific drivers]

**Value Proposition:**
[1-2 sentences on Schaeffler's unique advantages]

**Competitive Landscape:**
- Technology Leaders: [Name 2-3 real companies]
- Potential Partners: [Microsoft/SAP/Fraunhofer/others]
- Competitive Threats: [Specific companies]

**Implementation Readiness:**
- Technical Feasibility: [High/Medium/Low with reason]
- Manufacturing Readiness: [Specific facilities]
- Market Readiness: [Customer demand level]
- Partnership Requirements: [Key collaborations needed]

---

Ensure each technology is distinct and uses specific, realistic details."""

    print("DEBUG: Calling LLM with enhanced prompt")
    
    try:
        result = call_llm(prompt_text, max_tokens=2500)
        print(f"DEBUG: LLM returned {len(result)} characters")
        
        if not result or len(result.strip()) < 50:
            print("DEBUG: Using fallback trends")
            return generate_fallback_trends(uc, sec, dem)
            
        return result
        
    except Exception as e:
        print(f"DEBUG: LLM call failed: {str(e)}")
        return generate_fallback_trends(uc, sec, dem)

def generate_fallback_trends(uc: str, sec: str, dem: str) -> str:
    """Generate enhanced fallback trends with full structure"""
    print("DEBUG: Generating fallback trends")
    return f"""Technology Title: AI-Powered Predictive Motion Control for {uc}

Confidence Score: 0.75

**Strategic Alignment with Schaeffler:**
- **Motion Technology Fit**: Control Motion and Guide Motion product families
- **Division Relevance**: E-Mobility and Powertrain & Chassis divisions
- **Core Competency Leverage**: Mechatronics expertise with advanced control algorithms

**Confidence Justification:**
- **Market Evidence**: €4.2B global market, 23% CAGR through 2030
- **Technology Readiness Level**: 7 - System prototype demonstrated
- **Regulatory Readiness**: ISO 26262 ASIL-B compliant
- **Industry Adoption**: BMW, Mercedes, and VW pilot programs active
- **Risk Factors**: Data quality requirements, real-time processing constraints

**Description:**
AI-powered predictive motion control transforms {uc} applications in the {sec} sector by anticipating system behavior and optimizing performance in real-time. This technology enables unprecedented efficiency and reliability while supporting carbon neutrality goals.

**Market Impact Analysis:**
- **TAM/SAM/SOM**: €12B / €3.5B / €420M by 2030
- **Timeline**: 12mo - Prototype validation, 36mo - OEM integration, 60mo - Volume production
- **Regional Priorities**: Europe (regulation), China (volume), Americas (innovation)
- **Key Market Drivers**: Autonomous driving, energy efficiency, predictive maintenance

**Value Proposition for Schaeffler:**
Leverage 150+ years of motion expertise combined with Microsoft Azure partnership for cloud-based AI solutions.

**Key Players & Competitive Landscape:**
- **Technology Leaders**: NVIDIA, MathWorks
- **Potential Partners**: Microsoft Azure, Fraunhofer IIS
- **Competitive Threats**: Bosch, Chinese AI startups

**Implementation Readiness Assessment:**
- **Technical Feasibility**: High - builds on OPTIME platform
- **Manufacturing Readiness**: Retrofit existing lines
- **Market Readiness**: Strong OEM demand
- **Partnership Requirements**: Microsoft collaboration for edge AI

---

Technology Title: Sustainable Thermal Management Systems for {dem}

Confidence Score: 0.82

**Strategic Alignment with Schaeffler:**
- **Motion Technology Fit**: Energize Motion and Sustain Motion families
- **Division Relevance**: E-Mobility division primary
- **Core Competency Leverage**: Thermal management from 4-in-1 e-axle

**Confidence Justification:**
- **Market Evidence**: €45B market by 2027, 15% CAGR
- **Technology Readiness Level**: 8 - System qualified
- **Regulatory Readiness**: Euro 7 and China VI compliant
- **Industry Adoption**: Industry-wide shift to integrated solutions
- **Risk Factors**: Material costs, system complexity

**Description:**
Next-generation sustainable thermal management revolutionizes {dem} requirements in {sec} through bio-based coolants and intelligent heat recovery, supporting performance optimization and carbon neutrality.

**Market Impact Analysis:**
- **TAM/SAM/SOM**: €45B / €12B / €1.8B
- **Timeline**: 12mo - Validation, 36mo - Integration, 60mo - Global rollout
- **Regional Priorities**: China (EV growth), Europe (regulations), Americas (commercial)
- **Key Market Drivers**: EV thermal needs, circular economy, extreme weather

**Value Proposition for Schaeffler:**
Unique position combining ICE heritage with e-mobility innovation plus Vitesco capabilities.

**Key Players & Competitive Landscape:**
- **Technology Leaders**: Valeo, Mahle
- **Potential Partners**: BASF, SAP
- **Competitive Threats**: BYD, Denso

**Implementation Readiness Assessment:**
- **Technical Feasibility**: Very high - proven technology
- **Manufacturing Readiness**: Troy, MI and Bühl facilities ready
- **Market Readiness**: Immediate EV demand
- **Partnership Requirements**: Material suppliers

---

Technology Title: Intelligent Infrastructure Connectivity for {uc}

Confidence Score: 0.68

**Strategic Alignment with Schaeffler:**
- **Motion Technology Fit**: Generate Motion and Power Motion with digital
- **Division Relevance**: Bearings & Industrial Solutions
- **Core Competency Leverage**: Sensor integration, condition monitoring

**Confidence Justification:**
- **Market Evidence**: €8.5B V2X market by 2030, 28% CAGR
- **Technology Readiness Level**: 6 - Technology demonstrated
- **Regulatory Readiness**: C-V2X standards evolving
- **Industry Adoption**: 200+ smart city pilots globally
- **Risk Factors**: Investment cycles, standards, cybersecurity

**Description:**
Intelligent infrastructure connectivity transforms {uc} by enabling real-time communication between vehicles, infrastructure, and motion components for optimized traffic flow and enhanced safety.

**Market Impact Analysis:**
- **TAM/SAM/SOM**: €25B / €6B / €600M
- **Timeline**: 12mo - Pilots, 36mo - Urban rollout, 60mo - Highways
- **Regional Priorities**: China (investment), Europe (Green Deal), Singapore
- **Key Market Drivers**: Congestion, autonomous vehicles, sustainability

**Value Proposition for Schaeffler:**
Embed intelligence into infrastructure bearings creating data service revenue streams.

**Key Players & Competitive Landscape:**
- **Technology Leaders**: Qualcomm, Siemens
- **Potential Partners**: Microsoft Azure IoT, Deutsche Telekom
- **Competitive Threats**: Huawei, Continental

**Implementation Readiness Assessment:**
- **Technical Feasibility**: Medium - ecosystem coordination needed
- **Manufacturing Readiness**: Adapt sensor production
- **Market Readiness**: Growing but fragmented
- **Partnership Requirements**: Telecom providers, city planners"""

# ─── Main chat route ────────────────────────────────────────────────────────
@app.route("/", methods=["GET", "POST"])
def chat():
    print(f"DEBUG: Request method: {request.method}")
    
    if request.method == "GET":
        print("DEBUG: GET request - clearing session")
        session.clear()
        session["step"] = "identification"
        session["session_id"] = f"session_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{os.urandom(4).hex()}"
        return render_template("index.html", step="identification", feedback_url=FEEDBACK_FORM_URL)

    print(f"DEBUG: POST request received")
    step = session.get("step")

    try:
        # Phase 1: Identification
        if step == "identification":
            uc = request.form.get("use_case", "").strip()
            sec = request.form.get("sector", "").strip()
            dem = request.form.get("demand", "").strip()
           
            print(f"DEBUG: Received form data - uc='{uc}', sec='{sec}', dem='{dem}'")
           
            if not (uc and sec and dem):
                print("DEBUG: Form validation failed - missing fields")
                flash("Please fill in Use-case, Sector & Demand.", "warning")
                return render_template("index.html", step="identification", feedback_url=FEEDBACK_FORM_URL)

            print("DEBUG: Form validation passed, calling generate_trends...")
            raw = generate_trends(uc, sec, dem)
            print(f"DEBUG: generate_trends returned: {len(raw) if raw else 0} characters")
           
            if not raw or len(raw.strip()) < 10:
                print("DEBUG: Empty or minimal response from generate_trends")
                raw = generate_fallback_trends(uc, sec, dem)
           
            titles, blocks = split_trend_blocks(raw)
            print(f"DEBUG: Split result - {len(titles)} titles, {len(blocks)} blocks")
           
            if not titles:
                print("DEBUG: No titles found, using fallback")
                raw = generate_fallback_trends(uc, sec, dem)
                titles, blocks = split_trend_blocks(raw)
           
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
            return render_template("index.html", step="scouting", feedback_url=FEEDBACK_FORM_URL)

        # Phase 2: Scouting
        elif step == "scouting":
            idx_str = request.form.get("selected_trend_idx", "")
            action = request.form.get("action", "")
           
            if not (idx_str.isdigit() and action in ("validate", "implement")):
                flash("Pick one trend and click Validate or Implement.", "warning")
                return render_template("index.html", step="scouting", feedback_url=FEEDBACK_FORM_URL)

            idx = int(idx_str)
            rem = session.get("remaining_trends", [])
           
            if idx < 0 or idx >= len(rem):
                flash("Select a valid trend index.", "warning")
                return render_template("index.html", step="scouting", feedback_url=FEEDBACK_FORM_URL)

            sel = rem.pop(idx)
            titles = session.get("titles", [])
            blocks = session.get("blocks", [])
           
            if sel not in titles:
                flash("Selected trend not found.", "error")
                return render_template("index.html", step="scouting", feedback_url=FEEDBACK_FORM_URL)
               
            block = blocks[titles.index(sel)]
            session["selected_trend"] = sel

            if action == "validate":
                print(f"DEBUG: Validating trend: {sel}")
                ass = assess_trend(sel, block)
                rad = radar_positioning(sel, ass)
                rel = relation_criteria(sel, block)
                session["validation_results"][sel] = {
                    "assessment": ass, "radar": rad, "relation": rel
                }
                session["step"] = "validation"
                return render_template("index.html", step="validation", feedback_url=FEEDBACK_FORM_URL)

            # Direct implementation
            print(f"DEBUG: Direct implementation for trend: {sel}")
            msol = market_ready_solution(sel, block, session.get("sector", ""))
            prts = partners_navigation(sel, block)
            save_to_db(session["use_case"], session["sector"], session["demand"],
                       session["trends_md"], sel, "", "", "",
                       msol, prts, titles, blocks)
            session["market_solution"] = msol
            session["partners"] = prts
            session["step"] = "implementation"
            return render_template("index.html", step="implementation", feedback_url=FEEDBACK_FORM_URL)

        # Phase 3: Validation
        elif step == "validation":
            action = request.form.get("action", "")
            sel = session.get("selected_trend", "")
            titles = session.get("titles", [])
            blocks = session.get("blocks", [])
           
            if not sel or sel not in titles:
                flash("No trend selected for validation.", "error")
                session["step"] = "scouting"
                return render_template("index.html", step="scouting", feedback_url=FEEDBACK_FORM_URL)
               
            block = blocks[titles.index(sel)]

            if action == "validate_more":
                session["step"] = "scouting"
                return render_template("index.html", step="scouting", feedback_url=FEEDBACK_FORM_URL)

            # Proceed to implementation
            print(f"DEBUG: Proceeding to implementation for trend: {sel}")
            msol = market_ready_solution(sel, block, session.get("sector", ""))
            prts = partners_navigation(sel, block)
            vr = session["validation_results"].get(sel, {})
            save_to_db(session["use_case"], session["sector"], session["demand"],
                       session["trends_md"], sel,
                       vr.get("assessment", ""), vr.get("radar", ""), vr.get("relation", ""),
                       msol, prts, titles, blocks)
            session["market_solution"] = msol
            session["partners"] = prts
            session["step"] = "implementation"
            return render_template("index.html", step="implementation", feedback_url=FEEDBACK_FORM_URL)

    except Exception as e:
        print(f"ERROR in chat route: {e}")
        import traceback
        traceback.print_exc()
        flash(f"An error occurred: {str(e)}", "error")
        session["step"] = "identification"
        return render_template("index.html", step="identification", feedback_url=FEEDBACK_FORM_URL)

    # Fallback - reset
    session["step"] = "identification"
    return render_template("index.html", step="identification", feedback_url=FEEDBACK_FORM_URL)

# ─── CSS Injection for Better Formatting ────────────────────────────────────
@app.context_processor
def inject_custom_css():
   """Inject custom CSS for enhanced formatting"""
   custom_css = """
   <style>
       /* Enhanced Table Styling */
       .trend-table {
           margin: 2rem 0;
           box-shadow: 0 2px 8px rgba(0,0,0,0.1);
           border-radius: 8px;
           overflow: hidden;
           font-size: 0.95rem;
       }
       
       .trend-table thead {
           background: linear-gradient(135deg, #00B140 0%, #00893D 100%);
       }
       
       .trend-table th {
           color: white !important;
           font-weight: 600;
           text-transform: uppercase;
           font-size: 0.9rem;
           letter-spacing: 0.5px;
       }
       
       .trend-table tr:hover td {
           background-color: #f0f8ff !important;
       }
       
       /* Section Dividers */
       .rendered-content hr {
           border: none;
           border-top: 2px solid #00B140;
           margin: 2rem 0;
           opacity: 0.3;
       }
       
       /* Enhanced Headers */
       .rendered-content h2 {
           position: relative;
           padding-left: 20px;
           margin-top: 2.5rem;
           margin-bottom: 1.5rem;
       }
       
       .rendered-content h2:before {
           content: '';
           position: absolute;
           left: 0;
           top: 50%;
           transform: translateY(-50%);
           width: 4px;
           height: 24px;
           background: #00B140;
           border-radius: 2px;
       }
       
       .rendered-content h3 {
           color: #003826;
           margin-top: 2rem;
           margin-bottom: 1rem;
           font-size: 1.3rem;
       }
       
       .rendered-content h4 {
           color: #00B140;
           margin-top: 1.5rem;
           margin-bottom: 0.8rem;
           font-size: 1.1rem;
       }
       
       /* Enhanced Lists */
       .rendered-content ul {
           margin: 1rem 0;
           padding-left: 2rem;
       }
       
       .rendered-content ul li {
           position: relative;
           padding-left: 20px;
           margin: 0.8rem 0;
           line-height: 1.7;
       }
       
       .rendered-content ul li:before {
           content: '▸';
           position: absolute;
           left: 0;
           color: #00B140;
           font-weight: bold;
       }
       
       /* Info Boxes */
       .info-box {
           background: #f0f8ff;
           border-left: 4px solid #0066CC;
           padding: 1rem 1.5rem;
           margin: 1.5rem 0;
           border-radius: 4px;
       }
       
       .success-box {
           background: #d4edda;
           border-left: 4px solid #28a745;
           padding: 1rem 1.5rem;
           margin: 1.5rem 0;
           border-radius: 4px;
       }
       
       .warning-box {
           background: #fff3cd;
           border-left: 4px solid #ffc107;
           padding: 1rem 1.5rem;
           margin: 1.5rem 0;
           border-radius: 4px;
       }
       
       /* Code Blocks */
       .rendered-content pre {
           background: #f8f9fa;
           border: 1px solid #dee2e6;
           border-radius: 4px;
           padding: 1rem;
           overflow-x: auto;
       }
       
       .rendered-content code {
           background: #f8f9fa;
           padding: 0.2rem 0.4rem;
           border-radius: 3px;
           font-size: 0.9em;
       }
       
       /* Feedback Button */
       .feedback-float {
           position: fixed;
           bottom: 20px;
           right: 20px;
           z-index: 1000;
       }
       
       .feedback-btn {
           background: #00B140;
           color: white;
           padding: 12px 24px;
           border-radius: 50px;
           text-decoration: none;
           display: flex;
           align-items: center;
           gap: 8px;
           box-shadow: 0 4px 12px rgba(0,177,64,0.3);
           transition: all 0.3s ease;
       }
       
       .feedback-btn:hover {
           background: #00893D;
           color: white;
           transform: translateY(-2px);
           box-shadow: 0 6px 20px rgba(0,177,64,0.4);
       }
       
       /* Responsive Design */
       @media (max-width: 768px) {
           .trend-table {
               font-size: 0.85rem;
           }
           
           .trend-table th,
           .trend-table td {
               padding: 8px;
           }
           
           .rendered-content h2 {
               font-size: 1.4rem;
           }
           
           .rendered-content h3 {
               font-size: 1.2rem;
           }
       }
       
       /* Print Styles */
       @media print {
           .feedback-float,
           .btn-primary,
           .btn-secondary {
               display: none !important;
           }
           
           .trend-table {
               box-shadow: none;
               border: 1px solid #ddd;
           }
       }
   </style>
   """
   return dict(custom_css=Markup(custom_css))

# ─── Error Handlers ─────────────────────────────────────────────────────────
@app.errorhandler(404)
def not_found(error):
   return "Page not found", 404

@app.errorhandler(500)
def internal_error(error):
   return "Internal server error", 500

# ─────────────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
   app.run(debug=True)
