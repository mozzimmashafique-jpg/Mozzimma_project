# --------------------------- VISUALS ---------------------------
st.markdown("## 📊 Engagement Insights")

if not fwh.empty and "created_date" in fwh.columns:
    # 1️⃣ Engagement Trend Over Time — Line + Area Chart
    st.markdown("### 📈 Engagement Trend Over Time")
    daily = fwh.groupby("created_date").size().reset_index(name="views")
    fig1 = px.area(
        daily, x="created_date", y="views",
        title="Daily Video Engagement",
        color_discrete_sequence=["#6A5ACD"],
        line_shape="spline"
    )
    fig1.update_traces(line_color="#4B0082", fill="tozeroy", opacity=0.4)
    fig1.update_layout(xaxis_title="Date", yaxis_title="Views", height=380)
    st.plotly_chart(fig1, use_container_width=True)

    # 2️⃣ Top 10 Videos by Average Duration — Lollipop Chart
    st.markdown("### ⏱️ Top 10 Videos by Average Duration Watched")
    if "video_title" in fwh.columns:
        top_avg = fwh.groupby("video_title")["duration_min"].mean().nlargest(10).reset_index()
        fig2 = px.scatter(
            top_avg, x="duration_min", y="video_title",
            color_discrete_sequence=["#9370DB"], size="duration_min", size_max=15
        )
        # Add connecting lines for lollipop effect
        for _, row in top_avg.iterrows():
            fig2.add_shape(type="line", x0=0, x1=row["duration_min"], y0=row["video_title"], y1=row["video_title"],
                           line=dict(color="#9370DB", width=2))
        fig2.update_layout(height=420, xaxis_title="Avg Duration (min)", yaxis_title="Video Title",
                           yaxis={'categoryorder': 'total ascending'})
        st.plotly_chart(fig2, use_container_width=True)

    # 3️⃣ Viewing Duration Distribution — Box Plot
    st.markdown("### 🎬 Viewing Duration Distribution")
    fig3 = px.box(
        fwh, y="duration_min",
        color_discrete_sequence=["#8A2BE2"],
        points="all",
        title="Distribution of Viewing Durations"
    )
    fig3.update_layout(height=420, yaxis_title="Watch Duration (min)")
    st.plotly_chart(fig3, use_container_width=True)

# 4️⃣ Yearly Comparison — Donut Pie Chart
st.markdown("### 🔄 Video Counts by Academic Year (2022/2023 vs 2023/2024)")
if "acad_year" in counts.columns:
    vc = counts[counts["acad_year"].isin(["2022/2023", "2023/2024"])]
    if not vc.empty:
        total = vc.groupby("acad_year")["view_count"].sum().reset_index()
        fig4 = px.pie(
            total, names="acad_year", values="view_count",
            hole=0.5, color_discrete_sequence=["#9370DB", "#BA55D3"],
            title="Share of Total Views by Academic Year"
        )
        fig4.update_traces(textinfo="percent+label", pull=[0.05, 0])
        fig4.update_layout(height=420)
        st.plotly_chart(fig4, use_container_width=True)

# 5️⃣ Repeat Users — Bubble Scatter Chart
st.markdown("### 👥 Repeat Users — Videos Watched per User")
if "user_id" in fwh.columns:
    per_user = fwh.groupby("user_id")["video_id"].nunique().value_counts().reset_index()
    per_user.columns = ["Videos Watched", "User Count"]
    fig5 = px.scatter(
        per_user, x="Videos Watched", y="User Count",
        size="User Count", color="Videos Watched",
        color_continuous_scale="Purples",
        title="User Engagement Spread",
        size_max=40
    )
    fig5.update_layout(height=420, xaxis_title="Videos Watched", yaxis_title="User Count")
    st.plotly_chart(fig5, use_container_width=True)
else:
    st.info("No user ID column found, skipping repeat user analysis.")



