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

# ─── Autonomous validation helper (simplified) ─────────────────────────────
def autonomous_trend_validation(trend_block: str) -> str:
    # Simplified validation to speed up
    v_prompt = f"Rate this disruptive technology 1-10 for market viability:\n{trend_block[:200]}..."
    return call_llm(v_prompt, max_tokens=100)

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
    p = f"""## Strategic Technology Assessment for "{title}"

As a Schaeffler innovation strategist, provide a comprehensive assessment using our Innovation-to-Business (P³) framework and strategic priorities.

{block}

Provide a structured assessment using Schaeffler's strategic evaluation criteria:

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

## Executive Summary
**Strategic Recommendation**: [Clear GO/NO-GO decision with rationale]
**Priority Level**: [Critical/High/Medium/Low based on strategic fit]
**Investment Range**: [€X-Y million over Z years]
**Expected Returns**: [Revenue potential and timeline]

## Risk Mitigation Strategy
- **Technical Risks**: [Specific mitigation approaches]
- **Market Risks**: [Hedging strategies]
- **Competitive Risks**: [Defensive positioning]"""
    return call_llm(p, max_tokens=1000)

# ─── Enhanced radar positioning with action-oriented framework ──────────────
def radar_positioning(title, assessment):
    p = f"""{assessment}

## Technology Radar Positioning for "{title}"

Using Schaeffler's three-horizon innovation framework, classify this technology and provide specific action plans:

**RADAR CLASSIFICATION:** [ACT/PREPARE/WATCH]

**Horizon Mapping:**
- **Horizon 1 (1-3 years)**: [Immediate optimization opportunities]
- **Horizon 2 (3-7 years)**: [Adjacent innovation potential]
- **Horizon 3 (7+ years)**: [Transformative possibilities]

**Classification Justification:**

### ACT (Immediate Implementation Required)
*Select if technology scores 8+ on market opportunity AND manufacturing readiness*
- **Rationale**: [Why immediate action is critical]
- **90-Day Action Plan**: [Specific milestones]
- **Resource Allocation**: [Teams, budget, facilities]
- **Success Metrics**: [KPIs for first year]

### PREPARE (Strategic Development Phase)
*Select if high potential but requires 6-18 months preparation*
- **Rationale**: [Development needs before deployment]
- **Capability Building**: [Skills, partnerships, infrastructure]
- **Pilot Program Design**: [Test markets and applications]
- **Go/No-Go Criteria**: [Decision gates]

### WATCH (Monitor and Reassess)
*Select if promising but premature or uncertain*
- **Rationale**: [Why not ready for investment]
- **Monitoring Plan**: [Tracking indicators]
- **Trigger Points**: [When to reassess]
- **Minimal Investment**: [Learning activities only]

**Recommended Timeline:**
- **Q1-Q2**: [Immediate actions]
- **Q3-Q4**: [Medium-term milestones]
- **Year 2+**: [Long-term objectives]

**Key Success Factors:**
1. [Critical enabler #1]
2. [Critical enabler #2]
3. [Critical enabler #3]"""
    return call_llm(p, max_tokens=600)

