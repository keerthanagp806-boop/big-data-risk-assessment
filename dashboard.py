"""NEWSGUARD - Big Data News Risk Intelligence Platform.
Interactive Streamlit Dashboard powered by Apache Hive 4.0.0 and Plotly.
"""

import sys
from pathlib import Path
from datetime import datetime
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

# Setup paths
PROJECT_ROOT = Path(__file__).resolve().parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from utils.config import (
    OUTPUTS_DIR,
    RAW_DATA_PATH,
    PROCESSED_DATA_PATH,
    HIVE_DATABASE,
    HIVE_CONTAINER,
    HIVE_HOST,
    HIVE_PORT,
    HIVE_HTTP_PORT,
    RISK_LOW_THRESHOLD,
    RISK_HIGH_THRESHOLD,
    RISK_NEGATIVE_WEIGHT,
    RISK_SEVERITY_WEIGHT
)
from utils.validators import validate_dataset_schema, clean_and_validate_records
from scripts.prepare_data import preprocess_news_dataset
from scripts.hive_runner import HiveRunner

# Page Configuration
st.set_page_config(
    page_title="NewsGuard | Big Data Risk Intelligence",
    page_icon="🛡️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom Styling (Dark Navy & Cyan theme)
CUSTOM_CSS = """
<style>
    /* Global Background and Typography */
    .stApp {
        background-color: #0b0f19;
        color: #f1f5f9;
        font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
    }
    
    /* Sidebar */
    [data-testid="stSidebar"] {
        background-color: #0f172a;
        border-right: 1px solid #1e293b;
    }
    
    /* Metric Cards */
    .metric-card {
        background-color: #1e293b;
        border: 1px solid #334155;
        border-radius: 10px;
        padding: 16px 20px;
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.3);
        margin-bottom: 12px;
    }
    .metric-title {
        color: #94a3b8;
        font-size: 0.85rem;
        text-transform: uppercase;
        font-weight: 600;
        letter-spacing: 0.05em;
    }
    .metric-value {
        color: #f8fafc;
        font-size: 1.8rem;
        font-weight: 700;
        margin-top: 4px;
    }
    
    /* Risk Badges */
    .badge-high {
        background-color: rgba(239, 68, 68, 0.2);
        color: #ef4444;
        border: 1px solid #ef4444;
        padding: 4px 10px;
        border-radius: 6px;
        font-weight: 700;
        display: inline-block;
    }
    .badge-medium {
        background-color: rgba(245, 158, 11, 0.2);
        color: #f59e0b;
        border: 1px solid #f59e0b;
        padding: 4px 10px;
        border-radius: 6px;
        font-weight: 700;
        display: inline-block;
    }
    .badge-low {
        background-color: rgba(16, 185, 129, 0.2);
        color: #10b981;
        border: 1px solid #10b981;
        padding: 4px 10px;
        border-radius: 6px;
        font-weight: 700;
        display: inline-block;
    }

    /* Article Detail Box */
    .article-box {
        background-color: #161f30;
        border: 1px solid #2d3b55;
        border-radius: 12px;
        padding: 24px;
        margin-top: 16px;
    }
    
    /* Info banners */
    .engine-tag {
        background: linear-gradient(90deg, #0284c7 0%, #2563eb 100%);
        color: white;
        padding: 4px 12px;
        border-radius: 20px;
        font-size: 0.75rem;
        font-weight: 600;
        display: inline-block;
        margin-bottom: 12px;
    }
</style>
"""
st.markdown(CUSTOM_CSS, unsafe_allow_html=True)

# Plotly theme styling helper
def apply_plotly_theme(fig):
    fig.update_layout(
        template="plotly_dark",
        paper_bgcolor="rgba(15, 23, 42, 0.6)",
        plot_bgcolor="rgba(15, 23, 42, 0)",
        font=dict(color="#94a3b8", family="Inter, sans-serif"),
        margin=dict(l=20, r=20, t=40, b=20),
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="right",
            x=1
        )
    )
    return fig

