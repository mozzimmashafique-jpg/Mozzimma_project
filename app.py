import streamlit as st
import pandas as pd
import plotly.express as px
import re
import unicodedata

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
st.caption("An interactive visualization of ASPIRA students' engagement with FreeFuse videos.")

# -------------------- HELPERS --------------------
def norm(s: str) -> str:
    return re.sub(r'[^a-z0-9]+', '', str(s).strip().lower())

def pick_col(df: pd.DataFrame, want: str, candidates: list[str]) -> str | None:
    cols = list(df.columns)
    for c in candidates:
        if c in cols: return c
    target_norms = [norm(c) for c in candidates]
    name_by_norm = {norm(c): c for c in cols}
    for t in target_norms:
        if t in name_by_norm: return name_by_norm[t]
    for c in cols:
        nc = norm(c)
        if any(t in nc for t in target_norms): return c
    return None

# -------------------- CLEAN TITLES --------------------
def clean_title_series(s: pd.Series) -> pd.Series:
    """
    Enhanced cleaning:
    - Remove garbled, numeric-only, or symbol-only titles
    - Normalize unicode
    - Remove emojis / non-printables
    """
    s = s.astype(str).str.strip()
    s = s.apply(lambda x: unicodedata.normalize('NFKC', x))
    s = s.str.replace(r'[^\x00-\x7F]+', '', regex=True)       # remove non-ascii
    s = s.str.replace(r'([^\w\s])\1+', r'\1', regex=True)
    s = s.str.replace(r'[_\-=~`^]+', ' ', regex=True)
    s = s.str.replace(r'\s+', ' ', regex=True).str.strip()
    s = s.str.replace(r'^[\.\:\-\s0-9]+$', '', regex=True)    # remove numeric/symbol-only
    keep_mask = s.str.replace(r'[^A-Za-z0-9]+', '', regex=True).str.len() > 1
    s = s.where(keep_mask)
    return s

# -------------------- LOAD & CLEAN --------------------
@st.cache_data
def load_and_clean(path: str) -> tuple[pd.DataFrame, dict]:
    df = pd.read_excel(path)
    df.columns = df.columns.str.strip()

    colmap = {}
    colmap["video_name"] = pick_col(df, "video name",
        ["viewerChoices_VideoName","Video_Name","VideoName","video name"])
    colmap["date"] = pick_col(df, "view date",
        ["viewerChoices_ViewDate","View_Date","ViewDate","Date"])
    colmap["time"] = pick_col(df, "view time",
        ["viewerChoices_ViewTime","View_Time","ViewTime","Time"])
    colmap["duration_sec"] = pick_col(df, "duration",
        ["viewerChoices_ViewingDuration","Viewing_Duration_Sec","Duration","ViewingDuration"])
    colmap["done"] = pick_col(df, "done",
        ["viewerChoices_DoneViewing","Done_Viewing","Done","Completed"])
    colmap["viewer"] = pick_col(df, "viewer", ["videoViewer","Viewer","User","Student"])
    colmap["owner"] = pick_col(df, "owner", ["videoOwner","Owner","Instructor"])

    work = pd.DataFrame(index=df.index)
    work["Video_Name"] = clean_title_series(df[colmap["video_name"]]) if colmap["video_name"] else pd.NA

    # datetime
    if colmap["date"] and colmap["time"]:
        ts = pd.to_datetime(df[colmap["date"]].astype(str)+" "+df[colmap["time"]].astype(str), errors="coerce")
    elif colmap["date"]:
        ts = pd.to_datetime(df[colmap["date"]], errors="coerce")
    else:
        ts = pd.NaT
    work["View_Timestamp"] = ts
    work["View_DateOnly"] = pd.to_datetime(ts, errors="coerce").dt.date
    work["Hour"] = pd.to_datetime(ts, errors="coerce").dt.hour

    # duration
    work["Viewing_Duration_Min"] = pd.to_numeric(df[colmap["duration_sec"]], errors="coerce")/60.0 if colmap["duration_sec"] else pd.NA

    # completion
    if colmap["done"]:
        done = df[colmap["done"]].astype(str).str.strip().str.lower().map({
            "yes":True,"true":True,"1":True,"y":True,"completed":True,
            "no":False,"false":False,"0":False,"n":False,"not completed":False
        })
        work["Done_Viewing"] = done
    else:
        work["Done_Viewing"] = pd.NA

    work["Viewer"] = df[colmap["viewer"]] if colmap["viewer"] else pd.NA
    work["Owner"]  = df[colmap["owner"]]  if colmap["owner"]  else pd.NA

    work = work.dropna(subset=["Video_Name","View_DateOnly"])
    work = work[pd.to_numeric(work["Viewing_Duration_Min"], errors="coerce")>0]
    work.drop_duplicates(inplace=True)

    debug = {"detected_columns": colmap, "raw_columns": list(df.columns)}
    return work, debug

