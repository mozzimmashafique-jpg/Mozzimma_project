import pandas as pd
import numpy as np
import plotly.express as px
import streamlit as st

# --------------------------- PAGE SETUP ---------------------------
st.set_page_config(page_title="FreeFuse Engagement Dashboard", page_icon="🎥", layout="wide")

st.markdown("""
<style>
    h1, h2, h3 { color: #2b1b6b; }
    .metric-card { background-color: #f7f5ff; padding: 12px; border-radius: 10px; text-align: center; }
    [data-testid="stSidebar"] { background-color: #f4f2ff; }
</style>
""", unsafe_allow_html=True)

st.title("🎥 FreeFuse Interactive Engagement Dashboard")

# --------------------------- LOAD DATA ---------------------------
WATCH_HISTORY_FILE = "Main Nodes Watch History 2022-2024 School Year.xlsx"
VIDEO_COUNTS_FILE = "Video Counts 2022-2024.xlsx"

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

# --------------------------- CLEAN DATA ---------------------------
watch.columns = [c.strip().lower().replace(" ", "_") for c in watch.columns]
counts.columns = [c.strip().lower().replace(" ", "_") for c in counts.columns]

# Identify columns
date_cols = [c for c in watch.columns if "date" in c or "timestamp" in c]
time_cols = [c for c in watch.columns if "time" in c or "hour" in c]
dur_cols = [c for c in watch.columns if "duration" in c]
vid_col = [c for c in watch.columns if "video" in c][0]
title_col = [c for c in watch.columns if "title" in c or "name" in c or "video" in c][-1]

# Convert datetime
if date_cols:
    date_col = date_cols[0]
    if time_cols:
        watch["ts"] = pd.to_datetime(watch[date_col].astype(str) + " " + watch[time_cols[0]].astype(str), errors="coerce")
    else:
        watch["ts"] = pd.to_datetime(watch[date_col], errors="coerce")
else:
    st.error("⚠️ No date column found in Watch History.")
    st.stop()

watch["date"] = pd.to_datetime(watch["ts"], errors="coerce")
watch["month"] = watch["date"].dt.to_period("M").dt.to_timestamp()
watch["year"] = watch["date"].dt.year
watch["hour"] = watch["date"].dt.hour
watch["am_pm"] = np.where(watch["hour"] < 12, "AM", "PM")

# Normalize duration
if dur_cols:
    dur_col = dur_cols[0]
    watch["duration_min"] = pd.to_numeric(watch[dur_col], errors="coerce")
    watch["duration_min"] = np.where(watch["duration_min"] > 200, watch["duration_min"]/60, watch["duration_min"])
else:
    watch["duration_min"] = np.nan

# --------------------------- SIDEBAR FILTERS ---------------------------
st.sidebar.header("📊 Filters")

# Dropdown filters
years = sorted(watch["year"].dropna().unique().tolist())
selected_year = st.sidebar.selectbox("Select Year", options=years, index=len(years)-1)

videos = sorted(watch[title_col].dropna().unique().tolist())
selected_video = st.sidebar.selectbox("Select Video Title", options=["All"] + videos)

ampm_filter = st.sidebar.selectbox("Time of Day", ["Both", "AM", "PM"])

# Apply filters
filtered = watch[watch["year"] == selected_year].copy()
if selected_video != "All":
    filtered = filtered[filtered[title_col] == selected_video]
if ampm_filter != "Both":
    filtered = filtered[filtered["am_pm"] == ampm_filter]

# --------------------------- KPI CARDS ---------------------------
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

# --------------------------- VISUALIZATIONS ---------------------------

# 1️⃣ Engagement Trend
st.markdown("### 📊 Engagement Trend Over Time")
trend = filtered.groupby("date").size().reset_index(name="views")
if not trend.empty:
    fig1 = px.line(trend, x="date", y="views", markers=True,
                   color_discrete_sequence=["#6A5ACD"])
    fig1.update_layout(yaxis_title="Views", xaxis_title="", height=400)
    st.plotly_chart(fig1, use_container_width=True)
else:
    st.info("No data for selected filters.")

# 2️⃣ Top 10 Videos by Avg Duration
st.markdown("### ⏱️ Top 10 Videos by Average Duration Watched")
if "duration_min" in filtered:
    top_avg = (
        filtered.groupby(title_col)["duration_min"]
        .mean()
        .reset_index()
        .sort_values("duration_min", ascending=False)
        .head(10)
    )
    fig2 = px.bar(top_avg, x="duration_min", y=title_col, orientation="h",
                  color="duration_min", color_continuous_scale="Purples",
                  labels={"duration_min": "Avg Duration (min)", title_col: "Video"})
    fig2.update_layout(yaxis={'categoryorder':'total ascending'}, height=400)
    st.plotly_chart(fig2, use_container_width=True)
else:
    st.info("No duration data available.")

# 3️⃣ Viewing Duration Distribution
st.markdown("### 🎬 Viewing Duration Distribution")
if "duration_min" in filtered:
    fig3 = px.histogram(filtered, x="duration_min", nbins=30,
                        color_discrete_sequence=["#9370DB"],
                        labels={"duration_min": "Watch Duration (min)"})
    fig3.update_layout(yaxis_title="Count", height=400)
    st.plotly_chart(fig3, use_container_width=True)
else:
    st.info("No duration data available.")

# 4️⃣ Video Count Comparison 2022/2023 vs 2023/2024
st.markdown("### 🔄 Video Count Comparison by Academic Year")
# Clean and prep counts data
year_cols = [c for c in counts.columns if "2022" in c or "2023" in c or "2024" in c]
vid_name = [c for c in counts.columns if "video" in c or "title" in c][0]
if year_cols:
    df_counts = counts[[vid_name] + year_cols].melt(id_vars=vid_name, var_name="Year", value_name="Views")
    fig4 = px.bar(df_counts, x=vid_name, y="Views", color="Year",
                  barmode="group", title="Videos Watched by Academic Year")
    fig4.update_layout(xaxis_title="Video", yaxis_title="Views", height=500)
    st.plotly_chart(fig4, use_container_width=True)
else:
    st.info("Year comparison columns not found in Video Counts dataset.")

# 5️⃣ Repeat Users
st.markdown("### 👥 Repeat Users — How Many Videos Each User Watched")
viewer_cols = [c for c in filtered.columns if "user" in c or "viewer" in c or "id" in c]
if viewer_cols:
    vcol = viewer_cols[0]
    repeats = filtered.groupby(vcol)[vid_col].nunique().reset_index(name="videos_watched")
    counts_repeat = repeats["videos_watched"].value_counts().reset_index()
    counts_repeat.columns = ["Videos Watched", "User Count"]
    fig5 = px.bar(counts_repeat, x="Videos Watched", y="User Count",
                  color="User Count", color_continuous_scale="Blues")
    st.plotly_chart(fig5, use_container_width=True)
else:
    st.info("No viewer/user ID column found in Watch History.")

# --------------------------- DOWNLOAD ---------------------------
st.markdown("---")
st.download_button("📥 Download Filtered Data (CSV)",
                   filtered.to_csv(index=False).encode("utf-8"),
                   "freefuse_filtered.csv",
                   "text/csv")


