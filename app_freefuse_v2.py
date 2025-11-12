import pandas as pd
import numpy as np
import plotly.express as px
import streamlit as st

# ---------------------------  PAGE SETUP  ---------------------------
st.set_page_config(page_title="FreeFuse Engagement Dashboard", page_icon="🎥", layout="wide")

st.markdown("""
<style>
    h1, h2, h3 { color: #2b1b6b; }
    .metric-card { background-color: #f7f5ff; padding: 12px; border-radius: 10px; text-align: center; }
</style>
""", unsafe_allow_html=True)

st.title("🎥 FreeFuse Interactive Engagement Dashboard")

# ---------------------------  DATA FILES  ---------------------------
WATCH_HISTORY_FILE = "Main Nodes Watch History 2022-2024 School Year.xlsx"
VIDEO_COUNTS_FILE = "Video Counts 2022-2024.xlsx"

# ---------------------------  HELPER FUNCTIONS  ---------------------------
def normalize_minutes(series: pd.Series) -> pd.Series:
    s = pd.to_numeric(series, errors="coerce")
    if s.dropna().median() > 200:
        s = s / 60.0
    return s

def ensure_datetime(date_col: pd.Series, time_col: pd.Series = None) -> pd.Series:
    if time_col is not None:
        return pd.to_datetime(date_col.astype(str) + " " + time_col.astype(str), errors="coerce")
    return pd.to_datetime(date_col, errors="coerce")

def am_pm_from_hour(h: int) -> str:
    try:
        h = int(h)
    except Exception:
        return "Unknown"
    return "AM" if 0 <= h < 12 else "PM"

# ---------------------------  LOAD DATA  ---------------------------
try:
    excel_file = pd.ExcelFile(WATCH_HISTORY_FILE)
    watch = None
    for sheet in excel_file.sheet_names:
        temp = pd.read_excel(excel_file, sheet_name=sheet)
        if not temp.empty:
            watch = temp
            st.success(f"✅ Loaded Watch History sheet: {sheet}")
            break
    counts = pd.read_excel(VIDEO_COUNTS_FILE)
except Exception as e:
    st.error(f"❌ Could not load files: {e}")
    st.stop()

# ---------------------------  CLEAN WATCH HISTORY  ---------------------------
watch.columns = [c.strip().lower().replace(" ", "_") for c in watch.columns]
counts.columns = [c.strip().lower().replace(" ", "_") for c in counts.columns]

# Detect key columns
date_cols = [c for c in watch.columns if "date" in c or "timestamp" in c]
time_cols = [c for c in watch.columns if "time" in c or "hour" in c]
dur_cols = [c for c in watch.columns if "duration" in c]
vid_col = [c for c in watch.columns if "video" in c][0]

# Create datetime and derived cols
if date_cols:
    date_col = date_cols[0]
    if time_cols:
        watch["ts"] = ensure_datetime(watch[date_col], watch[time_cols[0]])
    else:
        watch["ts"] = pd.to_datetime(watch[date_col], errors="coerce")
else:
    st.error("⚠️ No date column found.")
    st.stop()

watch["date"] = pd.to_datetime(watch["ts"], errors="coerce")
watch["month"] = watch["date"].dt.to_period("M").dt.to_timestamp()
watch["year"] = watch["date"].dt.year
watch["hour"] = watch["date"].dt.hour
watch["am_pm"] = watch["hour"].apply(am_pm_from_hour)
watch["duration_min"] = normalize_minutes(watch[dur_cols[0]]) if dur_cols else np.nan

# ---------------------------  FILTERS  ---------------------------
st.sidebar.header("📊 Filters")

# Year filter
years = sorted(watch["year"].dropna().unique().tolist())
selected_years = st.sidebar.multiselect("Select Year(s)", years, default=years)

# Video filter
videos = sorted(watch[vid_col].dropna().unique().tolist())
selected_videos = st.sidebar.multiselect("Select Video(s)", videos, default=videos[:10] if len(videos) > 10 else videos)

# Time filter
ampm_filter = st.sidebar.radio("Time of Day", ["Both", "AM", "PM"], index=0, horizontal=True)

filtered = watch[
    watch["year"].isin(selected_years) &
    watch[vid_col].isin(selected_videos)
].copy()