DATAFILE = "Freefuse_Data.xlsx"
df, debug = load_and_clean(DATAFILE)

# -------------------- SIDEBAR FILTERS --------------------
st.sidebar.header("🔎 Filters")

# Year filter
years = sorted(pd.Series(df["View_Timestamp"]).dt.year.dropna().unique().astype(int).tolist())
year_selected = st.sidebar.selectbox("📅 Select Year", options=years, index=len(years)-1)

# Video filter with 'Select All'
videos = sorted(df["Video_Name"].dropna().unique().tolist())
videos_all = ["All Videos"] + videos
video_filter = st.sidebar.multiselect("🎬 Select Video Title(s)", videos_all, default=["All Videos"])

# Time of Day
time_choice = st.sidebar.selectbox("🕐 Time of Day", ["Both","AM","PM"])

# Apply filters
f = df.copy()
f = f[pd.to_datetime(f["View_Timestamp"]).dt.year == year_selected]
if "All Videos" not in video_filter:
    f = f[f["Video_Name"].isin(video_filter)]

# AM / PM
if time_choice != "Both":
    if time_choice == "AM":
        f = f[(f["Hour"]>=0)&(f["Hour"]<12)]
    else:
        f = f[(f["Hour"]>=12)&(f["Hour"]<24)]

# -------------------- KPI SECTION --------------------
st.subheader("📊 Key Engagement Metrics")
c1,c2,c3,c4 = st.columns(4)
c1.metric("🎬 Total Views", f"{len(f):,}")
c2.metric("👥 Unique Viewers", f[f["Viewer"].notna()]["Viewer"].nunique() if "Viewer" in f else 0)
c3.metric("⏱️ Avg Duration (min)", f"{pd.to_numeric(f['Viewing_Duration_Min'], errors='coerce').mean():.2f}" if not f.empty else "0.00")
c4.metric("✅ Completion Rate", f"{(f['Done_Viewing'].mean()*100):.1f}%" if f['Done_Viewing'].notna().any() else "0.0%")
st.markdown("---")