# ─── Enhanced innovation classification framework ───────────────────────────
def relation_criteria(title, block):
    p = f"""{block}

## Strategic Innovation Classification for "{title}"

As a Schaeffler innovation strategist, analyze this technology using our adapted innovation matrix framework, considering our position as the leading Motion Technology Company.

### Innovation Classification Matrix

Evaluate on two strategic dimensions:
* **X-axis**: Technology Novelty for Schaeffler (Low → High)
* **Y-axis**: Market Novelty for Mobility Sector (Low → High)

This creates four strategic quadrants aligned with Schaeffler's innovation approach:

#### EXPLOIT (Lower Left Quadrant)
- **Definition**: Incremental improvements to existing motion technologies in established markets
- **Schaeffler Example**: Enhanced bearing durability for current automotive applications
- **Investment Model**: Self-funded through divisional R&D budgets
- **Success Metrics**: Cost reduction, quality improvement, market share defense

#### EXTEND (Upper Left Quadrant)  
- **Definition**: New motion technologies applied to existing mobility markets
- **Schaeffler Example**: AI-enhanced predictive maintenance for traditional components
- **Investment Model**: Corporate innovation fund with divisional co-investment
- **Success Metrics**: Technology leadership, premium pricing, customer retention

#### DISRUPTIVE (Lower Right Quadrant)
- **Definition**: Existing Schaeffler technologies creating new mobility markets
- **Schaeffler Example**: Precision bearings enabling urban air mobility
- **Investment Model**: Strategic ventures and partnership-driven
- **Success Metrics**: New market creation, ecosystem leadership, option value

#### RADICAL (Upper Right Quadrant)
- **Definition**: Breakthrough technologies for emerging mobility ecosystems
- **Schaeffler Example**: Quantum sensors for autonomous vehicle navigation
- **Investment Model**: Corporate venture capital and university partnerships
- **Success Metrics**: IP generation, technology scouting, future positioning

### Strategic Analysis for "{title}"

**Primary Classification:** [EXPLOIT/EXTEND/DISRUPTIVE/RADICAL]

**Technology Novelty Assessment:** 
- **Rating**: [Established (1-3) / Adjacent (4-6) / New to Schaeffler (7-8) / New to World (9-10)]
- **Current Capability Base**: [Existing Schaeffler technologies that apply]
- **Technology Gap Analysis**: [What new capabilities are needed]
- **Development Pathway**: [Build / Buy / Partner / Acquire]

**Market Novelty Assessment:**  
- **Rating**: [Existing Markets (1-3) / Adjacent Markets (4-6) / New to Schaeffler (7-8) / New to Industry (9-10)]
- **Customer Readiness**: [Early Adopters / Early Majority / Late Majority]
- **Market Development Needs**: [Education, infrastructure, regulations]
- **Competitive Dynamics**: [First-mover advantages vs. fast-follower benefits]

### Strategic Implementation Roadmap

**For [Classification] Innovation:**

**Phase 1 - Validation (Months 1-6)**
- **Technical Proof Points**: [Specific demonstrations needed]
- **Market Validation**: [Customer pilots and feedback loops]
- **Investment**: [€X budget range]
- **Go/No-Go Criteria**: [Clear decision metrics]

**Phase 2 - Development (Months 7-18)**
- **Capability Building**: [Internal development vs. partnerships]
- **Market Development**: [Channel strategies and customer engagement]
- **Investment**: [€Y budget range]
- **Scale-Up Triggers**: [Market signals for expansion]

**Phase 3 - Commercialization (Months 19+)**
- **Production Strategy**: [Which facilities and capacity plans]
- **Go-to-Market**: [Direct sales vs. ecosystem approach]
- **Investment**: [€Z budget range]
- **Success Metrics**: [Revenue targets and market share goals]

### Risk-Return Profile

**Innovation Risk Assessment:**
- **Technical Risk**: [Low/Medium/High] - [Mitigation strategies]
- **Market Risk**: [Low/Medium/High] - [Hedging approaches]
- **Competitive Risk**: [Low/Medium/High] - [Defensive strategies]
- **Regulatory Risk**: [Low/Medium/High] - [Compliance roadmap]

**Expected Returns by Scenario:**
- **Base Case**: [ROI and timeline]
- **Upside Case**: [ROI with accelerated adoption]
- **Downside Case**: [Minimum viable returns]

**Strategic Recommendation:**
[Specific action plan based on classification, including investment level, organizational model, and success metrics aligned with Schaeffler's motion technology leadership vision]"""
    return call_llm(p, max_tokens=1200)

