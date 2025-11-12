# app.py
import streamlit as st
import pandas as pd
import plotly.express as px
import re, unicodedata

# -------------------- PAGE STYLE --------------------
st.set_page_config(page_title="FreeFuse Engagement Dashboard", layout="wide")
st.markdown("""
<style>
  [data-testid="stSidebar"] { background-color:#f4f1fb; }
  h1,h2,h3{ color:#3b0764; }
  .stMetric label{ font-weight:600; color:#3b0764; }
</style>
""", unsafe_allow_html=True)

st.title("🎥 FreeFuse Engagement Dashboard")
st.caption("Interactive analytics on FreeFuse viewing behaviour (ASPIRA data).")

# -------------------- HELPERS --------------------
def norm(s: str) -> str:
    return re.sub(r'[^a-z0-9]+', '', str(s).strip().lower())

def pick_col(df: pd.DataFrame, candidates: list[str]) -> str | None:
    cols = list(df.columns)
    # exact
    for c in candidates:
        if c in cols: return c
    # normalized
    want_norm = [norm(c) for c in candidates]
    by_norm = {norm(c): c for c in cols}
    for t in want_norm:
        if t in by_norm: return by_norm[t]
    # contains
    for c in cols:
        nc = norm(c)
        if any(t in nc for t in want_norm): return c
    return None

def clean_title_series(s: pd.Series) -> pd.Series:
    """Remove garbled/symbol-only video titles and normalize spacing/encoding."""
    s = s.astype(str).str.strip()
    s = s.apply(lambda x: unicodedata.normalize('NFKC', x))
    s = s.str.replace(r'[^\x00-\x7F]+', '', regex=True)        # strip non-ascii junk/emojis
    s = s.str.replace(r'([^\w\s])\1+', r'\1', regex=True)      # collapse repeated punctuation
    s = s.str.replace(r'[_\-=~`^]+', ' ', regex=True)
    s = s.str.replace(r'\s+', ' ', regex=True).str.strip()
    # drop numeric/symbol-only strings like ". 1", "2:", "----"
    s = s.mask(s.str.match(r'^[\.\:\-\s0-9]+$'))
    keep_mask = s.str.replace(r'[^A-Za-z0-9]+', '', regex=True).str.len() > 1
    return s.where(keep_mask)

# -------------------- LOAD & CLEAN --------------------
@st.cache_data
def load_and_clean(path: str) -> pd.DataFrame:
    raw = pd.read_excel(path)
    raw.columns = raw.columns.str.strip()

    # map likely column names
    c_name  = pick_col(raw, ["viewerChoices_VideoName","Video_Name","VideoName","video name"])
    c_dur   = pick_col(raw, ["viewerChoices_ViewingDuration","Viewing_Duration_Sec","ViewingDuration","Duration","Duration_Seconds"])
    c_done  = pick_col(raw, ["viewerChoices_DoneViewing","Done_Viewing","Done","Completed","Completion"])
    c_date  = pick_col(raw, ["viewerChoices_ViewDate","View_Date","ViewDate","Date"])
    c_time  = pick_col(raw, ["viewerChoices_ViewTime","View_Time","ViewTime","Time"])
    c_viewr = pick_col(raw, ["videoViewer","Viewer","User","Student"])
    c_own   = pick_col(raw, ["videoOwner","Owner","Instructor"])
    c_qid   = pick_col(raw, ["questionnaireId","QuestionnaireId"])

    df = pd.DataFrame(index=raw.index)

    # core fields
    df["Video_Name"] = clean_title_series(raw[c_name]) if c_name else pd.NA

    # timestamp from (date + time)
    if c_date and c_time:
        ts = pd.to_datetime(raw[c_date].astype(str) + " " + raw[c_time].astype(str), errors="coerce")
    elif c_date:
        ts = pd.to_datetime(raw[c_date], errors="coerce")
    else:
        ts = pd.NaT
    df["View_Timestamp"] = ts
    df["View_Date"] = pd.to_datetime(ts, errors="coerce").dt.date
    df["Hour"] = pd.to_datetime(ts, errors="coerce").dt.hour
    df["Dow"]  = pd.to_datetime(ts, errors="coerce").dt.day_name()

    # duration to minutes
    df["Viewing_Duration_Min"] = pd.to_numeric(raw[c_dur], errors="coerce")/60.0 if c_dur else pd.NA

    # completion (use your corrected values; drop rows that are still blank/invalid)
    if c_done:
        val = raw[c_done].astype(str).str.strip().str.lower()
        yes_map = {"yes","true","1","y","completed"}
        no_map  = {"no","false","0","n","not completed"}
        def map_done(x):
            if x in yes_map: return True
            if x in no_map: return False
            return pd.NA
        df["Done_Viewing"] = val.map(map_done)
    else:
        df["Done_Viewing"] = pd.NA

    # viewer/owner & questionnaire
    df["Viewer"] = raw[c_viewr] if c_viewr else pd.NA
    df["Owner"]  = raw[c_own]   if c_own   else pd.NA
    df["questionnaireId"] = raw[c_qid] if c_qid else pd.NA
    df["Has_Questionnaire"] = df["questionnaireId"].notna() & (df["questionnaireId"].astype(str).str.len() > 0)

    # keep usable rows
    df = df.dropna(subset=["Video_Name","View_Date"]).copy()
    df = df[pd.to_numeric(df["Viewing_Duration_Min"], errors="coerce") > 0]
    # drop any rows with unknown completion (per your request: do NOT include "No Data")
    df = df[df["Done_Viewing"].notna()]
    df.drop_duplicates(inplace=True)

    return df