# -------------------- VISUALIZATIONS --------------------
if not f.empty:

    # 1️⃣ Engagement trend
    st.subheader("📈 Engagement Trend Over Time")
    trend = f.groupby("View_DateOnly").size().reset_index(name="Total_Views")
    fig1 = px.line(trend, x="View_DateOnly", y="Total_Views", markers=True,
                   title="Views Over Time", color_discrete_sequence=["#7B68EE"])
    fig1.update_layout(xaxis_title="Date", yaxis_title="Views")
    st.plotly_chart(fig1, use_container_width=True)

    # 2️⃣ Top 10 videos by avg duration
    st.subheader("🏆 Top 10 Videos by Avg Duration")
    top = (f.groupby("Video_Name", as_index=False)["Viewing_Duration_Min"]
             .mean().sort_values("Viewing_Duration_Min", ascending=False).head(10))
    fig2 = px.bar(top, x="Video_Name", y="Viewing_Duration_Min",
                  title="Top 10 Videos by Avg Duration (Minutes)",
                  color="Viewing_Duration_Min", color_continuous_scale="Purples")
    fig2.update_layout(xaxis_title="Video", yaxis_title="Avg Duration (min)")
    st.plotly_chart(fig2, use_container_width=True)

    # 3️⃣ Top 10 videos by completion rate
    st.subheader("✅ Top 10 Videos by Completion Rate")
    comp = (f.groupby("Video_Name")["Done_Viewing"].mean()
              .reset_index().rename(columns={"Done_Viewing":"Completion_Rate"})
              .sort_values("Completion_Rate", ascending=False).head(10))
    fig3 = px.bar(comp, x="Video_Name", y="Completion_Rate",
                  title="Top 10 Videos by Completion Rate",
                  color="Completion_Rate", color_continuous_scale="Greens")
    st.plotly_chart(fig3, use_container_width=True)

    # 4️⃣ AM vs PM engagement
    st.subheader("🌞 AM vs 🌙 PM Engagement Comparison")
    f["TimeOfDay"] = f["Hour"].apply(lambda h: "AM" if h<12 else "PM")
    ampm = f.groupby("TimeOfDay").size().reset_index(name="Views")
    fig_ampm = px.bar(ampm, x="TimeOfDay", y="Views", color="TimeOfDay",
                      title="Views Distribution: AM vs PM",
                      color_discrete_map={"AM":"#9370DB","PM":"#8A2BE2"})
    st.plotly_chart(fig_ampm, use_container_width=True)

    # 5️⃣ Heatmap by day and hour
    st.subheader("🔥 Engagement Heatmap (Day vs Hour)")
    f["Day"] = pd.to_datetime(f["View_Timestamp"]).dt.day_name()
    heat = f.groupby(["Day","Hour"]).size().reset_index(name="Views")
    fig_heat = px.density_heatmap(heat, x="Hour", y="Day", z="Views",
                                  title="Engagement by Day & Hour",
                                  color_continuous_scale="Purples")
    st.plotly_chart(fig_heat, use_container_width=True)

    # 6️⃣ Viewer vs Owner
    st.subheader("👤 Avg Duration: Owner vs Viewer")
    f["IsOwner"] = f["Viewer"] == f["Owner"]
    grp = f.groupby("IsOwner")["Viewing_Duration_Min"].mean().reset_index()
    grp["Group"] = grp["IsOwner"].map({True:"Owner", False:"Viewer"})
    fig_owner = px.bar(grp, x="Group", y="Viewing_Duration_Min",
                       color="Group", color_discrete_map={"Owner":"#8B008B","Viewer":"#9370DB"},
                       title="Avg Viewing Duration: Owner vs Viewer")
    st.plotly_chart(fig_owner, use_container_width=True)

    # 7️⃣ Repeat viewing
    st.subheader("🔁 Repeat Viewers per Video")
    replays = f.groupby(["Viewer","Video_Name"]).size().reset_index(name="Count")
    multi = replays[replays["Count"]>1]
    replay_counts = multi["Video_Name"].value_counts().head(10)
    fig_replay = px.bar(x=replay_counts.index, y=replay_counts.values,
                        title="Top 10 Videos by Repeat Viewers",
                        labels={"x":"Video","y":"Repeat Viewers"})
    st.plotly_chart(fig_replay, use_container_width=True)

    # 8️⃣ Duration distribution
    st.subheader("📊 Viewing Duration Distribution")
    fig_hist = px.histogram(f, x="Viewing_Duration_Min", nbins=30,
                            title="Distribution of Viewing Duration (Minutes)",
                            color_discrete_sequence=["#6A5ACD"])
    st.plotly_chart(fig_hist, use_container_width=True)

# -------------------- DOWNLOAD --------------------
st.download_button(
    "📥 Download Filtered Data (CSV)",
    f.to_csv(index=False).encode("utf-8"),
    "Freefuse_Cleaned_Filtered.csv",
    "text/csv"
)
