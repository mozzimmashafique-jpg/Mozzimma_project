import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime

# ------------------- PAGE CONFIGURATION -------------------
st.set_page_config(page_title="FreeFuse Engagement Dashboard", layout="wide")

st.markdown("""
    <style>
    .main {background-color: #F7F5FF;}
    </style>
""", unsafe_allow_html=True)

# ------------------- LOAD & CLEAN DATA -------------------
@st.cache_data
def load_and_clean_data(file_path):
    df = pd.read_excel(file_path)

    # Normalize column names
    df.columns = df.columns.str.strip().str.replace(" ", "_").str.replace("-", "_")

    # Rename to consistent names
    rename_map = {
        "viewerChoices_VideoId": "Video_ID",
        "viewerChoices_VideoName": "Video_Name",
        "viewerChoices_ViewingDuration": "Duration",
        "viewerChoices_DoneViewing": "Done_Viewing",
        "viewerChoices_ViewDate": "View_Date",
        "viewerChoices_ViewTime": "View_Time",
        "isPublished": "isPublished",
        "questionnaireId": "Questionnaire_ID",
        "videoViewer": "Viewer_ID"
    }
    df.rename(columns=rename_map, inplace=True)

    # Clean video titles — remove symbols or invalid names
    df["Video_Name"] = df["Video_Name"].astype(str)
    df["Video_Name"] = df["Video_Name"].str.replace(r"[^a-zA-Z0-9\s:/()-]+", "", regex=True)
    df = df[df["Video_Name"].str.strip() != ""]

    # Merge date + time to timestamp
    df["View_Timestamp"] = pd.to_datetime(
        df["View_Date"].astype(str) + " " + df["View_Time"].astype(str),
        errors="coerce"
    )
    df["Hour"] = df["View_Timestamp"].dt.hour
    df["Date"] = df["View_Timestamp"].dt.date

    # Convert duration to minutes
    df["Duration_Min"] = pd.to_numeric(df["Duration"], errors="coerce") / 60

    # Normalize Done_Viewing column
    df["Done_Viewing"] = df["Done_Viewing"].astype(str).str.strip().str.lower()
    df["Done_Viewing"] = df["Done_Viewing"].replace(
        {"1": True, "true": True, "yes": True, "0": False, "false": False, "no": False}
    )
    df["Done_Viewing"] = df["Done_Viewing"].fillna(False)

    return df.dropna(subset=["Video_Name", "View_Timestamp"])

# Load data
df = load_and_clean_data("ASPIRA_Watched_Duration_052825_V2.xlsx")

# ------------------- SIDEBAR FILTERS -------------------
st.sidebar.header("🔍 Filters")

# Date range filter
min_date = df["View_Timestamp"].min().date()
max_date = df["View_Timestamp"].max().date()
date_range = st.sidebar.date_input("📅 Select Date Range", [min_date, max_date])

# Hour range filter
hour_range = st.sidebar.slider("⏰ Time of Day Range (Hours)", 0, 23, (0, 23))

# Video selection filter
videos = ["All Videos"] + sorted(df["Video_Name"].unique().tolist())
selected_videos = st.sidebar.multiselect("🎬 Select Video Title(s)", videos, default=["All Videos"])

# Completion filter
completion_filter = st.sidebar.radio("✅ Completion Status", ["All", "Completed", "Not Completed"])

# Questionnaire filter
questionnaire_filter = st.sidebar.selectbox("🧾 Has Questionnaire?", ["All", "Has questionnaire", "No questionnaire"])

# Apply filters
f = df.copy()
f = f[
    (f["View_Timestamp"].dt.date >= date_range[0])
    & (f["View_Timestamp"].dt.date <= date_range[1])
    & (f["Hour"].between(hour_range[0], hour_range[1]))
]

if "All Videos" not in selected_videos:
    f = f[f["Video_Name"].isin(selected_videos)]

if completion_filter == "Completed":
    f = f[f["Done_Viewing"] == True]
elif completion_filter == "Not Completed":
    f = f[f["Done_Viewing"] == False]

if questionnaire_filter == "Has questionnaire":
    f = f[f["Questionnaire_ID"].notna()]
