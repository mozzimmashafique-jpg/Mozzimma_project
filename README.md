streamlit app 

**FreeFuse Engagement Analytics – Streamlit Dashboards**
A dual-dashboard analytics suite for understanding watch behavior, engagement, and viewing patterns on the FreeFuse learning platform.

**Problem Statement**

FreeFuse collects large amounts of watch-history, video engagement, and questionnaire activity data from multiple academic years. However, this data is stored across several raw Excel files with inconsistent column names, missing values, irregular timestamps, and unstructured formats.

Because of this, FreeFuse faces several challenges:

-Decision-makers cannot easily access a centralized view of platform engagement.
-Video performance cannot be compared across time periods or academic years.
-High-engagement and low-engagement content is difficult to identify.
-Viewing behaviour patterns such as peak days, hours, or AM/PM trends are unclear.
-Questionnaire participation and completion rates are not easily measurable.
-Viewer-level insights such as repeat-user behaviour are not immediately visible.
-Manual data cleaning and merging is time-consuming and prone to error.

FreeFuse required an automated, interactive analytics solution that presents engagement trends clearly and allows non-technical users to explore insights intuitively.

**Solution Overview: Streamlit Engagement Dashboards**

This project provides two interactive Streamlit dashboards that clean, transform, and visualize FreeFuse’s engagement datasets. These dashboards automate data preparation and deliver real-time analytical insights.

**Step-by-Step Solution Approach**

**1. Data Extraction and Preparation**

-Load raw datasets from Excel files.
-Normalize inconsistent and irregular column names.
-Clean and validate timestamps, dates, and times.
-Merge date and time into a single timestamp where necessary.
-Convert duration fields into consistent minutes.
-Clean video names and remove incomplete or invalid records.
-Standardize completion values across multiple formats.

**2. Build a Clean Analytical Dataset**

-Extract year, month, hour, and day-of-week from timestamps.
-Classify AM and PM values, even with inconsistent time formats.
-Label repeat viewers and unique users.
-Identify top-performing content by views and duration.
-Remove empty or duplicated video records.

**3. Create Interactive Filters**

*Users can dynamically filter data by*:

-Date range
-Hour of day
-AM or PM
-Academic year
-Video title
-Completed vs not completed views
-Questionnaire participation

**4. Compute Core Engagement Metrics**

*Each dashboard automatically calculates metrics such as*:

-Total views
-Unique viewers
-Unique videos
-Average watch duration
-Total minutes watched
-Completion rate
-Most engaged video
-Viewer-level questionnaire participation

**5. Develop Interactive Visualizations**

***Dashboard 1 includes***:

-Views over time
-Day × hour heatmap
-Hourly viewership trend
-Top videos by total views
-Completion-rate comparison
-Questionnaire participation analysis

***Dashboard 2 includes:***

*Daily engagement trend*

-Top videos by average duration (lollipop chart)
-Viewing duration distribution (violin plot)
-Top videos by academic year comparison
-Repeat-user analysis

**6. Enable Data Export**

Each dashboard provides a downloadable CSV of the filtered dataset to support reporting, offline analysis, or further modeling.

**7. Prepare a Clean Repository Structure**

The project is organized with separate app files, a data directory, asset folder, optional utilities, and a .gitignore to avoid committing raw datasets. Documentation is consolidated in a clean, readable README.

**Impact for FreeFuse**

These dashboards allow FreeFuse to:

-Identify high-performing and low-performing content.
-Observe when users are most engaged throughout the day and week.
-Understand trends across academic years.
-Measure content completion, questionnaire engagement, and retention.
-Report insights clearly to internal teams, educators, and partner organizations.
-Make informed product, content, and operational decisions using real data.