def market_ready_solution(title, block, sec):
    p = f"""{block}

## Comprehensive Technology Implementation Roadmap for "{title}" in {sec}

As a Schaeffler technology expert with deep knowledge of motion systems, mechatronics, thermal management, and advanced materials, provide a detailed implementation blueprint aligned with our strategic capabilities and global infrastructure.

### 1. Core Technology Architecture for "{title}"

**Identify and detail THREE enabling technologies essential for implementing "{title}" in {sec}, leveraging Schaeffler's motion technology expertise:**

#### Technology 1: [Specific Technology Name]
**Strategic Purpose**: [How this advances Schaeffler's motion technology leadership]
**Revolutionary Impact**: [Transformative effect on {sec} mobility]

**Technical Specifications**:
- **Performance Metrics**: [Specific quantified targets]
- **Integration Requirements**: [With existing Schaeffler systems]
- **Compliance Standards**: [ISO 26262, ASPICE, etc.]

#### Technology 2: [Specific Technology Name]
**Strategic Purpose**: [Market differentiation potential]
**Revolutionary Impact**: [Customer value creation]

**Technical Specifications**:
- **Performance Metrics**: [Quantified improvements]
- **Scalability Parameters**: [Volume production considerations]
- **Quality Standards**: [Zero-defect targets]

#### Technology 3: [Specific Technology Name]
**Strategic Purpose**: [Sustainability and efficiency gains]
**Revolutionary Impact**: [Contribution to carbon neutrality]

**Technical Specifications**:
- **Efficiency Gains**: [Energy, material, cost reductions]
- **Lifecycle Impact**: [Cradle-to-grave assessment]
- **Circular Economy**: [Recycling and reuse strategies]

### 2. Schaeffler-Specific Implementation Requirements

**For each technology, detail Schaeffler's unique value-add:**

#### Precision Engineering Excellence
- **Tolerances Required**: [Specific μm-level precision needs]
- **Manufacturing Processes**: [Leveraging Schaeffler's production expertise]
- **Quality Assurance**: [6-sigma methodologies and testing protocols]

#### Mechatronic Integration
- **Sensor Systems**: [Types, specifications, data rates]
- **Control Algorithms**: [Real-time processing requirements]
- **Software Architecture**: [Edge vs. cloud computing needs]
- **Cybersecurity**: [ISO 21434 compliance approach]

#### Thermal Management Systems
- **Heat Dissipation**: [W/m²K requirements]
- **Temperature Ranges**: [Operating conditions]
- **Coolant Systems**: [Integration with 4-in-1 e-axle expertise]
- **Efficiency Targets**: [COP improvements]

#### Advanced Materials Application
- **Material Selection**: [Leverage Schaeffler's materials database]
- **Surface Treatments**: [DLC coatings, specialized finishes]
- **Lightweighting**: [Mass reduction targets]
- **Durability**: [Million-cycle testing requirements]

### 3. System Architecture and Integration

**Technical Infrastructure Requirements:**

#### Hardware Systems
- **Core Components**: [Detailed BoM with Schaeffler part numbers where applicable]
- **Modular Architecture**: [Scalability and customization approach]
- **Interface Standards**: [CAN, FlexRay, Ethernet specifications]
- **Power Requirements**: [Voltage levels, current draws, efficiency]

#### Software Platform
- **Operating System**: [Real-time OS requirements]
- **Middleware**: [ROS2, AUTOSAR, custom frameworks]
- **AI/ML Framework**: [TensorFlow, PyTorch integration]
- **OTA Capabilities**: [Update mechanisms and security]

#### Testing Environment
- **HIL Systems**: [Hardware-in-the-loop specifications]
- **Environmental Testing**: [-40°C to +85°C, vibration, EMC]
- **Endurance Testing**: [Million-cycle validation protocols]
- **Field Testing**: [Real-world validation approach]

### 4. Manufacturing and Production Strategy

**Leveraging Schaeffler's Global Manufacturing Network:**

#### Production Locations
- **Lead Factory**: [Specific Schaeffler facility for industrialization]
- **Regional Production**: [Localization strategy across 250+ sites]
- **Supply Chain**: [Critical component sourcing strategies]

#### Manufacturing Technologies
- **Industry 4.0**: [Digital twin implementation]
- **Automation Level**: [Cobots, AGVs, smart logistics]
- **Quality Systems**: [In-line measurement and AI-based inspection]
- **Flexibility**: [Multi-product line capabilities]

### 5. User Experience and System Interfaces

**Human-Machine Interface Design:**
- **User Personas**: [OEM engineers, service technicians, end-users]
- **Interface Types**: [Physical, digital, AR/VR applications]
- **Data Visualization**: [Real-time performance dashboards]
- **Predictive Maintenance**: [OPTIME platform integration]

**System Integration Points:**
- **Vehicle Architecture**: [Zonal, domain, centralized options]
- **Communication Protocols**: [Standards and proprietary interfaces]
- **Diagnostic Capabilities**: [OBD-III readiness]
- **Service Tools**: [Technician training and equipment]

### 6. Scientific Foundation and Innovation

**Fundamental Research Requirements:**

#### Core Physics and Engineering
- **Tribology**: [Friction, wear, lubrication advancements]
- **Materials Science**: [Nanostructures, composites, smart materials]
- **Control Theory**: [Advanced algorithms for motion control]
- **Thermodynamics**: [Heat transfer optimization]

#### Breakthrough Technologies Needed
- **Quantum Sensors**: [For ultra-precise positioning]
- **Neuromorphic Computing**: [For adaptive control systems]
- **Bio-inspired Materials**: [Self-healing, adaptive properties]
- **Energy Harvesting**: [Recovering waste energy]

#### Schaeffler Research Priorities
- **Patent Strategy**: [IP protection and freedom-to-operate]
- **University Partnerships**: [Fraunhofer, RWTH Aachen collaborations]
- **Open Innovation**: [Startup scouting and accelerator programs]

### 7. Development Status and Roadmap

**Current Technology Readiness:**
- **TRL Assessment**: [Current level with evidence]
- **Pilot Programs**: [Ongoing validations with OEMs]
- **Demonstrators**: [Prototype specifications and results]

**Development Timeline:**
- **2025 Q1-Q2**: [Concept validation and design freeze]
- **2025 Q3-Q4**: [Prototype testing and customer trials]
- **2026**: [Industrialization and SOP preparation]
- **2027+**: [Volume production and continuous improvement]

**Key Milestones:**
1. [Technical readiness gate]
2. [Customer commitment]
3. [Production readiness]
4. [Market launch]

### 8. Market Analysis and Business Case

**5-Year Market Projection:**

#### Revenue Potential by Technology
1. **Technology 1**: €[X]M by 2030 ([Y]% CAGR)
2. **Technology 2**: €[X]M by 2030 ([Y]% CAGR)
3. **Technology 3**: €[X]M by 2030 ([Y]% CAGR)

**Total Addressable Market**: €[X]B globally

#### Regional Market Penetration (2030 targets)
- **Europe**: [X]% market share (€[Y]M revenue)
   - Drivers: Green Deal regulations, OEM partnerships
   - Strategy: Leverage German engineering reputation
   
- **Americas**: [X]% market share (€[Y]M revenue)
   - Drivers: USMCA benefits, electrification mandates
   - Strategy: Localize through Wooster and Troy facilities
   
- **China**: [X]% market share (€[Y]M revenue)
   - Drivers: NEV quotas, local content requirements
   - Strategy: JVs and local partnerships
   
- **Rest of Asia**: [X]% market share (€[Y]M revenue)
   - Drivers: Emerging market growth, Japanese OEMs
   - Strategy: ASEAN manufacturing hubs

**Investment Requirements:**
- **R&D**: €[X]M over 3 years
- **CapEx**: €[Y]M for production setup
- **OpEx**: €[Z]M annually
- **ROI**: [X]% by year 5

**Competitive Positioning:**
- **Cost Leadership**: [How Schaeffler's scale enables competitive pricing]
- **Technology Differentiation**: [Unique capabilities competitors lack]
- **Speed to Market**: [Leveraging existing infrastructure]
- **Customer Intimacy**: [Long-term OEM relationships advantage]

---
### OUTPUT STRUCTURE REQUIREMENTS
Respond ONLY with the above section headings and bullet points. DO NOT write any summary or extra text before or after. DO NOT leave any [bracketed] field empty or as a placeholder. For every heading, bullet, or bracketed prompt, provide a plausible, specific expert answer using your knowledge of mobility, engineering, and the global automotive industry. If necessary, make logical and realistic assumptions. Never output only the structure or placeholder text—always fill with detailed content as if presenting to the Schaeffler innovation board.
"""
    return call_llm(p, max_tokens=1800)