# Helper to load exported Hive results
@st.cache_data(ttl=5)
def load_hive_data():
    records_file = OUTPUTS_DIR / "news_records.csv"
    risk_file = OUTPUTS_DIR / "risk_summary.csv"
    category_file = OUTPUTS_DIR / "category_summary.csv"
    source_file = OUTPUTS_DIR / "source_summary.csv"
    sentiment_file = OUTPUTS_DIR / "sentiment_summary.csv"
    trend_file = OUTPUTS_DIR / "trend_summary.csv"

    if not records_file.exists():
        return None

    try:
        data = {
            "records": pd.read_csv(records_file),
            "risk_summary": pd.read_csv(risk_file) if risk_file.exists() else pd.DataFrame(),
            "category_summary": pd.read_csv(category_file) if category_file.exists() else pd.DataFrame(),
            "source_summary": pd.read_csv(source_file) if source_file.exists() else pd.DataFrame(),
            "sentiment_summary": pd.read_csv(sentiment_file) if sentiment_file.exists() else pd.DataFrame(),
            "trend_summary": pd.read_csv(trend_file) if trend_file.exists() else pd.DataFrame(),
        }
        return data
    except Exception as e:
        st.error(f"Error loading Hive output files: {e}")
        return None

# Sidebar Navigation & Branding
st.sidebar.markdown(
    """
    <div style="text-align: center; padding-bottom: 15px; border-bottom: 1px solid #334155;">
        <h2 style="color: #38bdf8; margin: 0; font-size: 1.6rem; font-weight: 800;">🛡️ NEWSGUARD</h2>
        <p style="color: #94a3b8; font-size: 0.8rem; margin-top: 4px;">Big Data Risk Intelligence Platform</p>
        <span class="engine-tag">Powered by Apache Hive 4.0.0</span>
    </div>
    """,
    unsafe_allow_html=True
)

pages = [
    "Overview Dashboard",
    "News Explorer",
    "Risk Analytics",
    "Sentiment Analysis",
    "Data Management",
    "System Information"
]
selected_page = st.sidebar.radio("Navigation Menu", pages, index=0)

st.sidebar.markdown("---")
st.sidebar.markdown(
    f"""
    **Platform Engine:**  
    • Database: `{HIVE_DATABASE}`  
    • Table: `assessed_news` (ORC)  
    • Metastore: Embedded Derby  
    • Server: HiveServer2 / Beeline  
    """
)

# Load data
hive_data = load_hive_data()

