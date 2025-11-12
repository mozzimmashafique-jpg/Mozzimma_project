import math
from typing import Optional, List

import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

# ---------------------------  PAGE SETUP  ---------------------------
st.set_page_config(page_title="FreeFuse Engagement Dashboard — Final",
                   page_icon="🎥", layout="wide")

st.markdown("""
<style>
  :root { --accent:#6A5ACD; --accent2:#9370DB; --bg:#f7f5ff; }
  [data-testid="stSidebar"] { background-color: var(--bg); }
  h1,h2,h3 { color:#2b1b6b; }
  .card { padding:1rem; background:white; border-radius:16px; box-shadow:0 2px 10px rgba(0,0,0,0.05); }
  .kpi { display:flex; flex-direction:column; gap:0.25rem; }
  .kpi .label { color:#4b4b4b; font-size:0.85rem; }
  .kpi .value { font-size:1.6rem; font-weight:700; color:#2b1b6b; }
</style>
""", unsafe_allow_html=True)

st.title("🎥 FreeFuse Interactive Engagement Dashboard")

# ---------------------------  DATA FILES  ---------------------------
WATCH_HISTORY_FILE = "Main Nodes Watch History 2022-2024 School Year.xlsx"
VIDEO_COUNTS_FILE  = "Video Counts 2022-2024.xlsx"
PARENT_CHILD_FILE  = "Watched_Durations_Parent_And_ChildVideos.xlsx"

# ---------------------------  HELPER FUNCTIONS  ---------------------------
@st.cache_data(show_spinner=False)
def read_xlsx(path: str, sheet_name: Optional[str] = None) -> pd.DataFrame:
    return pd.read_excel(path, sheet_name=sheet_name)

def normalize_minutes(series: pd.Series) -> pd.Series:
    s = pd.to_numeric(series, errors="coerce")
    if s.dropna().median() > 200:
        s = s / 60.0
    return s

def ensure_datetime(date_col: pd.Series, time_col: Optional[pd.Series] = None) -> pd.Series:
    if time_col is not None:
        ts = pd.to_datetime(date_col.astype(str) + " " + time_col.astype(str), errors="coerce")
    else:
        ts = pd.to_datetime(date_col, errors="coerce")
    return ts

def am_pm_from_hour(h: int) -> str:
    try:
        h = int(h)
    except Exception:
        return "Unknown"
    return "AM" if 0 <= h < 12 else "PM"

def fmt_int(n):
    try:
        return f"{int(n):,}"
    except Exception:
        return "—"

# ---------------------------  LOAD DATA  ---------------------------
try:
    watch = read_xlsx(WATCH_HISTORY_FILE)
    counts = read_xlsx(VIDEO_COUNTS_FILE)
    pc = read_xlsx(PARENT_CHILD_FILE)
except Exception as e:
    st.error(f"❌ Could not load files: {e}")
    st.stop()

# ---------------------------  CLEAN WATCH HISTORY  ---------------------------

# Make sure we really have a DataFrame
if not isinstance(watch, pd.DataFrame):
    st.error("❌ The Watch History file could not be read as a table.")
    st.stop()

# Normalize column names for flexible matching
watch.columns = [c.strip().lower().replace(" ", "_") for c in watch.columns]

# Auto-detect possible date/time and duration columns
date_cols = [c for c in watch.columns if "date" in c or "day" in c or "timestamp" in c]
time_cols = [c for c in watch.columns if "time" in c or "hour" in c]
dur_cols = [c for c in watch.columns if "duration" in c or "watch" in c or "length" in c]

# Create datetime and derived columns
if date_cols:
    date_col = date_cols[0]
    if time_cols:
        watch["ts"] = ensure_datetime(watch[date_col], watch[time_cols[0]])
    else:
        watch["ts"] = pd.to_datetime(watch[date_col], errors="coerce")
else:
    # No date column found
    st.error("⚠️ No date-like column found in your Watch History file.")
    st.stop()

watch["date"] = pd.to_datetime(watch["ts"], errors="coerce").dt.date
watch["month"] = pd.to_datetime(watch["ts"], errors="coerce").dt.to_period("M").dt.to_timestamp()
watch["hour"] = pd.to_datetime(watch["ts"], errors="coerce").dt.hour
watch["am_pm"] = watch["hour"].apply(am_pm_from_hour)
watch["dow"] = pd.to_datetime(watch["ts"], errors="coerce").dt.day_name()

# Convert durations to minutes
if dur_cols:
    watch["duration_min"] = normalize_minutes(watch[dur_cols[0]])
else:
    watch["duration_min"] = np.nan

# ---------------------------  FILTERS  ---------------------------
st.sidebar.header("📊 Filters")
if "date" in watch.columns:
    dmin, dmax = watch["date"].min(), watch["date"].max()
else:
    dmin = dmax = pd.Timestamp.today()
date_range = st.sidebar.date_input("Date Range", (dmin, dmax))
start_date, end_date = date_range if isinstance(date_range, tuple) else (dmin, dmax)
f = watch[(pd.to_datetime(watch["date"]) >= pd.to_datetime(start_date)) &
          (pd.to_datetime(watch["date"]) <= pd.to_datetime(end_date))].copy()

pick_ampm = st.sidebar.radio("Time of Day", ["Both", "AM", "PM"], index=0, horizontal=True)
if pick_ampm != "Both":
    f = f[f["am_pm"] == pick_ampm]

