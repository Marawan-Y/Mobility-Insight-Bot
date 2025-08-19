# variance_assessment_dashboard.py
#
# Unified, production-ready dashboard that merges:
# - Variance-focused analytics (overview, deep dive, temporal, consistency),
# - A robust Raw Data tab (column selection, fingerprint filtering, CSV export),
# - A Full History explorer (grouped/flat browsing, per-group + global export),
# - SciPy-optional trend analysis (graceful fallback) and Plotly size sanitization.
#
# Usage:
#   streamlit run variance_assessment_dashboard.py
#
# Env:
#   DB_HOST, DB_USER, DB_PASSWORD, DB_NAME, (optional) DB_PORT
#
# Notes:
# - Reads from `trend_queries` (historical runs).
# - No hard SciPy dependency; will use numpy fallback if SciPy is not installed.

import os
import json
import hashlib
import re
from collections import Counter
from datetime import datetime

import numpy as np
import pandas as pd
import pymysql
import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from dotenv import load_dotenv

load_dotenv()

# --- Streamlit config (must be first Streamlit call) ---
st.set_page_config(
    page_title="LLM Output Variance Analysis Dashboard",
    page_icon="📊",
    layout="wide",
)


# -----------------------
# Helpers: DB & Caching
# -----------------------
def _get_db_config_from_env() -> dict:
    return {
        "host": os.getenv("DB_HOST", "localhost"),
        "user": os.getenv("DB_USER", ""),
        "password": os.getenv("DB_PASSWORD", ""),
        "database": os.getenv("DB_NAME", ""),
        "port": int(os.getenv("DB_PORT", 3306)),
        "charset": "utf8mb4",
        "autocommit": True,
    }


@st.cache_data(ttl=60)
def fetch_trend_queries(db_cfg: dict) -> pd.DataFrame:
    """Fetch ALL historical data from trend_queries as a DataFrame (cached)."""
    query = """
        SELECT 
            id,
            use_case,
            sector,
            demand,
            selected_trend,
            trend_solutions,
            trend_assessment,
            radar_positioning,
            pestel_tag,
            market_solution,
            partners,
            confidence_score,
            session_id,
            created_at
        FROM trend_queries
        ORDER BY created_at DESC
    """
    try:
        conn = pymysql.connect(**db_cfg)
        df = pd.read_sql(query, conn)
        conn.close()
    except Exception as e:
        st.error(f"Database query failed: {e}")
        return pd.DataFrame()

    # Normalize dtypes
    if "created_at" in df.columns:
        df["created_at"] = pd.to_datetime(df["created_at"], errors="coerce")
    if "confidence_score" in df.columns:
        df["confidence_score"] = pd.to_numeric(df["confidence_score"], errors="coerce")

    # Ensure string columns are str (avoid None issues down the line)
    text_cols = [
        "use_case",
        "sector",
        "demand",
        "selected_trend",
        "trend_solutions",
        "trend_assessment",
        "radar_positioning",
        "pestel_tag",
        "market_solution",
        "partners",
        "session_id",
    ]
    for c in text_cols:
        if c in df.columns:
            df[c] = df[c].fillna("").astype(str)

    return df


# -----------------------
# Text & Metric Extractors
# -----------------------
def create_query_fingerprint(use_case: str, sector: str, demand: str) -> str:
    """Create unique fingerprint for each (use_case, sector, demand) combo."""
    query_str = f"{use_case}|{sector}|{demand}".lower().strip()
    return hashlib.md5(query_str.encode()).hexdigest()[:12]


def extract_trend_titles(trend_solutions: str):
    """Extract trend titles from the trend_solutions text (supports multiple formats)."""
    if not trend_solutions:
        return []
    patterns = [
        r"Technology Title:\s*(.+?)(?:\n|$)",
        r"### Trend \d+:\s*(.+?)(?:\n|$)",
        r"Disruptive Technology \d+:\s*(.+?)(?:\n|$)",
        r"\*\*Technology Title\*\*:\s*(.+?)(?:\n|$)",
    ]
    titles = []
    for pattern in patterns:
        found = re.findall(pattern, trend_solutions, re.IGNORECASE | re.MULTILINE)
        if found:
            titles.extend(found)
    return [t.strip() for t in titles if t.strip()]


def extract_confidence_scores(trend_solutions: str):
    """Extract confidence scores from trend text."""
    if not trend_solutions:
        return []
    pattern = r"Confidence Score:\s*([0-9.]+)"
    scores = re.findall(pattern, trend_solutions, re.IGNORECASE)
    out = []
    for s in scores:
        try:
            out.append(float(s))
        except Exception:
            pass
    return out


