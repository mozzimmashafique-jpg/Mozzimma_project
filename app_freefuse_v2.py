
import math
import re
from typing import Dict, List, Optional

import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

# ========================================
# Page config & styles
# ========================================
st.set_page_config(page_title="FreeFuse Engagement Dashboard (v2)", page_icon="📊", layout="wide")
st.markdown(
    """
    <style>
      [data-testid="stSidebar"] { background-color:#f4f1fb; }
      h1,h2,h3{ color:#3b0764; }
      .stMetric label{ font-weight:600; color:#3b0764; }
      .muted { color:#5b5b5b; font-size:0.9rem; }
    </style>
    """,
    unsafe_allow_html=True,
)
st.title("📊 FreeFuse Interactive Engagement Dashboard — v2")
st.caption("Unified from Watch History, Video Counts, and Parent/Child Durations datasets.")

# ========================================
# Helpers
# ========================================
def norm(s: str) -> str:
    return re.sub(r"[^a-z0-9]+", "", str(s).strip().lower())

def pick_col(df: pd.DataFrame, candidates: List[str]) -> Optional[str]:
    """Fuzzy-pick a column name by exact, normalized, then 'contains' match."""
    if df is None or df.empty:
        return None
    cols = list(df.columns)
    # exact
    for c in candidates:
        if c in cols:
            return c
    target_norms = [norm(c) for c in candidates]
    name_by_norm = {norm(c): c for c in cols}
    for t in target_norms:
        if t in name_by_norm:
            return name_by_norm[t]
    for c in cols:
        nc = norm(c)
        if any(t in nc for t in target_norms):
            return c
    return None

def clean_title_series(s: pd.Series) -> pd.Series:
    s = s.astype(str).str.strip()
    keep = s.str.replace(r"[^0-9A-Za-z]+", "", regex=True).str.len() > 0
    return s.where(keep)

def to_minutes(x):
    try:
        v = pd.to_numeric(x, errors="coerce")
        return v / 60.0
    except Exception:
        return np.nan

def pct(n):
    return None if pd.isna(n) else f"{n*100:.1f}%"

# ========================================
# Sidebar: data ingestion
# ========================================
st.sidebar.header("1) Load datasets")

st.sidebar.caption("Upload the three Excel files. If left empty, the app will try reading preloaded files by name.")

file_watch = st.sidebar.file_uploader("Watch History (2022–2024)", type=["xlsx"], key="watch")
file_counts = st.sidebar.file_uploader("Video Counts (2022–2024)", type=["xlsx"], key="counts")
file_parent = st.sidebar.file_uploader("Watched_Durations_Parent_And_ChildVideos", type=["xlsx"], key="parent")

# Fallback to pre-mounted files if present
fallback_watch = "Main Nodes Watch History 2022-2024 School Year.xlsx"
fallback_counts = "Video Counts 2022-2024.xlsx"
fallback_parent = "Watched_Durations_Parent_And_ChildVideos.xlsx"

@st.cache_data(show_spinner=False)
def read_excel_flex(upload, fallback_name: str):
    if upload is not None:
        return pd.read_excel(upload)
    try:
        return pd.read_excel(fallback_name)
    except Exception:
        return None

watch_df = read_excel_flex(file_watch, fallback_watch)
counts_df = read_excel_flex(file_counts, fallback_counts)
parent_df = read_excel_flex(file_parent, fallback_parent)

if watch_df is None:
    st.error("Please upload the **Watch History** file (or ensure it exists on disk).")
    st.stop()

# ========================================
# Column mapping
# ========================================
st.sidebar.header("2) Map columns")

def map_columns_ui(df, title, spec: Dict[str, List[str]]):
    st.sidebar.subheader(title)
    mapping = {}
    for key, cands in spec.items():
        options = ["—"] + list(df.columns)
        default = 0
        # preselect best guess
        guess = pick_col(df, cands)
        if guess and guess in df.columns:
            default = options.index(guess) if guess in options else 0
        mapping[key] = st.sidebar.selectbox(f"{key}", options, index=default, key=f"{title}-{key}")
    return {k: (None if v == "—" else v) for k, v in mapping.items()}

