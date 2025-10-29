import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px

# ------------------------------------------------------------
# PAGE CONFIG
# ------------------------------------------------------------
st.set_page_config(page_title="FreeFuse Engagement Dashboard", layout="wide")

st.title("🎥 FreeFuse Engagement Dashboard")
st.caption("An interactive visualization of ASPIRA students' engagement with FreeFuse videos.")

# ------------------------------------------------------------
# LOAD & CLEAN DATA
# ------------------------------------------------------------
@st.cache_data
def load_and_clean(path: str) -> pd.DataFrame:
    df = pd.read_excel(path)
    df.columns = df.columns.str.strip()

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

    # Combine date + time safely
    if "View_Date" in df.columns:
        if "View_Time" in df.columns:
            df["View_Timestamp"] = pd.to_datetime(
                df["View_Date"].astype(str) + " " + df["View_Time"].astype(str),
                errors="coerce"
            )
        else:
            df["View_Timestamp"] = pd.to_datetime(df["View_Date"], errors="coerce")
    else:
        df["View_Timestamp"] = pd.NaT

    # Always create a date-only column safely
    df["View_DateOnly"] = pd.to_datetime(df["View_Timestamp"], errors="coerce").dt.date

    # Clean duration
    if "Viewing_Duration_Sec" in df.columns:
        df["Viewing_Duration_Sec"] = pd.to_numeric(df["Viewing_Duration_Sec"], errors="coerce")
        df["Viewing_Duration_Min"] = df["Viewing_Duration_Sec"] / 60
        df = df[df["Viewing_Duration_Min"] > 0]

    # Standardize completion column
    if "Done_Viewing" in df.columns:
        df["Done_Viewing"] = df["Done_Viewing"].astype(str).str.lower().map({
            "yes": True, "true": True, "1": True, "y": True,
            "no": False, "false": False, "0": False, "n": False
        })

    df.dropna(subset=["Video_Name"], inplace=True)
    df.drop_duplicates(inplace=True)

    return df

df = load_and_clean("Freefuse_Data.xlsx")

# ------------------------------------------------------------
# SIDEBAR FILTERS
# ------------------------------------------------------------
st.sidebar.header("🔎 Filters")

video_filter = st.sidebar.multiselect("🎬 Select Video", sorted(df["Video_Name"].unique()))

completion_filter = st.sidebar.radio("✅ Completion Status", ["All", "Completed", "Not Completed"], index=0)

# Handle missing dates safely
if "View_DateOnly" in df.columns and df["View_DateOnly"].notna().any():
    min_date, max_date = df["View_DateOnly"].min(), df["View_DateOnly"].max()
else:
    min_date, max_date = pd.to_datetime("2024-01-01"), pd.to_datetime("2024-12-31")

date_range = st.sidebar.date_input("📅 Select Date Range", [min_date, max_date])

filtered_df = df.copy()

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

c1, c2, c3, c4 = st.columns(4)

total_views = len(filtered_df)
unique_viewers = filtered_df["Viewer"].nunique() if "Viewer" in filtered_df.columns else 0
avg_duration = filtered_df["Viewing_Duration_Min"].mean() if "Viewing_Duration_Min" in filtered_df.columns else 0
completion_rate = (
    filtered_df["Done_Viewing"].mean() * 100 if "Done_Viewing" in filtered_df.columns else 0
)

c1.metric("🎬 Total Views", f"{total_views:,}")
c2.metric("👥 Unique Viewers", f"{unique_viewers:,}")
c3.metric("⏱️ Avg Duration (min)", f"{avg_duration:.2f}")
c4.metric("✅ Completion Rate", f"{completion_rate:.1f}%")

st.markdown("---")

# ------------------------------------------------------------
# CHARTS
# ------------------------------------------------------------

# 1️⃣ Engagement Trend
if "View_DateOnly" in filtered_df.columns and not filtered_df.empty:
    st.subheader("📈 Engagement Trend Over Time")
    trend_df = filtered_df.groupby("View_DateOnly").size().reset_index(name="Total_Views")
    fig1 = px.line(trend_df, x="View_DateOnly", y="Total_Views", markers=True, title="Views Over Time")
    st.plotly_chart(fig1, use_container_width=True)

# 2️⃣ Bar Chart: Top Videos by Duration
if "Video_Name" in filtered_df.columns and "Viewing_Duration_Min" in filtered_df.columns:
    st.subheader("🏆 Top 10 Videos by Average Duration")
    top_videos_df = (
        filtered_df.groupby("Video_Name", as_index=False)["Viewing_Duration_Min"]
        .mean()
        .sort_values("Viewing_Duration_Min", ascending=False)
        .head(10)
    )
    fig2 = px.bar(top_videos_df, x="Video_Name", y="Viewing_Duration_Min",
                  title="Top 10 Videos by Avg Duration (Minutes)",
                  color="Viewing_Duration_Min", color_continuous_scale="Blues")
    fig2.update_layout(xaxis_title="Video", yaxis_title="Avg Duration (min)")
    st.plotly_chart(fig2, use_container_width=True)

# 3️⃣ Pie Chart: Completion Breakdown
if "Done_Viewing" in filtered_df.columns:
    st.subheader("🥧 Completion Breakdown")
    comp_counts = filtered_df["Done_Viewing"].value_counts(dropna=True)
    pie_df = pd.DataFrame({
        "Status": ["Completed" if k else "Not Completed" for k in comp_counts.index],
        "Count": comp_counts.values
    })
    fig3 = px.pie(pie_df, names="Status", values="Count", color="Status",
                  title="Overall Completion Breakdown",
                  color_discrete_map={"Completed": "green", "Not Completed": "red"})
    st.plotly_chart(fig3, use_container_width=True)

# 4️⃣ Histogram: Viewing Duration Distribution
if "Viewing_Duration_Min" in filtered_df.columns:
    st.subheader("📊 Viewing Duration Distribution")
    fig4 = px.histogram(filtered_df, x="Viewing_Duration_Min", nbins=30,
                        title="Distribution of Viewing Duration (Minutes)",
                        color_discrete_sequence=["#636EFA"])
    fig4.update_layout(xaxis_title="Duration (min)", yaxis_title="Frequency")
    st.plotly_chart(fig4, use_container_width=True)

# ------------------------------------------------------------
# DOWNLOAD CLEANED DATA
# ------------------------------------------------------------
st.download_button(
    "📥 Download Filtered Data (CSV)",
    filtered_df.to_csv(index=False).encode("utf-8"),
    "Freefuse_Cleaned_Filtered.csv",
    "text/csv"
)
