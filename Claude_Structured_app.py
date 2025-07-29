# ───────────────────────────────────────────────────────── app.py ───────────
import os, re, time
from datetime import datetime
from contextlib import contextmanager

import pymysql
import markdown as md
from dotenv import load_dotenv
from flask import Flask, render_template, request, session, flash, Markup
import openai
from openai import OpenAI, RateLimitError

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
    
    # Format lists with better spacing
    rendered_html = re.sub(r'<ul>', r'<ul style="margin: 1rem 0; padding-left: 2rem;">', rendered_html)
    rendered_html = re.sub(r'<li>', r'<li style="margin: 0.5rem 0; line-height: 1.6;">', rendered_html)
    
    # Format strong text with Schaeffler green
    rendered_html = re.sub(r'<strong>(.*?)</strong>', r'<strong style="color: #003826; font-weight: 600;">\1</strong>', rendered_html)
    
    # Add container divs for better structure
    rendered_html = f'<div class="rendered-content" style="font-family: -apple-system, BlinkMacSystemFont, \'Segoe UI\', Roboto, sans-serif; line-height: 1.8; color: #2c3e50;">{rendered_html}</div>'
    
    return Markup(rendered_html)

def format_assessment_table(text):
    """Special formatter for assessment tables"""
    # This function specifically handles the assessment table format
    lines = text.strip().split('\n')
    formatted_lines = []
    
    for line in lines:
        # Check if line contains table row data
        if '|' in line and not line.strip().startswith('|---'):
            parts = [p.strip() for p in line.split('|')]
            if len(parts) >= 4:  # Valid table row
                # Apply special formatting for scores
                if parts[2] and any(char.isdigit() for char in parts[2]):
                    # Color code the score
                    score = ''.join(filter(str.isdigit, parts[2]))
                    if score:
                        score_int = int(score)
                        if score_int >= 8:
                            parts[2] = f'<span style="color: #28a745; font-weight: bold;">{parts[2]}</span>'
                        elif score_int >= 6:
                            parts[2] = f'<span style="color: #ffc107; font-weight: bold;">{parts[2]}</span>'
                        else:
                            parts[2] = f'<span style="color: #dc3545; font-weight: bold;">{parts[2]}</span>'
                
                line = ' | '.join(parts)
        
        formatted_lines.append(line)
    
    return '\n'.join(formatted_lines)

# Add the filters to Jinja environment
app.jinja_env.filters["markdown"] = render_markdown
app.jinja_env.filters["format_assessment"] = format_assessment_table

# ─── User Feedback Configuration ───────────────────────────────────────────
FEEDBACK_FORM_URL = os.getenv("FEEDBACK_FORM_URL", "https://forms.google.com/your-form-id")  # Replace with your Google Form URL

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

# ─── Utility Functions ──────────────────────────────────────────────────────
def split_trend_blocks(raw_md: str):
    """Return (titles:list, blocks:list) given markdown with 'Technology Title: '"""
    matches = list(re.finditer(r"(?mi)^.*?technology title:\s*(.+)$", raw_md))
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

def format_trend_block(block: str) -> str:
    """Format trend block for better display"""
    # Add section dividers
    block = re.sub(r'(\*\*Strategic Alignment.*?:\*\*)', r'\n---\n\n\1', block)
    block = re.sub(r'(\*\*Confidence Justification.*?:\*\*)', r'\n---\n\n\1', block)
    block = re.sub(r'(\*\*Description.*?:\*\*)', r'\n---\n\n\1', block)
    block = re.sub(r'(\*\*Market Impact.*?:\*\*)', r'\n---\n\n\1', block)
    block = re.sub(r'(\*\*Value Proposition.*?:\*\*)', r'\n---\n\n\1', block)
    block = re.sub(r'(\*\*Key Players.*?:\*\*)', r'\n---\n\n\1', block)
    block = re.sub(r'(\*\*Implementation Readiness.*?:\*\*)', r'\n---\n\n\1', block)
    
    return block