# Watch history mapping
watch_spec = {
    "video_name": ["viewerChoices_VideoName","Video_Name","VideoName","video name","viewerChoices video name"],
    "viewer_id":  ["videoViewer","Viewer","User","Student","viewer id"],
    "owner_id":   ["videoOwner","Owner","Instructor"],
    "date":       ["viewerChoices_ViewDate","View_Date","ViewDate","Date"],
    "time":       ["viewerChoices_ViewTime","View_Time","ViewTime","Time"],
    "duration_s": ["viewerChoices_ViewingDuration","Viewing_Duration_Sec","ViewingDuration","Duration","Duration_Seconds"],
    "done":       ["viewerChoices_DoneViewing","Done_Viewing","Done","Completed","Completion"],
    "video_id":   ["viewerChoices_VideoId","VideoID","Video_Id","video id","id"],
}
watch_map = map_columns_ui(watch_df, "Watch History columns", watch_spec)

# Video counts mapping
counts_spec = {
    "video_id":   ["VideoID","Video_Id","viewerChoices_VideoId","id","video id"],
    "video_name": ["Video_Name","VideoName","viewerChoices_VideoName","name","title"],
    "view_count": ["Count","Views","View_Count","Total_Views","n"],
}
if counts_df is not None:
    counts_map = map_columns_ui(counts_df, "Video Counts columns", counts_spec)
else:
    counts_map = {}

# Parent/Child mapping
parent_spec = {
    "parent_or_child": ["Type","Level","ParentChild","parent_child","is_parent","Parent/Child"],
    "video_id":        ["VideoID","Video_Id","viewerChoices_VideoId","id","video id"],
    "video_name":      ["Video_Name","VideoName","viewerChoices_VideoName","name","title"],
    "category":        ["Category","Topic","Module","Tag","Tags"],
    "date":            ["ViewDate","Date","viewerChoices_ViewDate"],
    "time":            ["ViewTime","Time","viewerChoices_ViewTime"],
    "duration_s":      ["ViewingDuration","Duration_Sec","Duration","viewerChoices_ViewingDuration"],
    "viewer_id":       ["Viewer","User","Student","videoViewer"],
}
if parent_df is not None:
    parent_map = map_columns_ui(parent_df, "Parent/Child columns", parent_spec)
else:
    parent_map = {}

# ========================================
# Standardize frames
# ========================================
def standardize_watch(df, m):
    w = pd.DataFrame(index=df.index)
    w["video_name"] = clean_title_series(df[m["video_name"]]) if m.get("video_name") else pd.NA
    if m.get("date") and m.get("time"):
        ts = pd.to_datetime(df[m["date"]].astype(str) + " " + df[m["time"]].astype(str), errors="coerce")
    elif m.get("date"):
        ts = pd.to_datetime(df[m["date"]], errors="coerce")
    else:
        ts = pd.NaT
    w["ts"] = ts
    w["date"] = pd.to_datetime(w["ts"], errors="coerce").dt.date
    w["hour"] = pd.to_datetime(w["ts"], errors="coerce").dt.hour
    w["dow"] = pd.to_datetime(w["ts"], errors="coerce").dt.day_name()
    w["viewer_id"] = df[m["viewer_id"]] if m.get("viewer_id") else pd.NA
    w["owner_id"] = df[m["owner_id"]] if m.get("owner_id") else pd.NA
    w["video_id"] = df[m["video_id"]] if m.get("video_id") else pd.NA
    w["duration_min"] = to_minutes(df[m["duration_s"]]) if m.get("duration_s") else np.nan
    if m.get("done"):
        done = df[m["done"]].astype(str).str.strip().str.lower().map(
            {"yes":True,"true":True,"1":True,"y":True,"completed":True,
             "no":False,"false":False,"0":False,"n":False,"not completed":False}
        )
        w["done"] = done
    else:
        w["done"] = np.nan
    w = w.dropna(subset=["video_name","date"])
    w = w[pd.to_numeric(w["duration_min"], errors="coerce") > 0]
    return w.copy()

def standardize_counts(df, m):
    if df is None or not m:
        return None
    c = pd.DataFrame(index=df.index)
    c["video_id"]   = df[m["video_id"]] if m.get("video_id") else pd.NA
    c["video_name"] = clean_title_series(df[m["video_name"]]) if m.get("video_name") else pd.NA
    c["view_count"] = pd.to_numeric(df[m["view_count"]], errors="coerce") if m.get("view_count") else np.nan
    c = c.dropna(subset=["video_name"])
    return c.copy()