def extract_key_metrics(text: str, metric_type: str):
    """Extract various metrics from different text sections."""
    if not text:
        return {}
    metrics = {}

    if metric_type == "assessment":
        # Example: "Relevance: 8/10" or "Clarity: 7"
        score_pattern = r"(\w+[\s\w]*?):\s*(\d+(?:\.\d+)?)\s*(?:/10|out of 10)?"
        matches = re.findall(score_pattern, text)
        for key, value in matches:
            try:
                metrics[key.strip()] = float(value)
            except Exception:
                pass

    elif metric_type == "radar":
        # Extract ACT/PREPARE/WATCH classification
        utext = text.upper()
        if "ACT" in utext:
            metrics["classification"] = "ACT"
        elif "PREPARE" in utext:
            metrics["classification"] = "PREPARE"
        elif "WATCH" in utext:
            metrics["classification"] = "WATCH"

        # Extract timeline mentions
        timeline_pattern = r"(\d+)[\s-]*(?:months?|years?)"
        timelines = re.findall(timeline_pattern, text, re.IGNORECASE)
        if timelines:
            metrics["timeline_mentions"] = len(timelines)

    elif metric_type == "market":
        # Extract budget figures like: € 1.5 Billion / € 50 million
        budget_pattern = r"€\s*(\d+(?:\.\d+)?)\s*[MBmb]illion"
        budgets = re.findall(budget_pattern, text, re.IGNORECASE)
        if budgets:
            try:
                metrics["budget_mentions"] = [float(b) for b in budgets]
            except Exception:
                pass

        # Extract ROI or percentage figures
        roi_pattern = r"(\d+(?:\.\d+)?)\s*%"
        rois = re.findall(roi_pattern, text)
        if rois:
            try:
                metrics["roi_percentages"] = [float(r) for r in rois]
            except Exception:
                pass

    return metrics


def jaccard_text_similarity(text1: str, text2: str) -> float:
    """Word-level Jaccard similarity."""
    if not text1 or not text2:
        return 0.0
    words1 = set(text1.lower().split())
    words2 = set(text2.lower().split())
    if not words1 and not words2:
        return 1.0
    if not words1 or not words2:
        return 0.0
    inter = words1.intersection(words2)
    uni = words1.union(words2)
    return len(inter) / len(uni) if uni else 0.0


def analyze_variance_for_query(df_subset: pd.DataFrame):
    """Compute variance metrics for a single query across trials."""
    if df_subset.empty:
        return {}

    variance_metrics = {
        "trial_count": len(df_subset),
        "time_span_days": int(
            (df_subset["created_at"].max() - df_subset["created_at"].min()).days
        )
        if len(df_subset) > 1
        else 0,
        "trends": {},
        "assessment": {},
        "implementation": {},
        "consistency": {},
    }

    # --- Trend variance ---
    all_trends = []
    all_conf_scores = []
    for _, row in df_subset.iterrows():
        ts = row.get("trend_solutions", "")
        all_trends.extend(extract_trend_titles(ts))
        all_conf_scores.extend(extract_confidence_scores(ts))

    if all_trends:
        unique_trends = set(all_trends)
        variance_metrics["trends"]["unique_count"] = len(unique_trends)
        variance_metrics["trends"]["total_count"] = len(all_trends)
        variance_metrics["trends"]["diversity_ratio"] = (
            len(unique_trends) / len(all_trends) if all_trends else 0
        )
        variance_metrics["trends"]["most_common"] = Counter(all_trends).most_common(5)

    if all_conf_scores:
        cm = float(np.mean(all_conf_scores))
        cs = float(np.std(all_conf_scores))
        variance_metrics["trends"]["confidence_mean"] = cm
        variance_metrics["trends"]["confidence_std"] = cs
        variance_metrics["trends"]["confidence_cv"] = (cs / cm) if cm > 0 else 0.0

    # --- Assessment variance & radar classification ---
    assessment_scores = []
    radar_classifications = []
    for _, row in df_subset.iterrows():
        if row.get("trend_assessment", ""):
            m = extract_key_metrics(row["trend_assessment"], "assessment")
            if m:
                assessment_scores.append(list(m.values()))
        if row.get("radar_positioning", ""):
            rm = extract_key_metrics(row["radar_positioning"], "radar")
            if "classification" in rm:
                radar_classifications.append(rm["classification"])

    if assessment_scores:
        flat_scores = [s for sub in assessment_scores for s in sub]
        if flat_scores:
            variance_metrics["assessment"]["score_mean"] = float(np.mean(flat_scores))
            variance_metrics["assessment"]["score_std"] = float(np.std(flat_scores))

    if radar_classifications:
        cc = Counter(radar_classifications)
        variance_metrics["assessment"]["classification_distribution"] = dict(cc)
        probs = np.array(list(cc.values()), dtype=float) / len(radar_classifications)
        entropy = float(-np.sum(probs * np.log2(probs + 1e-12)))
        # clip negative due to floating error
        variance_metrics["assessment"]["classification_entropy"] = max(entropy, 0.0)

    # --- Implementation variance (budget/ROI) ---
    all_budgets = []
    all_rois = []
    for _, row in df_subset.iterrows():
        ms = row.get("market_solution", "")
        if ms:
            mk = extract_key_metrics(ms, "market")
            if "budget_mentions" in mk:
                all_budgets.extend(mk["budget_mentions"])
            if "roi_percentages" in mk:
                all_rois.extend(mk["roi_percentages"])

    if all_budgets:
        bm = float(np.mean(all_budgets))
        bs = float(np.std(all_budgets))
        variance_metrics["implementation"]["budget_mean"] = bm
        variance_metrics["implementation"]["budget_std"] = bs
        variance_metrics["implementation"]["budget_cv"] = (bs / bm) if bm > 0 else 0.0

    if all_rois:
        variance_metrics["implementation"]["roi_mean"] = float(np.mean(all_rois))
        variance_metrics["implementation"]["roi_std"] = float(np.std(all_rois))

    # --- Pairwise text similarity across trials ---
    if len(df_subset) > 1:
        rows = df_subset.to_dict("records")
        trend_sims, assess_sims, market_sims = [], [], []
        for i in range(len(rows)):
            for j in range(i + 1, len(rows)):
                a, b = rows[i], rows[j]
                if a.get("trend_solutions") and b.get("trend_solutions"):
                    trend_sims.append(
                        jaccard_text_similarity(a["trend_solutions"], b["trend_solutions"])
                    )
                if a.get("trend_assessment") and b.get("trend_assessment"):
                    assess_sims.append(
                        jaccard_text_similarity(a["trend_assessment"], b["trend_assessment"])
                    )
                if a.get("market_solution") and b.get("market_solution"):
                    market_sims.append(
                        jaccard_text_similarity(a["market_solution"], b["market_solution"])
                    )

        if trend_sims:
            variance_metrics["consistency"]["trend_similarity_mean"] = float(
                np.mean(trend_sims)
            )
            variance_metrics["consistency"]["trend_similarity_std"] = float(
                np.std(trend_sims)
            )
        if assess_sims:
            variance_metrics["consistency"]["assessment_similarity_mean"] = float(
                np.mean(assess_sims)
            )
        if market_sims:
            variance_metrics["consistency"]["market_similarity_mean"] = float(
                np.mean(market_sims)
            )

    return variance_metrics


