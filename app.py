import os
import re
import time
from flask import Flask, request, session, render_template, redirect, url_for
from dotenv import load_dotenv
from sqlalchemy import create_engine, Column, Integer, String, Text, TIMESTAMP, func
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from google.oauth2 import service_account
import vertexai
from vertexai.generative_models import GenerativeModel, GenerationConfig
from google.api_core.exceptions import ResourceExhausted

# Load .env
load_dotenv()

# --- Environment & DB Setup ---

DB_HOST = os.getenv('DB_HOST', 'localhost')
DB_PORT = os.getenv('DB_PORT', '3306')
DB_NAME = os.getenv('DB_NAME', '')
DB_USER = os.getenv('DB_USER', '')
DB_PASSWORD = os.getenv('DB_PASSWORD', '')

DATABASE_URL = f"mysql+pymysql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"
engine = create_engine(DATABASE_URL, echo=False)
Base = declarative_base()
SessionLocal = sessionmaker(bind=engine)

# --- SQLAlchemy Model ---

class TrendQuery(Base):
    __tablename__ = 'trend_queries'
    id = Column(Integer, primary_key=True, autoincrement=True)
    use_case = Column(String(255))
    sector = Column(String(255))
    demand = Column(String(255))
    trend_solutions = Column(Text)
    trend_assessment = Column(Text)
    radar_positioning = Column(Text)
    pestel_tag = Column(Text)
    created_at = Column(TIMESTAMP, server_default=func.now(), nullable=False)

# --- Vertex AI / Gemini Setup ---

PROJECT_ID = os.getenv('PROJECT_ID', '')
LOCATION = os.getenv('LOCATION', 'us-central1')
SERVICE_ACCOUNT_FILE = os.getenv('SERVICE_ACCOUNT_FILE', '')
MODEL_NAME = os.getenv('MODEL_NAME', 'gemini-1.5-flash')

creds = None
if SERVICE_ACCOUNT_FILE:
    creds = service_account.Credentials.from_service_account_file(SERVICE_ACCOUNT_FILE)

try:
    vertexai.init(project=PROJECT_ID, location=LOCATION, credentials=creds)
    llm_model = GenerativeModel(model_name=MODEL_NAME)
    generation_params = GenerationConfig(temperature=0.2, max_output_tokens=1024)
except Exception as e:
    llm_model = None
    print("Vertex AI init failed:", e)

# --- Flask App Setup ---

app = Flask(__name__)
app.secret_key = os.getenv('FLASK_SECRET_KEY', 'change_me')

# --- Prompt Templates (now ask for Markdown) ---

FIRST_PROMPT_TEMPLATE = """
You are an expert in mobility technology and innovation. The user is interested in the following demand for **{use_case}** in the **{sector}** sector: “{demand}”.
[...existing detailed instructions...]
Please return the entire response **in Markdown**, using:
- Top‐level headings (e.g. `## Trend Title`)
- Bold labels or sub‐headings for each subsection
- Bullet lists where appropriate
- Ensure **all five** trends appear, in one coherent Markdown document.
"""

ASSESS_PROMPT_TEMPLATE = """
I need you to perform a comprehensive trend assessment for each of the following trends, based on these criteria.
{trends_markdown}

Please format your assessment **in Markdown**, using:
- A heading (`## Comprehensive Trend Assessment`)
- A bullet list for each criterion with its numeric score
- Ensure the scores are clearly labeled.
"""

RADAR_PROMPT_TEMPLATE = """
Based on the trend evaluations, classify each trend into one of: ACT, PREPARE, or WATCH.
Trends:
{trends_markdown}

Please format the classification **in Markdown**, using:
- A heading (`## Radar Positioning`)
- Bullet list (`- Trend Title: ACT`) for each trend
- Include a brief justification inline.
"""

PESTEL_PROMPT_TEMPLATE = """
Identify the primary PESTEL driver for each of the following trends, with a brief justification.
Trends:
{trends_markdown}

Please format the PESTEL results **in Markdown**, using:
- A heading (`## PESTEL Trend Radar`)
- Bullet lists (`- Trend Title: Technological`) for each trend
- The brief justification inline.
"""

# --- LLM Call with Retry & Backoff ---

def call_vertex_llm(prompt: str, max_retries=3, initial_delay=1.0) -> str:
    if llm_model is None:
        raise RuntimeError("LLM model not initialized")
    attempt = 0
    delay = initial_delay
    while True:
        try:
            response = llm_model.generate_content(prompt, generation_config=generation_params)
            # Extract text
            if hasattr(response, 'text'):
                return response.text.strip()
            elif response.candidates:
                return str(response.candidates[0]).strip()
            else:
                return ""
        except ResourceExhausted:
            attempt += 1
            if attempt > max_retries:
                raise
            print(f"429 received – retrying in {delay}s (attempt {attempt}/{max_retries})")
            time.sleep(delay)
            delay *= 2
        except Exception:
            raise

# --- Flask Routes ---