# ─── Enhanced generate_trends() with strategic context ──────────────────────
def generate_trends(uc: str, sec: str, dem: str) -> str:
    print(f"DEBUG: Starting generate_trends with uc='{uc}', sec='{sec}', dem='{dem}'")
    
    if not uc or not sec or not dem:
        print("DEBUG: Missing input parameters")
        return "Error: Missing input parameters"
    
    print("DEBUG: Creating structured prompt for trend generation")
    
    # Enhanced prompt with Schaeffler-specific strategic context
    prompt_text = f"""As a Schaeffler strategic innovation analyst with expertise in motion technology, precision components, mechatronics, and thermal management, generate exactly 3 comprehensive mobility disruptive technologies.

Consider Schaeffler's capabilities across their 8 product families: Guide Motion, Transmit Motion, Control Motion, Generate Motion, Power Motion, Drive Motion, Energize Motion, and Sustain Motion.

Target specifications:
- **Use-case**: {uc}
- **Sector**: {sec}
- **Demand**: {dem}

For each disruptive technology, provide the following structured analysis aligned with Schaeffler's Innovation-to-Business (P³) strategy:

Technology Title: [Specific disruptive technology name aligned with motion technology expertise]

Confidence Score: [0.1-1.0 based on TRL, MRL, and RRL assessments]

**Strategic Alignment with Schaeffler:**
- **Motion Technology Fit**: [How this aligns with Schaeffler's 8 product families]
- **Division Relevance**: [Which of Schaeffler's 4 divisions would lead: E-Mobility, Powertrain & Chassis, Vehicle Lifetime Solutions, or Bearings & Industrial Solutions]
- **Core Competency Leverage**: [Precision components / Mechatronics / Thermal management / Advanced materials]

**Confidence Justification:**
- **Market Evidence**: [Quantified market signals, growth rates, investment trends]
- **Technology Readiness Level (TRL)**: [1-9 scale with automotive-specific considerations]
- **Regulatory Readiness**: [ISO 26262 compliance, type approval status, emissions standards]
- **Industry Adoption**: [OEM commitments, tier-1 supplier activities, pilot programs]
- **Risk Factors**: [Technical barriers, supply chain challenges, competitive threats]

**Description:**
[2-3 sentences explaining the technology's transformative potential for {sec} mobility applications and alignment with sustainability goals]

**Market Impact Analysis:**
- **TAM/SAM/SOM**: [Total Addressable Market / Serviceable Addressable Market / Serviceable Obtainable Market]
- **Timeline**: [12-month, 36-month, and 60-month milestones]
- **Regional Priorities**: [Europe / Americas / Asia-Pacific / Greater China focus]
- **Key Market Drivers**: [Electrification, autonomous driving, digitalization, sustainability]

**Value Proposition for Schaeffler:**
[Specific competitive advantages leveraging Schaeffler's precision engineering heritage and post-Vitesco merger synergies]

**Key Players & Competitive Landscape:**
- **Technology Leaders**: [2-3 companies with specific capabilities]
- **Potential Partners**: [Microsoft Azure, SAP, Fraunhofer, or other ecosystem players]
- **Competitive Threats**: [Emerging players, particularly from China]

**Implementation Readiness Assessment:**
- **Technical Feasibility**: [Leverage existing Schaeffler capabilities vs. new development needs]
- **Manufacturing Readiness**: [Utilization of 250+ global locations and production capabilities]
- **Market Readiness**: [Customer pull vs. technology push dynamics]
- **Partnership Requirements**: [Critical ecosystem collaborations needed]

---

Ensure each technology is distinct, actionable, and leverages Schaeffler's €25 billion scale and global innovation network."""

    print(f"DEBUG: Created enhanced strategic prompt")
    
    try:
        print("DEBUG: Attempting OpenAI call...")
        
        if not OPENAI_API_KEY:
            print("DEBUG: No OpenAI API key found!")
            return generate_fallback_trends(uc, sec, dem)
        
        result = call_llm(prompt_text, max_tokens=1500)  # Increased for comprehensive output
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
    return f"""Technology Title: AI-Powered Predictive Motion Control for {uc}

Confidence Score: 0.75

**Strategic Alignment with Schaeffler:**
- **Motion Technology Fit**: Directly aligns with Control Motion and Guide Motion product families
- **Division Relevance**: E-Mobility and Powertrain & Chassis divisions would co-lead development
- **Core Competency Leverage**: Combines mechatronics expertise with advanced control algorithms

**Confidence Justification:**
- **Market Evidence**: €4.2B global market for AI in automotive, growing at 23% CAGR
- **Technology Readiness Level (TRL)**: 7 - System prototype demonstrated in operational environment
- **Regulatory Readiness**: ISO 26262 ASIL-B compliant architectures available
- **Industry Adoption**: BMW, Mercedes, and VW running pilot programs
- **Risk Factors**: Data quality requirements, real-time processing constraints

**Description:**
AI-powered predictive motion control transforms {uc} applications in the {sec} sector by anticipating system behavior and optimizing performance in real-time. This technology enables unprecedented efficiency and reliability while supporting Schaeffler's carbon neutrality goals through optimized energy consumption.

**Market Impact Analysis:**
- **TAM/SAM/SOM**: €12B / €3.5B / €420M (3.5% market share target by 2030)
- **Timeline**: 12mo - Prototype validation, 36mo - First OEM integration, 60mo - Volume production
- **Regional Priorities**: Europe (regulatory leadership), China (volume market), Americas (innovation hubs)
- **Key Market Drivers**: Autonomous driving requirements, energy efficiency mandates, predictive maintenance demand

**Value Proposition for Schaeffler:**
Leverage 150+ years of motion expertise combined with Microsoft Azure partnership for cloud-based AI, creating differentiated solutions that traditional software companies cannot match.

**Key Players & Competitive Landscape:**
- **Technology Leaders**: NVIDIA (AI chips), MathWorks (control algorithms)
- **Potential Partners**: Microsoft Azure (cloud AI), Fraunhofer IIS (research)
- **Competitive Threats**: Bosch (integrated systems), Chinese AI startups

**Implementation Readiness Assessment:**
- **Technical Feasibility**: High - builds on existing OPTIME platform and sensor capabilities
- **Manufacturing Readiness**: Retrofit existing production lines with minimal investment
- **Market Readiness**: Strong OEM pull for predictive capabilities
- **Partnership Requirements**: Deepen Microsoft collaboration for edge AI deployment

---

Technology Title: Sustainable Thermal Management Systems for {dem}

Confidence Score: 0.82

**Strategic Alignment with Schaeffler:**
- **Motion Technology Fit**: Energize Motion and Sustain Motion families
- **Division Relevance**: E-Mobility division primary, with Vehicle Lifetime Solutions support
- **Core Competency Leverage**: World-class thermal management expertise from 4-in-1 e-axle development

**Confidence Justification:**
- **Market Evidence**: Thermal management market reaching €45B by 2027, 15% CAGR
- **Technology Readiness Level (TRL)**: 8 - Actual system completed and qualified
- **Regulatory Readiness**: Meets Euro 7 and China VI emissions standards
- **Industry Adoption**: Industry-wide shift to integrated thermal solutions
- **Risk Factors**: Material cost volatility, system complexity integration

**Description:**
Next-generation sustainable thermal management revolutionizes {dem} requirements in {sec} through bio-based coolants, phase-change materials, and intelligent heat recovery. This supports both performance optimization and Schaeffler's 2040 carbon neutrality commitment.

**Market Impact Analysis:**
- **TAM/SAM/SOM**: €45B / €12B / €1.8B (15% market share in addressable segments)
- **Timeline**: 12mo - Material validation, 36mo - System integration, 60mo - Global rollout
- **Regional Priorities**: China (EV growth), Europe (sustainability regulations), Americas (commercial vehicles)
- **Key Market Drivers**: EV battery thermal requirements, circular economy mandates, extreme weather adaptation

**Value Proposition for Schaeffler:**
Unique position combining thermal expertise from ICE heritage with e-mobility innovation, plus Vitesco's electronics cooling capabilities for complete system solutions.

**Key Players & Competitive Landscape:**
- **Technology Leaders**: Valeo (thermal systems), Mahle (cooling modules)
- **Potential Partners**: BASF (sustainable materials), SAP (lifecycle tracking)
- **Competitive Threats**: BYD (vertical integration), Denso (Asian markets)

**Implementation Readiness Assessment:**
- **Technical Feasibility**: Very high - proven technology with innovation enhancements
- **Manufacturing Readiness**: Existing facilities in Troy, MI and Bühl, Germany ready
- **Market Readiness**: Immediate demand from EV manufacturers
- **Partnership Requirements**: Material suppliers for sustainable coolants

---

Technology Title: Intelligent Infrastructure Connectivity for {uc}

Confidence Score: 0.68

**Strategic Alignment with Schaeffler:**
- **Motion Technology Fit**: Generate Motion and Power Motion with digital integration
- **Division Relevance**: Bearings & Industrial Solutions leading infrastructure applications
- **Core Competency Leverage**: Sensor integration, condition monitoring, predictive analytics

**Confidence Justification:**
- **Market Evidence**: V2X market projected at €8.5B by 2030, 28% CAGR
- **Technology Readiness Level (TRL)**: 6 - Technology demonstrated in relevant environment
- **Regulatory Readiness**: C-V2X standards evolving, 5G infrastructure expanding
- **Industry Adoption**: Smart city pilots in 200+ cities globally
- **Risk Factors**: Infrastructure investment cycles, standardization delays, cybersecurity

**Description:**
Intelligent infrastructure connectivity transforms {uc} by enabling real-time communication between vehicles, infrastructure, and Schaeffler's motion components. This creates adaptive systems that optimize traffic flow, reduce emissions, and enhance safety for {dem} applications.

**Market Impact Analysis:**
- **TAM/SAM/SOM**: €25B / €6B / €600M (10% share in component market)
- **Timeline**: 12mo - Pilot deployments, 36mo - Urban rollouts, 60mo - Highway integration
- **Regional Priorities**: China (infrastructure investment), Europe (Green Deal), Singapore (smart nation)
- **Key Market Drivers**: Urban congestion, autonomous vehicle requirements, sustainability goals

**Value Proposition for Schaeffler:**
Embed intelligence into infrastructure bearings and components, creating new revenue streams from data services while leveraging industrial IoT expertise.

**Key Players & Competitive Landscape:**
- **Technology Leaders**: Qualcomm (C-V2X chips), Siemens (infrastructure)
- **Potential Partners**: Microsoft (Azure IoT), Deutsche Telekom (5G networks)
- **Competitive Threats**: Huawei (integrated solutions), Continental (V2X modules)

**Implementation Readiness Assessment:**
- **Technical Feasibility**: Medium - requires ecosystem coordination
- **Manufacturing Readiness**: Adapt existing sensor production capabilities
- **Market Readiness**: Growing but fragmented, requires standards alignment
- **Partnership Requirements**: Telecom providers, infrastructure operators, city planners"""

