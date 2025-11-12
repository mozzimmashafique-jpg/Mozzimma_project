import pandas as pd
import numpy as np
import plotly.express as px
import streamlit as st

# --------------------------- PAGE SETUP ---------------------------
st.set_page_config(page_title="FreeFuse Engagement Dashboard", page_icon="🎥", layout="wide")

st.markdown("""
<style>
  h1, h2, h3 { color:#2b1b6b; }
  [data-testid="stSidebar"] { background:#f4f2ff; }
  .metric-card { background:#f7f5ff; padding:12px; border-radius:12px; text-align:center; }
</style>
""", unsafe_allow_html=True)

st.title("🎥 FreeFuse Interactive Engagement Dashboard")

# --------------------------- FILE NAMES ---------------------------
WATCH_HISTORY_FILE = "Main Nodes Watch History 2022-2024 School Year.xlsx"
VIDEO_COUNTS_FILE = "Video Counts 2022-2024.xlsx"

# --------------------------- HELPER FUNCTIONS ---------------------------
def normalize_cols(df):
    """Normalize column names (strip spaces, lower, replace underscores, etc.)"""
    df.columns = (
        df.columns.str.strip()
        .str.replace(r"[\s_]+", " ", regex=True)
        .str.lower()
    )
    return df

def to_minutes(series):
    s = pd.to_numeric(series, errors="coerce")
    if s.dropna().median() > 200:  # likely seconds
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

# --------------------------- PRINT FOR DEBUGGING ---------------------------
st.write("📋 Watch History Columns:", watch.columns.tolist())
st.write("📋 Video Counts Columns:", counts.columns.tolist())

# --------------------------- RENAME / CLEAN WATCH HISTORY ---------------------------
# Attempt to auto-detect relevant columns
col_map = {}
for col in watch.columns:
    if "video id" in col: col_map[col] = "video_id"
    elif "title" in col: col_map[col] = "video_title"
    elif "duration" in col: col_map[col] = "duration_min"
    elif "created" in col: col_map[col] = "created_date"
    elif "watch" in col: col_map[col] = "watched_time"
    elif "user" in col: col_map[col] = "user_id"

watch.rename(columns=col_map, inplace=True)

required = ["video_id", "video_title", "duration_min", "created_date", "watched_time", "user_id"]
missing = [c for c in required if c not in watch.columns]
if missing:
    st.warning(f"⚠️ Missing columns in Watch History: {missing}")

# Clean and prep data
watch["created_date"] = pd.to_datetime(watch.get("created_date"), errors="coerce")
watch["duration_min"] = to_minutes(watch.get("duration_min"))
watch["am_pm"] = watch.get("watched_time", "").apply(classify_ampm)
watch["year"] = watch["created_date"].dt.year
watch["month"] = watch["created_date"].dt.to_period("M").dt.to_timestamp()

# --------------------------- CLEAN VIDEO COUNTS ---------------------------
col_map2 = {}
for col in counts.columns:
    if "video id" in col: col_map2[col] = "video_id"
    elif "title" in col: col_map2[col] = "video_title"
    elif "view" in col: col_map2[col] = "view_count"
    elif "year" in col: col_map2[col] = "acad_year"
counts.rename(columns=col_map2, inplace=True)

# --------------------------- FILTERS ---------------------------
st.sidebar.header("📊 Filters")

years = sorted(watch["year"].dropna().unique())
selected_year = st.sidebar.selectbox("Select Year", years, index=len(years)-1 if years else 0)

titles = sorted(watch["video_title"].dropna().unique()) if "video_title" in watch.columns else []
selected_titles = st.sidebar.multiselect("Select Video Title(s)", titles, default=titles[:10] if len(titles) > 10 else titles)

ampm_choice = st.sidebar.selectbox("Time of Day", ["Both", "AM", "PM"], index=0)

# --------------------------- APPLY FILTERS ---------------------------
fwh = watch.copy()
if "year" in fwh.columns:
    fwh = fwh[fwh["year"] == selected_year]
