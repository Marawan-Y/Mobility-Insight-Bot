# assessment_writer.py
import os, json, re, uuid, pymysql
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

def _conn():
    return pymysql.connect(
        host=os.getenv("DB_HOST"),
        user=os.getenv("DB_USER"),
        password=os.getenv("DB_PASSWORD"),
        database=os.getenv("DB_NAME"),
        charset="utf8mb4",
        autocommit=True,
    )

def ensure_tables():
    ddl_trials = """CREATE TABLE IF NOT EXISTS llm_assessment_trials (
        id INT AUTO_INCREMENT PRIMARY KEY,
        trial_id VARCHAR(64) UNIQUE,
        use_case VARCHAR(255),
        sector VARCHAR(255),
        demand TEXT,
        timestamp DATETIME,
        raw_output LONGTEXT,
        latency_ms FLOAT,
        token_count INT,
        api_calls INT,
        metadata JSON,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        INDEX idx_input (use_case, sector, demand(255))
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci"""
    ddl_metrics = """CREATE TABLE IF NOT EXISTS llm_assessment_metrics (
        id INT AUTO_INCREMENT PRIMARY KEY,
        assessment_id VARCHAR(64),
        metric_type VARCHAR(50),
        metric_name VARCHAR(100),
        metric_value FLOAT,
        details JSON,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        INDEX idx_assessment (assessment_id),
        INDEX idx_metric (metric_type, metric_name)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci"""
    conn = _conn()
    with conn.cursor() as cur:
        cur.execute(ddl_trials)
        cur.execute(ddl_metrics)
    conn.close()

# ---------- lightweight parsing ----------

SECTION_PATTERNS = [
    ("strategic_alignment", r"Strategic Alignment"),
    ("confidence_justification", r"Confidence Justification"),
    ("description", r"^Description\b"),
    ("market_impact_analysis", r"Market Impact Analysis"),
    ("value_proposition", r"Value Proposition"),
    ("competitive_landscape", r"Competitive Landscape"),
    ("implementation_readiness", r"Implementation Readiness"),
]

def extract_titles(md: str):
    # headings like: "Technology Title: XYZ"
    titles = re.findall(r"(?im)^.*?Technology\s*Title:\s*(.+)$", md or "")
    # fallback in case your renderer converts them into "### Trend n: Title"
    if not titles:
        titles = re.findall(r"(?im)^#+\s*Trend\s*\d+\s*:\s*(.+)$", md or "")
    return [t.strip() for t in titles if t.strip()]

def extract_confidence_scores(md: str):
    scores = re.findall(r"(?i)Confidence\s*Score\s*:\s*([0-9]+(?:\.[0-9]+)?)", md or "")
    return [float(s) for s in scores]

def compute_compliance(md: str):
    comp = {}
    for key, pat in SECTION_PATTERNS:
        comp[key] = 1.0 if re.search(pat, md or "", flags=re.IGNORECASE | re.MULTILINE) else 0.0
    if comp:
        comp["avg_compliance"] = sum(comp.values()) / len(SECTION_PATTERNS)
    else:
        comp["avg_compliance"] = 0.0
    return comp

# ---------- writers ----------

def _insert_metrics(assessment_id: str, metrics: dict):
    """Write metrics dict into llm_assessment_metrics."""
    conn = _conn()
    with conn.cursor() as cur:
        for mtype, kv in metrics.items():
            for name, val in kv.items():
                cur.execute(
                    """
                    INSERT INTO llm_assessment_metrics
                    (assessment_id, metric_type, metric_name, metric_value, details)
                    VALUES (%s,%s,%s,%s,%s)
                    """,
                    (assessment_id, mtype, name, float(val if val is not None else 0.0),
                     json.dumps({"trial_id": assessment_id})),
                )
    conn.close()

def write_trial_row(
    *,
    use_case: str,
    sector: str,
    demand: str,
    raw_markdown: str,
    latency_ms: float = 0.0,
    token_count: int = 0,
    api_calls: int = 0,
    trial_id: str | None = None,
) -> str:
    """
    Insert a trial AND emit per-trial metrics:
      - diversity.unique_title_ratio
      - diversity.title_diversity (set to 1.0 for a single trial proxy)
      - compliance.* (per section) + compliance.avg_compliance
    """
    ensure_tables()
    if not trial_id:
        trial_id = uuid.uuid4().hex

    titles = extract_titles(raw_markdown or "")
    uniq_ratio = (len(set(titles)) / len(titles)) if titles else 0.0
    confs = extract_confidence_scores(raw_markdown or "")
    compliance = compute_compliance(raw_markdown or "")

    meta = {
        "trend_count": len(titles),
        "trend_titles": titles[:10],
        "confidence_scores": confs,
        "structure_compliance": compliance,
    }

    # insert trial
    conn = _conn()
    with conn.cursor() as cur:
        cur.execute(
            """
            INSERT IGNORE INTO llm_assessment_trials
            (trial_id, use_case, sector, demand, timestamp, raw_output,
             latency_ms, token_count, api_calls, metadata)
            VALUES (%s,%s,%s,%s,NOW(),%s,%s,%s,%s,%s)
            """,
            (
                trial_id, use_case, sector, demand,
                raw_markdown, float(latency_ms or 0),
                int(token_count or 0), int(api_calls or 0),
                json.dumps(meta, ensure_ascii=False),
            ),
        )
    conn.close()

    # insert minimal metrics so the Quality tab has data
    metrics_payload = {
        "diversity": {
            "unique_title_ratio": uniq_ratio,
            # single-trial proxy to make the chart visible
            "title_diversity": 1.0 if titles else 0.0,
            "avg_titles_per_trial": float(len(titles)),
        },
        "compliance": {
            **{f"compliance_{k}": v for k, v in compliance.items() if k != "avg_compliance"},
            "avg_compliance": compliance.get("avg_compliance", 0.0),
        },
    }
    _insert_metrics(trial_id, metrics_payload)
    return trial_id
