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

# --------------------------- FILE NAMES (as confirmed) ---------------------------
WATCH_HISTORY_FILE = "Main Nodes Watch History 2022-2024 School Year.xlsx"
VIDEO_COUNTS_FILE  = "Video Counts 2022-2024.xlsx"

# --------------------------- HELPERS ---------------------------
def to_minutes(series: pd.Series) -> pd.Series:
    s = pd.to_numeric(series, errors="coerce")
    # If big values, assume seconds and convert to minutes
    if s.dropna().median() > 200:
        s = s / 60.0
    return s

def classify_ampm_from_string(t: str) -> str:
    try:
        t = str(t).strip()
        # handle "HH:MM[:SS]" 24h or AM/PM strings
        if "AM" in t.upper() or "PM" in t.upper():
            return "AM" if "AM" in t.upper() else "PM"
        parts = t.split(":")
        hour = int(parts[0])
        return "AM" if 0 <= hour < 12 else "PM"
    except Exception:
        return "Unknown"

# --------------------------- LOAD DATA ---------------------------
try:
    # Watch history: pick first non-empty sheet
    xfile = pd.ExcelFile(WATCH_HISTORY_FILE)
    watch = None
    for sh in xfile.sheet_names:
        df = pd.read_excel(xfile, sheet_name=sh)
        if not df.empty:
            watch = df.copy()
            break
    counts = pd.read_excel(VIDEO_COUNTS_FILE)
except Exception as e:
    st.error(f"❌ Could not load files: {e}")
    st.stop()

# --------------------------- STANDARDIZE COLUMNS ---------------------------
watch.columns  = [c.strip() for c in watch.columns]
counts.columns = [c.strip() for c in counts.columns]

# Expected columns based on your screenshot
REQUIRED_WATCH = ["Video ID", "Video Title", "duration (mins)", "created_Date", "Watched Time", "User ID"]
REQUIRED_COUNTS = ["Video ID", "Video Title", "View Count", "Year"]

missing_w = [c for c in REQUIRED_WATCH if c not in watch.columns]
missing_c = [c for c in REQUIRED_COUNTS if c not in counts.columns]
if missing_w:
    st.error(f"⚠️ Missing columns in Watch History: {missing_w}")
    st.stop()
if missing_c:
    st.error(f"⚠️ Missing columns in Video Counts: {missing_c}")
    st.stop()

# --------------------------- CLEAN WATCH HISTORY ---------------------------
wh = watch.rename(columns={
    "Video ID": "video_id",
    "Video Title": "video_title",
    "duration (mins)": "duration_min",
    "created_Date": "created_date",
    "Watched Time": "watched_time",
    "User ID": "user_id"
}).copy()

# Dates & derived fields
wh["created_date"] = pd.to_datetime(wh["created_date"], errors="coerce")
wh["year"] = wh["created_date"].dt.year
wh["month"] = wh["created_date"].dt.to_period("M").dt.to_timestamp()

# Duration normalized to minutes
wh["duration_min"] = to_minutes(wh["duration_min"])

# AM/PM from time text (fallback to AM if unknown)
wh["am_pm"] = wh["watched_time"].apply(classify_ampm_from_string)
wh.loc[~wh["am_pm"].isin(["AM", "PM"]), "am_pm"] = "Unknown"

# --------------------------- CLEAN VIDEO COUNTS ---------------------------
vc = counts.rename(columns={
    "Video ID": "video_id",
    "Video Title": "video_title",
    "View Count": "view_count",
    "Year": "acad_year"  # e.g., "2022/2023", "2023/2024"
}).copy()

# Some files have mixed year labels; keep only rows with an acad_year label
vc = vc.dropna(subset=["acad_year", "video_id"])

# --------------------------- SIDEBAR FILTERS ---------------------------
st.sidebar.header("📊 Filters")

# Year dropdown (from watch history calendar year)
years = sorted(wh["year"].dropna().unique().tolist())
if not years:
    st.info("No years found in watch history.")
    st.stop()
selected_year = st.sidebar.selectbox("Year", options=years, index=len(years)-1)

# Video titles multiselect (dropdown, multiple allowed)
all_titles = wh["video_title"].dropna().unique().tolist()
all_titles = sorted(all_titles)
default_titles = all_titles if len(all_titles) <= 10 else all_titles[:10]
selected_titles = st.sidebar.multiselect("Video Title(s)", options=all_titles, default=default_titles)

# AM/PM dropdown
ampm_choice = st.sidebar.selectbox("Time of Day", options=["Both", "AM", "PM"], index=0)

# --------------------------- APPLY FILTERS ---------------------------
fwh = wh[wh["year"] == selected_year].copy()
if selected_titles:
    fwh = fwh[fwh["video_title"].isin(selected_titles)]
if ampm_choice != "Both":
    fwh = fwh[fwh["am_pm"] == ampm_choice]

# --------------------------- KPIs ---------------------------
st.subheader("📌 Key Metrics")
c1, c2, c3, c4, c5 = st.columns(5)

total_views = len(fwh)
unique_videos = fwh["video_id"].nunique()
total_dur = fwh["duration_min"].sum(skipna=True)
avg_dur = fwh["duration_min"].mean(skipna=True)

most_engaged_title = "—"
if not fwh.empty:
    g = fwh.groupby(["video_id", "video_title"])["duration_min"].sum().reset_index()
    g = g.sort_values("duration_min", ascending=False)
    most_engaged_title = g.iloc[0]["video_title"]

