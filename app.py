import streamlit as st
import pandas as pd
import plotly.express as px

# Page setup
st.set_page_config(page_title="FreeFuse Engagement Dashboard", layout="wide")

st.title("🎥 FreeFuse Engagement Dashboard")
st.write("An interactive analysis of ASPIRA students' engagement with FreeFuse videos.")

# Load data
@st.cache_data
def load_data():
    df = pd.read_excel("ASPIRA_Watched_Duration_052825_V2.xlsx")
    df.columns = df.columns.str.strip()
    df.dropna(subset=["Video_Name", "Duration_Watched"], inplace=True)
    df["Date_Watched"] = pd.to_datetime(df["Date_Watched"], errors="coerce")
    df["Completion_%"] = df["Completion_%"].clip(0, 100)
    if "Organization" in df.columns:
        df["Organization"] = df["Organization"].astype(str).str.upper().str.strip()
    if "Total_Duration" in df.columns:
        df["Watch_Ratio"] = df["Duration_Watched"] / df["Total_Duration"]
    return df

df = load_data()

# Sidebar filters
st.sidebar.header("🔎 Filters")
org_filter = st.sidebar.multiselect("Select Organization", df["Organization"].unique())
video_filter = st.sidebar.multiselect("Select Video", df["Video_Name"].unique())
date_range = st.sidebar.date_input(
    "Select Date Range", [df["Date_Watched"].min(), df["Date_Watched"].max()]
)

filtered_df = df.copy()

if org_filter:
    filtered_df = filtered_df[filtered_df["Organization"].isin(org_filter)]
if video_filter:
    filtered_df = filtered_df[filtered_df["Video_Name"].isin(video_filter)]
if len(date_range) == 2:
    start_date, end_date = date_range
    filtered_df = filtered_df[
        (filtered_df["Date_Watched"] >= pd.to_datetime(start_date))
        & (filtered_df["Date_Watched"] <= pd.to_datetime(end_date))
    ]

# KPI metrics
col1, col2, col3, col4 = st.columns(4)
col1.metric("🎬 Total Videos Watched", len(filtered_df))
col2.metric("👥 Unique Viewers", filtered_df["User_Email"].nunique())
col3.metric("⏱️ Avg Watch Duration (min)", round(filtered_df["Duration_Watched"].mean(), 2))
col4.metric("✅ Avg Completion %", f"{filtered_df['Completion_%'].mean():.1f}%")

# Data highlights
st.subheader("📊 Data Highlights")
st.write(f"Records after filtering: **{len(filtered_df)}**")
if "Completion_%" in filtered_df.columns:
    st.write(f"Average completion rate: **{filtered_df['Completion_%'].mean():.2f}%**")
top_videos = (
    filtered_df.groupby("Video_Name")["Completion_%"].mean().nlargest(3).index
)
st.write(f"Top 3 engaging videos: {', '.join(top_videos)}")

# Chart 1: Engagement trend
st.subheader("📈 Engagement Trend Over Time")
trend_df = (
    filtered_df.groupby("Date_Watched", as_index=False)["Completion_%"].mean()
    .sort_values("Date_Watched")
)
fig1 = px.line(trend_df, x="Date_Watched", y="Completion_%", title="Average Completion % Over Time")
st.plotly_chart(fig1, use_container_width=True)

# Chart 2: Top videos
st.subheader("🏆 Top Videos by Completion Rate")
top_videos_df = (
    filtered_df.groupby("Video_Name", as_index=False)["Completion_%"].mean().nlargest(10, "Completion_%")
)
fig2 = px.bar(top_videos_df, x="Video_Name", y="Completion_%", title="Top 10 Videos by Completion %")
st.plotly_chart(fig2, use_container_width=True)

# Chart 3: Watch time share
st.subheader("🌍 Watch Time Share by Organization")
if "Organization" in filtered_df.columns:
    fig3 = px.pie(filtered_df, names="Organization", values="Duration_Watched", hole=0.4)
    st.plotly_chart(fig3, use_container_width=True)

# Chart 4: Completion distribution
st.subheader("📊 Completion Rate Distribution")
fig4 = px.histogram(filtered_df, x="Completion_%", nbins=20, title="Distribution of Completion Rates")
st.plotly_chart(fig4, use_container_width=True)

# Download button
st.download_button(
    "📥 Download Cleaned Data",
    filtered_df.to_csv(index=False).encode("utf-8"),
    "cleaned_freefuse_data.csv",
    "text/csv",
)

