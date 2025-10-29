import streamlit as st
import pandas as pd
import plotly.express as px
import re

# --------------------- Page config & style ---------------------
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

# --------------------- Helpers ---------------------
def norm(s: str) -> str:
    """normalize header names for fuzzy matching"""
    return re.sub(r'[^a-z0-9]+', '', str(s).strip().lower())

def pick_col(df: pd.DataFrame, want: str, candidates: list[str]) -> str | None:
    """
    Pick a column by fuzzy match from candidates (exact, normalized, contains).
    want is just for debug messages.
    """
    cols = list(df.columns)
    # exact first
    for c in candidates:
        if c in cols: return c
    # normalized match
    target_norms = [norm(c) for c in candidates]
    name_by_norm = {norm(c): c for c in cols}
    for t in target_norms:
        if t in name_by_norm: return name_by_norm[t]
    # contains-based (norm)
    for c in cols:
        nc = norm(c)
        if any(t in nc for t in target_norms): return c
    return None

def clean_title_series(s: pd.Series) -> pd.Series:
    """
    Keep titles that contain at least one letter or digit after stripping spaces.
    Preserve accents & punctuation. Drop rows that are blank or symbol-only.
    """
    s = s.astype(str).str.strip()
    # keep rows where removing all non-alphanumeric left at least 1 char
    keep_mask = s.str.replace(r'[^0-9A-Za-z]+', '', regex=True).str.len() > 0
    return s.where(keep_mask)

# --------------------- Load & clean ---------------------
@st.cache_data
def load_and_clean(path: str) -> tuple[pd.DataFrame, dict]:
    df = pd.read_excel(path)
    df.columns = df.columns.str.strip()

    # Detect columns
    colmap = {}
    colmap["video_name"] = pick_col(df, "video name", [
        "viewerChoices_VideoName","Video_Name","VideoName","video name","viewerChoices video name"
    ])
    colmap["date"] = pick_col(df, "view date", [
        "viewerChoices_ViewDate","View_Date","ViewDate","Date"
    ])
    colmap["time"] = pick_col(df, "view time", [
        "viewerChoices_ViewTime","View_Time","ViewTime","Time"
    ])
    colmap["duration_sec"] = pick_col(df, "duration (sec)", [
        "viewerChoices_ViewingDuration","Viewing_Duration_Sec","ViewingDuration","Duration","Duration_Seconds"
    ])
    colmap["done"] = pick_col(df, "done/completed", [
        "viewerChoices_DoneViewing","Done_Viewing","Done","Completed","Completion"
    ])
    colmap["viewer"] = pick_col(df, "viewer", ["videoViewer","Viewer","User","Student"])
    colmap["owner"]  = pick_col(df, "owner",  ["videoOwner","Owner","Instructor"])

    # Build a working frame with standardized column names
    work = pd.DataFrame(index=df.index)

    # Video name
    if colmap["video_name"]:
        work["Video_Name"] = clean_title_series(df[colmap["video_name"]])
    else:
        work["Video_Name"] = pd.NA

    # Datetime
    if colmap["date"] and colmap["time"]:
        ts = pd.to_datetime(df[colmap["date"]].astype(str) + " " + df[colmap["time"]].astype(str), errors="coerce")
    elif colmap["date"]:
        ts = pd.to_datetime(df[colmap["date"]], errors="coerce")
    else:
        ts = pd.NaT
    work["View_Timestamp"] = ts
    work["View_DateOnly"] = pd.to_datetime(work["View_Timestamp"], errors="coerce").dt.date

    # Duration
    if colmap["duration_sec"]:
        dsec = pd.to_numeric(df[colmap["duration_sec"]], errors="coerce")
        work["Viewing_Duration_Min"] = dsec/60.0
    else:
        work["Viewing_Duration_Min"] = pd.NA

    # Done/completed
    if colmap["done"]:
        done = df[colmap["done"]].astype(str).str.strip().str.lower().map(
            {"yes":True,"true":True,"1":True,"y":True,"completed":True,
             "no":False,"false":False,"0":False,"n":False,"not completed":False}
        )
        work["Done_Viewing"] = done
    else:
        work["Done_Viewing"] = pd.NA

    # Viewer / Owner (optional)
    work["Viewer"] = df[colmap["viewer"]] if colmap["viewer"] else pd.NA
    work["Owner"]  = df[colmap["owner"]]  if colmap["owner"]  else pd.NA

    # Final cleaning: drop obviously unusable rows
    work = work.dropna(subset=["Video_Name", "View_DateOnly"]).copy()
    if "Viewing_Duration_Min" in work:
        work = work[pd.to_numeric(work["Viewing_Duration_Min"], errors="coerce") > 0]

    work.drop_duplicates(inplace=True)

    debug = {"detected_columns": colmap, "raw_columns": list(df.columns)}
    return work, debug

# ⬅️ Update filename if needed
DATAFILE = "Freefuse_Data.xlsx"
df, debug = load_and_clean(DATAFILE)