with c1:
    st.markdown(f"<div class='metric-card'><h4>Total Views</h4><h2>{total_views:,}</h2></div>", unsafe_allow_html=True)
with c2:
    st.markdown(f"<div class='metric-card'><h4>Unique Videos</h4><h2>{unique_videos:,}</h2></div>", unsafe_allow_html=True)
with c3:
    st.markdown(f"<div class='metric-card'><h4>Total Watch (min)</h4><h2>{total_dur:,.1f}</h2></div>", unsafe_allow_html=True)
with c4:
    st.markdown(f"<div class='metric-card'><h4>Avg Watch (min)</h4><h2>{(avg_dur if not np.isnan(avg_dur) else 0):.2f}</h2></div>", unsafe_allow_html=True)
with c5:
    st.markdown(f"<div class='metric-card'><h4>Most Engaged Video</h4><h3>{most_engaged_title}</h3></div>", unsafe_allow_html=True)

st.markdown("---")

# --------------------------- VISUALS ---------------------------

# 1) Engagement trend over time (daily)
st.markdown("### 📊 Engagement Trend Over Time (Daily Views)")
trend = fwh.groupby("created_date").size().reset_index(name="views")
if not trend.empty:
    fig1 = px.line(trend, x="created_date", y="views", markers=True)
    fig1.update_layout(xaxis_title="", yaxis_title="Views", height=380)
    st.plotly_chart(fig1, use_container_width=True)
else:
    st.info("No events in the selected filters.")

# 2) Top 10 videos by average duration
st.markdown("### ⏱️ Top 10 Videos by Average Duration Watched")
if not fwh.empty:
    top_avg = (
        fwh.groupby(["video_id", "video_title"])["duration_min"]
        .mean()
        .reset_index()
        .sort_values("duration_min", ascending=False)
        .head(10)
    )
    fig2 = px.bar(top_avg, x="duration_min", y="video_title", orientation="h",
                  labels={"duration_min": "Avg Duration (min)", "video_title": "Video"})
    fig2.update_layout(height=420, yaxis={'categoryorder': 'total ascending'})
    st.plotly_chart(fig2, use_container_width=True)
else:
    st.info("No duration data available for this selection.")

# 3) Viewing duration distribution
st.markdown("### 🎬 Viewing Duration Distribution")
if "duration_min" in fwh.columns and not fwh["duration_min"].dropna().empty:
    fig3 = px.histogram(fwh, x="duration_min", nbins=30, labels={"duration_min": "Watch Duration (min)"})
    fig3.update_layout(height=380, yaxis_title="Count")
    st.plotly_chart(fig3, use_container_width=True)
else:
    st.info("No duration data available for this selection.")

# 4) Year-over-year comparison (2022/2023 vs 2023/2024) with variance
st.markdown("### 🔄 Video Counts by Academic Year (YOY with Variance)")
# Prepare counts long-form: one row per video per acad_year
vc_long = vc[["video_id", "video_title", "acad_year", "view_count"]].copy()
# Filter only the two academic years if present
target_years = ["2022/2023", "2023/2024"]
vc_long = vc_long[vc_long["acad_year"].isin(target_years)]

if not vc_long.empty:
    # Overall totals per academic year
    totals = vc_long.groupby("acad_year")["view_count"].sum().reindex(target_years).reset_index()
    # Compute variance % if both years present
    var_txt = ""
    if set(target_years).issubset(set(totals["acad_year"].tolist())) and len(totals) == 2:
        base = totals.loc[totals["acad_year"] == "2022/2023", "view_count"].values
        new  = totals.loc[totals["acad_year"] == "2023/2024", "view_count"].values
        if len(base) and len(new) and base[0] != 0:
            var_pct = ((new[0] - base[0]) / base[0]) * 100.0
            sign = "▲" if var_pct >= 0 else "▼"
            var_txt = f"  ({sign} {var_pct:.1f}% vs 2022/2023)"
    fig4 = px.bar(totals, x="acad_year", y="view_count",
                  text="view_count", labels={"acad_year":"Academic Year", "view_count":"Total Views"},
                  title=f"Total Views by Academic Year{var_txt}")
    fig4.update_traces(texttemplate='%{text:,}', textposition='outside')
    fig4.update_layout(height=420, uniformtext_minsize=10, uniformtext_mode='hide')
    st.plotly_chart(fig4, use_container_width=True)
else:
    st.info("Video Counts file does not contain 2022/2023 or 2023/2024.")

# 5) Repeat users (how many different videos each user watched)
st.markdown("### 👥 Repeat Users — Videos Watched per User")
viewer_col = "user_id"
if viewer_col in fwh.columns and not fwh.empty:
    per_user = fwh.groupby(viewer_col)["video_id"].nunique().reset_index(name="videos_watched")
    dist = per_user["videos_watched"].value_counts().sort_index().reset_index()
    dist.columns = ["Videos Watched", "User Count"]
    fig5 = px.bar(dist, x="Videos Watched", y="User Count", title="")
    fig5.update_layout(height=380)
    st.plotly_chart(fig5, use_container_width=True)
else:
    st.info("No viewer IDs available for repeat-user analysis.")

# --------------------------- DOWNLOAD ---------------------------
st.markdown("---")
st.download_button(
    "📥 Download Filtered Watch History (CSV)",
    fwh.to_csv(index=False).encode("utf-8"),
    "freefuse_filtered_watch_history.csv",
    "text/csv"
)


