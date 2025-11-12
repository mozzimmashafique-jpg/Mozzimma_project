import math
from typing import Optional, List

import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

st.set_page_config(page_title="FreeFuse Engagement Dashboard — v2", page_icon="📊", layout="wide")

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


st.title(\"🎥 FreeFuse Interactive Engagement Dashboard\")

WATCH_HISTORY_FILE = \"Main Nodes Watch History 2022-2024 School Year.xlsx\"
VIDEO_COUNTS_FILE  = \"Video Counts 2022-2024.xlsx\"
PARENT_CHILD_FILE  = \"Watched_Durations_Parent_And_ChildVideos.xlsx\"

@st.cache_data(show_spinner=False)
def read_xlsx(path: str, sheet_name: Optional[str]=None) -> pd.DataFrame:
    return pd.read_excel(path, sheet_name=sheet_name)

def normalize_minutes(series: pd.Series) -> pd.Series:
    s = pd.to_numeric(series, errors=\"coerce\")
    if s.dropna().median() > 200:
        s = s / 60.0
    return s

def ensure_datetime(date_col: pd.Series, time_col: Optional[pd.Series]=None) -> pd.Series:
    if time_col is not None:
        ts = pd.to_datetime(date_col.astype(str) + \" \" + time_col.astype(str), errors=\"coerce\")
    else:
        ts = pd.to_datetime(date_col, errors=\"coerce\")
    return ts

def am_pm_from_hour(h: int) -> str:
    try:
        h = int(h)
    except Exception:
        return \"Unknown\"
    return \"AM\" if 0 <= h < 12 else \"PM\"

def fmt_int(n):
    try:
        return f\"{int(n):,}\"
    except Exception:
        return \"—\"

try:
    watch_raw = read_xlsx(WATCH_HISTORY_FILE)
    counts_raw = read_xlsx(VIDEO_COUNTS_FILE)
    pc_raw = read_xlsx(PARENT_CHILD_FILE)
except Exception as e:
    st.error(f\"Failed to load one or more files: {e}\")
    st.stop()

watch_cols = {c.lower().strip(): c for c in watch_raw.columns}
counts_cols = {c.lower().strip(): c for c in counts_raw.columns}
pc_cols = {c.lower().strip(): c for c in pc_raw.columns}

def get_col(mapping, *names):
    for n in names:
        key = n.lower()
        if key in mapping:
            return mapping[key]
    return None

w_video_id = get_col(watch_cols, \"video_id\")
w_title    = get_col(watch_cols, \"video_name\", \"title\", \"name\")
w_date     = get_col(watch_cols, \"date\", \"view_date\", \"viewerchoices_viewdate\")
w_time     = get_col(watch_cols, \"time\", \"view_time\", \"viewerchoices_viewtime\")
w_duration = get_col(watch_cols, \"duration\", \"viewing_duration_min\", \"viewing_duration\", \"viewerchoices_viewingduration\")
w_viewer   = get_col(watch_cols, \"viewer\", \"videoviewer\", \"user_id\", \"viewer_id\")
w_owner    = get_col(watch_cols, \"owner\", \"videoowner\", \"owner_id\")
w_done     = get_col(watch_cols, \"done\", \"completed\", \"done_viewing\", \"viewerchoices_doneviewing\")
w_category = get_col(watch_cols, \"category\", \"module\", \"topic\", \"tag\")

watch = pd.DataFrame()
watch[\"video_id\"] = watch_raw[w_video_id] if w_video_id else pd.NA
watch[\"video_name\"] = watch_raw[w_title] if w_title else pd.NA
watch[\"ts\"] = ensure_datetime(watch_raw[w_date], watch_raw[w_time]) if w_date else pd.to_datetime(pd.NaT)
watch[\"date\"] = pd.to_datetime(watch[\"ts\"], errors=\"coerce\").dt.date
watch[\"hour\"] = pd.to_datetime(watch[\"ts\"], errors=\"coerce\").dt.hour
watch[\"dow\"] = pd.to_datetime(watch[\"ts\"], errors=\"coerce\").dt.day_name
watch[\"duration_min\"] = normalize_minutes(watch_raw[w_duration]) if w_duration else np.nan
watch[\"viewer_id\"] = watch_raw[w_viewer] if w_viewer else pd.NA
watch[\"owner_id\"] = watch_raw[w_owner] if w_owner else pd.NA
if w_done:
    done_norm = watch_raw[w_done].astype(str).str.strip().str.lower().map(
        {\"yes\":True,\"true\":True,\"1\":True,\"y\":True,\"completed\":True,
         \"no\":False,\"false\":False,\"0\":False,\"n\":False,\"not completed\":False}
    )
    watch[\"done\"] = done_norm
else:
    watch[\"done\"] = np.nan
watch[\"category\"] = watch_raw[w_category] if w_category else pd.NA
watch = watch.dropna(subset=[\"date\"]).copy()

c_video_id = get_col(counts_cols, \"video_id\")
c_title    = get_col(counts_cols, \"video_name\", \"title\", \"name\")
c_views    = get_col(counts_cols, \"view_count\", \"views\", \"count\", \"total_views\")
counts = pd.DataFrame()
counts[\"video_id\"] = counts_raw[c_video_id] if c_video_id else pd.NA
counts[\"video_name\"] = counts_raw[c_title] if c_title else pd.NA
counts[\"view_count\"] = pd.to_numeric(counts_raw[c_views], errors=\"coerce\") if c_views else np.nan

p_video_id = get_col(pc_cols, \"video_id\")
p_title    = get_col(pc_cols, \"video_name\", \"title\", \"name\")
p_type     = get_col(pc_cols, \"parent_or_child\", \"type\", \"level\", \"parentchild\")
p_duration = get_col(pc_cols, \"duration\", \"viewing_duration_min\", \"viewing_duration\")
p_category = get_col(pc_cols, \"category\", \"module\", \"topic\", \"tag\")
p_date     = get_col(pc_cols, \"date\", \"view_date\")
p_time     = get_col(pc_cols, \"time\", \"view_time\")

pc = pd.DataFrame()
pc[\"video_id\"] = pc_raw[p_video_id] if p_video_id else pd.NA
pc[\"video_name\"] = pc_raw[p_title] if p_title else pd.NA
pc[\"parent_or_child\"] = pc_raw[p_type] if p_type else pd.NA
pc[\"duration_min\"] = normalize_minutes(pc_raw[p_duration]) if p_duration else np.nan
pc[\"category\"] = pc_raw[p_category] if p_category else pd.NA
pc[\"ts\"] = ensure_datetime(pc_raw[p_date], pc_raw[p_time]) if p_date else pd.to_datetime(pd.NaT)
pc[\"date\"] = pd.to_datetime(pc[\"ts\"], errors=\"coerce\").dt.date

merge_key = \"video_id\" if watch[\"video_id\"].notna().any() and counts[\"video_id\"].notna().any() else \"video_name\"
if counts.dropna(subset=[merge_key]).empty:
    watch[\"view_count\"] = np.nan
else:
    watch = watch.merge(counts[[merge_key, \"view_count\"]].dropna(), on=merge_key, how=\"left\")

if not pc.dropna(subset=[merge_key]).empty:
    meta_cols = [c for c in [\"parent_or_child\",\"category\"] if c in pc.columns]
    watch = watch.merge(pc[[merge_key]+meta_cols].drop_duplicates(), on=merge_key, how=\"left\")

watch[\"month\"] = pd.to_datetime(watch[\"date\"], errors=\"coerce\").to_period(\"M\").dt.to_timestamp()
watch[\"am_pm\"] = watch[\"hour\"].apply(am_pm_from_hour)
watch[\"is_owner_view\"] = watch[\"viewer_id\"].astype(str) == watch[\"owner_id\"].astype(str)

rep_key = \"video_id\" if watch[\"video_id\"].notna().any() else \"video_name\"
rep = watch.groupby([\"viewer_id\", rep_key]).size().rename(\"plays_user_video\").reset_index()
watch = watch.merge(rep, on=[\"viewer_id\", rep_key], how=\"left\")

st.sidebar.header(\"Filters\")
if watch[\"date\"].notna().any():
    dmin = pd.to_datetime(watch[\"date\"]).min().date()
    dmax = pd.to_datetime(watch[\"date\"]).max().date()
else:
    dmin = dmax = pd.to_datetime(\"today\").date()
date_range = st.sidebar.date_input(\"Date range\", (dmin, dmax))
start_date, end_date = date_range if isinstance(date_range, tuple) else (dmin, dmax)

f = watch[(pd.to_datetime(watch[\"date\"]) >= pd.to_datetime(start_date)) & (pd.to_datetime(watch[\"date\"]) <= pd.to_datetime(end_date))]

if \"category\" in f.columns and f[\"category\"].notna().any():
    cats = [\"All\"] + sorted([c for c in f[\"category\"].dropna().unique().tolist() if str(c).strip()])
    pick_cat = st.sidebar.selectbox(\"Category / Module\", cats, index=0)
    if pick_cat != \"All\":
        f = f[f[\"category\"] == pick_cat]

if \"parent_or_child\" in f.columns and f[\"parent_or_child\"].notna().any():
    poc = [\"All\"] + sorted(f[\"parent_or_child\"].dropna().unique().tolist())
    pick_poc = st.sidebar.selectbox(\"Parent vs Child\", poc, index=0)
    if pick_poc != \"All\":
        f = f[f[\"parent_or_child\"] == pick_poc]

pick_ampm = st.sidebar.radio(\"Time of day\", [\"Both\",\"AM\",\"PM\"], index=0, horizontal=True)
if pick_ampm != \"Both\":
    f = f[f[\"am_pm\"] == pick_ampm]

vid_names = sorted([v for v in f[\"video_name\"].dropna().unique().tolist() if str(v).strip()])
picked_videos = st.sidebar.multiselect(\"Videos\", vid_names, default=[])
if picked_videos:
    f = f[f[\"video_name\"].isin(picked_videos)]

st.sidebar.write(\"Min views (tables)\")
min_views = st.sidebar.slider(\"\", 0, 100, 0, 1)

st.subheader(\"📌 Key Metrics\")
k1,k2,k3,k4,k5 = st.columns(5)

total_views = len(f)
unique_viewers = f[\"viewer_id\"].nunique()
videos_watched = f[\"video_name\"].nunique()
avg_duration = pd.to_numeric(f[\"duration_min\"], errors=\"coerce\").mean()

monthly = f.groupby(\"month\").size().rename(\"views\").reset_index()
if not monthly.empty:
    peak = monthly.sort_values(\"views\", ascending=False).head(1)
    most_month = peak[\"month\"].dt.strftime(\"%b %Y\").iloc[0]
else:
    most_month = \"—\"

st.markdown(f'<div class=\"card kpi\"><div class=\"label\">Total Views</div><div class=\"value\">{fmt_int(total_views)}</div></div>', unsafe_allow_html=True)
with k2:
    st.markdown(f'<div class=\"card kpi\"><div class=\"label\">Unique Viewers</div><div class=\"value\">{fmt_int(unique_viewers)}</div></div>', unsafe_allow_html=True)
with k3:
    st.markdown(f'<div class=\"card kpi\"><div class=\"label\">Videos Watched</div><div class=\"value\">{fmt_int(videos_watched)}</div></div>', unsafe_allow_html=True)
with k4:
    st.markdown(f'<div class=\"card kpi\"><div class=\"label\">Avg Duration (min)</div><div class=\"value\">{(f\"{avg_duration:.2f}\" if not math.isnan(avg_duration) else \"—\")}</div></div>', unsafe_allow_html=True)
with k5:
    st.markdown(f'<div class=\"card kpi\"><div class=\"label\">Most Watched Month</div><div class=\"value\">{most_month}</div></div>', unsafe_allow_html=True)

st.markdown(\"---\")

tab1, tab2, tab3, tab4, tab5 = st.tabs([
    \"Overview\",
    \"Top Videos (Counts)\",
    \"Completion & Duration\",
    \"Time Heatmap\",
    \"Owner vs Viewer\",
])

with tab1:
    left, right = st.columns([2,1], gap=\"large\")
    with left:
        if not monthly.empty:
            fig = px.bar(monthly, x=\"month\", y=\"views\", title=\"Monthly Views\", text_auto=True)
            fig.update_layout(xaxis_title=\"\", yaxis_title=\"Views\", height=420)
            st.plotly_chart(fig, use_container_width=True)

        daily = f.groupby(\"date\").size().rename(\"views\").reset_index()
        if not daily.empty:
            fig2 = px.line(daily, x=\"date\", y=\"views\", markers=True, title=\"Views Over Time\")
            fig2.update_layout(xaxis_title=\"Date\", yaxis_title=\"Views\", height=420)
            st.plotly_chart(fig2, use_container_width=True)
    with right:
        ampm = f[\"am_pm\"].value_counts()
        pie_df = pd.DataFrame({\"Period\":[\"AM\",\"PM\"], \"Views\":[int(ampm.get(\"AM\",0)), int(ampm.get(\"PM\",0))]})
        fig3 = px.pie(pie_df, names=\"Period\", values=\"Views\", hole=0.5, title=\"AM vs PM Engagement\")
        st.plotly_chart(fig3, use_container_width=True)

        mdur = f.groupby(\"month\")[\"duration_min\"].mean().reset_index()
        if not mdur.empty:
            fig4 = px.line(mdur, x=\"month\", y=\"duration_min\", markers=True, title=\"Avg Duration by Month\")
            fig4.update_layout(xaxis_title=\"\", yaxis_title=\"Avg duration (min)\", height=360)
            st.plotly_chart(fig4, use_container_width=True)

with tab2:
    if \"view_count\" in counts_raw.columns or \"view_count\" in counts.columns:
        # ensure counts df normalized
        cc = pd.DataFrame(counts)
        cc[\"video_label\"] = cc[\"video_name\"].fillna(cc[\"video_id\"])
        cc = cc.dropna(subset=[\"view_count\"]).copy()
        mode = st.radio(\"Ranking\", [\"Most Watched\",\"Least Watched\"], index=0, horizontal=True)
        if mode == \"Most Watched\":
            view = cc.sort_values(\"view_count\", ascending=False).head(10)
        else:
            view = cc.sort_values(\"view_count\", ascending=True).head(10)
        fig5 = px.bar(view, x=\"video_label\", y=\"view_count\", title=f\"Top 10 — {mode} (Video Counts)\")
        fig5.update_layout(xaxis_title=\"Video\", yaxis_title=\"View count\", height=520)
        st.plotly_chart(fig5, use_container_width=True)
        st.dataframe(view[[\"video_id\",\"video_name\",\"view_count\"]], use_container_width=True, hide_index=True)
    else:
        st.info(\"Video Counts file has no 'view_count' detected.\")

with tab3:
    c1, c2 = st.columns([1,1], gap=\"large\")
    with c1:
        if \"done\" in f.columns and f[\"done\"].notna().any():
            counts_done = f[\"done\"].value_counts(dropna=False)
            pie = pd.DataFrame({
                \"Status\": [\"Completed\" if k is True else (\"Not Completed\" if k is False else \"Unknown\") for k in counts_done.index],
                \"Count\": counts_done.values
            })
            fig6 = px.pie(pie, names=\"Status\", values=\"Count\", title=\"Completion Breakdown\")
            st.plotly_chart(fig6, use_container_width=True)
        if \"duration_min\" in f:
            fig7 = px.histogram(f, x=\"duration_min\", nbins=30, title=\"Viewing Duration Distribution (min)\")
            fig7.update_layout(xaxis_title=\"Duration (min)\", yaxis_title=\"Frequency\", height=420)
            st.plotly_chart(fig7, use_container_width=True)
    with c2:
        if \"parent_or_child\" in f.columns and f[\"parent_or_child\"].notna().any():
            box = f.dropna(subset=[\"parent_or_child\",\"duration_min\"])
            if not box.empty:
                fig8 = px.box(box, x=\"parent_or_child\", y=\"duration_min\", points=\"suspectedoutliers\",
                              title=\"Duration by Video Type (Parent vs Child)\")
                fig8.update_layout(xaxis_title=\"\", yaxis_title=\"Duration (min)\", height=420)
                st.plotly_chart(fig8, use_container_width=True)
        if \"category\" in f.columns and f[\"category\"].notna().any():
            cat = f.groupby(\"category\")[\"duration_min\"].mean().reset_index().sort_values(\"duration_min\", ascending=False)
            if not cat.empty:
                fig9 = px.bar(cat, x=\"category\", y=\"duration_min\", title=\"Avg Duration by Category/Module\")
                fig9.update_layout(xaxis_title=\"\", yaxis_title=\"Avg duration (min)\", height=420)
                st.plotly_chart(fig9, use_container_width=True)

with tab4:
    if not f.empty:
        order = [\"Monday\",\"Tuesday\",\"Wednesday\",\"Thursday\",\"Friday\",\"Saturday\",\"Sunday\"]
        tmp = f.copy()
        tmp[\"dow\"] = pd.Categorical(tmp[\"dow\"], categories=order, ordered=True)
        heat = tmp.pivot_table(index=\"dow\", columns=\"hour\", values=\"video_name\", aggfunc=\"count\", fill_value=0)
        fig10 = px.imshow(heat, aspect=\"auto\", title=\"Engagement Heatmap (Day of Week × Hour)\")
        st.plotly_chart(fig10, use_container_width=True)
    else:
        st.info(\"No data to show.\")

with tab5:
    if \"is_owner_view\" in f.columns:
        grp = f.groupby(\"is_owner_view\").agg(
            views=(\"video_name\",\"count\"),
            mean_duration=(\"duration_min\",\"mean\"),
            repeat_share=(\"plays_user_video\", lambda s: (s>1).mean() if s.notna().any() else np.nan),
        ).reset_index()
        grp[\"Viewer Type\"] = grp[\"is_owner_view\"].map({True:\"Owner viewing own video\", False:\"Other viewers\"})
        grp[\"Repeat %\"] = (grp[\"repeat_share\"]*100).round(1)
        show = grp[[\"Viewer Type\",\"views\",\"mean_duration\",\"Repeat %\"]].rename(columns={\"views\":\"Views\",\"mean_duration\":\"Avg Duration (min)\"})
        st.dataframe(show, use_container_width=True, hide_index=True)
        fig11 = px.bar(show, x=\"Viewer Type\", y=\"Avg Duration (min)\", title=\"Avg Duration — Owner vs Others\")
        fig11.update_layout(xaxis_title=\"\", yaxis_title=\"Minutes\", height=420)
        st.plotly_chart(fig11, use_container_width=True)
    else:
        st.info(\"Missing owner/viewer IDs for comparison.\")

st.markdown(\"---\")
st.download_button(
    \"📥 Download Filtered Rows (CSV)\",
    f.to_csv(index=False).encode(\"utf-8\"),
    \"freefuse_filtered.csv\",
    \"text/csv\",
)
""")
code_path