# ==============================================================================
# PAGE 1: OVERVIEW DASHBOARD
# ==============================================================================
if selected_page == "Overview Dashboard":
    st.title("Executive Risk Overview")
    st.markdown("Real-time aggregated indicators computed directly from Apache Hive analytical tables.")

    if not hive_data:
        st.warning(
            "⚠️ No Hive analytical results detected in `outputs/`.\n\n"
            "Please go to **Page 5 (Data Management)** or run `python run_pipeline.py` to trigger the Hive pipeline."
        )
    else:
        df = hive_data["records"]
        total_articles = len(df)
        high_risk_count = len(df[df["risk_level"] == "HIGH"])
        med_risk_count = len(df[df["risk_level"] == "MEDIUM"])
        low_risk_count = len(df[df["risk_level"] == "LOW"])
        avg_risk = round(df["risk_score"].mean(), 2) if total_articles > 0 else 0.0
        total_sources = df["source"].nunique()
        total_categories = df["category"].nunique()

        # Top Metric Cards
        m1, m2, m3, m4, m5, m6, m7 = st.columns(7)
        m1.markdown(f"<div class='metric-card'><div class='metric-title'>Total Articles</div><div class='metric-value'>{total_articles}</div></div>", unsafe_allow_html=True)
        m2.markdown(f"<div class='metric-card'><div class='metric-title' style='color:#ef4444;'>High Risk</div><div class='metric-value' style='color:#ef4444;'>{high_risk_count}</div></div>", unsafe_allow_html=True)
        m3.markdown(f"<div class='metric-card'><div class='metric-title' style='color:#f59e0b;'>Medium Risk</div><div class='metric-value' style='color:#f59e0b;'>{med_risk_count}</div></div>", unsafe_allow_html=True)
        m4.markdown(f"<div class='metric-card'><div class='metric-title' style='color:#10b981;'>Low Risk</div><div class='metric-value' style='color:#10b981;'>{low_risk_count}</div></div>", unsafe_allow_html=True)
        m5.markdown(f"<div class='metric-card'><div class='metric-title'>Avg Risk</div><div class='metric-value'>{avg_risk}</div></div>", unsafe_allow_html=True)
        m6.markdown(f"<div class='metric-card'><div class='metric-title'>Sources</div><div class='metric-value'>{total_sources}</div></div>", unsafe_allow_html=True)
        m7.markdown(f"<div class='metric-card'><div class='metric-title'>Categories</div><div class='metric-value'>{total_categories}</div></div>", unsafe_allow_html=True)

        st.markdown("---")

        # Row 1 Charts: Risk Donut & Category Distribution
        c1, c2 = st.columns(2)

        with c1:
            st.subheader("1. Risk Distribution")
            risk_counts = df["risk_level"].value_counts().reset_index()
            risk_counts.columns = ["risk_level", "count"]
            color_map = {"HIGH": "#ef4444", "MEDIUM": "#f59e0b", "LOW": "#10b981"}
            fig_donut = px.pie(
                risk_counts,
                names="risk_level",
                values="count",
                hole=0.55,
                color="risk_level",
                color_discrete_map=color_map,
                title="Proportion of Articles by Risk Level"
            )
            st.plotly_chart(apply_plotly_theme(fig_donut), use_container_width=True)

        with c2:
            st.subheader("2. News Category Distribution")
            cat_counts = df["category"].value_counts().reset_index()
            cat_counts.columns = ["category", "count"]
            fig_cat = px.bar(
                cat_counts,
                x="category",
                y="count",
                color="category",
                title="Total Articles Ingested per Category",
                color_discrete_sequence=px.colors.qualitative.Prism
            )
            st.plotly_chart(apply_plotly_theme(fig_cat), use_container_width=True)

        # Row 2 Charts: Average Risk by Category & Daily Publication Trend
        c3, c4 = st.columns(2)

        with c3:
            st.subheader("3. Average Risk by Category")
            avg_risk_cat = df.groupby("category")["risk_score"].mean().reset_index().sort_values(by="risk_score", ascending=False)
            fig_avg_cat = px.bar(
                avg_risk_cat,
                x="category",
                y="risk_score",
                color="risk_score",
                color_continuous_scale="Reds",
                title="Mean Explainable Risk Score (0-100)"
            )
            st.plotly_chart(apply_plotly_theme(fig_avg_cat), use_container_width=True)

        with c4:
            st.subheader("4. Daily Publication Trend")
            df["pub_day"] = pd.to_datetime(df["published_at"]).dt.strftime("%Y-%m-%d")
            trend_df = df.groupby("pub_day").size().reset_index(name="article_count").sort_values("pub_day")
            fig_trend = px.line(
                trend_df,
                x="pub_day",
                y="article_count",
                markers=True,
                title="Daily Volume of Ingested Articles",
                line_shape="spline"
            )
            fig_trend.update_traces(line_color="#38bdf8")
            st.plotly_chart(apply_plotly_theme(fig_trend), use_container_width=True)

        # Row 3 Charts: Sentiment Distribution & Top Sources
        c5, c6 = st.columns(2)

        with c5:
            st.subheader("5. Sentiment Distribution")
            sent_counts = df["sentiment_label"].value_counts().reset_index()
            sent_counts.columns = ["sentiment_label", "count"]
            fig_sent = px.pie(
                sent_counts,
                names="sentiment_label",
                values="count",
                color="sentiment_label",
                color_discrete_map={"Positive": "#10b981", "Neutral": "#64748b", "Negative": "#ef4444"},
                title="Sentiment Class Breakdown"
            )
            st.plotly_chart(apply_plotly_theme(fig_sent), use_container_width=True)

        with c6:
            st.subheader("6. Top News Sources by Article Volume")
            src_counts = df["source"].value_counts().reset_index().head(8)
            src_counts.columns = ["source", "count"]
            fig_src = px.bar(
                src_counts,
                x="count",
                y="source",
                orientation="h",
                color="count",
                color_continuous_scale="Blues",
                title="Publication Count by Source"
            )
            fig_src.update_layout(yaxis=dict(autorange="reversed"))
            st.plotly_chart(apply_plotly_theme(fig_src), use_container_width=True)

        # Analytical Summary generated from actual Hive outputs
        st.markdown("### 📋 Executive Analytical Summary")
        top_high_cat = avg_risk_cat.iloc[0]["category"] if len(avg_risk_cat) > 0 else "N/A"
        top_high_score = avg_risk_cat.iloc[0]["risk_score"] if len(avg_risk_cat) > 0 else 0
        st.info(
            f"**Hive Analytics Findings:** Out of {total_articles} assessed articles in table `assessed_news`, "
            f"**{high_risk_count}** ({round(high_risk_count/total_articles*100, 1)}%) triggered high-risk indicators (score >= {RISK_HIGH_THRESHOLD}), "
            f"while **{low_risk_count}** ({round(low_risk_count/total_articles*100, 1)}%) remain low-risk. "
            f"The category with the highest average risk intensity is **{top_high_cat}** with an average risk score of **{top_high_score:.1f}**."
        )