# -----------------------
# Dashboard class
# -----------------------
class VarianceAnalysisDashboard:
    def __init__(self):
        self.db_cfg = _get_db_config_from_env()

    def create_dashboard(self):
        st.title("🔬 LLM Output Variance Analysis Dashboard")
        st.markdown("Analyzing consistency and variance in LLM responses across identical queries")

        # Fetch (cached) historical data
        df = fetch_trend_queries(self.db_cfg)
        if df.empty:
            st.warning("No data available in the database.")
            return

        # Add query fingerprint
        df["query_fingerprint"] = df.apply(
            lambda r: create_query_fingerprint(r["use_case"], r["sector"], r["demand"]),
            axis=1,
        )

        # Group queries (for filters and overviews)
        query_groups = (
            df.groupby("query_fingerprint")
            .agg(
                trial_count=("id", "count"),
                use_case=("use_case", "first"),
                sector=("sector", "first"),
                demand=("demand", "first"),
                first_trial=("created_at", "min"),
                last_trial=("created_at", "max"),
            )
            .reset_index()
            .rename(columns={"query_fingerprint": "fingerprint"})
            .sort_values("trial_count", ascending=False)
        )

        # Sidebar filters
        st.sidebar.header("📋 Filters")
        max_trials = int(query_groups["trial_count"].max() or 1)
        min_trials = st.sidebar.slider(
            "Minimum trials per query", min_value=1, max_value=max_trials, value=min(2, max_trials)
        )

        filtered_queries = query_groups[query_groups["trial_count"] >= min_trials].copy()

        use_case_opts = filtered_queries["use_case"].unique().tolist()
        selected_use_cases = st.sidebar.multiselect(
            "Use Cases",
            options=use_case_opts,
            default=use_case_opts[:5] if len(use_case_opts) > 5 else use_case_opts,
        )
        if selected_use_cases:
            filtered_queries = filtered_queries[filtered_queries["use_case"].isin(selected_use_cases)]

        # Overview metrics
        c1, c2, c3, c4 = st.columns(4)
        with c1:
            st.metric("Total Unique Queries", len(query_groups))
        with c2:
            st.metric("Total Trials", len(df))
        with c3:
            st.metric("Avg Trials/Query", f"{query_groups['trial_count'].mean():.1f}")
        with c4:
            st.metric("Queries with Multiple Trials", int((query_groups["trial_count"] > 1).sum()))

        # Tabs (merged best-of-both worlds)
        tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs(
            ["📊 Variance Overview", "🎯 Query Deep Dive", "📈 Temporal Analysis", "🔄 Consistency Metrics", "📋 Raw Data", "🗃️ Full History"]
        )

        with tab1:
            self.show_variance_overview(df, filtered_queries)

        with tab2:
            self.show_query_deep_dive(df, filtered_queries)

        with tab3:
            self.show_temporal_analysis(df, filtered_queries)

        with tab4:
            self.show_consistency_metrics(df, filtered_queries)

        with tab5:
            self.show_raw_data(df, filtered_queries)

        with tab6:
            self.show_full_history(df)

    # -----------------------
    # Tab: Variance Overview
    # -----------------------
    def show_variance_overview(self, df: pd.DataFrame, filtered_queries: pd.DataFrame):
        st.header("Variance Overview")

        if filtered_queries.empty:
            st.info("No queries match the selected filters.")
            return

        records = []
        for _, q in filtered_queries.iterrows():
            qdf = df[df["query_fingerprint"] == q["fingerprint"]]
            m = analyze_variance_for_query(qdf)
            records.append(
                {
                    "Query": f"{q['use_case'][:20]}... / {q['sector'][:20]}...",
                    "Trials": q["trial_count"],
                    "Trend Diversity": m.get("trends", {}).get("diversity_ratio", 0.0) * 100,
                    "Confidence CV": m.get("trends", {}).get("confidence_cv", 0.0) * 100,
                    "Budget CV": m.get("implementation", {}).get("budget_cv", 0.0) * 100,
                    "Text Consistency": m.get("consistency", {}).get("trend_similarity_mean", 0.0) * 100,
                }
            )

        variance_df = pd.DataFrame(records)

        fig = make_subplots(
            rows=2,
            cols=2,
            subplot_titles=("Trend Diversity by Query", "Confidence Score Variance", "Budget Variance", "Text Consistency"),
        )

        fig.add_trace(go.Bar(x=variance_df["Query"], y=variance_df["Trend Diversity"], name="Trend Diversity %"), row=1, col=1)
        fig.add_trace(go.Bar(x=variance_df["Query"], y=variance_df["Confidence CV"], name="Confidence CV %"), row=1, col=2)
        fig.add_trace(go.Bar(x=variance_df["Query"], y=variance_df["Budget CV"], name="Budget CV %"), row=2, col=1)
        fig.add_trace(go.Bar(x=variance_df["Query"], y=variance_df["Text Consistency"], name="Text Consistency %"), row=2, col=2)

        fig.update_layout(height=800, showlegend=False)
        fig.update_xaxes(tickangle=45)
        st.plotly_chart(fig, use_container_width=True)

        st.subheader("📊 Summary Statistics")
        c1, c2, c3 = st.columns(3)

        with c1:
            st.markdown("**High Variance Queries** (Confidence CV > 30%)")
            hv = variance_df[variance_df["Confidence CV"] > 30]
            if not hv.empty:
                for _, r in hv.iterrows():
                    st.write(f"- {r['Query']}: {r['Confidence CV']:.1f}% CV")
            else:
                st.write("No queries with high variance")

        with c2:
            st.markdown("**Most Consistent Queries** (Text Similarity > 70%)")
            mc = variance_df[variance_df["Text Consistency"] > 70]
            if not mc.empty:
                for _, r in mc.iterrows():
                    st.write(f"- {r['Query']}: {r['Text Consistency']:.1f}% similarity")
            else:
                st.write("No highly consistent queries")

        with c3:
            st.markdown("**Most Diverse Outputs** (Diversity > 80%)")
            md = variance_df[variance_df["Trend Diversity"] > 80]
            if not md.empty:
                for _, r in md.iterrows():
                    st.write(f"- {r['Query']}: {r['Trend Diversity']:.1f}% diversity")
            else:
                st.write("No highly diverse queries")

    # -----------------------
    # Tab: Query Deep Dive
    # -----------------------
    def show_query_deep_dive(self, df: pd.DataFrame, filtered_queries: pd.DataFrame):
        st.header("Query Deep Dive Analysis")

        if filtered_queries.empty:
            st.info("No queries available for analysis.")
            return

        # Build selector options
        options = [
            {
                "label": f"{row['use_case']} / {row['sector']} / {row['demand'][:50]}... ({row['trial_count']} trials)",
                "fingerprint": row["fingerprint"],
            }
            for _, row in filtered_queries.iterrows()
        ]

        selected = st.selectbox("Select a query to analyze:", options=options, format_func=lambda x: x["label"])
        if not selected:
            return

        qdf = df[df["query_fingerprint"] == selected["fingerprint"]].sort_values("created_at")
        if qdf.empty:
            st.info("No records for the selected query.")
            return

        st.subheader("📝 Query Details")
        first_row = qdf.iloc[0]
        st.write(f"**Use Case:** {first_row['use_case']}")
        st.write(f"**Sector:** {first_row['sector']}")
        st.write(f"**Demand:** {first_row['demand']}")
        st.write(f"**Total Trials:** {len(qdf)}")
        st.write(f"**Date Range:** {qdf['created_at'].min().date()} → {qdf['created_at'].max().date()}")

        metrics = analyze_variance_for_query(qdf)

        st.subheader("🎯 Trend Generation Variance")
        c1, c2 = st.columns(2)

        with c1:
            st.markdown("**Trend Diversity Metrics**")
            t = metrics.get("trends", {})
            st.write(f"- Unique Trends: {int(t.get('unique_count', 0))}")
            st.write(f"- Total Trends Generated: {int(t.get('total_count', 0))}")
            st.write(f"- Diversity Ratio: {t.get('diversity_ratio', 0):.2%}")
            if "confidence_mean" in t:
                st.write(f"- Confidence Score Mean: {t['confidence_mean']:.2f}")
                st.write(f"- Confidence Score Std: {t['confidence_std']:.2f}")
                st.write(f"- Coefficient of Variation: {t['confidence_cv']:.2%}")

        with c2:
            st.markdown("**Most Common Trends**")
            common = t.get("most_common", [])
            if common:
                for tr, cnt in common:
                    st.write(f"- {tr[:60]}... — {cnt}×")
            else:
                st.write("None")

        # Trial-by-trial comparison
        st.subheader("📊 Trial-by-Trial Comparison")
        rows = []
        for i, (_, r) in enumerate(qdf.iterrows(), 1):
            titles = extract_trend_titles(r.get("trend_solutions", ""))
            scores = extract_confidence_scores(r.get("trend_solutions", ""))
            rows.append(
                {
                    "Trial": i,
                    "Date": r["created_at"].date() if pd.notna(r["created_at"]) else "",
                    "Trends Generated": len(titles),
                    "Avg Confidence": float(np.mean(scores)) if scores else 0.0,
                    "Selected Trend": (r["selected_trend"][:60] + "...") if r["selected_trend"] else "N/A",
                }
            )
        comp_df = pd.DataFrame(rows)
        st.dataframe(comp_df, use_container_width=True)

        # Confidence evolution
        if (comp_df["Avg Confidence"] > 0).any():
            fig = px.line(comp_df, x="Trial", y="Avg Confidence", markers=True, title="Confidence Score Across Trials")
            fig.add_hline(y=comp_df["Avg Confidence"].mean(), line_dash="dash", annotation_text="Mean")
            st.plotly_chart(fig, use_container_width=True)

        # Pairwise similarity heatmap
        if len(qdf) > 1:
            st.subheader("🔄 Text Similarity Matrix (Trend Solutions)")
            texts = qdf["trend_solutions"].tolist()
            n = len(texts)
            mtx = np.zeros((n, n))
            for i in range(n):
                for j in range(n):
                    if i == j:
                        mtx[i, j] = 1.0
                    else:
                        a, b = texts[i], texts[j]
                        mtx[i, j] = jaccard_text_similarity(a, b) if a and b else 0.0

            fig = go.Figure(
                data=go.Heatmap(
                    z=mtx,
                    x=[f"Trial {i+1}" for i in range(n)],
                    y=[f"Trial {i+1}" for i in range(n)],
                    colorscale="RdYlGn",
                    text=np.round(mtx, 2),
                    texttemplate="%{text}",
                    textfont={"size": 10},
                    colorbar=dict(title="Similarity"),
                )
            )
            fig.update_layout(title="Trend Solutions Similarity", xaxis_title="Trial", yaxis_title="Trial", height=500)
            st.plotly_chart(fig, use_container_width=True)

    # -----------------------
    # Tab: Temporal Analysis
    # -----------------------
    def show_temporal_analysis(self, df: pd.DataFrame, filtered_queries: pd.DataFrame):
        st.header("Temporal Variance Analysis")

        if df["created_at"].isna().all():
            st.info("No timestamps available to plot temporal trends.")
            return

        # Date input
        min_d, max_d = df["created_at"].min().date(), df["created_at"].max().date()
        start_d, end_d = st.date_input("Select date range:", value=(min_d, max_d), min_value=min_d, max_value=max_d)

        m = (df["created_at"].dt.date >= start_d) & (df["created_at"].dt.date <= end_d)
        tdf = df[m].copy()

        if tdf.empty:
            st.info("No data in the selected range.")
            return

        # Weekly aggregation
        tdf["week"] = tdf["created_at"].dt.to_period("W")
        weekly_stats = []
        for wk in tdf["week"].unique():
            wkdf = tdf[tdf["week"] == wk]
            confs = []
            uniq_trends = set()
            for _, r in wkdf.iterrows():
                confs.extend(extract_confidence_scores(r.get("trend_solutions", "")))
                uniq_trends.update(extract_trend_titles(r.get("trend_solutions", "")))
            weekly_stats.append(
                {
                    "Week": wk.to_timestamp(),
                    "Trials": len(wkdf),
                    "Unique Queries": wkdf["query_fingerprint"].nunique(),
                    "Avg Confidence": float(np.mean(confs)) if confs else 0.0,
                    "Confidence Std": float(np.std(confs)) if confs else 0.0,
                    "Unique Trends": len(uniq_trends),
                }
            )

        if not weekly_stats:
            st.info("Not enough data to display weekly statistics.")
            return

        wdf = pd.DataFrame(weekly_stats)

        fig = make_subplots(
            rows=3,
            cols=1,
            subplot_titles=("Trial Volume Over Time", "Confidence Score Stability", "Trend Diversity Over Time"),
            vertical_spacing=0.1,
        )
        fig.add_trace(go.Bar(x=wdf["Week"], y=wdf["Trials"], name="Trials"), row=1, col=1)
        fig.add_trace(
            go.Scatter(
                x=wdf["Week"],
                y=wdf["Avg Confidence"],
                mode="lines+markers",
                name="Avg Confidence",
                error_y=dict(type="data", array=wdf["Confidence Std"], visible=True),
            ),
            row=2,
            col=1,
        )
        fig.add_trace(
            go.Scatter(x=wdf["Week"], y=wdf["Unique Trends"], mode="lines+markers", name="Unique Trends"),
            row=3,
            col=1,
        )
        fig.update_layout(height=900, showlegend=False)
        fig.update_xaxes(title_text="Week", row=3, col=1)
        st.plotly_chart(fig, use_container_width=True)

        # Trend stats
        st.subheader("📈 Trend Analysis")
        cc1, cc2 = st.columns(2)

        with cc1:
            # Try SciPy's linregress; fallback to numpy.polyfit if SciPy is unavailable
            if len(wdf) > 2:
                x = np.arange(len(wdf))
                y = wdf["Confidence Std"].fillna(0).to_numpy(dtype=float)
                slope, p_value = None, None
                try:
                    from scipy.stats import linregress  # type: ignore

                    res = linregress(x, y)
                    slope, p_value = float(res.slope), float(res.pvalue)
                except Exception:
                    # Fallback (no p-value): use polyfit slope only
                    try:
                        slope = float(np.polyfit(x, y, 1)[0])
                        p_value = None
                    except Exception:
                        slope = None
                        p_value = None

                if slope is not None and p_value is not None:
                    trend = "increasing" if slope > 0 else "decreasing"
                    if p_value < 0.05:
                        st.success(f"Confidence variance is **{trend}** over time (p={p_value:.3f})")
                    else:
                        st.info("No significant trend in confidence variance over time")
                elif slope is not None:
                    trend = "increasing" if slope > 0 else "decreasing"
                    st.info(f"Confidence variance slope is {trend} (no p-value available)")
                else:
                    st.info("Trend could not be computed.")

        with cc2:
            if len(wdf) > 3:
                wdf["Rolling_Std"] = wdf["Avg Confidence"].rolling(window=3, min_periods=1).std()
                current = float(wdf["Rolling_Std"].iloc[-1]) if pd.notna(wdf["Rolling_Std"].iloc[-1]) else 0.0
                avg = float(wdf["Rolling_Std"].mean())
                if avg == 0:
                    st.info("Rolling stability could not be determined.")
                elif current < avg * 0.8:
                    st.success("Recent outputs are more stable than average")
                elif current > avg * 1.2:
                    st.warning("Recent outputs show higher variance than average")
                else:
                    st.info("Output stability is within normal range")

    # -----------------------
    # Tab: Consistency Metrics
    # -----------------------
    def show_consistency_metrics(self, df: pd.DataFrame, filtered_queries: pd.DataFrame):
        st.header("Consistency Analysis Across Output Types")

        if filtered_queries.empty:
            st.info("No queries available for consistency analysis.")
            return

        rows = []
        for _, q in filtered_queries.iterrows():
            if q["trial_count"] < 2:
                continue
            qdf = df[df["query_fingerprint"] == q["fingerprint"]]
            m = analyze_variance_for_query(qdf)
            rows.append(
                {
                    "Query": f"{q['use_case'][:30]}... / {q['sector'][:20]}...",
                    "Trials": q["trial_count"],
                    "Trend Consistency": m.get("consistency", {}).get("trend_similarity_mean", 0.0) * 100,
                    "Assessment Consistency": m.get("consistency", {}).get("assessment_similarity_mean", 0.0) * 100,
                    "Market Consistency": m.get("consistency", {}).get("market_similarity_mean", 0.0) * 100,
                    "Classification Entropy": m.get("assessment", {}).get("classification_entropy", 0.0),
                }
            )

        if not rows:
            st.info("Not enough data for consistency analysis (need queries with ≥ 2 trials).")
            return

        cdf = pd.DataFrame(rows)

        st.subheader("📊 Consistency Distribution")
        fig = go.Figure()
        fig.add_trace(go.Box(y=cdf["Trend Consistency"], name="Trends", boxpoints="all", jitter=0.3, pointpos=-1.8))
        fig.add_trace(go.Box(y=cdf["Assessment Consistency"], name="Assessment", boxpoints="all", jitter=0.3, pointpos=-1.8))
        fig.add_trace(go.Box(y=cdf["Market Consistency"], name="Market Solution", boxpoints="all", jitter=0.3, pointpos=-1.8))
        fig.update_layout(title="Consistency Distribution Across Output Types", yaxis_title="Consistency %", showlegend=True, height=500)
        st.plotly_chart(fig, use_container_width=True)

        st.subheader("🔗 Correlation Analysis")
        col1, col2 = st.columns(2)

        with col1:
            if len(cdf) > 3:
                corr = cdf[["Trials", "Trend Consistency", "Assessment Consistency", "Market Consistency"]].corr()
                fig = go.Figure(
                    data=go.Heatmap(
                        z=corr.values,
                        x=corr.columns,
                        y=corr.columns,
                        colorscale="RdBu",
                        zmid=0,
                        text=np.round(corr.values, 2),
                        texttemplate="%{text}",
                        textfont={"size": 10},
                        colorbar=dict(title="Correlation"),
                    )
                )
                fig.update_layout(title="Correlation Matrix", height=400)
                st.plotly_chart(fig, use_container_width=True)

        with col2:
            # sanitize size (entropy) to be strictly positive to avoid Plotly errors
            cdf["EntropySize"] = cdf["Classification Entropy"].clip(lower=0).fillna(0) + 0.01
            fig = px.scatter(
                cdf,
                x="Trials",
                y="Trend Consistency",
                size="EntropySize",
                size_max=40,
                color="Assessment Consistency",
                hover_data=["Query", "Market Consistency", "Classification Entropy"],
                title="Relationship: Trials vs Consistency",
                labels={"Trials": "Number of Trials", "Trend Consistency": "Trend Consistency %"},
            )
            st.plotly_chart(fig, use_container_width=True)

        st.subheader("🎯 Consistency Outliers")
        oc1, oc2, oc3 = st.columns(3)
        with oc1:
            st.markdown("**Highly Consistent** (> 80%)")
            hc = cdf[(cdf["Trend Consistency"] > 80) & (cdf["Assessment Consistency"] > 80)]
            if not hc.empty:
                for _, r in hc.head(5).iterrows():
                    st.write(f"- {r['Query']}")
            else:
                st.write("None")
        with oc2:
            st.markdown("**Highly Variable** (< 40%)")
            hv = cdf[(cdf["Trend Consistency"] < 40) | (cdf["Assessment Consistency"] < 40)]
            if not hv.empty:
                for _, r in hv.head(5).iterrows():
                    st.write(f"- {r['Query']}")
            else:
                st.write("None")
        with oc3:
            st.markdown("**Mixed Consistency**")
            mix = cdf[(cdf["Trend Consistency"] - cdf["Assessment Consistency"]).abs() > 30]
            if not mix.empty:
                for _, r in mix.head(5).iterrows():
                    st.write(f"- {r['Query']}")
                    st.write(
                        f"  Trend: {r['Trend Consistency']:.0f}%, Assessment: {r['Assessment Consistency']:.0f}%"
                    )
            else:
                st.write("None")

    # -----------------------
    # Tab: Raw Data (richer)
    # -----------------------
    def show_raw_data(self, df: pd.DataFrame, filtered_queries: pd.DataFrame):
        st.header("Raw Data (trend_queries)")

        col1, col2, col3 = st.columns(3)
        with col1:
            show_all = st.checkbox("Show all data", value=False)
        with col2:
            if not show_all:
                fps = filtered_queries["fingerprint"].tolist()
                selected_fps = st.multiselect(
                    "Select specific queries (fingerprints):",
                    options=fps,
                    default=fps[:3] if len(fps) > 3 else fps,
                )
            else:
                selected_fps = df["query_fingerprint"].unique().tolist()
        with col3:
            default_cols = ["use_case", "sector", "demand", "selected_trend", "confidence_score", "created_at"]
            cols_to_show = st.multiselect("Columns to display:", options=df.columns.tolist(), default=default_cols)

        if selected_fps and cols_to_show:
            display_df = df[df["query_fingerprint"].isin(selected_fps)][cols_to_show].copy()

            # Basic formatting for created_at
            if "created_at" in display_df.columns:
                display_df["created_at"] = pd.to_datetime(display_df["created_at"], errors="coerce")

            st.subheader(f"Showing {len(display_df)} records")
            st.dataframe(display_df, use_container_width=True, hide_index=True)

            # Download button
            csv = display_df.to_csv(index=False).encode("utf-8")
            st.download_button(
                label="Download filtered data as CSV",
                data=csv,
                file_name=f"variance_analysis_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                mime="text/csv",
            )

        # Summary statistics
        st.subheader("📊 Summary Statistics")
        if selected_fps:
            summary_df = df[df["query_fingerprint"].isin(selected_fps)].copy()
            colA, colB = st.columns(2)

            with colA:
                st.markdown("**Data Coverage**")
                st.write(f"- Total Records: {len(summary_df)}")
                st.write(f"- Unique Queries: {summary_df['query_fingerprint'].nunique()}")
                if not summary_df["created_at"].isna().all():
                    st.write(
                        f"- Date Range: {summary_df['created_at'].min().date()} → {summary_df['created_at'].max().date()}"
                    )
                st.write(f"- Unique Use Cases: {summary_df['use_case'].nunique()}")
                st.write(f"- Unique Sectors: {summary_df['sector'].nunique()}")

            with colB:
                st.markdown("**Data Quality**")
                st.write(f"- Records with Trends: {summary_df['trend_solutions'].astype(bool).sum()}")
                st.write(f"- Records with Assessment: {summary_df['trend_assessment'].astype(bool).sum()}")
                st.write(f"- Records with Market Solution: {summary_df['market_solution'].astype(bool).sum()}")
                st.write(f"- Records with Partners: {summary_df['partners'].astype(bool).sum()}")
                if "confidence_score" in summary_df.columns:
                    st.write(f"- Avg Confidence Score: {pd.to_numeric(summary_df['confidence_score'], errors='coerce').mean():.2f}")

    # -----------------------
    # Tab: Full History Explorer
    # -----------------------
    def show_full_history(self, df: pd.DataFrame):
        st.header("Full History Explorer")

        # Quick search filters
        q1, q2, q3 = st.columns(3)
        with q1:
            uc_filter = st.text_input("Filter by use_case contains:", "")
        with q2:
            sec_filter = st.text_input("Filter by sector contains:", "")
        with q3:
            demand_filter = st.text_input("Filter by demand contains:", "")

        fdf = df.copy()
        if uc_filter:
            fdf = fdf[fdf["use_case"].str.contains(uc_filter, case=False, na=False)]
        if sec_filter:
            fdf = fdf[fdf["sector"].str.contains(sec_filter, case=False, na=False)]
        if demand_filter:
            fdf = fdf[fdf["demand"].str.contains(demand_filter, case=False, na=False)]

        st.caption(f"Filtered records: {len(fdf)}")

        # Grouped summary
        grouped = (
            fdf.groupby("query_fingerprint")
            .agg(
                trials=("id", "count"),
                use_case=("use_case", "first"),
                sector=("sector", "first"),
                demand=("demand", "first"),
                first=("created_at", "min"),
                last=("created_at", "max"),
            )
            .reset_index()
            .sort_values("trials", ascending=False)
        )

        st.subheader("Grouped by Query Fingerprint")
        st.dataframe(
            grouped.rename(columns={"query_fingerprint": "fingerprint"}),
            use_container_width=True,
            hide_index=True,
        )

        # Download grouped summary
        gcsv = grouped.to_csv(index=False).encode("utf-8")
        st.download_button(
            "Download grouped summary (CSV)",
            data=gcsv,
            file_name=f"grouped_summary_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
            mime="text/csv",
        )

        # Limit how many groups to expand at once
        max_groups = st.slider("Max groups to expand below", 1, min(20, len(grouped)) if len(grouped) else 1, min(5, len(grouped)) if len(grouped) else 1)
        top_groups = grouped.head(max_groups)

        for idx, row in top_groups.iterrows():
            fp = row["query_fingerprint"]
            label = f"{row['use_case']} / {row['sector']} / {row['demand']} — {row['trials']} trials"
            with st.expander(label, expanded=False):
                gdf = fdf[fdf["query_fingerprint"] == fp].sort_values("created_at").copy()

                # Compact view
                view_cols = [
                    "created_at",
                    "selected_trend",
                    "confidence_score",
                    "session_id",
                ]
                available_cols = [c for c in view_cols if c in gdf.columns]
                st.dataframe(gdf[available_cols], use_container_width=True, hide_index=True)

                # Full export for this fingerprint
                csv = gdf.to_csv(index=False).encode("utf-8")
                st.download_button(
                    f"Download all records for this query (CSV)",
                    data=csv,
                    file_name=f"history_{fp}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                    mime="text/csv",
                    key=f"dl_{fp}",
                )

        # Global export
        st.subheader("Export Full History")
        full_csv = fdf.to_csv(index=False).encode("utf-8")
        st.download_button(
            "Download ALL filtered history (CSV)",
            data=full_csv,
            file_name=f"full_history_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
            mime="text/csv",
        )


def main():
    dashboard = VarianceAnalysisDashboard()
    dashboard.create_dashboard()


if __name__ == "__main__":
    main()