if ampm_filter != "Both":
    filtered = filtered[filtered["am_pm"] == ampm_filter]

# ---------------------------  KPIs  ---------------------------
st.subheader("📌 Key Metrics")

col1, col2, col3, col4 = st.columns(4)
total_views = len(filtered)
unique_videos = filtered[vid_col].nunique()
avg_duration = filtered["duration_min"].mean()
most_month = filtered["month"].value_counts().idxmax().strftime("%b %Y") if not filtered.empty else "—"

with col1:
    st.markdown(f"<div class='metric-card'><h4>Total Views</h4><h2>{total_views:,}</h2></div>", unsafe_allow_html=True)
with col2:
    st.markdown(f"<div class='metric-card'><h4>Unique Videos</h4><h2>{unique_videos:,}</h2></div>", unsafe_allow_html=True)
with col3:
    st.markdown(f"<div class='metric-card'><h4>Avg Duration (min)</h4><h2>{avg_duration:.2f}</h2></div>", unsafe_allow_html=True)
with col4:
    st.markdown(f"<div class='metric-card'><h4>Most Watched Month</h4><h2>{most_month}</h2></div>", unsafe_allow_html=True)

st.markdown("---")

# ---------------------------  VISUALS  ---------------------------
st.subheader("📈 Engagement Insights")

# 1️⃣ ENGAGEMENT TREND
trend_col, duration_col = st.columns([1.2, 1])
with trend_col:
    st.markdown("### 📊 Engagement Trend Over Time")
    trend = filtered.groupby("date").size().reset_index(name="views")
    if not trend.empty:
        fig1 = px.line(trend, x="date", y="views", markers=True,
                       title="", color_discrete_sequence=["#6A5ACD"])
        fig1.update_layout(yaxis_title="Views", xaxis_title="", height=400)
        st.plotly_chart(fig1, use_container_width=True)
    else:
        st.info("No trend data available for selection.")

# 2️⃣ TOP VIDEOS BY AVG DURATION
with duration_col:
    st.markdown("### ⏱️ Top 10 Videos by Avg Duration")
    if "duration_min" in filtered:
        top_avg = (
            filtered.groupby(vid_col)["duration_min"]
            .mean()
            .reset_index()
            .sort_values("duration_min", ascending=False)
            .head(10)
        )
        fig2 = px.bar(top_avg, x="duration_min", y=vid_col, orientation="h",
                      color="duration_min", color_continuous_scale="Purples",
                      title="")
        fig2.update_layout(xaxis_title="Avg Duration (min)", yaxis_title="", height=400)
        st.plotly_chart(fig2, use_container_width=True)
    else:
        st.info("No duration data available.")

# 3️⃣ VIEWING DURATION DISTRIBUTION
st.markdown("### 🎬 Viewing Duration Distribution")
if "duration_min" in filtered:
    fig3 = px.histogram(filtered, x="duration_min", nbins=30,
                        color_discrete_sequence=["#9370DB"],
                        title="", labels={"duration_min": "Watch Duration (min)"})
    fig3.update_layout(yaxis_title="Count", height=400)
    st.plotly_chart(fig3, use_container_width=True)
else:
    st.info("No duration data available.")

# 4️⃣ REPEAT USERS
st.markdown("### 👥 Repeat Users (Videos Watched per User)")
viewer_cols = [c for c in filtered.columns if "user" in c or "viewer" in c or "id" in c]
if viewer_cols:
    vcol = viewer_cols[0]
    repeats = filtered.groupby(vcol)[vid_col].nunique().reset_index(name="videos_watched")
    counts_repeat = repeats["videos_watched"].value_counts().reset_index()
    counts_repeat.columns = ["Videos Watched", "User Count"]

    fig4 = px.bar(counts_repeat, x="Videos Watched", y="User Count",
                  color="User Count", color_continuous_scale="Blues",
                  title="")
    fig4.update_layout(height=400)
    st.plotly_chart(fig4, use_container_width=True)
else:
    st.info("No viewer/user ID column found in this dataset.")

# ---------------------------  DOWNLOAD  ---------------------------
st.markdown("---")
st.download_button("📥 Download Filtered Data (CSV)",
                   filtered.to_csv(index=False).encode("utf-8"),
                   "freefuse_filtered.csv",
                   "text/csv")