# ─── Enhanced assessment with strategic criteria ────────────────────────────
def assess_trend(title, block):
   # Pre-format the assessment table structure
   p = f"""## Strategic Technology Assessment for "{title}"

As a Schaeffler innovation strategist, provide a comprehensive assessment using our Innovation-to-Business (P³) framework and strategic priorities.

{block}

Provide a structured assessment using Schaeffler's strategic evaluation criteria. Format the response with clear sections and a professional table:

### Assessment Matrix

| Assessment Dimension | Score (1-10) | Strategic Justification | Action Items |
|---------------------|--------------|------------------------|--------------|
| **Motion Technology Impact** | [score] | [How this advances Schaeffler's motion technology leadership] | [Specific capability development needs] |
| **Disruptive Potential** | [score] | [Market transformation potential and competitive differentiation] | [First-mover opportunities] |
| **Technology Uncertainty** | [score] | [Technical risks and mitigation strategies] | [R&D focus areas] |
| **Market Opportunity (TAM)** | [score] | [Addressable market size and growth trajectory] | [Market entry strategies] |
| **Synergy with Vitesco** | [score] | [Post-merger integration opportunities] | [Cross-division initiatives] |
| **Sustainability Impact** | [score] | [Contribution to 2040 carbon neutrality goal] | [ESG enhancement actions] |
| **Customer Value Creation** | [score] | [Direct benefits to OEMs and end-users] | [Value proposition refinement] |
| **Manufacturing Readiness** | [score] | [Leverage of existing 250+ locations] | [Production ramp-up plan] |
| **Partnership Ecosystem** | [score] | [Alignment with Microsoft, SAP, Fraunhofer partnerships] | [Collaboration priorities] |
| **ROI Potential** | [score] | [Revenue impact and margin improvement] | [Investment requirements] |

### Executive Summary

**Strategic Recommendation**: [Clear GO/NO-GO decision with rationale]

**Priority Level**: [Critical/High/Medium/Low based on strategic fit]

**Investment Range**: [€X-Y million over Z years]

**Expected Returns**: [Revenue potential and timeline]

### Risk Mitigation Strategy

- **Technical Risks**: [Specific mitigation approaches]
- **Market Risks**: [Hedging strategies]
- **Competitive Risks**: [Defensive positioning]"""
   
   result = call_llm(p, max_tokens=1000)
   
   # Post-process to ensure proper formatting
   result = format_assessment_table(result)
   
   return result