# --------------------- Debug expander ---------------------
with st.expander("🔧 Debug: detected columns & sample values", expanded=False):
    st.write("Detected:", debug["detected_columns"])
    st.write("All columns:", debug["raw_columns"])
    st.write("Sample Video_Name values:", df["Video_Name"].dropna().unique()[:20])

# --------------------- Sidebar filters ---------------------
st.sidebar.header("🔎 Filters")

videos = sorted(df["Video_Name"].dropna().unique().tolist())
video_filter = st.sidebar.multiselect("🎬 Select Video", videos)

comp_filter = st.sidebar.radio("✅ Completion Status", ["All","Completed","Not Completed"], index=0)

# Date range
if df["View_DateOnly"].notna().any():
    min_date = min(df["View_DateOnly"])
    max_date = max(df["View_DateOnly"])
else:
    # fallback guard
    min_date = pd.to_datetime("2024-01-01").date()
    max_date = pd.to_datetime("2024-12-31").date()
date_input = st.sidebar.date_input("📅 Select Date Range", [min_date, max_date])

# Filtering
f = df.copy()
if video_filter:
    f = f[f["Video_Name"].isin(video_filter)]

if comp_filter == "Completed":
    f = f[f["Done_Viewing"] == True]
elif comp_filter == "Not Completed":
    f = f[f["Done_Viewing"] == False]

# single vs range safe handling
if isinstance(date_input, list) and len(date_input) == 2:
    start, end = date_input
elif isinstance(date_input, list) and len(date_input) == 1:
    start = end = date_input[0]
else:
    start, end = min_date, max_date

f = f[(f["View_DateOnly"] >= start) & (f["View_DateOnly"] <= end)]

# --------------------- KPIs ---------------------
st.subheader("📊 Key Engagement Metrics")
c1, c2, c3, c4 = st.columns(4)
c1.metric("🎬 Total Views", f"{len(f):,}")
c2.metric("👥 Unique Viewers", f[f["Viewer"].notna()]["Viewer"].nunique() if "Viewer" in f else 0)
c3.metric("⏱️ Avg Duration (min)", f"{pd.to_numeric(f['Viewing_Duration_Min'], errors='coerce').mean():.2f}" if not f.empty else "0.00")
c4.metric("✅ Completion Rate", f"{(f['Done_Viewing'].mean()*100):.1f}%" if "Done_Viewing" in f and f['Done_Viewing'].notna().any() else "0.0%")

st.markdown("---")

# --------------------- Charts ---------------------
if not f.empty:
    st.subheader("📈 Engagement Trend Over Time")
    trend = f.groupby("View_DateOnly").size().reset_index(name="Total_Views")
    fig1 = px.line(trend, x="View_DateOnly", y="Total_Views", markers=True, title="Views Over Time",
                   color_discrete_sequence=["#7B68EE"])
    fig1.update_layout(xaxis_title="Date", yaxis_title="Total Views")
    st.plotly_chart(fig1, use_container_width=True)

if not f.empty and "Viewing_Duration_Min" in f:
    st.subheader("🏆 Top 10 Videos by Avg Duration")
    top = (f.groupby("Video_Name", as_index=False)["Viewing_Duration_Min"]
             .mean()
             .sort_values("Viewing_Duration_Min", ascending=False)
             .head(10))
    if not top.empty:
        fig2 = px.bar(top, x="Video_Name", y="Viewing_Duration_Min",
                      title="Top 10 Videos by Avg Duration (Minutes)",
                      color="Viewing_Duration_Min", color_continuous_scale="Purples")
        fig2.update_layout(xaxis_title="Video", yaxis_title="Avg Duration (min)")
        st.plotly_chart(fig2, use_container_width=True)

if "Done_Viewing" in f and f["Done_Viewing"].notna().any():
    st.subheader("🥧 Completion Breakdown")
    counts = f["Done_Viewing"].value_counts()
    pie = pd.DataFrame({
        "Status": ["Completed" if k else "Not Completed" for k in counts.index],
        "Count": counts.values
    })
    fig3 = px.pie(pie, names="Status", values="Count", title="Completion Breakdown",
                  color="Status", color_discrete_map={"Completed":"green","Not Completed":"red"})
    st.plotly_chart(fig3, use_container_width=True)

if not f.empty and "Viewing_Duration_Min" in f:
    st.subheader("📊 Viewing Duration Distribution")
    fig4 = px.histogram(f, x="Viewing_Duration_Min", nbins=30,
                        title="Distribution of Viewing Duration (Minutes)",
                        color_discrete_sequence=["#6A5ACD"])
    fig4.update_layout(xaxis_title="Duration (min)", yaxis_title="Frequency")
    st.plotly_chart(fig4, use_container_width=True)

# --------------------- Download ---------------------
st.download_button(
    "📥 Download Filtered Data (CSV)",
    f.to_csv(index=False).encode("utf-8"),
    "Freefuse_Cleaned_Filtered.csv",
    "text/csv"
)
