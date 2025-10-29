import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px

# ------------------------------------------------------------
# PAGE CONFIGURATION
# ------------------------------------------------------------
st.set_page_config(page_title="FreeFuse Engagement Dashboard", layout="wide")

st.title("🎥 FreeFuse Engagement Dashboard")
st.caption("An interactive visualization of ASPIRA student engagement with FreeFuse videos.")

# ------------------------------------------------------------
# LOAD & CLEAN DATA
# ------------------------------------------------------------
@st.cache_data
def load_and_clean(path: str) -> pd.DataFrame:
    df = pd.read_excel(path)
    df.columns = df.columns.str.strip()

    # --- Rename columns to clean names for easier referencing
    rename_map = {
        "viewerChoices_VideoName": "Video_Name",
        "viewerChoices_ViewingDuration": "Viewing_Duration_Sec",
        "viewerChoices_ViewDate": "View_Date",
        "viewerChoices_ViewTime": "View_Time",
        "viewerChoices_DoneViewing": "Done_Viewing",
        "videoViewer": "Viewer",
        "videoOwner": "Owner"
    }
    df.rename(columns=rename_map, inplace=True)

    # --- Combine date + time if both exist
    if "View_Date" in df.columns and "View_Time" in df.columns:
        df["View_Timestamp"] = pd.to_datetime(
            df["View_Date"].astype(str) + " " + df["View_Time"].astype(str),
            errors="coerce"
        )
    elif "View_Date" in df.columns:
        df["View_Timestamp"] = pd.to_datetime(df["View_Date"], errors="coerce")

    # --- Convert duration from seconds → minutes
    if "Viewing_Duration_Sec" in df.columns:
        df["Viewing_Duration_Sec"] = pd.to_numeric(df["Viewing_Duration_Sec"], errors="coerce")
        df["Viewing_Duration_Min"] = df["Viewing_Duration_Sec"] / 60
        df = df[df["Viewing_Duration_Min"] > 0]  # remove invalid durations

    # --- Clean Done_Viewing values (standardize yes/no)
    if "Done_Viewing" in df.columns:
        df["Done_Viewing"] = df["Done_Viewing"].astype(str).str.lower().map(
            {"yes": True, "y": True, "1": True, "true": True, "no": False, "n": False, "0": False, "false": False}
        )

    # --- Remove duplicates and missing rows
    df.drop_duplicates(inplace=True)
    df.dropna(subset=["Video_Name"], inplace=True)

    # --- Add derived columns
    if "View_Timestamp" in df.columns:
        df["View_DateOnly"] = df["View_Timestamp"].dt.date

    return df

df = load_and_clean("Freefuse_Data.xlsx")

# ------------------------------------------------------------
# SIDEBAR FILTERS
# ------------------------------------------------------------
st.sidebar.header("🔎 Filters")

video_filter = st.sidebar.multiselect("🎬 Select Video", sorted(df["Video_Name"].unique()))
completion_filter = st.sidebar.radio("✅ Completion Status", ["All", "Completed", "Not Completed"], index=0)
date_range = st.sidebar.date_input(
    "📅 Select Date Range",
    [df["View_DateOnly"].min(), df["View_DateOnly"].max()]
)

filtered_df = df.copy()

# Apply filters
if video_filter:
    filtered_df = filtered_df[filtered_df["Video_Name"].isin(video_filter)]

if completion_filter == "Completed":
    filtered_df = filtered_df[filtered_df["Done_Viewing"] == True]
elif completion_filter == "Not Completed":
    filtered_df = filtered_df[filtered_df["Done_Viewing"] == False]

if len(date_range) == 2:
    start, end = date_range
    filtered_df = filtered_df[
        (filtered_df["View_DateOnly"] >= start) & (filtered_df["View_DateOnly"] <= end)
    ]

# ------------------------------------------------------------
# KPI METRICS
# ------------------------------------------------------------
st.subheader("📊 Key Engagement Metrics")