# ==============================================================================
# PAGE 2: NEWS EXPLORER
# ==============================================================================
elif selected_page == "News Explorer":
    st.title("News Article Explorer & Explainability")
    st.markdown("Inspect individual articles, filter across attributes, and trace risk calculation signals.")

    if not hive_data:
        st.warning("No Hive results found. Please execute the pipeline in Data Management.")
    else:
        df = hive_data["records"]

        # Filters
        st.subheader("Filters")
        f1, f2, f3, f4 = st.columns(4)

        categories = ["All"] + sorted(df["category"].dropna().unique().tolist())
        selected_cat = f1.selectbox("Category", categories)

        risk_levels = ["All", "HIGH", "MEDIUM", "LOW"]
        selected_risk = f2.selectbox("Risk Level", risk_levels)

        sentiments = ["All"] + sorted(df["sentiment_label"].dropna().unique().tolist())
        selected_sent = f3.selectbox("Sentiment", sentiments)

        sources = ["All"] + sorted(df["source"].dropna().unique().tolist())
        selected_src = f4.selectbox("Source", sources)

        # Search bar
        search_query = st.text_input("🔍 Search by article title or keywords in content:", "")

        # Filter dataframe
        filtered_df = df.copy()
        if selected_cat != "All":
            filtered_df = filtered_df[filtered_df["category"] == selected_cat]
        if selected_risk != "All":
            filtered_df = filtered_df[filtered_df["risk_level"] == selected_risk]
        if selected_sent != "All":
            filtered_df = filtered_df[filtered_df["sentiment_label"] == selected_sent]
        if selected_src != "All":
            filtered_df = filtered_df[filtered_df["source"] == selected_src]
        if search_query.strip():
            q = search_query.strip().lower()
            filtered_df = filtered_df[
                filtered_df["title"].str.lower().str.contains(q, na=False) |
                filtered_df["content"].str.lower().str.contains(q, na=False)
            ]

        st.markdown(f"**Showing {len(filtered_df)} of {len(df)} articles**")

        # Table Display
        display_cols = ["article_id", "title", "source", "category", "published_at", "sentiment_label", "risk_score", "risk_level"]
        st.dataframe(
            filtered_df[display_cols],
            use_container_width=True,
            hide_index=True
        )

        st.markdown("---")
        st.subheader("🔍 Detailed Article Signal Inspection")

        if len(filtered_df) == 0:
            st.info("No articles match the current filter selection.")
        else:
            article_titles = filtered_df["title"].tolist()
            selected_title = st.selectbox("Select an article to examine risk signals:", article_titles)
            selected_row = filtered_df[filtered_df["title"] == selected_title].iloc[0]

            risk_lvl = selected_row["risk_level"]
            badge_class = "badge-high" if risk_lvl == "HIGH" else ("badge-medium" if risk_lvl == "MEDIUM" else "badge-low")

            st.markdown(
                f"""
                <div class="article-box">
                    <div style="display: flex; justify-content: space-between; align-items: center;">
                        <span class="{badge_class}">{risk_lvl} RISK ({selected_row['risk_score']:.1f}/100)</span>
                        <span style="color: #94a3b8; font-size: 0.85rem;">ID: {selected_row['article_id']} | {selected_row['source']} | {selected_row['published_at']}</span>
                    </div>
                    <h3 style="color: #f8fafc; margin-top: 12px;">{selected_row['title']}</h3>
                    <p style="color: #cbd5e1; font-size: 1.05rem; line-height: 1.6;">{selected_row['content']}</p>
                    <div style="margin-top: 10px;">
                        <a href="{selected_row['url']}" target="_blank" style="color: #38bdf8; text-decoration: none;">🔗 Source Article Link</a>
                    </div>
                </div>
                """,
                unsafe_allow_html=True
            )

            # Signal Breakdown
            st.markdown("#### Explainable Risk Signal Breakdown")
            s1, s2, s3, s4 = st.columns(4)

            s1.metric(
                label="VADER Compound Sentiment",
                value=f"{selected_row['sentiment_compound']:.4f}",
                delta=f"Label: {selected_row['sentiment_label']}"
            )
            s2.metric(
                label="Signal 1: Negative Intensity",
                value=f"{selected_row['negative_intensity']:.1f}%",
                help="Formula: ABS(compound) * 100 for negative sentiment; 0 otherwise."
            )
            s3.metric(
                label="Signal 2: Severity Score",
                value=f"{selected_row['severity_score']:.1f}/100",
                help="Detected crisis, conflict, disaster, or cyber emergency terms."
            )
            s4.metric(
                label="Computed Risk Score",
                value=f"{selected_row['risk_score']:.1f}",
                delta=f"Weight: 60% Neg + 40% Sev"
            )

            st.markdown(
                f"""
                **Detected Severity Keywords:** `{selected_row.get('severity_keywords', 'None')}`  
                *Formula Applied:* `risk_score = MIN(100, MAX(0, ({RISK_NEGATIVE_WEIGHT} * {selected_row['negative_intensity']:.1f}) + ({RISK_SEVERITY_WEIGHT} * {selected_row['severity_score']:.1f})))` = **{selected_row['risk_score']:.1f}**
                """
            )