@app.route('/', methods=['GET', 'POST'])
def chat():
    db = SessionLocal()
    history = db.query(TrendQuery).order_by(TrendQuery.created_at.desc()).all()
    messages = session.get('messages', [])
    pending = session.get('pending')

    if request.method == 'GET':
        return render_template('index.html',
                               history=history,
                               messages=messages,
                               conversation_started=bool(messages),
                               history_mode=False,
                               current_id=session.get('conv_id'))

    # POST: handle user input
    user_input = request.form.get('message','').strip()
    if not pending:
        # Initial query: parse Use-case, Sector, Demand
        parts = [p.strip() for p in user_input.split(',')]
        if len(parts) < 3:
            messages.append({'sender':'bot','text':
                "❗ Please use the format: **Use-case, Sector, Demand**."})
            session['messages'] = messages
            db.close()
            return render_template('index.html', history=history,
                                   messages=messages, conversation_started=False,
                                   history_mode=False, current_id=None)
        use_case, sector, demand = parts[0], parts[1], ",".join(parts[2:]).strip()
        # record user
        messages = [{'sender':'user','text':f"{use_case}, {sector}, {demand}"}]

        # Step 1: Trend Solutions
        prompt1 = FIRST_PROMPT_TEMPLATE.format(use_case=use_case, sector=sector, demand=demand)
        try:
            solutions_md = call_vertex_llm(prompt1)
        except ResourceExhausted:
            messages.append({'sender':'bot','text':
                "⚠️ AI service busy. Please wait a few seconds and try sending again."})
            session['messages'] = messages
            db.close()
            return render_template('index.html', history=history,
                                   messages=messages, conversation_started=True,
                                   history_mode=False, current_id=None)

        messages.append({'sender':'bot','text':solutions_md})

        # Parse titles & descriptions
        trend_blocks = re.split(r'##\s*Trend Title:', solutions_md)
        titles = []
        descs = []
        for blk in trend_blocks[1:]:
            # each blk starts with "<title>\n..."
            lines = blk.splitlines()
            title = lines[0].strip()
            titles.append(title)
            descs.append("\n".join(lines[1:]).strip())
        # Store to DB
        record = TrendQuery(use_case=use_case, sector=sector, demand=demand,
                            trend_solutions=solutions_md)
        db.add(record)
        db.commit()

        # Save session state
        session['conv_id'] = record.id
        session['trend_titles'] = titles
        session['trend_descs']  = descs
        session['messages']     = messages

        # Ask next
        messages.append({'sender':'bot','text':
            "Would you like a **Comprehensive Trend Assessment** now? (Yes/No)"})
        session['pending'] = 'assessment'
        db.close()
        return render_template('index.html', history=history,
                               messages=messages, conversation_started=True,
                               history_mode=False, current_id=record.id)

    # --- Pending follow-up questions ---

    answered_yes = user_input.lower() in ['yes','y','sure','ok']
    messages.append({'sender':'user','text': 'Yes' if answered_yes else 'No'})

    if pending == 'assessment':
        if answered_yes:
            titles = session['trend_titles']
            descs  = session['trend_descs']
            # Batch assessment prompt
            trends_md = ""
            for t,d in zip(titles, descs):
                trends_md += f"### {t}\n{d}\n\n"
            prompt2 = ASSESS_PROMPT_TEMPLATE.format(trends_markdown=trends_md)
            try:
                assess_md = call_vertex_llm(prompt2)
            except ResourceExhausted:
                messages.append({'sender':'bot','text':
                    "⚠️ AI service busy. Please wait a few seconds and click **Send** again."})
                session['messages'] = messages
                db.close()
                return render_template('index.html', history=history,
                                       messages=messages, conversation_started=True,
                                       history_mode=False, current_id=session['conv_id'])
            messages.append({'sender':'bot','text': assess_md})
            # Extract average scores for DB
            scores = re.findall(r'Score.*?:\s*([0-9]{1,2}(?:\.\d+)?)', assess_md)
            record = db.query(TrendQuery).get(session['conv_id'])
            record.trend_assessment = ", ".join(scores)
            db.commit()
        messages.append({'sender':'bot','text':
            "Would you like **Radar Positioning** now? (Yes/No)"})
        session['pending'] = 'radar'
        session['messages'] = messages
        db.close()
        return render_template('index.html', history=history,
                               messages=messages, conversation_started=True,
                               history_mode=False, current_id=session['conv_id'])

    if pending == 'radar':
        if answered_yes:
            titles = session.get['trend_titles', []]
            descs  = session.get['trend_descs']
            if not descs:
                rec = db.query(TrendQuery).get(session.get('conv_id'))
                descs = []
                parts = re.split(r'##\s*Trend Title:', rec.trend_solutions or "")
                if parts and parts[0].strip()=="":
                    parts = parts[1:]
                for blk in parts:
                    lines = blk.splitlines()
                    descs.append("\n".join(lines[1:]).strip())
                session['trend_descs'] = descs
            trends_md = ""
            for t,d in zip(titles, descs):
                summary = d[:100].replace("\n"," ") + "..."
                trends_md += f"- **{t}**: {summary}\n"
            prompt3 = RADAR_PROMPT_TEMPLATE.format(trends_markdown=trends_md)
            try:
                radar_md = call_vertex_llm(prompt3)
            except ResourceExhausted:
                messages.append({'sender':'bot','text':
                    "⚠️ AI service busy. Please wait a few seconds and click **Send** again."})
                session['messages'] = messages
                db.close()
                return render_template('index.html', history=history,
                                       messages=messages, conversation_started=True,
                                       history_mode=False, current_id=session['conv_id'])
            messages.append({'sender':'bot','text': radar_md})
            cats = re.findall(r'\*\*(.*?)\*\*:\s*(ACT|PREPARE|WATCH)', radar_md)
            record = db.query(TrendQuery).get(session['conv_id'])
            record.radar_positioning = ", ".join([c[1] for c in cats])
            db.commit()
        messages.append({'sender':'bot','text':
            "Finally, would you like the **PESTEL Trend Radar**? (Yes/No)"})
        session['pending'] = 'pestel'
        session['messages'] = messages
        db.close()
        return render_template('index.html', history=history,
                               messages=messages, conversation_started=True,
                               history_mode=False, current_id=session['conv_id'])

    if pending == 'pestel':
        if answered_yes:
            titles = session.get['trend_titles', []]
            descs  = session.get['trend_descs']
            if not descs:
                rec = db.query(TrendQuery).get(session.get('conv_id'))
                descs = []
                parts = re.split(r'##\s*Trend Title:', rec.trend_solutions or "")
                if parts and parts[0].strip()=="":
                    parts = parts[1:]
                for blk in parts:
                    lines = blk.splitlines()
                    descs.append("\n".join(lines[1:]).strip())
                session['trend_descs'] = descs
            trends_md = ""
            for t,d in zip(titles, descs):
                summary = d[:100].replace("\n"," ") + "..."
                trends_md += f"- **{t}**: {summary}\n"
            prompt4 = PESTEL_PROMPT_TEMPLATE.format(trends_markdown=trends_md)
            try:
                pestel_md = call_vertex_llm(prompt4)
            except ResourceExhausted:
                messages.append({'sender':'bot','text':
                    "⚠️ AI service busy. Please wait a few seconds and click **Send** again."})
                session['messages'] = messages
                db.close()
                return render_template('index.html', history=history,
                                       messages=messages, conversation_started=True,
                                       history_mode=False, current_id=session['conv_id'])
            messages.append({'sender':'bot','text': pestel_md})
            tags = re.findall(r'\*\*(.*?)\*\*:\s*(Political|Economic|Social|Technological|Ecological|Legal)', pestel_md)
            record = db.query(TrendQuery).get(session['conv_id'])
            record.pestel_tag = ", ".join([t[1] for t in tags])
            db.commit()
        # Done
        session['pending'] = None
        session['messages'] = messages
        db.close()
        return render_template('index.html', history=history,
                               messages=messages, conversation_started=True,
                               history_mode=False, current_id=session['conv_id'])