# ─── Enhanced radar positioning with action-oriented framework ──────────────
def radar_positioning(title, assessment):
   p = f"""{assessment}

## Technology Radar Positioning for "{title}"

Using Schaeffler's three-horizon innovation framework, classify this technology and provide specific action plans:

### Radar Classification

**PRIMARY CLASSIFICATION:** [ACT/PREPARE/WATCH]

### Horizon Mapping

| Horizon | Timeframe | Focus | Opportunities |
|---------|-----------|-------|---------------|
| **Horizon 1** | 1-3 years | Immediate optimization | [List specific opportunities] |
| **Horizon 2** | 3-7 years | Adjacent innovation | [List potential innovations] |
| **Horizon 3** | 7+ years | Transformative possibilities | [List breakthrough opportunities] |

### Action Framework by Classification

#### If ACT (Immediate Implementation Required)
*Criteria: Technology scores 8+ on market opportunity AND manufacturing readiness*

- **Rationale**: [Why immediate action is critical]
- **90-Day Action Plan**: 
 1. [Specific milestone 1]
 2. [Specific milestone 2]
 3. [Specific milestone 3]
- **Resource Allocation**: [Teams, budget, facilities]
- **Success Metrics**: [KPIs for first year]

#### If PREPARE (Strategic Development Phase)
*Criteria: High potential but requires 6-18 months preparation*

- **Rationale**: [Development needs before deployment]
- **Capability Building**: [Skills, partnerships, infrastructure]
- **Pilot Program Design**: [Test markets and applications]
- **Go/No-Go Criteria**: [Decision gates]

#### If WATCH (Monitor and Reassess)
*Criteria: Promising but premature or uncertain*

- **Rationale**: [Why not ready for investment]
- **Monitoring Plan**: [Tracking indicators]
- **Trigger Points**: [When to reassess]
- **Minimal Investment**: [Learning activities only]

### Implementation Timeline

| Phase | Q1-Q2 | Q3-Q4 | Year 2+ |
|-------|-------|-------|---------|
| **Actions** | [Immediate actions] | [Medium-term milestones] | [Long-term objectives] |
| **Resources** | [Initial allocation] | [Scale-up requirements] | [Full deployment] |
| **Metrics** | [Early indicators] | [Performance measures] | [Success criteria] |

### Key Success Factors

1. **Critical Enabler #1**: [Description and importance]
2. **Critical Enabler #2**: [Description and importance]
3. **Critical Enabler #3**: [Description and importance]"""
   
   return call_llm(p, max_tokens=600)

# ─── Enhanced innovation classification framework ───────────────────────────
def relation_criteria(title, block):
   p = f"""{block}

## Strategic Innovation Classification for "{title}"

As a Schaeffler innovation strategist, analyze this technology using our adapted innovation matrix framework, considering our position as the leading Motion Technology Company.

### Innovation Classification Matrix

<div style="background: #f8f9fa; padding: 20px; border-radius: 10px; margin: 20px 0;">
<h4>Strategic Dimensions:</h4>
<ul>
<li><strong>X-axis</strong>: Technology Novelty for Schaeffler (Low → High)</li>
<li><strong>Y-axis</strong>: Market Novelty for Mobility Sector (Low → High)</li>
</ul>
</div>

### Four Strategic Quadrants

| Quadrant | Definition | Example | Investment Model | Success Metrics |
|----------|------------|---------|------------------|-----------------|
| **EXPLOIT** (Lower Left) | Incremental improvements to existing motion technologies | Enhanced bearing durability | Self-funded R&D | Cost reduction, quality improvement |
| **EXTEND** (Upper Left) | New motion technologies in existing markets | AI-enhanced predictive maintenance | Corporate innovation fund | Technology leadership, premium pricing |
| **DISRUPTIVE** (Lower Right) | Existing tech creating new markets | Precision bearings for urban air mobility | Strategic ventures | New market creation, ecosystem leadership |
| **RADICAL** (Upper Right) | Breakthrough tech for emerging ecosystems | Quantum sensors for autonomous navigation | Corporate VC + universities | IP generation, future positioning |

### Strategic Analysis for "{title}"

#### Primary Classification
**CLASSIFICATION:** [EXPLOIT/EXTEND/DISRUPTIVE/RADICAL]

#### Technology Novelty Assessment

| Aspect | Rating | Details |
|--------|--------|---------|
| **Novelty Level** | [1-10] | [Established/Adjacent/New to Schaeffler/New to World] |
| **Current Capability Base** | - | [Existing Schaeffler technologies that apply] |
| **Technology Gap Analysis** | - | [What new capabilities are needed] |
| **Development Pathway** | - | [Build/Buy/Partner/Acquire] |

#### Market Novelty Assessment

| Aspect | Rating | Details |
|--------|--------|---------|
| **Market Maturity** | [1-10] | [Existing/Adjacent/New to Schaeffler/New to Industry] |
| **Customer Readiness** | - | [Early Adopters/Early Majority/Late Majority] |
| **Market Development Needs** | - | [Education, infrastructure, regulations] |
| **Competitive Dynamics** | - | [First-mover advantages vs. fast-follower benefits] |

### Strategic Implementation Roadmap

#### Phase 1 - Validation (Months 1-6)
- **Technical Proof Points**: [Specific demonstrations needed]
- **Market Validation**: [Customer pilots and feedback loops]
- **Investment**: €[X] budget range
- **Go/No-Go Criteria**: [Clear decision metrics]

#### Phase 2 - Development (Months 7-18)
- **Capability Building**: [Internal development vs. partnerships]
- **Market Development**: [Channel strategies and customer engagement]
- **Investment**: €[Y] budget range
- **Scale-Up Triggers**: [Market signals for expansion]

#### Phase 3 - Commercialization (Months 19+)
- **Production Strategy**: [Which facilities and capacity plans]
- **Go-to-Market**: [Direct sales vs. ecosystem approach]
- **Investment**: €[Z] budget range
- **Success Metrics**: [Revenue targets and market share goals]

### Risk-Return Profile

| Risk Type | Level | Mitigation Strategy | Expected Return Scenario |
|-----------|-------|-------------------|-------------------------|
| **Technical** | [Low/Med/High] | [Specific approaches] | Base: [X]% ROI |
| **Market** | [Low/Med/High] | [Hedging strategies] | Upside: [Y]% ROI |
| **Competitive** | [Low/Med/High] | [Defensive positioning] | Downside: [Z]% ROI |
| **Regulatory** | [Low/Med/High] | [Compliance roadmap] | Timeline: [Years] |

### Strategic Recommendation

<div style="background: #e6f4ea; padding: 20px; border-radius: 10px; border-left: 5px solid #00B140;">
<h4>Final Recommendation:</h4>
[Specific action plan based on classification, including investment level, organizational model, and success metrics aligned with Schaeffler's motion technology leadership vision]
</div>"""
   
   return call_llm(p, max_tokens=1200)