def standardize_parent(df, m):
    if df is None or not m:
        return None
    p = pd.DataFrame(index=df.index)
    p["video_id"]   = df[m["video_id"]] if m.get("video_id") else pd.NA
    p["video_name"] = clean_title_series(df[m["video_name"]]) if m.get("video_name") else pd.NA
    p["parent_or_child"] = df[m["parent_or_child"]] if m.get("parent_or_child") else pd.NA
    p["category"]   = df[m["category"]] if m.get("category") else pd.NA
    # optional ts
    if m.get("date") and m.get("time"):
        ts = pd.to_datetime(df[m["date"]].astype(str) + " " + df[m["time"]].astype(str), errors="coerce")
    elif m.get("date"):
        ts = pd.to_datetime(df[m["date"]], errors="coerce")
    else:
        ts = pd.NaT
    p["ts"] = ts
    p["duration_min"] = to_minutes(df[m["duration_s"]]) if m.get("duration_s") else np.nan
    p["viewer_id"] = df[m["viewer_id"]] if m.get("viewer_id") else pd.NA
    p = p.dropna(subset=["video_name"])
    return p.copy()

watch = standardize_watch(watch_df, watch_map)
counts = standardize_counts(counts_df, counts_map)
parent = standardize_parent(parent_df, parent_map)

# Merge counts (by name preferred, fallback to id)
if counts is not None and not counts.empty:
    key = "video_name" if "video_name" in counts.columns and counts["video_name"].notna().any() else "video_id"
    watch = watch.merge(counts[[key, "view_count"]], on=key, how="left")

# Merge parent/child meta
if parent is not None and not parent.empty:
    join_cols = ["video_name","video_id"]
    use_cols = [c for c in join_cols if c in parent.columns]
    meta_cols = [c for c in ["parent_or_child","category"] if c in parent.columns]
    watch = watch.merge(parent[use_cols + meta_cols].drop_duplicates(), on=use_cols, how="left")

# Derived fields
watch["month"] = pd.to_datetime(watch["date"]).astype("datetime64[M]")
watch["is_owner_view"] = watch["viewer_id"].astype(str) == watch["owner_id"].astype(str)
# repeat plays: per viewer per video
repeat = watch.groupby(["viewer_id","video_name"]).size().rename("plays_user_video").reset_index()
watch = watch.merge(repeat, on=["viewer_id","video_name"], how="left")

# ========================================
# Sidebar: filters
# ========================================
st.sidebar.header("3) Filters")

# date
if watch["date"].notna().any():
    dmin = pd.to_datetime(watch["date"]).min().date()
    dmax = pd.to_datetime(watch["date"]).max().date()
else:
    dmin = dmax = pd.to_datetime("today").date()

date_range = st.sidebar.date_input("Date range", (dmin, dmax))
if isinstance(date_range, tuple) and len(date_range) == 2:
    start_date, end_date = date_range
else:
    start_date, end_date = dmin, dmax

f = watch[(pd.to_datetime(watch["date"]) >= pd.to_datetime(start_date)) & (pd.to_datetime(watch["date"]) <= pd.to_datetime(end_date))]

# category
if "category" in f.columns and f["category"].notna().any():
    cats = ["All"] + sorted([c for c in f["category"].dropna().unique().tolist() if str(c).strip()])
    pick_cat = st.sidebar.selectbox("Category / Module", cats, index=0)
    if pick_cat != "All":
        f = f[f["category"] == pick_cat]

# parent/child
if "parent_or_child" in f.columns and f["parent_or_child"].notna().any():
    poc = ["All"] + sorted(f["parent_or_child"].dropna().unique().tolist())
    pick_poc = st.sidebar.selectbox("Parent vs Child", poc, index=0)
    if pick_poc != "All":
        f = f[f["parent_or_child"] == pick_poc]

# owner vs viewer
owner_filter = st.sidebar.selectbox("Viewer type", ["All","Owner only","Non-owner only"], index=0)
if owner_filter == "Owner only":
    f = f[f["is_owner_view"] == True]
elif owner_filter == "Non-owner only":
    f = f[f["is_owner_view"] == False]

# min views threshold for leaderboard
min_views = st.sidebar.slider("Min views per video (for tables)", 0, 100, 0, 1)

# ========================================
# KPIs
# ========================================
st.subheader("📊 Key Metrics")
c1,c2,c3,c4,c5 = st.columns(5)

total_views = len(f)
unique_viewers = f["viewer_id"].nunique()
videos_watched = f["video_name"].nunique()
avg_duration = pd.to_numeric(f["duration_min"], errors="coerce").mean()
repeat_rate = (f["plays_user_video"] > 1).mean() if "plays_user_video" in f.columns else np.nan