if selected_titles:
    fwh = fwh[fwh["video_title"].isin(selected_titles)]
if ampm_choice != "Both" and "am_pm" in fwh.columns:
    fwh = fwh[fwh["am_pm"] == ampm_choice]

# --------------------------- KPIs ---------------------------
st.subheader("📌 Key Metrics")
c1, c2, c3, c4, c5 = st.columns(5)

total_views = len(fwh)
unique_videos = fwh["video_id"].nunique() if "video_id" in fwh.columns else 0
total_dur = fwh["duration_min"].sum() if "duration_min" in fwh.columns else 0
avg_dur = fwh["duration_min"].mean() if "duration_min" in fwh.columns else 0

most_engaged = "—"
if "video_title" in fwh.columns and not fwh.empty:
    most_engaged = fwh.groupby("video_title")["duration_min"].sum().idxmax()

with c1: st.markdown(f"<div class='metric-card'><h4>Total Views</h4><h2>{total_views:,}</h2></div>", unsafe_allow_html=True)
with c2: st.markdown(f"<div class='metric-card'><h4>Unique Videos</h4><h2>{unique_videos:,}</h2></div>", unsafe_allow_html=True)
with c3: st.markdown(f"<div class='metric-card'><h4>Total Watch (min)</h4><h2>{total_dur:,.1f}</h2></div>", unsafe_allow_html=True)
with c4: st.markdown(f"<div class='metric-card'><h4>Avg Watch (min)</h4><h2>{avg_dur:.2f}</h2></div>", unsafe_allow_html=True)
with c5: st.markdown(f"<div class='metric-card'><h4>Most Engaged Video</h4><h3>{most_engaged}</h3></div>", unsafe_allow_html=True)

st.markdown("---")

# --------------------------- VISUALS ---------------------------

if not fwh.empty and "created_date" in fwh.columns:
    # Engagement Trend
    st.markdown("### 📈 Engagement Trend Over Time")
    daily = fwh.groupby("created_date").size().reset_index(name="views")
    fig1 = px.line(daily, x="created_date", y="views", markers=True)
    st.plotly_chart(fig1, use_container_width=True)

    # Top 10 by Avg Duration
    st.markdown("### ⏱️ Top 10 Videos by Average Duration")
    if "video_title" in fwh.columns:
        top_avg = fwh.groupby("video_title")["duration_min"].mean().nlargest(10).reset_index()
        fig2 = px.bar(top_avg, x="duration_min", y="video_title", orientation="h",
                      labels={"duration_min": "Avg Duration (min)", "video_title": "Video"})
        fig2.update_layout(yaxis={'categoryorder': 'total ascending'})
        st.plotly_chart(fig2, use_container_width=True)

    # Viewing Duration Distribution
    st.markdown("### 🎬 Viewing Duration Distribution")
    fig3 = px.histogram(fwh, x="duration_min", nbins=25)
    st.plotly_chart(fig3, use_container_width=True)

# --------------------------- YEARLY COMPARISON ---------------------------
st.markdown("### 🔄 Video Counts by Academic Year (2022/2023 vs 2023/2024)")
if "acad_year" in counts.columns:
    vc = counts[counts["acad_year"].isin(["2022/2023", "2023/2024"])]
    if not vc.empty:
        total = vc.groupby("acad_year")["view_count"].sum().reset_index()
        fig4 = px.bar(total, x="acad_year", y="view_count", text="view_count")
        st.plotly_chart(fig4, use_container_width=True)

# --------------------------- REPEAT USERS ---------------------------
st.markdown("### 👥 Repeat Users — Videos Watched per User")
if "user_id" in fwh.columns:
    per_user = fwh.groupby("user_id")["video_id"].nunique().value_counts().reset_index()
    per_user.columns = ["Videos Watched", "User Count"]
    fig5 = px.bar(per_user, x="Videos Watched", y="User Count")
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