# ---------------------------  KPIs  ---------------------------
st.subheader("📌 Key Metrics")
k1, k2, k3, k4, k5 = st.columns(5)

total_views = len(f)
unique_viewers = f["viewer_id"].nunique() if "viewer_id" in f else 0
videos_watched = f["video_id"].nunique() if "video_id" in f else 0
avg_duration = f["duration_min"].mean() if "duration_min" in f else 0

monthly = f.groupby("month").size().rename("views").reset_index()
most_month = "—"
if not monthly.empty:
    peak = monthly.sort_values("views", ascending=False).head(1)
    most_month = peak["month"].dt.strftime("%b %Y").iloc[0]

with k1:
    st.markdown(f'<div class="card kpi"><div class="label">Total Views</div><div class="value">{fmt_int(total_views)}</div></div>', unsafe_allow_html=True)
with k2:
    st.markdown(f'<div class="card kpi"><div class="label">Unique Viewers</div><div class="value">{fmt_int(unique_viewers)}</div></div>', unsafe_allow_html=True)
with k3:
    st.markdown(f'<div class="card kpi"><div class="label">Videos Watched</div><div class="value">{fmt_int(videos_watched)}</div></div>', unsafe_allow_html=True)
with k4:
    st.markdown(f'<div class="card kpi"><div class="label">Avg Duration (min)</div><div class="value">{avg_duration:.2f}</div></div>', unsafe_allow_html=True)
with k5:
    st.markdown(f'<div class="card kpi"><div class="label">Most Watched Month</div><div class="value">{most_month}</div></div>', unsafe_allow_html=True)

st.markdown("---")

# ---------------------------  TABS  ---------------------------
tab1, tab2, tab3, tab4 = st.tabs(["Overview", "Top Videos", "Duration Insights", "Time Heatmap"])

# ---------- TAB 1: Overview ----------
with tab1:
    col1, col2 = st.columns([2, 1])
    with col1:
        if not monthly.empty:
            fig = px.bar(monthly, x="month", y="views", title="Monthly Views", text_auto=True)
            fig.update_layout(xaxis_title="", yaxis_title="Views", height=400)
            st.plotly_chart(fig, use_container_width=True)
        daily = f.groupby("date").size().rename("views").reset_index()
        if not daily.empty:
            fig2 = px.line(daily, x="date", y="views", markers=True, title="Views Over Time")
            st.plotly_chart(fig2, use_container_width=True)
    with col2:
        ampm = f["am_pm"].value_counts()
        pie_df = pd.DataFrame({"Period": ["AM", "PM"],
                               "Views": [int(ampm.get("AM", 0)), int(ampm.get("PM", 0))]})
        fig3 = px.pie(pie_df, names="Period", values="Views", hole=0.5,
                      title="AM vs PM Engagement")
        st.plotly_chart(fig3, use_container_width=True)

# ---------- TAB 2: Top Videos ----------
with tab2:
    if "view_count" in counts.columns:
        cc = counts.dropna(subset=["view_count"]).copy()
        cc["video_label"] = cc["video_name"].fillna(cc["video_id"])
        mode = st.radio("Ranking", ["Most Watched", "Least Watched"], index=0, horizontal=True)
        if mode == "Most Watched":
            view = cc.sort_values("view_count", ascending=False).head(10)
        else:
            view = cc.sort_values("view_count", ascending=True).head(10)
        fig5 = px.bar(view, x="video_label", y="view_count",
                      title=f"Top 10 — {mode} Videos")
        st.plotly_chart(fig5, use_container_width=True)
        st.dataframe(view[["video_id", "video_name", "view_count"]],
                     use_container_width=True, hide_index=True)
    else:
        st.info("No 'view_count' column found in Video Counts dataset.")

# ---------- TAB 3: Duration Insights ----------
with tab3:
    col1, col2 = st.columns(2)
    with col1:
        if "duration_min" in f:
            fig7 = px.histogram(f, x="duration_min", nbins=30,
                                title="Viewing Duration Distribution (min)")
            st.plotly_chart(fig7, use_container_width=True)
    with col2:
        if "parent_or_child" in pc.columns:
            box = pc.dropna(subset=["parent_or_child", "duration_min"])
            if not box.empty:
                fig8 = px.box(box, x="parent_or_child", y="duration_min",
                              points="suspectedoutliers",
                              title="Duration by Video Type (Parent vs Child)")
                st.plotly_chart(fig8, use_container_width=True)

# ---------- TAB 4: Time Heatmap ----------
with tab4:
    if not f.empty:
        f["hour"] = f["hour"].fillna(0).astype(int)
        order = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
        f["dow"] = pd.Categorical(f["dow"], categories=order, ordered=True)
        heat = f.pivot_table(index="dow", columns="hour", values="video_id", aggfunc="count", fill_value=0)
        fig10 = px.imshow(heat, aspect="auto", title="Engagement Heatmap (Day × Hour)")
        st.plotly_chart(fig10, use_container_width=True)
    else:
        st.info("No data to display in heatmap.")

# ---------------------------  DOWNLOAD  ---------------------------
st.markdown("---")
st.download_button("📥 Download Filtered Data (CSV)",
                   f.to_csv(index=False).encode("utf-8"),
                   "freefuse_filtered.csv",
                   "text/csv")

