import streamlit as st
import pandas as pd
import plotly.express as px

# ------------------------------------------------------------
# PAGE CONFIG
# ------------------------------------------------------------
st.set_page_config(page_title="FreeFuse Engagement Dashboard", layout="wide")

# Style the app
st.markdown("""
    <style>
        [data-testid="stSidebar"] {
            background-color: #f4f1fb;
        }
        h1, h2, h3 {
            color: #3b0764;
        }
    </style>
""", unsafe_allow_html=True)

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

    # Clean invalid video names
    if "Video_Name" in df.columns:
        df["Video_Name"] = df["Video_Name"].astype(str).str.strip()
        df = df[
            df["Video_Name"].notna()
            & (df["Video_Name"].str.len() > 1)
            & (~df["Video_Name"].str.contains(r"[^a-zA-Z0-9\s\-:,.!?]", na=False))
        ]

    # Combine date + time and convert to proper datetime
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

    # Create a proper datetime.date column for filtering
    df["View_DateOnly"] = pd.to_datetime(df["View_Timestamp"], errors="coerce").dt.date

    # Ensure that View_DateOnly is actually a datetime.date (not string)
    df = df[df["View_DateOnly"].notna()]
    df["View_DateOnly"] = pd.to_datetime(df["View_DateOnly"], errors="coerce").dt.date

    # Duration conversion
    if "Viewing_Duration_Sec" in df.columns:
        df["Viewing_Duration_Sec"] = pd.to_numeric(df["Viewing_Duration_Sec"], errors="coerce")
        df["Viewing_Duration_Min"] = df["Viewing_Duration_Sec"] / 60
        df = df[df["Viewing_Duration_Min"] > 0]

    # Clean Done_Viewing
    if "Done_Viewing" in df.columns:
        df["Done_Viewing"] = df["Done_Viewing"].astype(str).str.lower().map({
            "yes": True, "true": True, "1": True, "y": True,
            "no": False, "false": False, "0": False, "n": False
        })

    df.drop_duplicates(inplace=True)
    return df

df = load_and_clean("Freefuse_Data.xlsx")

# ------------------------------------------------------------
# SIDEBAR FILTERS
# ------------------------------------------------------------
st.sidebar.header("🔎 Filters")

video_filter = st.sidebar.multiselect("🎬 Select Video", sorted(df["Video_Name"].unique()))
completion_filter = st.sidebar.radio("✅ Completion Status", ["All", "Completed", "Not Completed"], index=0)

# Safe min/max dates for Streamlit date picker
if df["View_DateOnly"].notna().any():
    min_date = min(df["View_DateOnly"])
    max_date = max(df["View_DateOnly"])
else:
    min_date, max_date = pd.to_datetime("2024-01-01").date(), pd.to_datetime("2024-12-31").date()

date_range = st.sidebar.date_input("📅 Select Date Range", [min_date, max_date])

filtered_df = df.copy()

# Apply filters
if video_filter:
    filtered_df = filtered_df[filtered_df["Video_Name"].isin(video_filter)]

if completion_filter == "Completed":
    filtered_df = filtered_df[filtered_df["Done_Viewing"] == True]
elif completion_filter == "Not Completed":
    filtered_df = filtered_df[filtered_df["Done_Viewing"] == False]

# ✅ Fix: Handle both single-date and multi-date input safely
if isinstance(date_range, list) and len(date_range) == 2:
    start, end = date_range
elif isinstance(date_range, list) and len(date_range) == 1:
    start = end = date_range[0]
else:
    start, end = min_date, max_date

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

# 1️⃣ Line Chart: Views Over Time
if not filtered_df.empty:
    st.subheader("📈 Engagement Trend Over Time")
    trend_df = filtered_df.groupby("View_DateOnly").size().reset_index(name="Total_Views")
    fig1 = px.line(trend_df, x="View_DateOnly", y="Total_Views", markers=True,
                   title="Views Over Time", color_discrete_sequence=["#7B68EE"])
    fig1.update_layout(xaxis_title="Date", yaxis_title="Total Views")
    st.plotly_chart(fig1, use_container_width=True)

# 2️⃣ Bar Chart: Top 10 Videos
if "Video_Name" in filtered_df.columns and "Viewing_Duration_Min" in filtered_df.columns:
    st.subheader("🏆 Top 10 Videos by Avg Duration")
    top_videos_df = (
        filtered_df.groupby("Video_Name", as_index=False)["Viewing_Duration_Min"]
        .mean()
        .sort_values("Viewing_Duration_Min", ascending=False)
        .head(10)
    )
    fig2 = px.bar(top_videos_df, x="Video_Name", y="Viewing_Duration_Min",
                  title="Top 10 Videos by Avg Duration (Minutes)",
                  color="Viewing_Duration_Min", color_continuous_scale="Purples")
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
    fig3 = px.pie(pie_df, names="Status", values="Count",
                  title="Completion Breakdown",
                  color="Status", color_discrete_map={"Completed": "green", "Not Completed": "red"})
    st.plotly_chart(fig3, use_container_width=True)

# 4️⃣ Histogram: Viewing Duration Distribution
if "Viewing_Duration_Min" in filtered_df.columns:
    st.subheader("📊 Viewing Duration Distribution")
    fig4 = px.histogram(filtered_df, x="Viewing_Duration_Min", nbins=30,
                        title="Distribution of Viewing Duration (Minutes)",
                        color_discrete_sequence=["#6A5ACD"])
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