c1.metric("Total Views", f"{total_views:,}")
c2.metric("Unique Viewers", f"{unique_viewers:,}")
c3.metric("Videos Watched", f"{videos_watched:,}")
c4.metric("Avg Duration (min)", f"{avg_duration:.2f}" if not math.isnan(avg_duration) else "—")
c5.metric("Repeat View Rate", f"{repeat_rate*100:.1f}%" if not pd.isna(repeat_rate) else "—")

# Peak month
monthly = f.groupby("month").agg(views=("video_name","count"),
                                 unique_viewers=("viewer_id","nunique"),
                                 avg_duration=("duration_min","mean")).reset_index()
if not monthly.empty:
    peak = monthly.sort_values("views", ascending=False).head(1)
    st.info(f"📈 Peak engagement month: **{peak['month'].dt.strftime('%b %Y').iloc[0]}** with **{int(peak['views'].iloc[0])}** views")

st.markdown("---")

# ========================================
# Tabs
# ========================================
tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs([
    "Overview",
    "Video Leaderboard",
    "Engagement Quality",
    "Repeat Viewing",
    "Time Heatmap",
    "Owner vs Viewer",
])

# -------- Overview --------
with tab1:
    colA, colB = st.columns([2,1], gap="large")

    with colA:
        if not monthly.empty:
            fig = px.line(monthly, x="month", y="views", markers=True, title="Monthly Views")
            fig.update_layout(height=420, xaxis_title="", yaxis_title="Views")
            st.plotly_chart(fig, use_container_width=True)

        daily = f.groupby("date").size().rename("views").reset_index()
        if not daily.empty:
            fig2 = px.area(daily, x="date", y="views", title="Daily Views")
            fig2.update_layout(height=420, xaxis_title="", yaxis_title="Views")
            st.plotly_chart(fig2, use_container_width=True)

    with colB:
        if "duration_min" in f:
            comp = pd.to_numeric(f["duration_min"], errors="coerce")
            st.metric("Median Duration (min)", f"{comp.median():.2f}")
            st.metric("P75 Duration (min)", f"{comp.quantile(0.75):.2f}")

# -------- Leaderboard --------
with tab2:
    agg = f.groupby(["video_name","category"] if "category" in f.columns else ["video_name"]).agg(
        views=("viewer_id","count"),
        unique_viewers=("viewer_id","nunique"),
        avg_duration=("duration_min","mean"),
        repeat_share=("plays_user_video", lambda s: (s>1).mean() if s.notna().any() else np.nan),
    ).reset_index()

    # attach counts table if present (by video_name)
    if "view_count" in f.columns and f["view_count"].notna().any():
        vc = f[["video_name","view_count"]].dropna().drop_duplicates()
        agg = agg.merge(vc, on="video_name", how="left")
    else:
        agg["view_count"] = np.nan

    agg = agg[agg["views"] >= min_views]
    agg["repeat_share_pct"] = (agg["repeat_share"]*100).round(1)

    st.caption("Sort columns; export below.")
    st.dataframe(agg.sort_values("views", ascending=False), use_container_width=True, hide_index=True)

    topn = st.slider("Top N videos", 3, 50, 10)
    fig4 = px.bar(
        agg.sort_values("views", ascending=False).head(topn),
        x="video_name", y="views",
        color=("category" if "category" in agg.columns else None),
        title="Top Videos by Views"
    )
    fig4.update_layout(xaxis_title="", yaxis_title="Views", height=520)
    st.plotly_chart(fig4, use_container_width=True)

    csv = agg.to_csv(index=False).encode("utf-8")
    st.download_button("Download leaderboard CSV", csv, file_name="video_leaderboard.csv", mime="text/csv")