elif questionnaire_filter == "No questionnaire":
    f = f[f["Questionnaire_ID"].isna()]

# ------------------- KPI METRICS -------------------
st.title("🎥 FreeFuse Engagement Dashboard")
st.markdown("Interactive analytics on FreeFuse viewing behaviour (ASPIRA data).")

total_views = len(f)
unique_viewers = f["Viewer_ID"].nunique()
avg_duration = round(f["Duration_Min"].mean(), 2) if total_views > 0 else 0
completion_rate = round((f["Done_Viewing"].mean() * 100), 1) if total_views > 0 else 0

kpi1, kpi2, kpi3, kpi4 = st.columns(4)
kpi1.metric("📊 Total Views", total_views)
kpi2.metric("👤 Unique Viewers", unique_viewers)
kpi3.metric("⏱️ Avg Duration (min)", avg_duration)
kpi4.metric("✅ Completion Rate", f"{completion_rate}%")

# ------------------- VISUALIZATIONS -------------------

# 1️⃣ Views Over Time
views_by_date = f.groupby("Date").size().reset_index(name="Views")
fig1 = px.line(views_by_date, x="Date", y="Views", title="Views Over Time", markers=True)
st.plotly_chart(fig1, use_container_width=True)

# 2️⃣ Engagement Heatmap (Day x Hour)
f["Day"] = f["View_Timestamp"].dt.day_name()
heatmap_data = f.groupby(["Day", "Hour"]).size().reset_index(name="Views")
fig2 = px.density_heatmap(
    heatmap_data,
    x="Hour",
    y="Day",
    z="Views",
    title="Engagement Heatmap (Day × Hour)",
    color_continuous_scale="Purples"
)
st.plotly_chart(fig2, use_container_width=True)

# 3️⃣ Hourly Viewership Trend
hourly_views = f.groupby("Hour").size().reset_index(name="Views")
fig3 = px.line(hourly_views, x="Hour", y="Views", markers=True, title="Hourly Viewership Trend")
st.plotly_chart(fig3, use_container_width=True)

# 4️⃣ Top 10 Videos by Total Views (with Completion Rate as Color)
top_videos = (
    f.groupby("Video_Name")
     .agg(
         Total_Views=("Done_Viewing", "count"),
         Completion_Rate=("Done_Viewing", "mean")
     )
     .reset_index()
     .sort_values("Total_Views", ascending=False)
     .head(10)
)

fig4 = px.bar(
    top_videos,
    x="Video_Name",
    y="Total_Views",
    color="Completion_Rate",
    color_continuous_scale="Greens",
    title="Top 10 Videos by Total Views (Completion Rate as Color)",
    text="Total_Views"
)
fig4.update_traces(texttemplate="%{text} views", textposition="outside")
fig4.update_layout(xaxis_title="Video Title", yaxis_title="Total Views", xaxis_tickangle=-30)
st.plotly_chart(fig4, use_container_width=True)

# 5️⃣ Questionnaire Participation (Viewer-Level)
questionnaire_participation = (
    f.groupby("Viewer_ID")
     .agg(Filled_Questionnaire=("Questionnaire_ID", lambda x: x.notna().any()))
     .reset_index()
)

viewer_counts = questionnaire_participation["Filled_Questionnaire"].value_counts().reset_index()
viewer_counts.columns = ["Filled_Questionnaire", "Viewer_Count"]

fig5 = px.bar(
    viewer_counts,
    x="Filled_Questionnaire",
    y="Viewer_Count",
    color="Filled_Questionnaire",
    title="Viewers Who Filled Out Questionnaire vs Did Not",
    text="Viewer_Count",
    color_discrete_map={True: "#3E9E5D", False: "#B0B0B0"}
)
fig5.update_traces(texttemplate="%{text}", textposition="outside")
fig5.update_layout(xaxis_title="Questionnaire Completion", yaxis_title="Number of Viewers")
st.plotly_chart(fig5, use_container_width=True)

# ------------------- DOWNLOAD SECTION -------------------
st.download_button(
    "📥 Download Filtered Dataset (CSV)",
    f.to_csv(index=False).encode("utf-8"),
    "FreeFuse_Filtered.csv",
    "text/csv",
    help="Download currently filtered dataset for further analysis"
)