def partners_navigation(title, block):
    p = f"""{block}

## Strategic Partners for "{title}"

Please provide a structured partner analysis for this disruptive technology:

| Partner Type | Organization | Role/Expertise | Strategic Value | Collaboration Model |
|--------------|--------------|----------------|-----------------|-------------------|
| Technology Provider | [Company Name] | [Specific expertise] | [Value to Schaeffler] | [Partnership approach] |
| Infrastructure Partner | [Company Name] | [Specific expertise] | [Value to Schaeffler] | [Partnership approach] |
| Market/Customer Partner | [Company Name] | [Specific expertise] | [Value to Schaeffler] | [Partnership approach] |
| Academic/Research Partner | [Institution Name] | [Specific expertise] | [Value to Schaeffler] | [Partnership approach] |
| Regulatory/Standards Partner | [Organization Name] | [Specific expertise] | [Value to Schaeffler] | [Partnership approach] |

## Partner Selection Justification & Criteria
- **Selection Criteria**: [List of criteria used to evaluate/select partners]
- **Justification**: Explain why each selected organization is a strategic fit, referencing the criteria above.

## Partnership Strategy 
- **Primary Partnership Priority**: [most critical partnership] 
- **Timeline for Engagement**: [recommended approach]
- **Risk Mitigation**: [partnership risk considerations]"""
    return call_llm(p, max_tokens=800)

# ─── DB helper --------------------------------------------------------------
def save_to_db(uc, sec, dem, trends_md, sel, ass, rad,
               rel, msol, prts, titles=None, blocks=None):
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
            """, (uc, sec, dem, sel, trends_md, ass, rad, rel,
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
                rel = relation_criteria(sel, block)
                session["validation_results"][sel] = {
                    "assessment": ass, "radar": rad, "relation": rel
                }
                session["step"] = "validation"
                return render_template("index.html", step="validation")

            # direct implementation
            msol = market_ready_solution(sel, block, session.get("sector", ""))
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