def market_ready_solution(title, block, sec):
   # Enhanced formatting for implementation roadmap
   p = f"""{block}

## Comprehensive Technology Implementation Roadmap for "{title}" in {sec}

<div style="background: #f0f8ff; padding: 15px; border-radius: 10px; margin: 20px 0;">
<strong>Executive Overview:</strong> This implementation roadmap provides a detailed blueprint for bringing "{title}" to market, leveraging Schaeffler's strategic capabilities and global infrastructure.
</div>

### 1. Core Technology Architecture

#### Technology Stack Overview

| Technology Component | Purpose | Impact | Specifications |
|---------------------|---------|--------|----------------|
| **Technology 1** | [Name] | [Strategic purpose] | [Technical details] |
| **Technology 2** | [Name] | [Market differentiation] | [Performance metrics] |
| **Technology 3** | [Name] | [Sustainability gains] | [Efficiency targets] |

#### Detailed Technology Specifications

##### Technology 1: [Specific Technology Name]
<div style="border-left: 4px solid #00B140; padding-left: 20px;">

**Strategic Purpose**: [How this advances Schaeffler's motion technology leadership]

**Revolutionary Impact**: [Transformative effect on {sec} mobility]

**Technical Specifications**:
- Performance Metrics: [Specific quantified targets]
- Integration Requirements: [With existing Schaeffler systems]
- Compliance Standards: [ISO 26262, ASPICE, etc.]

</div>

##### Technology 2: [Specific Technology Name]
<div style="border-left: 4px solid #00B140; padding-left: 20px;">

**Strategic Purpose**: [Market differentiation potential]

**Revolutionary Impact**: [Customer value creation]

**Technical Specifications**:
- Performance Metrics: [Quantified improvements]
- Scalability Parameters: [Volume production considerations]
- Quality Standards: [Zero-defect targets]

</div>

##### Technology 3: [Specific Technology Name]
<div style="border-left: 4px solid #00B140; padding-left: 20px;">

**Strategic Purpose**: [Sustainability and efficiency gains]

**Revolutionary Impact**: [Contribution to carbon neutrality]

**Technical Specifications**:
- Efficiency Gains: [Energy, material, cost reductions]
- Lifecycle Impact: [Cradle-to-grave assessment]
- Circular Economy: [Recycling and reuse strategies]

</div>

### 2. Schaeffler-Specific Implementation Requirements

#### Core Competency Leverage Matrix

| Competency Area | Requirements | Schaeffler Advantage | Implementation Approach |
|-----------------|--------------|---------------------|------------------------|
| **Precision Engineering** | [μm-level tolerances] | [150+ years expertise] | [Production methods] |
| **Mechatronic Integration** | [Sensor/control specs] | [OPTIME platform] | [System architecture] |
| **Thermal Management** | [Heat dissipation needs] | [4-in-1 e-axle expertise] | [Cooling strategies] |
| **Advanced Materials** | [Material properties] | [DLC coating leadership] | [Application methods] |

### 3. System Architecture and Integration

#### Technical Infrastructure Blueprint

<div style="background: #fff3cd; padding: 15px; border-radius: 10px; margin: 20px 0;">
<strong>System Overview:</strong>

**Hardware Systems**
- Core Components: [Detailed BoM with Schaeffler part numbers]
- Modular Architecture: [Scalability approach]
- Interface Standards: [CAN, FlexRay, Ethernet specs]
- Power Requirements: [Voltage, current, efficiency]

**Software Platform**
- Operating System: [Real-time OS requirements]
- Middleware: [ROS2, AUTOSAR frameworks]
- AI/ML Framework: [TensorFlow, PyTorch integration]
- OTA Capabilities: [Update mechanisms and security]

**Testing Environment**
- HIL Systems: [Hardware-in-the-loop specifications]
- Environmental Testing: [-40°C to +85°C, vibration, EMC]
- Endurance Testing: [Million-cycle validation protocols]
- Field Testing: [Real-world validation approach]
</div>

### 4. Manufacturing and Production Strategy

#### Global Production Network Utilization

| Region | Facility | Role | Capacity | Timeline |
|--------|----------|------|----------|----------|
| **Europe** | [Specific location] | Lead factory | [Units/year] | [Start date] |
| **Americas** | [Specific location] | Regional hub | [Units/year] | [Start date] |
| **Asia-Pacific** | [Specific location] | Volume production | [Units/year] | [Start date] |
| **China** | [Specific location] | Local market | [Units/year] | [Start date] |

### 5. Development Timeline and Milestones

#### Gantt Chart Overview

| Phase | Q1 2025 | Q2 2025 | Q3 2025 | Q4 2025 | 2026 | 2027+ |
|-------|---------|---------|---------|---------|------|-------|
| **Concept Validation** | ████████ | ████ | | | | |
| **Prototype Testing** | | ████████ | ████████ | | | |
| **Customer Trials** | | | ████████ | ████████ | | |
| **Industrialization** | | | | ████████ | ████████ | |
| **Volume Production** | | | | | ████████ | ████████ |

### 6. Market Analysis and Business Case

#### Financial Projections Dashboard

<div style="background: #d4edda; padding: 20px; border-radius: 10px; margin: 20px 0;">

**5-Year Revenue Projection**

| Technology | 2026 | 2027 | 2028 | 2029 | 2030 | CAGR |
|------------|------|------|------|------|------|------|
| Technology 1 | €[X]M | €[X]M | €[X]M | €[X]M | €[X]M | [Y]% |
| Technology 2 | €[X]M | €[X]M | €[X]M | €[X]M | €[X]M | [Y]% |
| Technology 3 | €[X]M | €[X]M | €[X]M | €[X]M | €[X]M | [Y]% |
| **Total** | **€[X]M** | **€[X]M** | **€[X]M** | **€[X]M** | **€[X]M** | **[Y]%** |

**Investment Requirements**
- R&D: €[X]M over 3 years
- CapEx: €[Y]M for production setup
- OpEx: €[Z]M annually
- Expected ROI: [X]% by year 5

</div>

### 7. Risk Management Framework

| Risk Category | Probability | Impact | Mitigation Strategy | Contingency Plan |
|---------------|------------|--------|-------------------|------------------|
| **Technical** | [Low/Med/High] | [1-5] | [Specific approaches] | [Backup options] |
| **Market** | [Low/Med/High] | [1-5] | [Hedging strategies] | [Alternative markets] |
| **Supply Chain** | [Low/Med/High] | [1-5] | [Dual sourcing] | [Buffer inventory] |
| **Regulatory** | [Low/Med/High] | [1-5] | [Compliance roadmap] | [Legal support] |

### 8. Success Metrics and KPIs

<div style="background: #e6f4ea; padding: 15px; border-radius: 10px; border-left: 5px solid #00B140;">

**Year 1 Success Criteria**
- Technical milestones achieved: [X]%
- Customer commitments secured: [Y] OEMs
- Production readiness: [Z]% complete
- Market penetration: [A]% of target

**Long-term Success Metrics**
- Market share: [X]% by 2030
- Revenue target: €[Y]M annually
- Profit margin: [Z]%
- Customer satisfaction: >[A]%

</div>"""
   
   return call_llm(p, max_tokens=1800)