DATAFILE = "ASPIRA_Watched_Duration_052825_V2.xlsx"
df = load_and_clean(DATAFILE)

# -------------------- SIDEBAR FILTERS --------------------
st.sidebar.header("🔎 Filters")

# Date range picker
min_date = pd.to_datetime(df["View_Date"]).min()
max_date = pd.to_datetime(df["View_Date"]).max()
date_range = st.sidebar.date_input("📅 Select Date Range", [min_date, max_date])

# Time-of-day range slider (0–23)
st.sidebar.markdown("⏰ **Time of Day Range (Hours)**")
time_range = st.sidebar.slider("Select hour range", 0, 23, (0, 23))

# Video multiselect with "All Videos"
videos = sorted(df["Video_Name"].dropna().unique().tolist())
video_opts = ["All Videos"] + videos
video_sel = st.sidebar.multiselect("🎬 Select Video Title(s)", options=video_opts, default=["All Videos"])

# Completion status (no 'No Data' option)
comp_choice = st.sidebar.radio("✅ Completion Status", ["All","Completed","Not Completed"], index=0)

# Questionnaire presence
q_sel = st.sidebar.selectbox("📝 Has Questionnaire?", ["All","Has questionnaire","No questionnaire"])

# -------------------- APPLY FILTERS --------------------
f = df.copy()

# Date filter
if isinstance(date_range, list) and len(date_range) == 2:
    start, end = pd.to_datetime(date_range[0]), pd.to_datetime(date_range[1])
else:
    start, end = min_date, max_date
f = f[(pd.to_datetime(f["View_Date"]) >= start) & (pd.to_datetime(f["View_Date"]) <= end)]

# Time filter
f = f[(f["Hour"] >= time_range[0]) & (f["Hour"] <= time_range[1])]

# Video filter
if "All Videos" not in video_sel:
    f = f[f["Video_Name"].isin(video_sel)]

# Completion filter
if comp_choice == "Completed":
    f = f[f["Done_Viewing"] == True]
elif comp_choice == "Not Completed":
    f = f[f["Done_Viewing"] == False]

# Questionnaire filter
if q_sel == "Has questionnaire":
    f = f[f["Has_Questionnaire"]]
elif q_sel == "No questionnaire":
    f = f[~f["Has_Questionnaire"]]

# Fallback to keep visuals alive
if f.empty:
    st.warning("No data matches filters — showing full dataset for visuals.")
    f = df.copy()

# -------------------- KPIs --------------------
st.subheader("📊 Key Engagement Metrics")
c1,c2,c3,c4 = st.columns(4)
c1.metric("🎬 Total Views", f"{len(f):,}")
c2.metric("👥 Unique Viewers", f[f["Viewer"].notna()]["Viewer"].nunique())
c3.metric("⏱️ Avg Duration (min)", f"{pd.to_numeric(f['Viewing_Duration_Min'], errors='coerce').mean():.2f}")
c4.metric("✅ Completion Rate", f"{(f['Done_Viewing'].mean()*100):.1f}%")
st.markdown("---")