@app.route('/conversation/<int:conv_id>')
def view_conversation(conv_id):
    db = SessionLocal()
    record = db.query(TrendQuery).get(conv_id)
    if not record:
        db.close()
        return redirect(url_for('chat'))
    msgs = []
    # Reconstruct conversation...
    msgs.append({'sender':'user','text':f"{record.use_case}, {record.sector}, {record.demand}"})
    msgs.append({'sender':'bot','text': record.trend_solutions})
    msgs.append({'sender':'bot','text':
        "Would you like a **Comprehensive Trend Assessment** now? (Yes/No)"})
    if record.trend_assessment:
        msgs.append({'sender':'user','text': 'Yes'})
        # format as Markdown block
        msgs.append({'sender':'bot','text': record.trend_assessment})
    else:
        msgs.append({'sender':'user','text': 'No'})
    msgs.append({'sender':'bot','text':
        "Would you like **Radar Positioning** now? (Yes/No)"})
    if record.radar_positioning:
        msgs.append({'sender':'user','text':'Yes'})
        msgs.append({'sender':'bot','text': record.radar_positioning})
    else:
        msgs.append({'sender':'user','text':'No'})
    msgs.append({'sender':'bot','text':
        "Finally, would you like the **PESTEL Trend Radar**? (Yes/No)"})
    if record.pestel_tag:
        msgs.append({'sender':'user','text':'Yes'})
        msgs.append({'sender':'bot','text': record.pestel_tag})
    else:
        msgs.append({'sender':'user','text':'No'})
    db.close()
    return render_template('index.html',
                           history=db.query(TrendQuery).order_by(TrendQuery.created_at.desc()).all(),
                           messages=msgs,
                           conversation_started=True,
                           history_mode=True,
                           current_id=conv_id)

@app.route('/new')
def new_conversation():
    session.clear()
    return redirect(url_for('chat'))

if __name__ == '__main__':
    Base.metadata.create_all(engine)
    app.run(host='0.0.0.0', port=5000, debug=True)