# ==============================================================================
# PAGE 3: RISK ANALYTICS
# ==============================================================================
elif selected_page == "Risk Analytics":
    st.title("In-Depth Risk Analytics")
    st.markdown("Comparative analysis of risk concentration across news categories, sources, and time.")

    if not hive_data:
        st.warning("No Hive data found. Please run the pipeline.")
    else:
        df = hive_data["records"]

        # Top 10 High-Risk Articles (Horizontal Bar Chart)
        st.subheader("1. Top High-Risk Articles")
        top_high = df.sort_values(by="risk_score", ascending=False).head(10)
        fig_top = px.bar(
            top_high,
            x="risk_score",
            y="title",
            orientation="h",
            color="risk_score",
            color_continuous_scale="Reds",
            hover_data=["source", "category", "sentiment_label", "severity_score"],
            title="Top 10 Highest Risk Articles Identified by HiveQL"
        )
        fig_top.update_layout(yaxis=dict(autorange="reversed"))
        st.plotly_chart(apply_plotly_theme(fig_top), use_container_width=True)

        r1, r2 = st.columns(2)

        with r1:
            st.subheader("2. Category vs. Risk Level Heatmap")
            cross_tab = pd.crosstab(df["category"], df["risk_level"], margins=False)
            for lvl in ["LOW", "MEDIUM", "HIGH"]:
                if lvl not in cross_tab.columns:
                    cross_tab[lvl] = 0
            cross_tab = cross_tab[["LOW", "MEDIUM", "HIGH"]]
            fig_heatmap = px.imshow(
                cross_tab,
                text_auto=True,
                color_continuous_scale="YlOrRd",
                title="Risk Level Count across Categories"
            )
            st.plotly_chart(apply_plotly_theme(fig_heatmap), use_container_width=True)

        with r2:
            st.subheader("3. Source-Wise Risk Profile")
            src_risk = df.groupby("source").agg(
                avg_risk=("risk_score", "mean"),
                high_count=("risk_level", lambda x: (x == "HIGH").sum()),
                total=("article_id", "count")
            ).reset_index().sort_values("avg_risk", ascending=False)
            fig_src_risk = px.bar(
                src_risk,
                x="source",
                y="avg_risk",
                color="high_count",
                color_continuous_scale="Oranges",
                title="Average Risk by Source (Colored by High Risk Count)"
            )
            st.plotly_chart(apply_plotly_theme(fig_src_risk), use_container_width=True)

        # Time series risk trends
        st.subheader("4. Risk Dynamics Over Time")
        df["date_str"] = pd.to_datetime(df["published_at"]).dt.strftime("%Y-%m-%d")
        daily_risk = df.groupby("date_str").agg(
            avg_risk=("risk_score", "mean"),
            high_risk_articles=("risk_level", lambda x: (x == "HIGH").sum())
        ).reset_index().sort_values("date_str")

        fig_time = go.Figure()
        fig_time.add_trace(go.Scatter(
            x=daily_risk["date_str"],
            y=daily_risk["avg_risk"],
            mode="lines+markers",
            name="Average Risk Score",
            line=dict(color="#f59e0b", width=3)
        ))
        fig_time.add_trace(go.Bar(
            x=daily_risk["date_str"],
            y=daily_risk["high_risk_articles"],
            name="High-Risk Volume",
            marker_color="#ef4444",
            opacity=0.6,
            yaxis="y2"
        ))
        fig_time.update_layout(
            title="Timeline of Daily Average Risk and High-Risk Article Counts",
            yaxis=dict(title="Average Risk Score (0-100)"),
            yaxis2=dict(title="High-Risk Articles", overlaying="y", side="right")
        )
        st.plotly_chart(apply_plotly_theme(fig_time), use_container_width=True)

