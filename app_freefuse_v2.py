# --------------------------- IMPORTS ---------------------------
import pandas as pd
import numpy as np
import plotly.express as px
import streamlit as st

# --------------------------- PAGE CONFIG ---------------------------
st.set_page_config(page_title="FreeFuse Interactive Dashboard", page_icon="🎥", layout="wide")

st.markdown("""
<style>
  h1, h2, h3 { color:#2b1b6b; }
  [data-testid="stSidebar"] { background:#f4f2ff; }
  .metric-card { background:#f7f5ff; padding:12px; border-radius:12px; text-align:center; }
  .stPlotlyChart { padding-bottom: 25px; }
</style>
""", unsafe_allow_html=True)

st.title("🎥 FreeFuse Interactive Engagement Dashboard")

# --------------------------- FILES ---------------------------
WATCH_HISTORY_FILE = "Main Nodes Watch History 2022-2024 School Year.xlsx"
VIDEO_COUNTS_FILE = "Video Counts 2022-2024.xlsx"

# --------------------------- HELPERS ---------------------------
def normalize_cols(df):
    df.columns = df.columns.str.strip().str.lower().str.replace(r"[\s_]+", " ", regex=True)
    return df

def to_minutes(series):
    s = pd.to_numeric(series, errors="coerce")
    if s.dropna().median() > 200:
        s = s / 60.0
    return s

def classify_ampm(t):
    t = str(t).strip()
    if "am" in t.lower(): return "AM"
    if "pm" in t.lower(): return "PM"
    try:
        hour = int(t.split(":")[0])
        return "AM" if hour < 12 else "PM"
    except:
        return "Unknown"

# --------------------------- LOAD DATA ---------------------------
try:
    watch = pd.read_excel(WATCH_HISTORY_FILE)
    counts = pd.read_excel(VIDEO_COUNTS_FILE)
    watch = normalize_cols(watch)
    counts = normalize_cols(counts)
except Exception as e:
    st.error(f"❌ Error loading files: {e}")
    st.stop()

# --------------------------- RENAME COLUMNS ---------------------------
watch.rename(columns={
    "video id": "video_id",
    "node title": "video_title",
    "duration (mins)": "duration_min",
    "created date": "created_date",
    "watched time": "watched_time",
    "userinfo. id": "user_id"
}, inplace=True)

counts.rename(columns={
    "video id": "video_id",
    "title of node": "video_title",
    "view count": "view_count",
    "year": "acad_year"
}, inplace=True)

# --------------------------- CLEAN DATA ---------------------------
watch["created_date"] = pd.to_datetime(watch.get("created_date"), errors="coerce")
watch["duration_min"] = to_minutes(watch.get("duration_min"))
watch["am_pm"] = watch.get("watched_time", "").apply(classify_ampm)
watch["year"] = watch["created_date"].dt.year
watch["month"] = watch["created_date"].dt.to_period("M").dt.to_timestamp()

# --------------------------- SIDEBAR FILTERS ---------------------------
st.sidebar.header("📊 Filters")

# Year
years = sorted(watch["year"].dropna().unique())
selected_year = st.sidebar.selectbox("Select Year", years, index=len(years)-1 if years else 0)

# Video Title dropdown (with Select All)
titles = sorted(watch["video_title"].dropna().unique()) if "video_title" in watch.columns else []
with st.sidebar.expander("🎞️ Select Video Title(s)", expanded=False):
    select_all = st.checkbox("Select All Videos", value=True)
    if select_all:
        selected_titles = titles
    else:
        selected_titles = st.multiselect(
            "Choose from list:",
            options=titles,
            default=[],
            placeholder="Select one or multiple videos..."
        )

# Time of Day
ampm_choice = st.sidebar.selectbox("Time of Day", ["Both", "AM", "PM"], index=0)

# --------------------------- FILTER DATA ---------------------------
fwh = watch.copy()
if "year" in fwh.columns:
    fwh = fwh[fwh["year"] == selected_year]
if selected_titles:
    fwh = fwh[fwh["video_title"].isin(selected_titles)]
if ampm_choice != "Both" and "am_pm" in fwh.columns:
    fwh = fwh[fwh["am_pm"] == ampm_choice]

# --------------------------- KPI CARDS ---------------------------
st.subheader("📌 Key Metrics")
c1, c2, c3, c4, c5 = st.columns(5)

total_views = len(fwh)
unique_videos = fwh["video_id"].nunique() if "video_id" in fwh.columns else 0
total_dur = fwh["duration_min"].sum() if "duration_min" in fwh.columns else 0
avg_dur = fwh["duration_min"].mean() if "duration_min" in fwh.columns else 0

most_engaged = "—"
if "video_title" in fwh.columns and not fwh.empty:
    most_engaged = fwh.groupby("video_title")["duration_min"].sum().idxmax()

