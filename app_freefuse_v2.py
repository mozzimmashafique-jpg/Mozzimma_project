import pandas as pd
import numpy as np
import plotly.express as px
import streamlit as st

st.set_page_config(page_title="FreeFuse Engagement Dashboard", page_icon="🎥", layout="wide")

# --------------------------- PAGE STYLE ---------------------------
st.markdown("""
<style>
  h1, h2, h3 { color:#2b1b6b; }
  [data-testid="stSidebar"] { background:#f4f2ff; }
  .metric-card { background:#f7f5ff; padding:12px; border-radius:12px; text-align:center; }
</style>
""", unsafe_allow_html=True)
st.title("🎥 FreeFuse Interactive Engagement Dashboard")

# --------------------------- FILE PATHS ---------------------------
WATCH_HISTORY_FILE = "Main Nodes Watch History 2022-2024 School Year.xlsx"
VIDEO_COUNTS_FILE = "Video Counts 2022-2024.xlsx"

# --------------------------- HELPER ---------------------------
def normalize_cols(df):
    df.columns = (
        df.columns.str.strip()
        .str.replace(r"\s+", " ", regex=True)
        .str.replace("_", " ")
        .str.title()
    )
    return df

def to_minutes(series):
    s = pd.to_numeric(series, errors="coerce")
    if s.dropna().median() > 200:
        s = s / 60.0
    return s

def classify_ampm(t):
    t = str(t).strip()
    if "AM" in t.upper(): return "AM"
    if "PM" in t.upper(): return "PM"
    try:
        hour = int(t.split(":")[0])
        return "AM" if hour < 12 else "PM"
    except: return "Unknown"

# --------------------------- LOAD DATA ---------------------------
try:
    watch = pd.read_excel(WATCH_HISTORY_FILE)
    counts = pd.read_excel(VIDEO_COUNTS_FILE)
    watch = normalize_cols(watch)
    counts = normalize_cols(counts)
except Exception as e:
    st.error(f"❌ Error loading data: {e}")
    st.stop()

# --------------------------- FIX COLUMNS ---------------------------
col_map_watch = {
    "Video Id": "video_id",
    "Video Title": "video_title",
    "Duration (Mins)": "duration_min",
    "Created Date": "created_date",
    "Watched Time": "watched_time",
    "User Id": "user_id",
}
for col, new in col_map_watch.items():
    if col in watch.columns:
        watch.rename(columns={col: new}, inplace=True)

col_map_counts = {
    "Video Id": "video_id",
    "Video Title": "video_title",
    "View Count": "view_count",
    "Year": "acad_year",
}
for col, new in col_map_counts.items():
    if col in counts.columns:
        counts.rename(columns={col: new}, inplace=True)

missing_cols = [c for c in col_map_watch.values() if c not in watch.columns]
if missing_cols:
    st.warning(f"⚠️ Missing columns in Watch History: {missing_cols}")

# --------------------------- CLEAN DATA ---------------------------
watch["created_date"] = pd.to_datetime(watch.get("created_date"), errors="coerce")
watch["duration_min"] = to_minutes(watch.get("duration_min"))
watch["am_pm"] = watch.get("watched_time", "").apply(classify_ampm)
watch["year"] = watch["created_date"].dt.year
watch["month"] = watch["created_date"].dt.to_period("M").dt.to_timestamp()

counts = counts.dropna(subset=["acad_year", "video_id"])

# --------------------------- FILTERS ---------------------------
st.sidebar.header("📊 Filters")

years = sorted(watch["year"].dropna().unique())
selected_year = st.sidebar.selectbox("Year", years, index=len(years)-1)
titles = sorted(watch["video_title"].dropna().unique())
selected_titles = st.sidebar.multiselect("Video Title(s)", titles, default=titles[:10])
ampm_choice = st.sidebar.selectbox("Time of Day", ["Both", "AM", "PM"], index=0)

fwh = watch.query("year == @selected_year")
if selected_titles:
    fwh = fwh[fwh["video_title"].isin(selected_titles)]
if ampm_choice != "Both":
    fwh = fwh[fwh["am_pm"] == ampm_choice]

# --------------------------- KPIs ---------------------------
st.subheader("📌 Key Metrics")
c1, c2, c3, c4, c5 = st.columns(5)
total_views = len(fwh)
unique_videos = fwh["video_id"].nunique()
total_dur = fwh["duration_min"].sum()
avg_dur = fwh["duration_min"].mean()
most_engaged = fwh.groupby("video_title")["duration_min"].sum().idxmax() if not fwh.empty else "—"

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

# --------------------------- VISUALS ---------------------------
if not fwh.empty:
    # Engagement Trend
    st.markdown("### 📈 Engagement Trend Over Time")
    daily = fwh.groupby("created_date").size().reset_index(name="views")
    fig1 = px.line(daily, x="created_date", y="views", markers=True)
    st.plotly_chart(fig1, use_container_width=True)

    # Top 10 Videos by Avg Duration
    st.markdown("### ⏱️ Top 10 Videos by Average Duration")
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
    st.info("No User ID data to show repeat users.")

# --------------------------- DOWNLOAD ---------------------------
st.download_button(
    "📥 Download Filtered Data",
    fwh.to_csv(index=False).encode("utf-8"),
    "filtered_watch_history.csv",
    "text/csv"
)