def partners_navigation(title, block):
   p = f"""{block}

## Strategic Partnership Ecosystem for "{title}"

<div style="background: #f0f8ff; padding: 15px; border-radius: 10px; margin: 20px 0;">
<strong>Partnership Philosophy:</strong> Building a collaborative ecosystem that leverages complementary strengths to accelerate innovation and market penetration for "{title}".
</div>

### Strategic Partner Analysis

| Partner Type | Organization | Core Expertise | Strategic Value to Schaeffler | Proposed Collaboration Model | Priority |
|--------------|--------------|----------------|------------------------------|----------------------------|----------|
| **Technology Provider** | [Company Name] | [Specific technology expertise] | [How it complements Schaeffler] | [JV/License/Co-development] | High/Med/Low |
| **Infrastructure Partner** | [Company Name] | [Infrastructure capabilities] | [Market access/Scale benefits] | [Strategic alliance] | High/Med/Low |
| **Market/Customer Partner** | [Company Name] | [Market position/Customer base] | [Channel access/Validation] | [Supply agreement/Partnership] | High/Med/Low |
| **Academic/Research Partner** | [Institution Name] | [Research excellence area] | [Innovation pipeline/Talent] | [Joint research/Sponsorship] | High/Med/Low |
| **Regulatory/Standards Partner** | [Organization Name] | [Standards expertise/Influence] | [Compliance/Market shaping] | [Membership/Collaboration] | High/Med/Low |

### Detailed Partner Profiles

#### Technology Partners
<div style="border-left: 4px solid #0066CC; padding-left: 20px; margin: 20px 0;">

**Primary Technology Partner: [Company Name]**
- **Core Competency**: [Specific technology area]
- **Strategic Fit**: [How it aligns with Schaeffler's needs]
- **Collaboration History**: [Previous successful partnerships]
- **Proposed Structure**: [Detailed partnership model]
- **Expected Outcomes**: [Specific deliverables and timeline]

</div>

#### Market Access Partners
<div style="border-left: 4px solid #28a745; padding-left: 20px; margin: 20px 0;">

**Key Customer Partner: [OEM Name]**
- **Market Position**: [Leadership in specific segment]
- **Innovation Appetite**: [Track record of adopting new tech]
- **Schaeffler Relationship**: [Existing business volume/history]
- **Co-development Opportunity**: [Specific applications]
- **Revenue Potential**: €[X]M over [Y] years

</div>

### Partner Selection Criteria & Evaluation

| Criteria | Weight | Description | Evaluation Method |
|----------|--------|-------------|-------------------|
| **Strategic Alignment** | 25% | Fit with Schaeffler's vision and values | Executive assessment |
| **Technical Capability** | 30% | Complementary expertise and resources | Technical due diligence |
| **Market Position** | 20% | Industry standing and customer base | Market analysis |
| **Financial Stability** | 15% | Long-term viability as partner | Financial review |
| **Cultural Fit** | 10% | Collaboration compatibility | Team interactions |

### Partnership Implementation Strategy

#### Phase 1: Partner Engagement (Months 1-3)
<div style="background: #fff3cd; padding: 15px; border-radius: 10px; margin: 20px 0;">

**Immediate Actions:**
1. Executive introductions and vision alignment
2. Technical capability assessments
3. Legal framework establishment
4. Pilot project definition

**Key Deliverables:**
- Signed NDAs and MOUs
- Joint project teams formed
- Initial technical specifications
- Communication protocols established

</div>

#### Phase 2: Collaboration Execution (Months 4-12)
<div style="background: #d4edda; padding: 15px; border-radius: 10px; margin: 20px 0;">

**Development Activities:**
1. Joint R&D initiatives launch
2. Resource allocation and team integration
3. Milestone-based project execution
4. Regular steering committee reviews

**Success Metrics:**
- Technical milestones achieved
- IP framework operational
- Cost-sharing mechanisms active
- Market feedback incorporated

</div>

### Risk Mitigation in Partnerships

| Risk Type | Potential Impact | Mitigation Strategy | Contingency Plan |
|-----------|-----------------|-------------------|------------------|
| **IP Leakage** | High | Clear IP ownership agreements | Legal enforcement options |
| **Partner Dependency** | Medium | Multiple partner options | In-house capability development |
| **Cultural Misalignment** | Medium | Regular communication cadence | Mediation processes |
| **Financial Instability** | Low | Due diligence and monitoring | Alternative partner pipeline |

### Partnership Governance Framework

<div style="background: #e6f4ea; padding: 20px; border-radius: 10px; border-left: 5px solid #00B140;">

**Governance Structure:**
- **Executive Steering Committee**: Quarterly strategic reviews
- **Technical Working Groups**: Bi-weekly progress meetings
- **Commercial Team**: Monthly business reviews
- **Legal/IP Committee**: As-needed issue resolution

**Communication Protocols:**
- Regular video conferences
- Shared project management tools
- Quarterly face-to-face summits
- Annual partnership reviews

**Success Measurement:**
- Joint KPIs and scorecards
- 360-degree feedback processes
- Financial performance tracking
- Innovation output metrics

</div>"""
   
   return call_llm(p, max_tokens=800)

