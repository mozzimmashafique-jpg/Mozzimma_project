import streamlit as st
import pandas as pd
import plotly.express as px

# ------------------------------------------------------------
# PAGE CONFIGURATION
# ------------------------------------------------------------
st.set_page_config(page_title="FreeFuse Engagement Dashboard", layout="wide")

st.title("🎥 FreeFuse Engagement Dashboard")
st.markdown("An interactive analysis of ASPIRA students' engagement with FreeFuse videos.")

# ------------------------------------------------------------
# LOAD AND CLEAN DATA
# ------------------------------------------------------------
@st.cache_data
def load_data():
    df = pd.read_excel("ASPIRA_Watched_Duration_052825_V2.xlsx")
    df.columns = df.columns.str.strip()

    # Rename columns for easier handling
    rename_map = {
        "viewerChoices_VideoName": "Video_Name",
        "viewerChoices_ViewingDuration": "Viewing_Duration",
        "viewerChoices_DoneViewing": "Done_Viewing",
        "viewerChoices_ViewDate": "View_Date",
        "videoViewer": "Viewer",
        "videoOwner": "Owner"
    }
    df.rename(columns=rename_map, inplace=True)

    # Convert data types
    if "View_Date" in df.columns:
        df["View_Date"] = pd.to_datetime(df["View_Date"], errors="coerce")

    # Basic cleaning
    df = df.dropna(subset=["Video_Name", "Viewing_Duration"])
    df["Viewing_Duration"] = pd.to_numeric(df["Viewing_Duration"], errors="coerce")
    df["Viewing_Duration_Min"] = df["Viewing_Duration"] / 60  # convert seconds to minutes

    return df

df = load_data()

# ------------------------------------------------------------
# SIDEBAR FILTERS
# ------------------------------------------------------------
st.sidebar.header("🔎 Filters")

video_filter = st.sidebar.multiselect("🎬 Select Video", df["Video_Name"].unique())
owner_filter = st.sidebar.multiselect("👤 Select Owner", df["Owner"].unique())
date_range = st.sidebar.date_input(
    "📅 Select Date Range",
    [df["View_Date"].min(), df["View_Date"].max()]
)

filtered_df = df.copy()

if video_filter:
    filtered_df = filtered_df[filtered_df["Video_Name"].isin(video_filter)]
if owner_filter:
    filtered_df = filtered_df[filtered_df["Owner"].isin(owner_filter)]
if len(date_range) == 2:
    start_date, end_date = date_range
    filtered_df = filtered_df[
        (filtered_df["View_Date"] >= pd.to_datetime(start_date)) &
        (filtered_df["View_Date"] <= pd.to_datetime(end_date))
    ]

# ------------------------------------------------------------
# KPI METRICS
# ------------------------------------------------------------
col1, col2, col3, col4 = st.columns(4)

col1.metric("🎬 Total Views", len(filtered_df))
col2.metric("👥 Unique Viewers", filtered_df["Viewer"].nunique())
col3.metric("⏱️ Avg Viewing Duration (min)", f"{filtered_df['Viewing_Duration_Min'].mean():.2f}")
col4.metric("✅ Completed Views", filtered_df["Done_Viewing"].sum())

# ------------------------------------------------------------
# DATA HIGHLIGHTS
# ------------------------------------------------------------
st.subheader("📊 Data Highlights")
st.write(f"Records after filtering: **{len(filtered_df)}**")

if not filtered_df.empty:
    top_videos = (
        filtered_df.groupby("Video_Name")["Viewing_Duration_Min"].mean().nlargest(3).index
    )
    st.write(f"🏆 Top 3 videos by average viewing time: {', '.join(top_videos)}")

# ------------------------------------------------------------
# VISUALIZATIONS
# ------------------------------------------------------------

# 1️⃣ Viewing Trend Over Time
if "View_Date" in filtered_df.columns:
    st.subheader("📈 Viewing Trend Over Time")
    trend_df = filtered_df.groupby("View_Date", as_index=False)["Viewer"].nunique()
    fig1 = px.line(trend_df, x="View_Date", y="Viewer", title="Unique Viewers Over Time",
                   markers=True)
    st.plotly_chart(fig1, use_container_width=True)

# 2️⃣ Top Videos by Avg Viewing Duration
if "Video_Name" in filtered_df.columns:
    st.subheader("🏆 Top Videos by Average Viewing Duration")
    top_videos_df = (
        filtered_df.groupby("Video_Name", as_index=False)["Viewing_Duration_Min"].mean()
        .sort_values("Viewing_Duration_Min", ascending=False)
        .head(10)
    )
    fig2 = px.bar(top_videos_df, x="Video_Name", y="Viewing_Duration_Min",
                  title="Top 10 Videos by Average Viewing Duration (min)",
                  color="Viewing_Duration_Min", color_continuous_scale="Blues")
    st.plotly_chart(fig2, use_container_width=True)

# 3️⃣ Viewing Duration Distribution
st.subheader("📊 Viewing Duration Distribution")
fig3 = px.histogram(filtered_df, x="Viewing_Duration_Min", nbins=30,
                    title="Distribution of Viewing Durations (min)",
                    color_discrete_sequence=["#636EFA"])
st.plotly_chart(fig3, use_container_width=True)

# ------------------------------------------------------------
# DOWNLOAD CLEANED DATA
# ------------------------------------------------------------
st.download_button(
    "📥 Download Filtered Data",
    filtered_df.to_csv(index=False).encode("utf-8"),
    "filtered_freefuse_data.csv",
    "text/csv",
)
