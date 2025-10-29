import streamlit as st
import pandas as pd
import plotly.express as px

# ------------------------------------------------------------
# PAGE CONFIGURATION
# ------------------------------------------------------------
st.set_page_config(page_title="FreeFuse Engagement Dashboard", layout="wide")

st.title("🎥 FreeFuse Engagement Dashboard")
st.write("An interactive analysis of ASPIRA students' engagement with FreeFuse videos.")

# ------------------------------------------------------------
# LOAD AND CLEAN DATA
# ------------------------------------------------------------
@st.cache_data
def load_data():
    df = pd.read_excel("ASPIRA_Watched_Duration_052825_V2.xlsx")
    df.columns = df.columns.str.strip()  # remove extra spaces

    # Display all detected column names for debugging
    st.write("🧾 **Columns detected in dataset:**", list(df.columns))

    # Try renaming common variations automatically
    rename_map = {
        "Video Name": "Video_Name",
        "Video": "Video_Name",
        "Watched Duration": "Duration_Watched",
        "Duration Watched": "Duration_Watched",
        "Watch Duration": "Duration_Watched",
        "Completion %": "Completion_%",
        "Completion%": "Completion_%",
        "User Email": "User_Email",
        "Email": "User_Email",
        "Organization Name": "Organization",
        "Date Watched": "Date_Watched",
        "Date": "Date_Watched"
    }
    df.rename(columns=rename_map, inplace=True)

    # Basic cleanup
    for col in ["Video_Name", "Duration_Watched"]:
        if col in df.columns:
            df = df[df[col].notna()]

    if "Date_Watched" in df.columns:
        df["Date_Watched"] = pd.to_datetime(df["Date_Watched"], errors="coerce")
    if "Completion_%" in df.columns:
        df["Completion_%"] = df["Completion_%"].clip(0, 100)

    # Normalize organization names
    if "Organization" in df.columns:
        df["Organization"] = df["Organization"].astype(str).str.upper().str.strip()

    # Derived column
    if "Total_Duration" in df.columns:
        df["Watch_Ratio"] = df["Duration_Watched"] / df["Total_Duration"]

    return df

df = load_data()

# ------------------------------------------------------------
# SIDEBAR FILTERS
# ------------------------------------------------------------
st.sidebar.header("🔎 Filters")

org_filter = []
video_filter = []
date_range = []

if "Organization" in df.columns:
    org_filter = st.sidebar.multiselect("Select Organization", df["Organization"].unique())
if "Video_Name" in df.columns:
    video_filter = st.sidebar.multiselect("Select Video", df["Video_Name"].unique())
if "Date_Watched" in df.columns:
    date_range = st.sidebar.date_input(
        "Select Date Range",
        [df["Date_Watched"].min(), df["Date_Watched"].max()]
    )

filtered_df = df.copy()

if org_filter and "Organization" in filtered_df.columns:
    filtered_df = filtered_df[filtered_df["Organization"].isin(org_filter)]
if video_filter and "Video_Name" in filtered_df.columns:
    filtered_df = filtered_df[filtered_df["Video_Name"].isin(video_filter)]
if len(date_range) == 2 and "Date_Watched" in filtered_df.columns:
    start_date, end_date = date_range
    filtered_df = filtered_df[
        (filtered_df["Date_Watched"] >= pd.to_datetime(start_date)) &
        (filtered_df["Date_Watched"] <= pd.to_datetime(end_date))
    ]

# ------------------------------------------------------------
# KPI METRICS
# ------------------------------------------------------------
col1, col2, col3, col4 = st.columns(4)
col1.metric("🎬 Total Videos Watched", len(filtered_df))
if "User_Email" in filtered_df.columns:
    col2.metric("👥 Unique Viewers", filtered_df["User_Email"].nunique())
if "Duration_Watched" in filtered_df.columns:
    col3.metric("⏱️ Avg Watch Duration (min)", round(filtered_df["Duration_Watched"].mean(), 2))
if "Completion_%" in filtered_df.columns:
    col4.metric("✅ Avg Completion %", f"{filtered_df['Completion_%'].mean():.1f}%")

# ------------------------------------------------------------
# DATA HIGHLIGHTS
# ------------------------------------------------------------
st.subheader("📊 Data Highlights")
st.write(f"Records after filtering: **{len(filtered_df)}**")

if "Completion_%" in filtered_df.columns:
    st.write(f"Average completion rate: **{filtered_df['Completion_%'].mean():.2f}%**")

if "Video_Name" in filtered_df.columns and "Completion_%" in filtered_df.columns:
    top_videos = (
        filtered_df.groupby("Video_Name")["Completion_%"].mean().nlargest(3).index
    )
    st.write(f"Top 3 engaging videos: {', '.join(top_videos)}")

# ------------------------------------------------------------
# VISUALIZATIONS
# ------------------------------------------------------------

# 1️⃣ Engagement Trend Over Time
if "Date_Watched" in filtered_df.columns and "Completion_%" in filtered_df.columns:
    st.subheader("📈 Engagement Trend Over Time")
    trend_df = (
        filtered_df.groupby("Date_Watched", as_index=False)["Completion_%"].mean()
        .sort_values("Date_Watched")
    )
    fig1 = px.line(trend_df, x="Date_Watched", y="Completion_%", title="Average Completion % Over Time")
    st.plotly_chart(fig1, use_container_width=True)

# 2️⃣ Top Videos by Completion %
if "Video_Name" in filtered_df.columns and "Completion_%" in filtered_df.columns:
    st.subheader("🏆 Top Videos by Completion Rate")
    top_videos_df =