# ─── DB helper with session tracking ────────────────────────────────────────
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
   except Exception as e:
       print(f"Database error saving trend query: {e}")
       flash("Error saving to database", "error")

# ─── Feedback integration helper ────────────────────────────────────────────
def get_feedback_link():
   """Generate feedback form link with session context"""
   session_id = session.get('session_id', 'unknown')
   use_case = session.get('use_case', 'unknown')
   sector = session.get('sector', 'unknown')
   
   # Pre-fill Google Form with session data (if supported)
   base_url = FEEDBACK_FORM_URL
   if '?' in base_url:
       separator = '&'
   else:
       separator = '?'
   
   feedback_url = f"{base_url}{separator}entry.session={session_id}&entry.usecase={use_case}&entry.sector={sector}"
   
   return feedback_url

# ─── Main chat route with enhanced formatting ───────────────────────────────
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
               return render_template("index.html", step="identification", feedback_url=FEEDBACK_FORM_URL)

           print("DEBUG: Form validation passed, calling generate_trends...")
           raw = generate_trends(uc, sec, dem)
           print(f"DEBUG: generate_trends returned: {len(raw) if raw else 0} characters")
           print(f"DEBUG: Raw response preview: {raw[:200] if raw else 'None'}...")
           
           if not raw or len(raw.strip()) < 10:
               print("DEBUG: Empty or minimal response from generate_trends")
               raw = generate_fallback_trends(uc, sec, dem)
           
           titles, blocks = split_trend_blocks(raw)
           print(f"DEBUG: Split result - {len(titles)} titles, {len(blocks)} blocks")
           print(f"DEBUG: Titles found: {titles}")
           
           if not titles:
               print("DEBUG: No titles found, using fallback")
               raw = generate_fallback_trends(uc, sec, dem)
               titles, blocks = split_trend_blocks(raw)
               print(f"DEBUG: Fallback split result - {len(titles)} titles, {len(blocks)} blocks")
           
           # Format trend blocks for better display
           formatted_blocks = [format_trend_block(block) for block in blocks]
           
           trends_md = "\n\n".join(f"### Trend {i+1}: {t}\n{formatted_blocks[i]}"
                                  for i, t in enumerate(titles))
           
           print(f"DEBUG: Final trends_md length: {len(trends_md)}")

           session.update({
               "step": "scouting",
               "use_case": uc, "sector": sec, "demand": dem,
               "titles": titles, "blocks": formatted_blocks, "trends_md": trends_md,
               "remaining_trends": titles.copy(), "validation_results": {}
           })
           
           print("DEBUG: Session updated, rendering scouting template")
           return render_template("index.html", step="scouting", feedback_url=get_feedback_link())

       # ------------- Phase 2  Scouting ---------------------------------------
       elif step == "scouting":
           idx_str = request.form.get("selected_trend_idx", "")
           action  = request.form.get("action", "")
           
           if not (idx_str.isdigit() and action in ("validate", "implement")):
               flash("Pick one trend and click Validate or Implement.", "warning")
               return render_template("index.html", step="scouting", feedback_url=get_feedback_link())

           idx = int(idx_str)
           rem = session.get("remaining_trends", [])
           
           if idx < 0 or idx >= len(rem):
               flash("Select a valid trend index.", "warning")
               return render_template("index.html", step="scouting", feedback_url=get_feedback_link())

           sel   = rem.pop(idx)
           titles = session.get("titles", [])
           blocks = session.get("blocks", [])
           
           if sel not in titles:
               flash("Selected trend not found.", "error")
               return render_template("index.html", step="scouting", feedback_url=get_feedback_link())
               
           block = blocks[titles.index(sel)]
           session["selected_trend"] = sel

           if action == "validate":
               ass = assess_trend(sel, block)
               rad = radar_positioning(sel, ass)
               rel = relation_criteria(sel, block)
               session["validation_results"][sel] = {
                   "assessment": ass, "radar": rad, "relation": rel
               }
               session["step"] = "validation"
               return render_template("index.html", step="validation", feedback_url=get_feedback_link())

           # direct implementation
           msol = market_ready_solution(sel, block, session.get("sector", ""))
           prts = partners_navigation(sel, block)
           save_to_db(session["use_case"], session["sector"], session["demand"],
                      session["trends_md"], sel, "", "", "",
                      msol, prts, titles, blocks)
           session["market_solution"] = msol
           session["partners"]        = prts
           session["step"]            = "implementation"
           return render_template("index.html", step="implementation", feedback_url=get_feedback_link())

       # ------------- Phase 3  Validation --------------------------------------
       elif step == "validation":
           action = request.form.get("action", "")
           sel    = session.get("selected_trend", "")
           titles = session.get("titles", [])
           blocks = session.get("blocks", [])
           
           if not sel or sel not in titles:
               flash("No trend selected for validation.", "error")
               session["step"] = "scouting"
               return render_template("index.html", step="scouting", feedback_url=get_feedback_link())
               
           block = blocks[titles.index(sel)]

           if action == "validate_more":
               session["step"] = "scouting"
               return render_template("index.html", step="scouting", feedback_url=get_feedback_link())

           # proceed → implementation
           msol = market_ready_solution(sel, block, session.get("sector", ""))
           prts = partners_navigation(sel, block)
           vr   = session["validation_results"].get(sel, {})
           save_to_db(session["use_case"], session["sector"], session["demand"],
                      session["trends_md"], sel,
                      vr.get("assessment", ""), vr.get("radar", ""), vr.get("relation", ""),
                      msol, prts, titles, blocks)
           session["market_solution"] = msol
           session["partners"]        = prts
           session["step"]            = "implementation"
           return render_template("index.html", step="implementation", feedback_url=get_feedback_link())

   except Exception as e:
       print(f"ERROR in chat route: {e}")
       import traceback
       traceback.print_exc()
       flash(f"An error occurred: {str(e)}", "error")
       session["step"] = "identification"
       return render_template("index.html", step="identification", feedback_url=FEEDBACK_FORM_URL)

   # Fallback → reset
   session["step"] = "identification"
   return render_template("index.html", step="identification", feedback_url=FEEDBACK_FORM_URL)