col1, col2, col3, col4 = st.columns(4)

total_views = len(filtered_df)
unique_viewers = filtered_df["Viewer"].nunique() if "Viewer" in filtered_df.columns else 0
avg_duration = filtered_df["Viewing_Duration_Min"].mean() if "Viewing_Duration_Min" in filtered_df.columns else 0
completion_rate = (
    filtered_df["Done_Viewing"].mean() * 100 if "Done_Viewing" in filtered_df.columns else 0
)

col1.metric("🎬 Total Views", f"{total_views:,}")
col2.metric("👥 Unique Viewers", f"{unique_viewers:,}")
col3.metric("⏱️ Avg Viewing Duration (min)", f"{avg_duration:.2f}")
col4.metric("✅ Avg Completion Rate", f"{completion_rate:.1f}%")

# ------------------------------------------------------------
# CHARTS
# ------------------------------------------------------------

# 1️⃣ Trend of Views Over Time
if "View_DateOnly" in filtered_df.columns:
    st.subheader("📈 Engagement Trend Over Time")
    trend_df = filtered_df.groupby("View_DateOnly").size().reset_index(name="Total_Views")
    fig1 = px.line(
        trend_df,
        x="View_DateOnly",
        y="Total_Views",
        title="Total Views Over Time",
        markers=True
    )
    fig1.update_layout(xaxis_title="Date", yaxis_title="Views")
    st.plotly_chart(fig1, use_container_width=True)

# 2️⃣ Top Videos by Average Viewing Duration
if "Video_Name" in filtered_df.columns and "Viewing_Duration_Min" in filtered_df.columns:
    st.subheader("🏆 Top Videos by Average Viewing Duration")
    top_videos_df = (
        filtered_df.groupby("Video_Name", as_index=False)["Viewing_Duration_Min"]
        .mean()
        .sort_values("Viewing_Duration_Min", ascending=False)
        .head(10)
    )
    fig2 = px.bar(
        top_videos_df,
        x="Video_Name",
        y="Viewing_Duration_Min",
        color="Viewing_Duration_Min",
        title="Top 10 Videos by Avg Viewing Duration (Minutes)",
        color_continuous_scale="Blues"
    )
    st.plotly_chart(fig2, use_container_width=True)

# 3️⃣ Completion Rate by Video
if "Done_Viewing" in filtered_df.columns:
    st.subheader("✅ Completion Rate by Video")
    comp_df = (
        filtered_df.groupby("Video_Name")["Done_Viewing"]
        .mean()
        .mul(100)
        .reset_index(name="Completion_Rate_%")
        .sort_values("Completion_Rate_%", ascending=False)
        .head(10)
    )
    fig3 = px.bar(
        comp_df,
        x="Video_Name",
        y="Completion_Rate_%",
        title="Top 10 Videos by Completion Rate (%)",
        color="Completion_Rate_%",
        color_continuous_scale="Greens"
    )
    st.plotly_chart(fig3, use_container_width=True)

# 4️⃣ Viewing Duration Distribution
if "Viewing_Duration_Min" in filtered_df.columns:
    st.subheader("📊 Viewing Duration Distribution")
    fig4 = px.histogram(
        filtered_df,
        x="Viewing_Duration_Min",
        nbins=30,
        title="Distribution of Viewing Durations (Minutes)",
        color_discrete_sequence=["#636EFA"]
    )
    fig4.update_layout(xaxis_title="Viewing Duration (min)", yaxis_title="Count")
    st.plotly_chart(fig4, use_container_width=True)

# ------------------------------------------------------------
# DOWNLOAD CLEANED DATA
# ------------------------------------------------------------
st.download_button(
    "📥 Download Filtered Dataset (CSV)",
    filtered_df.to_csv(index=False).encode("utf-8"),
    "FreeFuse_Cleaned_Filtered.csv",
    "text/csv"
)
