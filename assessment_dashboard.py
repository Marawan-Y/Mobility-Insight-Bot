# assessment_dashboard.py

import os
from datetime import datetime
import json

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import pymysql
from dotenv import load_dotenv

load_dotenv()

# IMPORTANT: set page config before any other Streamlit call
st.set_page_config(
    page_title="LLM Quality Assessment Dashboard",
    page_icon="📊",
    layout="wide",
)


class AssessmentDashboard:
    def __init__(self):
        self.conn = self.get_db_connection()

    def get_db_connection(self):
        return pymysql.connect(
            host=os.getenv("DB_HOST"),
            user=os.getenv("DB_USER"),
            password=os.getenv("DB_PASSWORD"),
            database=os.getenv("DB_NAME"),
            charset="utf8mb4",
            autocommit=True,
        )

    # Optional: make the dashboard self-healing by creating tables if missing.
    def ensure_tables(self):
        DDLs = [
            """CREATE TABLE IF NOT EXISTS llm_assessment_trials (
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
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci""",
            """CREATE TABLE IF NOT EXISTS llm_assessment_metrics (
                id INT AUTO_INCREMENT PRIMARY KEY,
                assessment_id VARCHAR(64),
                metric_type VARCHAR(50),
                metric_name VARCHAR(100),
                metric_value FLOAT,
                details JSON,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                INDEX idx_assessment (assessment_id),
                INDEX idx_metric (metric_type, metric_name)
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci""",
        ]
        with self.conn.cursor() as cur:
            for ddl in DDLs:
                cur.execute(ddl)

    def fetch_assessment_data(self, days_back=7) -> pd.DataFrame:
        """Fetch assessment data from database"""
        query = """
        SELECT 
            t.trial_id,
            t.use_case,
            t.sector,
            t.demand,
            t.timestamp,
            t.latency_ms,
            t.token_count,
            t.api_calls,
            JSON_EXTRACT(t.metadata, '$.trend_count') AS trend_count,
            JSON_EXTRACT(t.metadata, '$.confidence_scores') AS confidence_scores
        FROM llm_assessment_trials t
        WHERE t.timestamp >= DATE_SUB(NOW(), INTERVAL %s DAY)
        ORDER BY t.timestamp DESC
        """
        try:
            df = pd.read_sql(query, self.conn, params=[days_back])
        except Exception as e:
            st.error(f"Database query failed for trials: {e}")
            return pd.DataFrame()
        return df

    def fetch_metrics_data(self, days_back=7) -> pd.DataFrame:
        """Fetch aggregated metrics data"""
        query = """
        SELECT 
            m.assessment_id,
            m.metric_type,
            m.metric_name,
            m.metric_value,
            m.created_at
        FROM llm_assessment_metrics m
        WHERE m.created_at >= DATE_SUB(NOW(), INTERVAL %s DAY)
        """
        try:
            df = pd.read_sql(query, self.conn, params=[days_back])
        except Exception as e:
            st.error(f"Database query failed for metrics: {e}")
            return pd.DataFrame()
        return df

    def create_dashboard(self):
        """Create Streamlit dashboard"""
        st.title("🤖 LLM Output Quality Assessment Dashboard")
        st.markdown("Real-time monitoring of LLM performance and quality metrics")

        # Ensure required tables exist (no-op if already created)
        try:
            self.ensure_tables()
        except Exception as e:
            st.warning(f"Could not ensure tables: {e}")

        # Sidebar filters
        st.sidebar.header("Filters")
        days_back = st.sidebar.slider("Days to analyze", 1, 30, 7)

        # Fetch data
        trials_df = self.fetch_assessment_data(days_back)
        metrics_df = self.fetch_metrics_data(days_back)

        # Overview metrics
        col1, col2, col3, col4 = st.columns(4)

        with col1:
            st.metric("Total Trials", len(trials_df), f"Last {days_back} days")

        with col2:
            avg_latency = pd.to_numeric(trials_df.get("latency_ms", pd.Series(dtype=float)), errors="coerce").mean()
            st.metric("Avg Latency", f"{(avg_latency or 0):.0f} ms")

        with col3:
            avg_tokens = pd.to_numeric(trials_df.get("token_count", pd.Series(dtype=float)), errors="coerce").mean()
            total_tokens = pd.to_numeric(trials_df.get("token_count", pd.Series(dtype=float)), errors="coerce").sum()
            st.metric("Avg Tokens", f"{(avg_tokens or 0):.0f}", f"Total: {int(total_tokens):,}")

        with col4:
            total_cost = (pd.to_numeric(trials_df.get("token_count", pd.Series(dtype=float)), errors="coerce").sum() / 1000.0) * 0.002
            st.metric("Est. Cost", f"${total_cost:.2f}", "GPT-3.5 pricing")

        # Main content area
        tab1, tab2, tab3, tab4 = st.tabs(
            ["Performance Trends", "Quality Metrics", "Comparative Analysis", "Raw Data"]
        )

        with tab1:
            self.show_performance_trends(trials_df)

        with tab2:
            self.show_quality_metrics(metrics_df)

        with tab3:
            self.show_comparative_analysis(trials_df, metrics_df)

        with tab4:
            self.show_raw_data(trials_df, metrics_df)

    def show_performance_trends(self, df: pd.DataFrame):
        """Show performance trend charts"""
        st.header("Performance Trends")

        if df is None or df.empty:
            st.info("No trial data available yet.")
            return

        df = df.copy()
        # Ensure types are usable for plotting
        df["timestamp"] = pd.to_datetime(df.get("timestamp"), errors="coerce")
        df["latency_ms"] = pd.to_numeric(df.get("latency_ms"), errors="coerce")
        df["token_count"] = pd.to_numeric(df.get("token_count"), errors="coerce")
        df["api_calls"] = pd.to_numeric(df.get("api_calls"), errors="coerce")

        if df["timestamp"].isna().all():
            st.info("No valid timestamps to plot.")
            return

        # Latency over time
        fig_latency = px.scatter(
            df,
            x="timestamp",
            y="latency_ms",
            color="use_case",
            title="Response Latency Over Time",
            labels={"latency_ms": "Latency (ms)"},
        )
        try:
            mean_latency = df["latency_ms"].mean()
            if pd.notna(mean_latency):
                fig_latency.add_hline(y=mean_latency, line_dash="dash", annotation_text="Average")
        except Exception:
            pass
        st.plotly_chart(fig_latency, use_container_width=True)

        # Token usage distribution + API calls by use case
        col1, col2 = st.columns(2)

        with col1:
            fig_tokens = px.histogram(df, x="token_count", nbins=20, title="Token Usage Distribution")
            st.plotly_chart(fig_tokens, use_container_width=True)

        with col2:
            api_calls_by_case = (
                df.groupby("use_case", dropna=False)["api_calls"]
                .mean()
                .reset_index(name="avg_api_calls")
                .sort_values("avg_api_calls", ascending=False)
            )
            if not api_calls_by_case.empty and api_calls_by_case["avg_api_calls"].notna().any():
                fig_api = px.bar(
                    api_calls_by_case,
                    x="use_case",
                    y="avg_api_calls",
                    title="Average API Calls by Use Case",
                    text="avg_api_calls",
                )
                fig_api.update_traces(texttemplate="%{text:.2f}", textposition="outside")
                fig_api.update_layout(yaxis_title="Avg API Calls", xaxis_title="Use Case")
                st.plotly_chart(fig_api, use_container_width=True)
            else:
                st.info("No API-call data available to plot.")

    def show_quality_metrics(self, df: pd.DataFrame):
        """Show quality metrics visualizations"""
        st.header("Quality Metrics")

        if df is None or df.empty:
            st.info("No metrics available yet.")
            return

        # Diversity metrics
        diversity_df = df[df["metric_type"] == "diversity"]
        if not diversity_df.empty:
            col1, col2 = st.columns(2)

            with col1:
                title_diversity = diversity_df[diversity_df["metric_name"] == "title_diversity"]["metric_value"]
                if not title_diversity.empty:
                    fig_diversity = go.Figure()
                    fig_diversity.add_trace(go.Box(y=title_diversity, name="Title Diversity", boxpoints="all"))
                    fig_diversity.update_layout(title="Title Diversity Distribution", yaxis_title="Diversity Score")
                    st.plotly_chart(fig_diversity, use_container_width=True)
                else:
                    st.info("No title diversity data to display.")

            with col2:
                unique_ratio = diversity_df[diversity_df["metric_name"] == "unique_title_ratio"]["metric_value"]
                if not unique_ratio.empty:
                    fig_unique = go.Figure()
                    fig_unique.add_trace(go.Histogram(x=unique_ratio, nbinsx=20, name="Unique Title Ratio"))
                    fig_unique.update_layout(title="Unique Title Ratio Distribution", xaxis_title="Ratio")
                    st.plotly_chart(fig_unique, use_container_width=True)
                else:
                    st.info("No unique title ratio data to display.")

        # Compliance metrics
        compliance_df = df[df["metric_type"] == "compliance"]
        if not compliance_df.empty:
            st.subheader("Structure Compliance")
            section_compliance = (
                compliance_df[compliance_df["metric_name"].str.startswith("compliance_")]
                .groupby("metric_name")["metric_value"]
                .mean()
                .reset_index()
            )
            if not section_compliance.empty:
                section_compliance["Section"] = (
                    section_compliance["metric_name"]
                    .str.replace("^compliance_", "", regex=True)
                    .str.replace("_", " ")
                    .str.title()
                )
                section_compliance.rename(columns={"metric_value": "Rate"}, inplace=True)
                fig_compliance = px.bar(
                    section_compliance,
                    x="Rate",
                    y="Section",
                    orientation="h",
                    title="Average Compliance by Section",
                    labels={"Rate": "Compliance Rate", "Section": "Section"},
                )
                fig_compliance.update_traces(marker_color="green")
                fig_compliance.add_vline(x=0.9, line_dash="dash", annotation_text="Target")
                st.plotly_chart(fig_compliance, use_container_width=True)
            else:
                st.info("No section-level compliance metrics to display.")

    def show_comparative_analysis(self, trials_df: pd.DataFrame, metrics_df: pd.DataFrame):
        """Show comparative analysis across different inputs"""
        st.header("Comparative Analysis")

        if trials_df is None or trials_df.empty:
            st.info("No trial data available for comparison.")
            return

        df = trials_df.copy()
        df["latency_ms"] = pd.to_numeric(df.get("latency_ms"), errors="coerce")
        df["token_count"] = pd.to_numeric(df.get("token_count"), errors="coerce")

        input_groups = df.groupby(["use_case", "sector", "demand"], dropna=False)
        comparison_data = []
        for (use_case, sector, demand), group in input_groups:
            comparison_data.append(
                {
                    "Input": f"{use_case} / {sector} / {demand}",
                    "Trials": len(group),
                    "Avg Latency": group["latency_ms"].mean(),
                    "Latency Std": group["latency_ms"].std(),
                    "Avg Tokens": group["token_count"].mean(),
                    "Total Cost": (group["token_count"].sum() / 1000.0) * 0.002,
                }
            )

        comparison_df = pd.DataFrame(comparison_data)

        if not comparison_df.empty:
            fig_scatter = px.scatter(
                comparison_df,
                x="Avg Tokens",
                y="Avg Latency",
                size="Trials",
                hover_data=["Input", "Total Cost"],
                title="Performance Comparison: Latency vs Token Usage",
            )
            st.plotly_chart(fig_scatter, use_container_width=True)

            st.subheader("Detailed Comparison")
            st.dataframe(
                comparison_df.style.format(
                    {
                        "Avg Latency": "{:.0f} ms",
                        "Latency Std": "{:.0f} ms",
                        "Avg Tokens": "{:.0f}",
                        "Total Cost": "${:.3f}",
                    }
                ),
                use_container_width=True,
            )
        else:
            st.info("No comparative data to display.")

    def show_raw_data(self, trials_df: pd.DataFrame, metrics_df: pd.DataFrame):
        """Show raw data tables"""
        st.header("Raw Data")

        if trials_df is None or trials_df.empty:
            st.info("No trial rows yet.")
            return

        df = trials_df.copy()
        df["timestamp"] = pd.to_datetime(df.get("timestamp"), errors="coerce")
        # Clean up JSON_EXTRACT fields (may be JSON strings or None)
        for col in ("trend_count", "confidence_scores"):
            if col in df.columns:
                df[col] = df[col].apply(
                    lambda v: json.loads(v) if isinstance(v, (str, bytes)) and str(v).strip() != "" else v
                )

        # Prepare a pretty display table
        display_df = df.head(100).copy()
        display_df["timestamp"] = display_df["timestamp"].dt.strftime("%Y-%m-%d %H:%M:%S")

        st.subheader("Recent Trials")
        st.dataframe(
            display_df.style.format(
                {
                    "latency_ms": "{:.0f}",
                    "token_count": "{:,}",
                }
            ),
            use_container_width=True,
        )

        # Download button
        csv = df.to_csv(index=False)
        st.download_button(
            label="Download Trials Data as CSV",
            data=csv,
            file_name=f"llm_trials_{datetime.now().strftime('%Y%m%d')}.csv",
            mime="text/csv",
        )


def main():
    dashboard = AssessmentDashboard()
    dashboard.create_dashboard()


if __name__ == "__main__":
    main()