# ==============================================================================
# PAGE 4: SENTIMENT ANALYSIS
# ==============================================================================
elif selected_page == "Sentiment Analysis":
    st.title("VADER Sentiment Analysis Engine")
    st.markdown("In-depth emotional polarity and intensity evaluation across ingested news content.")

    if not hive_data:
        st.warning("No Hive results found. Please execute the pipeline in Data Management.")
    else:
        df = hive_data["records"]

        pos_cnt = len(df[df["sentiment_label"] == "Positive"])
        neu_cnt = len(df[df["sentiment_label"] == "Neutral"])
        neg_cnt = len(df[df["sentiment_label"] == "Negative"])
        avg_cmp = round(df["sentiment_compound"].mean(), 4)

        s1, s2, s3, s4 = st.columns(4)
        s1.markdown(f"<div class='metric-card'><div class='metric-title' style='color:#10b981;'>Positive Articles</div><div class='metric-value' style='color:#10b981;'>{pos_cnt}</div></div>", unsafe_allow_html=True)
        s2.markdown(f"<div class='metric-card'><div class='metric-title' style='color:#64748b;'>Neutral Articles</div><div class='metric-value' style='color:#64748b;'>{neu_cnt}</div></div>", unsafe_allow_html=True)
        s3.markdown(f"<div class='metric-card'><div class='metric-title' style='color:#ef4444;'>Negative Articles</div><div class='metric-value' style='color:#ef4444;'>{neg_cnt}</div></div>", unsafe_allow_html=True)
        s4.markdown(f"<div class='metric-card'><div class='metric-title'>Average Compound</div><div class='metric-value'>{avg_cmp}</div></div>", unsafe_allow_html=True)

        st.markdown("---")

        p1, p2 = st.columns(2)

        with p1:
            st.subheader("1. Compound Polarity Distribution")
            fig_hist = px.histogram(
                df,
                x="sentiment_compound",
                nbins=20,
                color="sentiment_label",
                color_discrete_map={"Positive": "#10b981", "Neutral": "#64748b", "Negative": "#ef4444"},
                title="Distribution of VADER Compound Scores (-1 to +1)"
            )
            st.plotly_chart(apply_plotly_theme(fig_hist), use_container_width=True)

        with p2:
            st.subheader("2. Sentiment Composition by Category")
            cat_sent = pd.crosstab(df["category"], df["sentiment_label"], normalize="index") * 100
            for col in ["Positive", "Neutral", "Negative"]:
                if col not in cat_sent.columns:
                    cat_sent[col] = 0.0
            cat_sent = cat_sent[["Positive", "Neutral", "Negative"]].reset_index()
            fig_cat_sent = px.bar(
                cat_sent,
                x="category",
                y=["Positive", "Neutral", "Negative"],
                color_discrete_map={"Positive": "#10b981", "Neutral": "#64748b", "Negative": "#ef4444"},
                title="Category Sentiment Breakdown (%)"
            )
            st.plotly_chart(apply_plotly_theme(fig_cat_sent), use_container_width=True)

        st.markdown("### ℹ️ VADER Sentiment Classification Guide")
        st.markdown(
            """
            > [!NOTE]
            > **Valence Aware Dictionary and sEntiment Reasoner (VADER):**
            > - **Compound Score:** A normalized, weighted composite index ranging from **-1.0** (extreme negative) to **+1.0** (extreme positive).
            > - **Positive:** Compound score >= `+0.05`
            > - **Neutral:** Compound score between `-0.05` and `+0.05`
            > - **Negative:** Compound score <= `-0.05`
            >
            > **Academic Disclaimer:** Negative sentiment alone does **not** indicate misinformation, hostility, or false reporting. 
            > Legitimate journalism covering natural disasters, medical crises, and conflicts naturally employs serious, negative vocabulary.
            """
        )