for c, (label, value) in zip(
    [c1, c2, c3, c4, c5],
    [
        ("Total Views", total_views),
        ("Unique Videos", unique_videos),
        ("Total Watch (min)", f"{total_dur:,.1f}"),
        ("Avg Watch (min)", f"{avg_dur:.2f}" if not np.isnan(avg_dur) else "0"),
        ("Most Engaged Video", most_engaged),
    ],
):
    c.markdown(f"<div class='metric-card'><h4>{label}</h4><h2>{value}</h2></div>", unsafe_allow_html=True)

st.markdown("---")

# --------------------------- VISUALIZATIONS ---------------------------
st.markdown("## 📊 Engagement Insights")

if not fwh.empty and "created_date" in fwh.columns:

    # 1️⃣ Line + Area Chart
    st.markdown("### 📈 Engagement Trend Over Time")
    daily = fwh.groupby("created_date").size().reset_index(name="views")
    fig1 = px.area(
        daily, x="created_date", y="views",
        title="Daily Video Engagement",
        color_discrete_sequence=["#6A5ACD"],
        line_shape="spline"
    )
    fig1.update_traces(line_color="#4B0082", fill="tozeroy", opacity=0.4)
    fig1.update_layout(xaxis_title="Date", yaxis_title="Views", height=380)
    st.plotly_chart(fig1, use_container_width=True)

    # 2️⃣ Lollipop Chart
    st.markdown("### ⏱️ Top 10 Videos by Average Duration Watched")
    if "video_title" in fwh.columns:
        top_avg = fwh.groupby("video_title")["duration_min"].mean().nlargest(10).reset_index()
        fig2 = px.scatter(
            top_avg, x="duration_min", y="video_title",
            color_discrete_sequence=["#9370DB"], size="duration_min", size_max=15
        )
        for _, row in top_avg.iterrows():
            fig2.add_shape(type="line", x0=0, x1=row["duration_min"],
                           y0=row["video_title"], y1=row["video_title"],
                           line=dict(color="#9370DB", width=2))
        fig2.update_layout(height=420, xaxis_title="Avg Duration (min)", yaxis_title="Video Title",
                           yaxis={'categoryorder': 'total ascending'})
        st.plotly_chart(fig2, use_container_width=True)

    # 3️⃣ Violin Plot
    st.markdown("### 🎬 Viewing Duration Distribution")
    fig3 = px.violin(
        fwh, y="duration_min", box=True, points="all",
        color_discrete_sequence=["#8A2BE2"],
        title="Distribution of Viewing Durations"
    )
    fig3.update_layout(height=420, yaxis_title="Watch Duration (min)")
    st.plotly_chart(fig3, use_container_width=True)

# 4️⃣ Horizontal Top-20 Comparison
st.markdown("### 📊 Top 20 Videos Watched by Academic Year")
if "acad_year" in counts.columns:
    vc = counts[counts["acad_year"].isin(["2022/2023", "2023/2024"])]
    if not vc.empty:
        top_videos = (
            vc.groupby(["video_title", "acad_year"])["view_count"]
            .sum()
            .reset_index()
        )
        top_videos["total_views"] = top_videos.groupby("video_title")["view_count"].transform("sum")
        top_videos = top_videos.sort_values("total_views", ascending=False).head(40)

        fig4 = px.bar(
            top_videos,
            x="view_count",
            y="video_title",
            color="acad_year",
            barmode="group",
            orientation="h",
            title="Top 20 Most Watched Videos by Academic Year",
            color_discrete_sequence=["#9370DB", "#BA55D3"]
        )
        fig4.update_layout(
            height=750,
            xaxis_title="Views",
            yaxis_title="Video Title",
            yaxis={'categoryorder': 'total ascending'},
            bargap=0.25,
            legend_title="Academic Year"
        )
        st.plotly_chart(fig4, use_container_width=True)

# 5️⃣ Bubble Scatter
st.markdown("### 👥 Repeat Users — Videos Watched per User")
if "user_id" in fwh.columns:
    per_user = fwh.groupby("user_id")["video_id"].nunique().value_counts().reset_index()
    per_user.columns = ["Videos Watched", "User Count"]
    fig5 = px.scatter(
        per_user, x="Videos Watched", y="User Count",
        size="User Count", color="Videos Watched",
        color_continuous_scale="Purples",
        title="User Engagement Spread",
        size_max=40
    )
    fig5.update_layout(height=420, xaxis_title="Videos Watched", yaxis_title="User Count")
    st.plotly_chart(fig5, use_container_width=True)
else:
    st.info("No user ID column found, skipping repeat user analysis.")

# --------------------------- DOWNLOAD ---------------------------
st.download_button(
    "📥 Download Filtered Data",
    fwh.to_csv(index=False).encode("utf-8"),
    "filtered_watch_history.csv",
    "text/csv"
)