# -------- Engagement Quality --------
with tab3:
    # If completion flag exists in watch, show completion distribution & scatter vs views
    if "done" in f.columns and f["done"].notna().any():
        st.subheader("Completion Breakdown")
        counts = f["done"].value_counts(dropna=False)
        pie = pd.DataFrame({
            "Status": ["Completed" if k is True else ("Not Completed" if k is False else "Unknown") for k in counts.index],
            "Count": counts.values
        })
        fig3 = px.pie(pie, names="Status", values="Count", title="Completion Breakdown")
        st.plotly_chart(fig3, use_container_width=True)

    st.subheader("Viewing Duration Distribution (min)")
    fig5 = px.histogram(f, x="duration_min", nbins=30, title="Distribution of Viewing Duration")
    fig5.update_layout(xaxis_title="Duration (min)", yaxis_title="Frequency", height=520)
    st.plotly_chart(fig5, use_container_width=True)

    by_video = f.groupby(["video_name","category"] if "category" in f.columns else ["video_name"]).agg(
        avg_duration=("duration_min","mean"),
        q25=("duration_min", lambda s: s.quantile(0.25)),
        q75=("duration_min", lambda s: s.quantile(0.75)),
        views=("viewer_id","count"),
    ).reset_index()

    fig6 = px.scatter(
        by_video, x="views", y="avg_duration",
        hover_data=[c for c in ["video_name","category"] if c in by_video.columns],
        title="Avg Duration vs Views (per video)"
    )
    fig6.update_layout(xaxis_title="Views", yaxis_title="Avg duration (min)", height=520)
    st.plotly_chart(fig6, use_container_width=True)

# -------- Repeat Viewing --------
with tab4:
    if "plays_user_video" in f.columns:
        fig7 = px.histogram(f, x="plays_user_video", nbins=10, title="Plays per User per Video")
        fig7.update_layout(xaxis_title="Plays (user-video)", yaxis_title="Count", height=520)
        st.plotly_chart(fig7, use_container_width=True)

        rep = f.groupby("video_name").agg(
            pct_repeat=("plays_user_video", lambda s: (s>1).mean() if s.notna().any() else np.nan),
            views=("viewer_id","count"),
        ).reset_index()
        rep["pct_repeat"] = (rep["pct_repeat"]*100).round(1)

        fig8 = px.bar(
            rep.sort_values("pct_repeat", ascending=False).head(15),
            x="video_name", y="pct_repeat",
            title="Videos with Highest Repeat-View %"
        )
        fig8.update_layout(xaxis_title="Video", yaxis_title="Repeat view %", height=520)
        st.plotly_chart(fig8, use_container_width=True)
    else:
        st.info("Repeat viewing requires both viewer_id and video_name in watch history.")

# -------- Time Heatmap --------
with tab5:
    if not f.empty:
        order = ["Monday","Tuesday","Wednesday","Thursday","Friday","Saturday","Sunday"]
        tmp = f.copy()
        tmp["dow"] = pd.Categorical(tmp["dow"], categories=order, ordered=True)
        heat = tmp.pivot_table(index="dow", columns="hour", values="video_name", aggfunc="count", fill_value=0)
        heat = heat.sort_index()

        fig9 = px.imshow(heat, aspect="auto", title="Engagement Heatmap (Day of Week × Hour)")
        st.plotly_chart(fig9, use_container_width=True)

        # Simple peak detection
        daily = f.groupby("date").size().rename("views").reset_index()
        if len(daily) >= 7:
            daily["roll7"] = daily["views"].rolling(7, min_periods=1).mean()
            peaks = daily[daily["views"] >= daily["roll7"]*1.25]  # 25% above 7-day avg
            if not peaks.empty:
                st.success(f"Detected {len(peaks)} peak day(s) of engagement.")
                st.dataframe(peaks.sort_values('views', ascending=False), use_container_width=True, hide_index=True)

# -------- Owner vs Viewer --------
with tab6:
    if "is_owner_view" in f.columns:
        grp = f.groupby("is_owner_view").agg(
            views=("video_name","count"),
            mean_duration=("duration_min","mean"),
            repeat_share=("plays_user_video", lambda s: (s>1).mean() if s.notna().any() else np.nan),
        ).reset_index()
        grp["is_owner_view"] = grp["is_owner_view"].map({True:"Owner viewing own video", False:"Other viewers"})
        grp["repeat_share_pct"] = (grp["repeat_share"]*100).round(1)
        st.dataframe(grp, use_container_width=True, hide_index=True)

        fig10 = px.bar(grp, x="is_owner_view", y="mean_duration", title="Mean Duration: Owner vs Others")
        fig10.update_layout(xaxis_title="", yaxis_title="Mean duration (min)", height=420)
        st.plotly_chart(fig10, use_container_width=True)
    else:
        st.info("Owner vs Viewer comparison unavailable (missing owner/viewer IDs).")

# ========================================
# Downloads
# ========================================
st.markdown("---")
st.download_button(
    "📥 Download Filtered Rows (CSV)",
    f.to_csv(index=False).encode("utf-8"),
    "freefuse_filtered.csv",
    "text/csv",
)