# ==============================================================================
# PAGE 5: DATA MANAGEMENT
# ==============================================================================
elif selected_page == "Data Management":
    st.title("Data Management & Pipeline Execution")
    st.markdown("Ingest new CSV datasets, validate schema, trigger preprocessing, and execute Hive analytics.")

    tab1, tab2 = st.tabs(["Upload New Dataset", "Execute Hive Pipeline"])

    with tab1:
        st.subheader("Upload News Articles (CSV)")
        st.markdown("File must include: `article_id`, `title`, `content`, `source`, `published_at`, `url`")

        uploaded_file = st.file_uploader("Choose CSV file", type=["csv"])
        if uploaded_file is not None:
            try:
                upload_df = pd.read_csv(uploaded_file)
                is_valid, errors = validate_dataset_schema(upload_df)

                if is_valid:
                    cleaned_df, stats = clean_and_validate_records(upload_df)
                    st.success(f"✅ Schema validation passed! Successfully validated {stats['final_count']} records.")
                    st.json(stats)

                    st.markdown("#### Preview Ingested Records")
                    st.dataframe(cleaned_df.head(5), use_container_width=True)

                    if st.button("Save as Current Dataset (Overwrite data/raw/news.csv)"):
                        cleaned_df.to_csv(RAW_DATA_PATH, index=False, encoding="utf-8")
                        st.success(f"Saved to {RAW_DATA_PATH}. You can now execute the pipeline.")
                else:
                    st.error(f"❌ Validation errors detected:\n" + "\n".join(f"- {e}" for e in errors))
            except Exception as e:
                st.error(f"Error parsing CSV file: {e}")

    with tab2:
        st.subheader("Automated Apache Hive Pipeline Runner")
        st.markdown(
            "This will execute the 16-step automated pipeline: cleaning, NLP text processing, "
            "Hive table creation (`news_raw`), ORC CTAS risk computation (`assessed_news`), "
            "and analytical summary export."
        )

        runner = HiveRunner()
        docker_ok, docker_msg = runner.check_docker_available()

        if not docker_ok:
            st.error(f"Docker is currently not available: {docker_msg}")
            st.info(
                "Please make sure Docker Desktop is running before launching Hive analytics.\n"
                "Command: `docker run -d --name hive4 -p 10000:10000 -p 10002:10002 -v hive_warehouse:/opt/hive/data/warehouse --env SERVICE_NAME=hiveserver2 apache/hive:4.0.0`"
            )
        else:
            st.success(f"Docker is available ({docker_msg})")

        if st.button("🚀 Trigger Full Apache Hive Pipeline", type="primary"):
            with st.spinner("Executing pipeline... This will run data preprocessing and HiveQL queries..."):
                try:
                    # Preprocess
                    prep_df = preprocess_news_dataset(RAW_DATA_PATH, PROCESSED_DATA_PATH)
                    st.info(f"Preprocessing completed: {len(prep_df)} records transformed into TSV.")

                    # Run Hive
                    ok, msg = runner.run_full_hive_pipeline()
                    if ok:
                        st.success(f"Pipeline executed successfully! {msg}")
                        st.cache_data.clear()
                    else:
                        st.error(f"Hive execution error: {msg}")
                except Exception as ex:
                    st.error(f"Pipeline execution encountered exception: {ex}")

