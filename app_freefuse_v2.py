import pandas as pd
import numpy as np
import plotly.express as px
import streamlit as st

# ---------------------------  PAGE SETUP  ---------------------------
st.set_page_config(page_title="FreeFuse Engagement Dashboard", page_icon="🎥", layout="wide")
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

# Detect columns
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

watch["date"] = pd.to_datetime(watch["ts"], errors="coerce").dt.date
watch["month"] = pd.to_datetime(watch["ts"], errors="coerce").dt.to_period("M").dt.to_timestamp()
watch["hour"] = pd.to_datetime(watch["ts"], errors="coerce").dt.hour
watch["am_pm"] = watch["hour"].apply(am_pm_from_hour)
watch["duration_min"] = normalize_minutes(watch[dur_cols[0]]) if dur_cols else np.nan

# ---------------------------  FILTERS  ---------------------------
st.sidebar.header("📊 Filters")
dmin, dmax = watch["date"].min(), watch["date"].max()
date_range = st.sidebar.date_input("Date Range", (dmin, dmax))
start_date, end_date = date_range if isinstance(date_range, tuple) else (dmin, dmax)

filtered = watch[
    (pd.to_datetime(watch["date"]) >= pd.to_datetime(start_date)) &
    (pd.to_datetime(watch["date"]) <= pd.to_datetime(end_date))
].copy()

ampm_filter = st.sidebar.radio("Time of Day", ["Both", "AM", "PM"], index=0, horizontal=True)
if ampm_filter != "Both":
    filtered = filtered[filtered["am_pm"] == ampm_filter]

# ---------------------------  KPIs  ---------------------------
st.subheader("📌 Key Metrics")
col1, col2, col3, col4 = st.columns(4)
total_views = len(filtered)
unique_videos = filtered[vid_col].nunique()
avg_duration = filtered["duration_min"].mean()
most_month = filtered["month"].value_counts().idxmax().strftime("%b %Y") if not filtered.empty else "—"
col1.metric("Total Views", f"{total_views:,}")
col2.metric("Unique Videos", f"{unique_videos:,}")
col3.metric("Avg Duration (min)", f"{avg_duration:.2f}")
col4.metric("Most Watched Month", most_month)
st.divider()

# ---------------------------  ANALYTICS  ---------------------------
st.subheader("📈 Engagement Insights")
tab1, tab2, tab3, tab4 = st.tabs([
    "Engagement Trend Over Time",
    "Top 10 Videos by Avg Duration",
    "Viewing Duration Distribution",
    "Repeat Users"
])

# ---- Engagement Trend Over Time ----
with tab1:
    trend = filtered.groupby("date").size().reset_index(name="views")
    if not trend.empty:
        fig1 = px.line(trend, x="date", y="views", markers=True,
                       title="Engagement Trend Over Time (Daily Views)")
        fig1.update_layout(yaxis_title="Total Views", xaxis_title="")
        st.plotly_chart(fig1, use_container_width=True)
    else:
        st.info("No data available for the selected range.")

# ---- Top 10 Videos by Avg Duration ----
with tab2:
    if "duration_min" in filtered:
        top_avg = (
            filtered.groupby(vid_col)["duration_min"]
            .mean()
            .reset_index()
            .sort_values("duration_min", ascending=False)
            .head(10)
        )
        fig2 = px.bar(top_avg, x="duration_min", y=vid_col, orientation="h",
                      title="Top 10 Videos by Average Duration Watched",
                      labels={"duration_min": "Avg Duration (min)", vid_col: "Video"})
        fig2.update_layout(yaxis={'categoryorder':'total ascending'})
        st.plotly_chart(fig2, use_container_width=True)
    else:
        st.info("No duration data available.")

# ---- Viewing Duration Distribution ----
with tab3:
    if "duration_min" in filtered:
        fig3 = px.histogram(filtered, x="duration_min", nbins=30,
                            title="Viewing Duration Distribution (Minutes)",
                            labels={"duration_min": "Watch Duration (min)"})
        st.plotly_chart(fig3, use_container_width=True)
    else:
        st.info("No duration data available.")

# ---- Repeat Users ----
with tab4:
    viewer_cols = [c for c in filtered.columns if "user" in c or "viewer" in c or "id" in c]
    if viewer_cols:
        vcol = viewer_cols[0]
        repeats = filtered.groupby(vcol)[vid_col].nunique().reset_index(name="videos_watched")
        counts_repeat = repeats["videos_watched"].value_counts().reset_index()
        counts_repeat.columns = ["Videos Watched", "User Count"]

        fig4 = px.bar(counts_repeat, x="Videos Watched", y="User Count",
                      title="Repeat Users — How Many Videos Each User Watched")
        st.plotly_chart(fig4, use_container_width=True)
    else:
        st.info("No viewer/user ID column found in this dataset.")

# ---------------------------  DOWNLOAD  ---------------------------
st.download_button("📥 Download Filtered Data (CSV)",
                   filtered.to_csv(index=False).encode("utf-8"),
                   "freefuse_filtered.csv",
                   "text/csv")

