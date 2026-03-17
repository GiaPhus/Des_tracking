import streamlit as st
import pandas as pd
import plotly.express as px
import altair as alt
from notion_client import Client

st.set_page_config(page_title="Discipline Tracker", layout="wide")

# =============================
# THEME DETECTION
# =============================
theme = st.get_option("theme.base")

if theme == "dark":
    plotly_template = "plotly_dark"
    text_color = "white"
    alt.themes.enable("dark")
else:
    plotly_template = "plotly_white"
    text_color = "black"
    alt.themes.enable("default")

# =============================
# STYLE
# =============================
st.markdown(f"""
<style>

.stApp {{
    background-color: transparent;
}}

.block-container {{
    padding-top: 1rem;
    padding-bottom: 2rem;
}}

[data-testid="metric-container"] {{
    background-color: rgba(255,255,255,0.05);
    border: 1px solid rgba(200,200,200,0.2);
    padding: 15px;
    border-radius: 12px;
}}

[data-testid="metric-container"]:hover {{
    transform: scale(1.03);
    transition: 0.2s;
}}

[data-testid="stMetricValue"] {{
    font-size: 30px;
}}

</style>
""", unsafe_allow_html=True)

# =============================
# TITLE
# =============================
st.markdown("""
<h1 style='
    background: linear-gradient(90deg, #00c6ff, #0072ff);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
'>
📊 Discipline Control Center
</h1>
""", unsafe_allow_html=True)

# =============================
# NOTION CONFIG
# =============================
notion = Client(auth=st.secrets["NOTION_TOKEN"])
DATABASE_ID = "31b142ff68fe809c9ec0d8dc27dcea43"

# =============================
# LOAD DATA
# =============================
@st.cache_data(ttl=240)
def get_data():
    db = notion.databases.retrieve(database_id=DATABASE_ID)
    data_source_id = db["data_sources"][0]["id"]
    res = notion.data_sources.query(data_source_id=data_source_id)

    data = []

    for page in res["results"]:
        props = page["properties"]

        def get_val(key):
            field = props.get(key)
            if not field:
                return 0
            if field["type"] == "formula":
                return field["formula"].get("number") or 0
            if field["type"] == "number":
                return field.get("number") or 0
            return 0

        def get_d(key):
            field = props.get(key)
            if field and field.get("date") and field["date"].get("start"):
                return pd.to_datetime(field["date"]["start"])
            return None

        gym = props.get("Gym", {}).get("checkbox", False)
        study = get_val("Study_hours")
        pushup = get_val("push_ups")
        sleep_time = get_d("sleep")
        wake_up_time = get_d("wake_up")
        leisure = get_val("leisure_time")
        eat = get_val("Eat_times")
        nsfw = get_val("NSFW_Event")
        sleep_duration = get_val("Sleep_Hours")

        # FIX LOGIC BUG
        score = (
            (20 if gym else 0)
            + min(study * 5, 30)
            + min(pushup / 5, 20)
            + (15 if sleep_duration >= 8 else 0)
            + (10 if leisure <= 5 else 0)
            + (5 if eat >= 3 else 0)
            - (10 if nsfw == 1 else 0)
            - (5 if sleep_time and (sleep_time.hour in [1, 2]) else 0)
        )

        if score >= 70:
            status = "🔥 Disciplined Day"
        elif score >= 50:
            status = "😊 Avg Day"
        else:
            status = "💀 Wasted Day"

        data.append({
            "Date": props["Date"]["date"]["start"],
            "Score": score,
            "Paid": get_val("Paid"),
            "Gym": gym,
            "Study": study,
            "Status": status,
            "WakeUp": wake_up_time,
            "Sleep": sleep_time,
            "NSFW": nsfw
        })

    return pd.DataFrame(data)

df = get_data()
df["Date"] = pd.to_datetime(df["Date"])
df = df.sort_values("Date")

# =============================
# FEATURE ENGINEERING
# =============================
df["Disciplined"] = df["Score"] >= 70
df["CleanDay"] = df["NSFW"] == 0
df["Date_Str"] = df["Date"].dt.strftime("%d/%m")

df["Sleep_Duration"] = (df["WakeUp"] - df["Sleep"]).dt.total_seconds() / 3600
df.loc[df["Sleep_Duration"] < 0, "Sleep_Duration"] += 24

# =============================
# STREAK
# =============================
def calc_streak(series):
    best = cur = 0
    for v in series:
        if v:
            cur += 1
            best = max(best, cur)
        else:
            cur = 0
    return best

best_streak = calc_streak(df["Disciplined"])
best_clean = calc_streak(df["CleanDay"])

current_streak = sum(1 for v in reversed(df["Disciplined"]) if v)
current_clean = sum(1 for v in reversed(df["CleanDay"]) if v)

# =============================
# KPI
# =============================
c1, c2, c3, c4 = st.columns(4)
c1.metric("Avg Score", f"{df['Score'].mean():.1f}")
c2.metric("Total Paid", f"{df['Paid'].sum():,.0f} VNĐ")
c3.metric("🔥 Current Streak", current_streak)
c4.metric("🧘 Clean Streak", current_clean)

# =============================
# SCORE TREND
# =============================
fig = px.line(df, x="Date_Str", y="Score", markers=True, template=plotly_template)
fig.update_layout(font=dict(color=text_color))
st.plotly_chart(fig, use_container_width=True)

# =============================
# STUDY VS SCORE
# =============================
fig2 = px.scatter(
    df,
    x="Study",
    y="Score",
    trendline="ols",
    template=plotly_template
)
fig2.update_layout(font=dict(color=text_color))
st.plotly_chart(fig2, use_container_width=True)

# =============================
# SLEEP CHART
# =============================
chart = alt.Chart(df).mark_line(point=True).encode(
    x='Date_Str:O',
    y='Sleep_Duration:Q'
)
st.altair_chart(chart, use_container_width=True)

# =============================
# TABLE
# =============================
with st.expander("Logs"):
    st.dataframe(df.sort_values("Date", ascending=False))