# ==============================================================================
# PAGE 6: SYSTEM INFORMATION
# ==============================================================================
elif selected_page == "System Information":
    st.title("System Status & Environment Information")
    st.markdown("Live verification of big data infrastructure, Hive metastore, Docker containers, and dataset health.")

    runner = HiveRunner()
    
    # Real checks
    with st.spinner("Checking live Docker daemon and Hive container status..."):
        docker_ok, docker_msg = runner.check_docker_available()
        container_ok, container_msg = runner.check_container_status()
        port_open = runner.check_hiveserver2_port(timeout_sec=2)

    st.subheader("Infrastructure Health Checks")
    col_s1, col_s2, col_s3 = st.columns(3)

    col_s1.markdown(
        f"""
        <div class="metric-card">
            <div class="metric-title">Docker Daemon</div>
            <div class="metric-value" style="color: {'#10b981' if docker_ok else '#ef4444'};">
                {'Active' if docker_ok else 'Unavailable'}
            </div>
            <small style="color: #94a3b8;">{docker_msg}</small>
        </div>
        """,
        unsafe_allow_html=True
    )

    col_s2.markdown(
        f"""
        <div class="metric-card">
            <div class="metric-title">Hive Container ('{HIVE_CONTAINER}')</div>
            <div class="metric-value" style="color: {'#10b981' if container_ok else '#f59e0b'};">
                {'Running' if container_ok else 'Stopped/Missing'}
            </div>
            <small style="color: #94a3b8;">{container_msg}</small>
        </div>
        """,
        unsafe_allow_html=True
    )

    col_s3.markdown(
        f"""
        <div class="metric-card">
            <div class="metric-title">HiveServer2 (Port {HIVE_PORT})</div>
            <div class="metric-value" style="color: {'#10b981' if port_open else '#ef4444'};">
                {'Listening' if port_open else 'Closed'}
            </div>
            <small style="color: #94a3b8;">Host: {HIVE_HOST}:{HIVE_PORT}</small>
        </div>
        """,
        unsafe_allow_html=True
    )

    st.markdown("---")
    st.subheader("Database & Table Configuration")

    raw_count = 0
    if RAW_DATA_PATH.exists():
        try:
            raw_count = len(pd.read_csv(RAW_DATA_PATH))
        except Exception:
            pass

    records_count = 0
    last_exec = "Never"
    records_file = OUTPUTS_DIR / "news_records.csv"
    if records_file.exists():
        try:
            records_count = len(pd.read_csv(records_file))
            mod_time = datetime.fromtimestamp(records_file.stat().st_mtime)
            last_exec = mod_time.strftime("%Y-%m-%d %H:%M:%S")
        except Exception:
            pass

    info_df = pd.DataFrame([
        {"Parameter": "Hive Database", "Value": HIVE_DATABASE},
        {"Parameter": "Ingestion Table", "Value": "news_raw (Delimited TSV, TextFile)"},
        {"Parameter": "Analytical Table", "Value": "assessed_news (ORC Format)"},
        {"Parameter": "Metastore", "Value": "Embedded Apache Derby"},
        {"Parameter": "Raw Dataset Path", "Value": str(RAW_DATA_PATH)},
        {"Parameter": "Raw Dataset Count", "Value": f"{raw_count} articles"},
        {"Parameter": "Processed TSV Path", "Value": str(PROCESSED_DATA_PATH)},
        {"Parameter": "Assessed Hive Records", "Value": f"{records_count} articles"},
        {"Parameter": "Last Successful Pipeline Run", "Value": last_exec},
        {"Parameter": "Risk Formula", "Value": f"MIN(100, MAX(0, ({RISK_NEGATIVE_WEIGHT} * Neg) + ({RISK_SEVERITY_WEIGHT} * Sev)))"},
        {"Parameter": "Risk Thresholds", "Value": f"Low: < {RISK_LOW_THRESHOLD} | Medium: {RISK_LOW_THRESHOLD}-{RISK_HIGH_THRESHOLD} | High: >= {RISK_HIGH_THRESHOLD}"}
    ])
    st.table(info_df)

    st.markdown("### 🛠️ Local Environment & Docker Setup Instructions")
    st.code(
        """
# 1. Pull Apache Hive 4.0.0 Docker Image:
docker pull apache/hive:4.0.0

# 2. Create Persistent Volume for Hive Warehouse:
docker volume create hive_warehouse

# 3. Start Apache HiveServer2 Container:
docker run -d --name hive4 -p 10000:10000 -p 10002:10002 -v hive_warehouse:/opt/hive/data/warehouse --env SERVICE_NAME=hiveserver2 apache/hive:4.0.0

# 4. Run the Pipeline:
python run_pipeline.py

# 5. Launch the Dashboard:
streamlit run dashboard.py
        """,
        language="powershell"
    )
