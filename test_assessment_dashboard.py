# variance_assessment_dashboard.py

import os
from datetime import datetime, timedelta
import json
import hashlib
from typing import Dict, List, Tuple

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import numpy as np
import pymysql
from dotenv import load_dotenv
import re
from collections import defaultdict, Counter
from io import StringIO, BytesIO

load_dotenv()

# IMPORTANT: set page config before any other Streamlit call
st.set_page_config(
    page_title="LLM Output Variance Analysis Dashboard",
    page_icon="📊",
    layout="wide",
)


class VarianceAnalysisDashboard:
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
    
    def fetch_all_historical_data(self) -> pd.DataFrame:
        """Fetch ALL historical data from trend_queries table"""
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
            df = pd.read_sql(query, self.conn)
            # Ensure proper dtypes
            if 'created_at' in df.columns:
                df['created_at'] = pd.to_datetime(df['created_at'], errors='coerce')
            return df
        except Exception as e:
            st.error(f"Database query failed: {e}")
            return pd.DataFrame()
    
    def create_query_fingerprint(self, use_case, sector, demand):
        """Create unique fingerprint for each query combination"""
        query_str = f"{use_case}|{sector}|{demand}".lower().strip()
        return hashlib.md5(query_str.encode()).hexdigest()[:12]
    
    def extract_trend_titles(self, trend_solutions):
        """Extract trend titles from the trend_solutions text"""
        if not trend_solutions:
            return []
        
        patterns = [
            r"Technology Title:\s*(.+?)(?:\n|$)",
            r"### Trend \d+:\s*(.+?)(?:\n|$)",
            r"Disruptive Technology \d+:\s*(.+?)(?:\n|$)",
            r"\*\*Technology Title\*\*:\s*(.+?)(?:\n|$)"
        ]
        
        titles = []
        for pattern in patterns:
            found = re.findall(pattern, trend_solutions, re.IGNORECASE | re.MULTILINE)
            if found:
                titles.extend(found)
        
        return [t.strip() for t in titles if t.strip()]
    
    def extract_confidence_scores(self, trend_solutions):
        """Extract confidence scores from trend text"""
        if not trend_solutions:
            return []
        
        pattern = r"Confidence Score:\s*([0-9.]+)"
        scores = re.findall(pattern, trend_solutions, re.IGNORECASE)
        return [float(s) for s in scores if s]
    
    def extract_key_metrics(self, text, metric_type):
        """Extract various metrics from different text sections"""
        if not text:
            return {}
        
        metrics = {}
        
        if metric_type == "assessment":
            score_pattern = r"(\w+[\s\w]*?):\s*(\d+(?:\.\d+)?)\s*(?:/10|out of 10)?"
            matches = re.findall(score_pattern, text)
            for key, value in matches:
                metrics[key.strip()] = float(value)
                
        elif metric_type == "radar":
            if "ACT" in text.upper():
                metrics["classification"] = "ACT"
            elif "PREPARE" in text.upper():
                metrics["classification"] = "PREPARE"
            elif "WATCH" in text.upper():
                metrics["classification"] = "WATCH"
            timeline_pattern = r"(\d+)[\s-]*(?:months?|years?)"
            timelines = re.findall(timeline_pattern, text, re.IGNORECASE)
            if timelines:
                metrics["timeline_mentions"] = len(timelines)
                
        elif metric_type == "market":
            budget_pattern = r"€\s*(\d+(?:\.\d+)?)\s*[MBmb]illion"
            budgets = re.findall(budget_pattern, text, re.IGNORECASE)
            if budgets:
                metrics["budget_mentions"] = [float(b) for b in budgets]
            roi_pattern = r"(\d+(?:\.\d+)?)\s*%"
            rois = re.findall(roi_pattern, text)
            if rois:
                metrics["roi_percentages"] = [float(r) for r in rois]
        
        return metrics
    
    def calculate_text_similarity(self, text1, text2):
        """Calculate similarity between two texts using Jaccard similarity of words"""
        if not text1 or not text2:
            return 0.0
        words1 = set(text1.lower().split())
        words2 = set(text2.lower().split())
        if not words1 and not words2:
            return 1.0
        if not words1 or not words2:
            return 0.0
        intersection = words1.intersection(words2)
        union = words1.union(words2)
        return len(intersection) / len(union) if union else 0.0
    
    def analyze_variance_for_query(self, df_subset):
        """Analyze variance for a specific query across multiple trials"""
        if df_subset.empty:
            return {}
        
        variance_metrics = {
            'trial_count': len(df_subset),
            'time_span_days': (df_subset['created_at'].max() - df_subset['created_at'].min()).days if len(df_subset) > 1 else 0,
            'trends': {},
            'assessment': {},
            'implementation': {},
            'consistency': {}
        }
        
        # Analyze trend variance
        all_trends = []
        all_confidence_scores = []
        for _, row in df_subset.iterrows():
            trends = self.extract_trend_titles(row['trend_solutions'])
            scores = self.extract_confidence_scores(row['trend_solutions'])
            all_trends.extend(trends)
            all_confidence_scores.extend(scores)
        
        if all_trends:
            unique_trends = set(all_trends)
            variance_metrics['trends']['unique_count'] = len(unique_trends)
            variance_metrics['trends']['total_count'] = len(all_trends)
            variance_metrics['trends']['diversity_ratio'] = len(unique_trends) / len(all_trends) if all_trends else 0
            trend_counter = Counter(all_trends)
            variance_metrics['trends']['most_common'] = trend_counter.most_common(5)
            
        if all_confidence_scores:
            variance_metrics['trends']['confidence_mean'] = np.mean(all_confidence_scores)
            variance_metrics['trends']['confidence_std'] = np.std(all_confidence_scores)
            variance_metrics['trends']['confidence_cv'] = (np.std(all_confidence_scores) / np.mean(all_confidence_scores)) if np.mean(all_confidence_scores) > 0 else 0
        
        # Assessment variance
        assessment_scores = []
        radar_classifications = []
        for _, row in df_subset.iterrows():
            if row['trend_assessment']:
                metrics = self.extract_key_metrics(row['trend_assessment'], 'assessment')
                if metrics:
                    assessment_scores.append(list(metrics.values()))
            if row['radar_positioning']:
                radar_metrics = self.extract_key_metrics(row['radar_positioning'], 'radar')
                if 'classification' in radar_metrics:
                    radar_classifications.append(radar_metrics['classification'])
        
        if assessment_scores:
            flat_scores = [score for sub in assessment_scores for score in sub]
            if flat_scores:
                variance_metrics['assessment']['score_mean'] = np.mean(flat_scores)
                variance_metrics['assessment']['score_std'] = np.std(flat_scores)
        
        if radar_classifications:
            classification_counter = Counter(radar_classifications)
            variance_metrics['assessment']['classification_distribution'] = dict(classification_counter)
            # Stable entropy (clip any tiny negative due to float)
            probs = np.array(list(classification_counter.values()), dtype=float) / len(radar_classifications)
            entropy = float(-(probs * np.log2(probs + 1e-12)).sum())
            variance_metrics['assessment']['classification_entropy'] = max(entropy, 0.0)
        
        # Implementation variance
        all_budgets, all_rois = [], []
        for _, row in df_subset.iterrows():
            if row['market_solution']:
                m = self.extract_key_metrics(row['market_solution'], 'market')
                if 'budget_mentions' in m:
                    all_budgets.extend(m['budget_mentions'])
                if 'roi_percentages' in m:
                    all_rois.extend(m['roi_percentages'])
        if all_budgets:
            variance_metrics['implementation']['budget_mean'] = np.mean(all_budgets)
            variance_metrics['implementation']['budget_std'] = np.std(all_budgets)
            variance_metrics['implementation']['budget_cv'] = (np.std(all_budgets) / np.mean(all_budgets)) if np.mean(all_budgets) > 0 else 0
        if all_rois:
            variance_metrics['implementation']['roi_mean'] = np.mean(all_rois)
            variance_metrics['implementation']['roi_std'] = np.std(all_rois)
        
        # Text consistency
        if len(df_subset) > 1:
            trend_similarities, assessment_similarities, market_similarities = [], [], []
            rows = df_subset.to_dict('records')
            for i in range(len(rows)):
                for j in range(i + 1, len(rows)):
                    if rows[i]['trend_solutions'] and rows[j]['trend_solutions']:
                        trend_similarities.append(self.calculate_text_similarity(rows[i]['trend_solutions'], rows[j]['trend_solutions']))
                    if rows[i]['trend_assessment'] and rows[j]['trend_assessment']:
                        assessment_similarities.append(self.calculate_text_similarity(rows[i]['trend_assessment'], rows[j]['trend_assessment']))
                    if rows[i]['market_solution'] and rows[j]['market_solution']:
                        market_similarities.append(self.calculate_text_similarity(rows[i]['market_solution'], rows[j]['market_solution']))
            if trend_similarities:
                variance_metrics['consistency']['trend_similarity_mean'] = np.mean(trend_similarities)
                variance_metrics['consistency']['trend_similarity_std'] = np.std(trend_similarities)
            if assessment_similarities:
                variance_metrics['consistency']['assessment_similarity_mean'] = np.mean(assessment_similarities)
            if market_similarities:
                variance_metrics['consistency']['market_similarity_mean'] = np.mean(market_similarities)
        
        return variance_metrics
    
    def create_dashboard(self):
        """Create the variance analysis dashboard"""
        st.title("🔬 LLM Output Variance Analysis Dashboard")
        st.markdown("Analyzing consistency and variance in LLM responses across identical queries")
        
        # Fetch all historical data
        df = self.fetch_all_historical_data()
        if df.empty:
            st.warning("No data available in the database.")
            return
        
        # Add query fingerprint
        df['query_fingerprint'] = df.apply(
            lambda row: self.create_query_fingerprint(row['use_case'], row['sector'], row['demand']),
            axis=1
        )
        
        # Group by query fingerprint to find repeated queries
        query_groups = df.groupby('query_fingerprint').agg({
            'id': 'count',
            'use_case': 'first',
            'sector': 'first',
            'demand': 'first',
            'created_at': ['min', 'max']
        }).reset_index()
        query_groups.columns = ['fingerprint', 'trial_count', 'use_case', 'sector', 'demand', 'first_trial', 'last_trial']
        query_groups = query_groups.sort_values('trial_count', ascending=False)
        
        # Sidebar filters
        st.sidebar.header("📋 Filters")
        min_trials = st.sidebar.slider(
            "Minimum trials per query",
            min_value=1,
            max_value=int(query_groups['trial_count'].max()),
            value=2
        )
        # Filter queries with minimum trials
        filtered_queries = query_groups[query_groups['trial_count'] >= min_trials]
        selected_use_cases = st.sidebar.multiselect(
            "Use Cases",
            options=filtered_queries['use_case'].unique(),
            default=filtered_queries['use_case'].unique()[:5] if len(filtered_queries) > 5 else filtered_queries['use_case'].unique()
        )
        if selected_use_cases:
            filtered_queries = filtered_queries[filtered_queries['use_case'].isin(selected_use_cases)]
        
        # Overview metrics
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("Total Unique Queries", len(query_groups))
        with col2:
            st.metric("Total Trials", len(df))
        with col3:
            avg_trials = query_groups['trial_count'].mean()
            st.metric("Avg Trials/Query", f"{avg_trials:.1f}")
        with col4:
            queries_with_variance = len(query_groups[query_groups['trial_count'] > 1])
            st.metric("Queries with Multiple Trials", queries_with_variance)
        
        # Main tabs (added 🗃️ Full History)
        tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs([
            "📊 Variance Overview",
            "🎯 Query Deep Dive",
            "📈 Temporal Analysis",
            "🔄 Consistency Metrics",
            "📋 Raw Data",
            "🗃️ Full History"
        ])
        
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
    
    def show_variance_overview(self, df, filtered_queries):
        """Show overview of variance across all queries"""
        st.header("Variance Overview")
        if filtered_queries.empty:
            st.info("No queries match the selected filters.")
            return
        
        variance_data = []
        for _, query in filtered_queries.iterrows():
            query_df = df[df['query_fingerprint'] == query['fingerprint']]
            metrics = self.analyze_variance_for_query(query_df)
            variance_data.append({
                'Query': f"{query['use_case'][:20]}... / {query['sector'][:20]}...",
                'Trials': query['trial_count'],
                'Trend Diversity': metrics['trends'].get('diversity_ratio', 0) * 100,
                'Confidence CV': metrics['trends'].get('confidence_cv', 0) * 100,
                'Budget CV': metrics['implementation'].get('budget_cv', 0) * 100,
                'Text Consistency': metrics['consistency'].get('trend_similarity_mean', 0) * 100
            })
        variance_df = pd.DataFrame(variance_data)
        
        fig = make_subplots(
            rows=2, cols=2,
            subplot_titles=(
                'Trend Diversity by Query',
                'Confidence Score Variance',
                'Budget Variance',
                'Text Consistency'
            )
        )
        fig.add_trace(go.Bar(x=variance_df['Query'], y=variance_df['Trend Diversity'], name='Trend Diversity %'), row=1, col=1)
        fig.add_trace(go.Bar(x=variance_df['Query'], y=variance_df['Confidence CV'], name='Confidence CV %'), row=1, col=2)
        fig.add_trace(go.Bar(x=variance_df['Query'], y=variance_df['Budget CV'], name='Budget CV %'), row=2, col=1)
        fig.add_trace(go.Bar(x=variance_df['Query'], y=variance_df['Text Consistency'], name='Text Consistency %'), row=2, col=2)
        fig.update_layout(height=800, showlegend=False)
        fig.update_xaxes(tickangle=45)
        st.plotly_chart(fig, use_container_width=True)
        
        st.subheader("📊 Summary Statistics")
        col1, col2, col3 = st.columns(3)
        with col1:
            st.markdown("**High Variance Queries** (CV > 30%)")
            high_variance = variance_df[variance_df['Confidence CV'] > 30]
            if not high_variance.empty:
                for _, row in high_variance.iterrows():
                    st.write(f"- {row['Query']}: {row['Confidence CV']:.1f}% CV")
            else:
                st.write("No queries with high variance")
        with col2:
            st.markdown("**Most Consistent Queries** (Text Similarity > 70%)")
            consistent = variance_df[variance_df['Text Consistency'] > 70]
            if not consistent.empty:
                for _, row in consistent.iterrows():
                    st.write(f"- {row['Query']}: {row['Text Consistency']:.1f}% similarity")
            else:
                st.write("No highly consistent queries")
        with col3:
            st.markdown("**Most Diverse Outputs** (Diversity > 80%)")
            diverse = variance_df[variance_df['Trend Diversity'] > 80]
            if not diverse.empty:
                for _, row in diverse.iterrows():
                    st.write(f"- {row['Query']}: {row['Trend Diversity']:.1f}% diversity")
            else:
                st.write("No highly diverse queries")
    
    def show_query_deep_dive(self, df, filtered_queries):
        """Deep dive into a specific query's variance"""
        st.header("Query Deep Dive Analysis")
        if filtered_queries.empty:
            st.info("No queries available for analysis.")
            return
        
        query_options = []
        for _, q in filtered_queries.iterrows():
            query_options.append({
                'label': f"{q['use_case']} / {q['sector']} / {q['demand'][:50]}... ({q['trial_count']} trials)",
                'fingerprint': q['fingerprint']
            })
        
        selected_query = st.selectbox(
            "Select a query to analyze:",
            options=query_options,
            format_func=lambda x: x['label']
        )
        
        if selected_query:
            query_df = df[df['query_fingerprint'] == selected_query['fingerprint']].sort_values('created_at')
            st.subheader("📝 Query Details")
            first_row = query_df.iloc[0]
            st.write(f"**Use Case:** {first_row['use_case']}")
            st.write(f"**Sector:** {first_row['sector']}")
            st.write(f"**Demand:** {first_row['demand']}")
            st.write(f"**Total Trials:** {len(query_df)}")
            st.write(f"**Date Range:** {query_df['created_at'].min().date()} to {query_df['created_at'].max().date()}")
            
            metrics = self.analyze_variance_for_query(query_df)
            st.subheader("🎯 Trend Generation Variance")
            col1, col2 = st.columns(2)
            with col1:
                st.markdown("**Trend Diversity Metrics**")
                if 'trends' in metrics and metrics['trends']:
                    st.write(f"- Unique Trends: {metrics['trends'].get('unique_count', 0)}")
                    st.write(f"- Total Trends Generated: {metrics['trends'].get('total_count', 0)}")
                    st.write(f"- Diversity Ratio: {metrics['trends'].get('diversity_ratio', 0):.2%}")
                    if 'confidence_mean' in metrics['trends']:
                        st.write(f"- Confidence Score Mean: {metrics['trends']['confidence_mean']:.2f}")
                        st.write(f"- Confidence Score Std: {metrics['trends']['confidence_std']:.2f}")
                        st.write(f"- Coefficient of Variation: {metrics['trends']['confidence_cv']:.2%}")
            with col2:
                st.markdown("**Most Common Trends**")
                if 'most_common' in metrics['trends']:
                    for trend, count in metrics['trends']['most_common']:
                        st.write(f"- {trend[:50]}...: {count} times")
            
            st.subheader("📊 Trial-by-Trial Comparison")
            trial_comparison = []
            for idx, (_, row) in enumerate(query_df.iterrows(), 1):
                trends = self.extract_trend_titles(row['trend_solutions'])
                scores = self.extract_confidence_scores(row['trend_solutions'])
                trial_comparison.append({
                    'Trial': idx,
                    'Date': row['created_at'].date(),
                    'Trends Generated': len(trends),
                    'Avg Confidence': np.mean(scores) if scores else 0,
                    'Selected Trend': row['selected_trend'][:30] if row['selected_trend'] else 'N/A'
                })
            comparison_df = pd.DataFrame(trial_comparison)
            st.dataframe(comparison_df, use_container_width=True)
            
            if any(row['Avg Confidence'] > 0 for row in trial_comparison):
                fig = px.line(
                    comparison_df, x='Trial', y='Avg Confidence',
                    markers=True, title='Confidence Score Evolution Across Trials'
                )
                fig.add_hline(y=comparison_df['Avg Confidence'].mean(), line_dash="dash", annotation_text="Mean")
                st.plotly_chart(fig, use_container_width=True)
            
            if len(query_df) > 1:
                st.subheader("🔄 Text Similarity Matrix")
                texts = query_df['trend_solutions'].tolist()
                n = len(texts)
                similarity_matrix = np.zeros((n, n))
                for i in range(n):
                    for j in range(n):
                        if i != j and texts[i] and texts[j]:
                            similarity_matrix[i, j] = self.calculate_text_similarity(texts[i], texts[j])
                        elif i == j:
                            similarity_matrix[i, j] = 1.0
                fig = go.Figure(data=go.Heatmap(
                    z=similarity_matrix,
                    x=[f"Trial {i+1}" for i in range(n)],
                    y=[f"Trial {i+1}" for i in range(n)],
                    colorscale='RdYlGn',
                    text=similarity_matrix.round(2),
                    texttemplate="%{text}",
                    textfont={"size": 10},
                    colorbar=dict(title="Similarity")
                ))
                fig.update_layout(
                    title="Trend Solutions Text Similarity Between Trials",
                    xaxis_title="Trial", yaxis_title="Trial", height=500
                )
                st.plotly_chart(fig, use_container_width=True)
    
    def show_temporal_analysis(self, df, filtered_queries):
        """Analyze variance patterns over time"""
        st.header("Temporal Variance Analysis")
        date_range = st.date_input(
            "Select date range:",
            value=(df['created_at'].min().date(), df['created_at'].max().date()),
            min_value=df['created_at'].min().date(),
            max_value=df['created_at'].max().date()
        )
        mask = (df['created_at'].dt.date >= date_range[0]) & (df['created_at'].dt.date <= date_range[1])
        temporal_df = df[mask].copy()
        temporal_df['week'] = temporal_df['created_at'].dt.to_period('W')
        
        weekly_stats = []
        for week in temporal_df['week'].unique():
            week_data = temporal_df[temporal_df['week'] == week]
            all_confidence_scores, unique_trends = [], set()
            for _, row in week_data.iterrows():
                trends = self.extract_trend_titles(row['trend_solutions'])
                scores = self.extract_confidence_scores(row['trend_solutions'])
                unique_trends.update(trends)
                all_confidence_scores.extend(scores)
            weekly_stats.append({
                'Week': week.to_timestamp(),
                'Trials': len(week_data),
                'Unique Queries': week_data['query_fingerprint'].nunique(),
                'Avg Confidence': np.mean(all_confidence_scores) if all_confidence_scores else 0,
                'Confidence Std': np.std(all_confidence_scores) if all_confidence_scores else 0,
                'Unique Trends': len(unique_trends)
            })
        
        if weekly_stats:
            weekly_df = pd.DataFrame(weekly_stats)
            fig = make_subplots(
                rows=3, cols=1,
                subplot_titles=('Trial Volume Over Time','Confidence Score Stability','Trend Diversity Over Time'),
                vertical_spacing=0.1
            )
            fig.add_trace(go.Bar(x=weekly_df['Week'], y=weekly_df['Trials'], name='Trials'), row=1, col=1)
            fig.add_trace(go.Scatter(
                x=weekly_df['Week'], y=weekly_df['Avg Confidence'],
                mode='lines+markers', name='Avg Confidence',
                error_y=dict(type='data', array=weekly_df['Confidence Std'], visible=True)
            ), row=2, col=1)
            fig.add_trace(go.Scatter(
                x=weekly_df['Week'], y=weekly_df['Unique Trends'],
                mode='lines+markers', name='Unique Trends', line=dict(color='green')
            ), row=3, col=1)
            fig.update_layout(height=900, showlegend=False)
            fig.update_xaxes(title_text="Week", row=3, col=1)
            st.plotly_chart(fig, use_container_width=True)
            
            st.subheader("📈 Trend Analysis")
            col1, col2 = st.columns(2)
            with col1:
                if len(weekly_df) > 2:
                    try:
                        from scipy.stats import linregress
                        x = np.arange(len(weekly_df))
                        slope, intercept, r_value, p_value, std_err = linregress(x, weekly_df['Confidence Std'].fillna(0))
                        if p_value < 0.05:
                            trend = "increasing" if slope > 0 else "decreasing"
                            st.success(f"Confidence variance is **{trend}** over time (p={p_value:.3f})")
                        else:
                            st.info("No significant trend in confidence variance over time")
                    except Exception:
                        y = weekly_df['Confidence Std'].fillna(0).to_numpy()
                        x = np.arange(len(y))
                        slope = np.polyfit(x, y, 1)[0]
                        trend = "increasing" if slope > 0 else "decreasing"
                        st.info(f"Confidence variance trend (no SciPy): **{trend}** (slope={slope:.4f})")
            with col2:
                if len(weekly_df) > 3:
                    weekly_df['Rolling_Std'] = weekly_df['Avg Confidence'].rolling(window=3, min_periods=1).std()
                    current_stability = weekly_df['Rolling_Std'].iloc[-1]
                    avg_stability = weekly_df['Rolling_Std'].mean()
                    if current_stability < avg_stability * 0.8:
                        st.success("Recent outputs are more stable than average")
                    elif current_stability > avg_stability * 1.2:
                        st.warning("Recent outputs show higher variance than average")
                    else:
                        st.info("Output stability is within normal range")
    
    def show_consistency_metrics(self, df, filtered_queries):
        """Show detailed consistency metrics across different output types"""
        st.header("Consistency Analysis Across Output Types")
        if filtered_queries.empty:
            st.info("No queries available for consistency analysis.")
            return
        
        consistency_data = []
        for _, query in filtered_queries.iterrows():
            if query['trial_count'] < 2:
                continue
            query_df = df[df['query_fingerprint'] == query['fingerprint']]
            metrics = self.analyze_variance_for_query(query_df)
            consistency_data.append({
                'Query': f"{query['use_case'][:30]}... / {query['sector'][:20]}...",
                'Trials': query['trial_count'],
                'Trend Consistency': metrics['consistency'].get('trend_similarity_mean', 0) * 100,
                'Assessment Consistency': metrics['consistency'].get('assessment_similarity_mean', 0) * 100,
                'Market Consistency': metrics['consistency'].get('market_similarity_mean', 0) * 100,
                'Classification Entropy': metrics['assessment'].get('classification_entropy', 0)
            })
        
        if not consistency_data:
            st.info("Not enough data for consistency analysis (need queries with 2+ trials)")
            return
        
        consistency_df = pd.DataFrame(consistency_data)
        st.subheader("📊 Consistency Distribution")
        fig = go.Figure()
        fig.add_trace(go.Box(y=consistency_df['Trend Consistency'], name='Trends', boxpoints='all', jitter=0.3, pointpos=-1.8))
        fig.add_trace(go.Box(y=consistency_df['Assessment Consistency'], name='Assessment', boxpoints='all', jitter=0.3, pointpos=-1.8))
        fig.add_trace(go.Box(y=consistency_df['Market Consistency'], name='Market Solution', boxpoints='all', jitter=0.3, pointpos=-1.8))
        fig.update_layout(title="Consistency Distribution Across Output Types", yaxis_title="Consistency %", showlegend=True, height=500)
        st.plotly_chart(fig, use_container_width=True)
        
        st.subheader("🔗 Correlation Analysis")
        col1, col2 = st.columns(2)
        with col1:
            if len(consistency_df) > 3:
                correlation_data = consistency_df[['Trials','Trend Consistency','Assessment Consistency','Market Consistency']].corr()
                fig = go.Figure(data=go.Heatmap(
                    z=correlation_data.values, x=correlation_data.columns, y=correlation_data.columns,
                    colorscale='RdBu', zmid=0,
                    text=correlation_data.values.round(2), texttemplate="%{text}", textfont={"size": 10},
                    colorbar=dict(title="Correlation")
                ))
                fig.update_layout(title="Correlation Matrix", height=400)
                st.plotly_chart(fig, use_container_width=True)
        with col2:
            # Sanitize bubble sizes (non-negative, visible)
            size_series = pd.to_numeric(consistency_df['Classification Entropy'], errors='coerce').fillna(0.0)
            size_series = size_series.replace([np.inf, -np.inf], 0.0).clip(lower=0.0)
            if (size_series <= 0).all():
                size_series = pd.Series(np.full(len(size_series), 1.0), index=size_series.index)
            fig = px.scatter(
                consistency_df,
                x='Trials', y='Trend Consistency',
                size=size_series, color='Assessment Consistency',
                hover_data=['Query'],
                title='Relationship: Trials vs Consistency',
                labels={'Trials':'Number of Trials','Trend Consistency':'Trend Consistency %','Assessment Consistency':'Assessment Consistency %'}
            )
            fig.update_traces(marker=dict(sizemode='area', sizemin=6))
            st.plotly_chart(fig, use_container_width=True)
        
        st.subheader("🎯 Consistency Outliers")
        col1, col2, col3 = st.columns(3)
        with col1:
            st.markdown("**Highly Consistent** (>80%)")
            highly_consistent = consistency_df[(consistency_df['Trend Consistency'] > 80) & (consistency_df['Assessment Consistency'] > 80)]
            if not highly_consistent.empty:
                for _, row in highly_consistent.head(5).iterrows():
                    st.write(f"- {row['Query']}")
            else:
                st.write("No highly consistent queries found")
        with col2:
            st.markdown("**Highly Variable** (<40%)")
            highly_variable = consistency_df[(consistency_df['Trend Consistency'] < 40) | (consistency_df['Assessment Consistency'] < 40)]
            if not highly_variable.empty:
                for _, row in highly_variable.head(5).iterrows():
                    st.write(f"- {row['Query']}")
            else:
                st.write("No highly variable queries found")
        with col3:
            st.markdown("**Mixed Consistency**")
            mixed = consistency_df[abs(consistency_df['Trend Consistency'] - consistency_df['Assessment Consistency']) > 30]
            if not mixed.empty:
                for _, row in mixed.head(5).iterrows():
                    st.write(f"- {row['Query']}")
                    st.write(f"  Trend: {row['Trend Consistency']:.0f}%, Assessment: {row['Assessment Consistency']:.0f}%")
            else:
                st.write("No mixed consistency patterns found")
    
    def show_raw_data(self, trials_df, metrics_df):
        """(Kept) Raw lightweight table view (unchanged layout intent)"""
        st.header("Raw Data")
        st.subheader("Recent Trials")
        # Basic formatting, avoid errors if missing columns
        display = trials_df.copy()
        if 'latency_ms' in display.columns:
            pass
        st.dataframe(display.head(100), use_container_width=True)
        csv = display.to_csv(index=False)
        st.download_button(
            label="Download Trials Data as CSV",
            data=csv,
            file_name=f"llm_trials_{datetime.now().strftime('%Y%m%d')}.csv",
            mime="text/csv"
        )

    # =========================
    # NEW: Full history browser
    # =========================
    def show_full_history(self, df: pd.DataFrame):
        st.header("🗃️ Full Historical Records (Queries & Answers)")
        st.caption("Browse every stored query with its generated sections. Use filters below to narrow results.")
        
        # Filters
        colf1, colf2, colf3 = st.columns([1,1,2])
        with colf1:
            group_by_fp = st.checkbox("Group by query fingerprint", value=True, help="Group identical (use_case/sector/demand) queries together.")
            records_limit = st.number_input("Max records to render", min_value=50, max_value=5000, value=500, step=50)
        with colf2:
            date_min = df['created_at'].min().date() if df['created_at'].notna().any() else datetime.today().date()
            date_max = df['created_at'].max().date() if df['created_at'].notna().any() else datetime.today().date()
            date_range = st.date_input("Date range", value=(date_min, date_max), min_value=date_min, max_value=date_max)
        with colf3:
            keyword = st.text_input("Keyword search (use_case / sector / demand / session / content)", value="")
        
        long_text_cols = ['trend_solutions','trend_assessment','radar_positioning','pestel_tag','market_solution','partners']
        nice_names = {
            'trend_solutions':'Trend Solutions',
            'trend_assessment':'Trend Assessment',
            'radar_positioning':'Radar Positioning',
            'pestel_tag':'Relation Criteria / PESTEL',
            'market_solution':'Market Solution',
            'partners':'Partners'
        }
        selected_sections = st.multiselect(
            "Answer sections to display",
            options=long_text_cols,
            default=['trend_solutions','trend_assessment','market_solution']
        )
        
        # Apply filters
        fdf = df.copy()
        if fdf['created_at'].notna().any():
            mask = (fdf['created_at'].dt.date >= date_range[0]) & (fdf['created_at'].dt.date <= date_range[1])
            fdf = fdf[mask]
        if keyword:
            kw = keyword.lower()
            content_cols = ['use_case','sector','demand','selected_trend','session_id'] + long_text_cols
            present = [c for c in content_cols if c in fdf.columns]
            fdf = fdf[fdf[present].apply(lambda row: any(str(row[c]).lower().find(kw) >= 0 for c in present), axis=1)]
        
        # Limit
        if len(fdf) > records_limit:
            st.info(f"Showing first {records_limit} of {len(fdf)} matching records. Increase the limit to see more.")
            fdf = fdf.head(records_limit)
        
        # Global export of filtered data
        st.subheader("Export Filtered Data")
        csv_all = fdf.to_csv(index=False).encode("utf-8")
        json_all = fdf.to_json(orient="records", force_ascii=False).encode("utf-8")
        c1, c2 = st.columns(2)
        with c1:
            st.download_button("Download CSV (filtered)", data=csv_all, file_name=f"history_filtered_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv", mime="text/csv")
        with c2:
            st.download_button("Download JSON (filtered)", data=json_all, file_name=f"history_filtered_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json", mime="application/json")
        
        st.markdown("---")
        
        if group_by_fp:
            # Grouped view
            grouped = fdf.sort_values('created_at', ascending=False).groupby('query_fingerprint')
            for fp, g in grouped:
                g = g.sort_values('created_at')
                first = g.iloc[0]
                with st.expander(f"🔑 {first['use_case']} / {first['sector']} / {first['demand'][:60]}...  •  {len(g)} trial(s)  •  {g['created_at'].min().date()} → {g['created_at'].max().date()}"):
                    # Per-group exports
                    gcsv = g.to_csv(index=False).encode("utf-8")
                    gjson = g.to_json(orient="records", force_ascii=False).encode("utf-8")
                    cc1, cc2 = st.columns(2)
                    with cc1:
                        st.download_button("Download group CSV", data=gcsv, file_name=f"group_{fp}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv", mime="text/csv")
                    with cc2:
                        st.download_button("Download group JSON", data=gjson, file_name=f"group_{fp}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json", mime="application/json")
                    
                    # Render each trial
                    for idx, row in enumerate(g.itertuples(index=False), 1):
                        head = f"Trial {idx} • {getattr(row, 'created_at')}"
                        sub = f"Selected trend: {getattr(row, 'selected_trend') or '—'} | Confidence: {getattr(row, 'confidence_score') if hasattr(row,'confidence_score') else '—'} | Session: {getattr(row,'session_id') or '—'}"
                        st.markdown(f"**{head}**  \n{sub}")
                        # Short meta table
                        meta_cols = ['id','use_case','sector','demand','selected_trend','confidence_score','session_id','created_at']
                        meta_present = {c: getattr(row, c) for c in meta_cols if hasattr(row, c)}
                        st.write(meta_present)
                        # Long sections
                        for col in selected_sections:
                            if hasattr(row, col) and getattr(row, col):
                                st.markdown(f"**{nice_names.get(col,col)}**")
                                st.code(getattr(row, col), language=None)
                        st.markdown("---")
        else:
            # Flat list view
            st.subheader("Records")
            for idx, row in enumerate(fdf.sort_values('created_at').itertuples(index=False), 1):
                with st.expander(f"#{idx} • {getattr(row,'created_at')} • {getattr(row,'use_case')} / {getattr(row,'sector')} / {str(getattr(row,'demand'))[:50]}..."):
                    meta_cols = ['id','query_fingerprint','use_case','sector','demand','selected_trend','confidence_score','session_id','created_at']
                    meta_present = {c: getattr(row, c) for c in meta_cols if hasattr(row, c)}
                    st.write(meta_present)
                    for col in selected_sections:
                        if hasattr(row, col) and getattr(row, col):
                            st.markdown(f"**{nice_names.get(col,col)}**")
                            st.code(getattr(row, col), language=None)


def main():
    dashboard = VarianceAnalysisDashboard()
    dashboard.create_dashboard()


if __name__ == "__main__":
    main()