# -------------------- VISUALIZATIONS --------------------
# 1) Views over time
trend = f.groupby("View_Date").size().reset_index(name="Views")
if not trend.empty:
    fig1 = px.line(trend, x="View_Date", y="Views", markers=True, title="Views Over Time")
    st.plotly_chart(fig1, use_container_width=True)
else:
    st.info("No data available for Views Over Time.")

# 2) Heatmap Day × Hour
heat = f.groupby(["Dow","Hour"]).size().reset_index(name="Views")
if not heat.empty:
    fig2 = px.density_heatmap(heat, x="Hour", y="Dow", z="Views",
                              title="Engagement Heatmap (Day × Hour)")
    st.plotly_chart(fig2, use_container_width=True)

# 3) Hourly peaks
hourly = f.groupby("Hour").size().reset_index(name="Views")
if not hourly.empty:
    fig3 = px.line(hourly, x="Hour", y="Views", markers=True,
                   title="Hourly Viewership (within selected time range)")
    st.plotly_chart(fig3, use_container_width=True)

# 4) Top 10 videos by average duration
top_dur = (f.groupby("Video_Name", as_index=False)["Viewing_Duration_Min"]
             .mean().sort_values("Viewing_Duration_Min", ascending=False).head(10))
if not top_dur.empty:
    fig4 = px.bar(top_dur, x="Video_Name", y="Viewing_Duration_Min",
                  color="Viewing_Duration_Min", color_continuous_scale="Purples",
                  title="Top 10 Videos by Average Duration (Minutes)")
    st.plotly_chart(fig4, use_container_width=True)

# 5) Top 10 videos by completion rate
comp = (f.groupby("Video_Name")["Done_Viewing"].mean()
          .reset_index().sort_values("Done_Viewing", ascending=False).head(10))
if not comp.empty:
    fig5 = px.bar(comp, x="Video_Name", y="Done_Viewing",
                  color="Done_Viewing", color_continuous_scale="Greens",
                  title="Top 10 Videos by Completion Rate")
    st.plotly_chart(fig5, use_container_width=True)

# 6) Distribution of viewing duration
fig6 = px.histogram(f, x="Viewing_Duration_Min", nbins=30,
                    title="Distribution of Viewing Duration (Minutes)")
st.plotly_chart(fig6, use_container_width=True)

# 7) Owner vs Viewer comparison
f["IsOwner"] = f["Viewer"] == f["Owner"]
grp1 = f.groupby("IsOwner")["Viewing_Duration_Min"].mean().reset_index()
grp1["Group"] = grp1["IsOwner"].map({True:"Owner", False:"Viewer"})
if not grp1.empty:
    fig7 = px.bar(grp1, x="Group", y="Viewing_Duration_Min",
                  color="Group", title="Avg Viewing Duration: Owner vs Viewer")
    st.plotly_chart(fig7, use_container_width=True)

# 8) Repeat viewers per video
rep = f.groupby(["Viewer","Video_Name"]).size().reset_index(name="Count")
multi = rep[rep["Count"] > 1]
rep_ct = multi["Video_Name"].value_counts().head(10)
if not rep_ct.empty:
    fig8 = px.bar(x=rep_ct.index, y=rep_ct.values,
                  title="Top 10 Videos by Repeat Viewers",
                  labels={"x":"Video","y":"Repeat Viewers"})
    st.plotly_chart(fig8, use_container_width=True)

# 9) Questionnaire presence impact
qv = f.groupby(f["Has_Questionnaire"].map({True:"Has questionnaire", False:"No questionnaire"})).size().reset_index(name="Views")
if not qv.empty:
    fig9 = px.bar(qv, x="Has_Questionnaire", y="Views",
                  title="Views vs Questionnaire Presence")
    st.plotly_chart(fig9, use_container_width=True)

# -------------------- DOWNLOAD --------------------
st.download_button(
    "📥 Download Filtered Data (CSV)",
    f.to_csv(index=False).encode("utf-8"),
    "Freefuse_Filtered.csv",
    "text/csv"
)