# ─── Enhanced template rendering ────────────────────────────────────────────
@app.template_filter('clean_markdown')
def clean_markdown(text):
   """Clean and format markdown for display"""
   if not text:
       return ""
   
   # Remove excessive newlines
   text = re.sub(r'\n{3,}', '\n\n', text)
   
   # Ensure proper spacing around headers
   text = re.sub(r'(#{1,6}.*?)\n(?!\n)', r'\1\n\n', text)
   
   # Format bullet points consistently
   text = re.sub(r'^(\s*)-\s+', r'\1• ', text, flags=re.MULTILINE)
   
   return text

@app.template_filter('highlight_scores')
def highlight_scores(text):
   """Highlight numerical scores in text"""
   def replace_score(match):
       score = int(match.group(1))
       if score >= 8:
           color = '#28a745'  # Green
       elif score >= 6:
           color = '#ffc107'  # Yellow
       else:
           color = '#dc3545'  # Red
       return f'<span style="color: {color}; font-weight: bold;">{match.group(0)}</span>'
   
   # Match scores in format "Score: X" or "X/10"
   text = re.sub(r'\b(\d+)(?:/10|\s*(?:out of|of)\s*10)\b', replace_score, text)
   text = re.sub(r'(?:Score|Rating):\s*(\d+)', replace_score, text)
   
   return text

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
       
       /* Enhanced Headers */
       .rendered-content h2 {
           position: relative;
           padding-left: 20px;
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
       
       /* Enhanced Lists */
       .rendered-content ul li {
           position: relative;
           padding-left: 20px;
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
       
       /* Feedback Button Styling */
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
       
       /* Phase Cards Enhancement */
       .phase-card {
           border: 2px solid #e0e0e0;
           border-radius: 12px;
           padding: 2rem;
           margin-bottom: 2rem;
           transition: all 0.3s ease;
       }
       
       .phase-card:hover {
           border-color: #00B140;
           box-shadow: 0 4px 12px rgba(0,177,64,0.1);
       }
       
       /* Score Highlighting */
       .score-high {
           color: #28a745;
           font-weight: bold;
       }
       
       .score-medium {
           color: #ffc107;
           font-weight: bold;
       }
       
       .score-low {
           color: #dc3545;
           font-weight: bold;
       }
       
       /* Responsive Tables */
       @media (max-width: 768px) {
           .trend-table {
               font-size: 0.85rem;
           }
           
           .trend-table th,
           .trend-table td {
               padding: 8px;
           }
       }
   </style>
   """
   return dict(custom_css=Markup(custom_css))

# ─── Error Handlers ─────────────────────────────────────────────────────────
@app.errorhandler(404)
def not_found(error):
   return render_template('404.html'), 404

@app.errorhandler(500)
def internal_error(error):
   return render_template('500.html'), 500

# ─────────────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
   app.run(debug=True)