import streamlit as st
import pandas as pd
import plotly.express as px
import altair as alt
from notion_client import Client
from datetime import timedelta

st.set_page_config(page_title="Discipline Tracker", layout="wide")

# --- STYLE ---
st.markdown("""
<style>

.stApp {
    background-color: #ffffff;
}

[data-testid="metric-container"] {
    background-color: #f7f7f7;
    border: 1px solid #e6e6e6;
    padding: 15px;
    border-radius: 12px;
}

[data-testid="stMetricValue"] {
    font-size: 30px;
}

.block-container {
    padding-top: 2rem;
}

h1 {
    color: #1f77b4;
}

h2, h3 {
    color: #333333;
}

</style>
""", unsafe_allow_html=True)

# --- NOTION CONFIG ---
notion = Client(auth=st.secrets["NOTION_TOKEN"])
DATABASE_ID = "31b142ff68fe809c9ec0d8dc27dcea43"

# --- DATA LOAD ---
@st.cache_data(ttl=240)
def get_data_from_notion():

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
                f = field["formula"]
                return f.get("number") if f.get("number") else 0

            if field["type"] == "number":
                return field.get("number") if field.get("number") else 0

            return 0

        def get_d(key):
            field = props.get(key)

            if field and field.get("date") and field["date"].get("start"):
                return pd.to_datetime(field["date"]["start"])

            return None

        def get_c(key):
            return props.get(key, {}).get("checkbox", False)

        gym = props.get("Gym", {}).get("checkbox", False)
        study = get_val("Study_hours")
        pushup = get_val("push_ups")

        wake_up_time = get_d("wake_up")
        sleep_time = get_d("sleep")

        leisure = get_val("leisure_time")
        eat = get_val("Eat_times")

        nsfw = get_val("NSFW_Event")
        sleep_duration = get_val("Sleep_Hours")

        score_calc = (
            (20 if gym else 0)
            + min(study * 5, 30)
            + min(pushup / 5, 20)
            + (15 if (sleep_duration >= 8) else 0)
            + (10 if leisure <= 5 else 0)
            + (5 if eat >= 3 else 0)
            - (10 if nsfw == 1 else 0)
            # - (10 if sleep_time and sleep_time.hour == 1 or sleep_time.hour == 2 else 0)
        )

        if score_calc >= 75:
            status_calc = "🔥 Disciplined Day"
        elif score_calc >= 50:
            status_calc = "😊 Avg Day"
        else:
            status_calc = "💀 Wasted Day"
        
        data.append({
            "Date": props["Date"]["date"]["start"],
            "Score": score_calc,
            "Paid": get_val("Paid"),
            "Water": get_c("hygrade"),
            "Gym": gym,
            "Study": study,
            "Status": status_calc,
            "WakeUp": wake_up_time,
            "Sleep": sleep_time,
            "NSFW": get_val("NSFW_Event"),
        })

    return pd.DataFrame(data)

df = get_data_from_notion()
if "NSFW" not in df.columns:
    df["NSFW"] = 0
df['Date'] = pd.to_datetime(df['Date'])
df = df.sort_values("Date")
# -------- STREAK CALCULATION --------

df["Disciplined"] = df["Score"] >= 70

best_streak = 0
current = 0

for val in df["Disciplined"]:
    if val:
        current += 1
        best_streak = max(best_streak, current)
    else:
        current = 0
df["CleanDay"] = df["NSFW"] == 0

best_nsfw_streak = 0
current = 0

for val in df["CleanDay"]:
    if val:
        current += 1
        best_nsfw_streak = max(best_nsfw_streak, current)
    else:
        current = 0

# current streak (tính từ ngày gần nhất)
current_streak = 0

for val in reversed(df["Disciplined"].tolist()):
    if val:
        current_streak += 1
    else:
        break
# -------- MONTH FILTER --------

df["Month"] = df["Date"].dt.strftime("%B %Y")

months = sorted(df["Month"].unique(), reverse=True)

selected_month = st.selectbox(
    "📅 Select Month",
    months
)

df = df[df["Month"] == selected_month]
df['Date_Str'] = df['Date'].dt.strftime('%d/%m')

df['Sleep_Duration'] = (df['WakeUp'] - df['Sleep']).dt.total_seconds() / 3600
df.loc[df['Sleep_Duration'] < 0, 'Sleep_Duration'] += 24
def metric_card(label, value):
    """Creates a consistent, bordered metric card."""
    with st.container(border=True):
        st.metric(label, value)
# --- KPIs ---
st.title("📊 Discipline Control Center")
current_nsfw_streak = 0

for val in reversed(df["CleanDay"].tolist()):
    if val:
        current_nsfw_streak += 1
    else:
        break
    
c1, c2, c3, c4,c9,c11 = st.columns(6)
with c1: metric_card("Avg Score", f"{df['Score'].mean():.1f}")
with c2: metric_card("Total Paid", f"{df['Paid'].sum():,.0f} VNĐ")
with c3: metric_card("Gym Days", df['Gym'].sum())
with c4: metric_card("Study Hours", f"{df['Study'].sum():.1f}")
with c9: metric_card("🔥 Current Streak", current_streak)
with c11: metric_card("🧘 Phim Streak", current_nsfw_streak)

c5, c6, c7, c8,c10,c12 = st.columns(6)
with c5: metric_card("🔥 Discipline Days", (df["Score"] >= 70).sum())
with c6: metric_card("📚 Avg Study/Day", f"{df['Study'].mean():.1f}h")
with c7: metric_card("😴 Avg Sleep", f"{df['Sleep_Duration'].mean():.1f}h")
with c8: metric_card("💪 Gym Rate", f"{(df['Gym'].sum() / len(df)) * 100:.0f}%")
with c10: metric_card("🏆 Best Streak", best_streak)
with c12: metric_card("🧘 Best Phim Streak", best_nsfw_streak)
st.divider()
# --- SCORE TREND ---
col1, col2, col3 = st.columns(3)

with col1:

    st.subheader("Score Trend")

    fig_line = px.line(
        df,
        x="Date_Str",
        y="Score",
        markers=True,
        template="plotly_white"
    )

    fig_line.update_yaxes(range=[0, 100])

    st.plotly_chart(fig_line, use_container_width=True)

with col2:

    st.subheader("Day Status")

    status_count = df["Status"].value_counts().reset_index()
    status_count.columns = ["Status", "Days"]

    fig_status = px.bar(
        status_count,
        x="Status",
        y="Days",
        color="Status",
        template="plotly_white",
        color_discrete_map={
            "🔥 Disciplined Day": "#2ecc71",
            "😊 Avg Day": "#f1c40f",
            "💀 Wasted Day": "#e74c3c"
        }
    )

    st.plotly_chart(fig_status, use_container_width=True)

with col3:

    st.subheader("Daily Spending")

    base = alt.Chart(df).encode(
        x='Date_Str:O',
        y='Paid:Q'
    )

    line = base.mark_line(color='#ff4b4b')

    rule = alt.Chart(
        pd.DataFrame({'y': [100000]})
    ).mark_rule(
        color='green',
        strokeDash=[5,5]
    ).encode(y='y')

    st.altair_chart(line + rule, use_container_width=True)

# --- SLEEP ---
col4, col5, col6 = st.columns(3)

with col4:

    st.subheader("Sleep Patterns")

    sleep_df = df[df['Sleep'].notna()].copy()

    sleep_df['Hour'] = sleep_df['Sleep'].dt.hour + sleep_df['Sleep'].dt.minute / 60

    fig_sleep = px.scatter(
        sleep_df,
        x="Date_Str",
        y="Hour",
        template="plotly_white"
    )

    fig_sleep.update_yaxes(range=[0,24])

    st.plotly_chart(fig_sleep, use_container_width=True)

with col5:

    st.subheader("WakeUp Patterns")

    wake_df = df[df['WakeUp'].notna()].copy()

    wake_df['Hour'] = wake_df['WakeUp'].dt.hour + wake_df['WakeUp'].dt.minute / 60

    fig_wake = px.scatter(
        wake_df,
        x="Date_Str",
        y="Hour",
        template="plotly_white"
    )

    fig_wake.update_yaxes(range=[0,24])

    st.plotly_chart(fig_wake, use_container_width=True)

with col6:

    st.subheader("Sleep Duration")

    chart = alt.Chart(df).mark_line(point=True).encode(
        x='Date_Str:O',
        y='Sleep_Duration:Q'
    )

    st.altair_chart(chart, use_container_width=True)

st.divider()


st.divider()

col7, col8 = st.columns(2)

# --- GYM ACTIVITY ---
with col7:

    st.subheader("💪 Gym Activity")

    gym_df = df.copy()

    gym_df = gym_df[gym_df["Gym"] == True]

    gym_df["Weekday"] = gym_df["Date"].dt.day_name()
    gym_df["WeekOfMonth"] = (gym_df["Date"].dt.day - 1) // 7 + 1
    gym_df["Month"] = gym_df["Date"].dt.strftime("%b")

    gym_df["WeekLabel"] = "W" + gym_df["WeekOfMonth"].astype(str) + " " + gym_df["Month"]

    order = ["Monday","Tuesday","Wednesday","Thursday","Friday","Saturday","Sunday"]
    gym_df["Weekday"] = pd.Categorical(gym_df["Weekday"], categories=order, ordered=True)

    fig = px.scatter(
        gym_df,
        x="WeekLabel",
        y="Weekday",
        hover_data=["Date"]
    )

    fig.update_traces(
        marker=dict(
            size=18,
            color="#2ecc71"
        )
    )

    fig.update_layout(
        template="plotly_white",
        xaxis_title="",
        yaxis_title="",
        height=320
    )

    st.plotly_chart(fig, use_container_width=True)

# --- STUDY HOURS ---
with col8:

    st.subheader("📚 Study Hours Trend")

    fig_study = px.line(
        df,
        x="Date_Str",
        y="Study",
        markers=True,
        template="plotly_white"
    )

    st.plotly_chart(fig_study, use_container_width=True)

st.divider()

# =============================
# EXTRA ANALYTICS
# =============================

col9, col10 = st.columns(2)

# --- STUDY VS SCORE ---
with col9:

    st.subheader("📈 Study vs Score")

    fig_corr = px.scatter(
        df,
        x="Study",
        y="Score",
        trendline="ols",
        template="plotly_white"
    )

    st.plotly_chart(fig_corr, use_container_width=True)


# --- CLEAN DAYS TRACKER ---
with col10:

    st.subheader("🧘 Clean Days (NSFW Tracker)")

    clean_df = df.copy()
    clean_df["Clean"] = clean_df["NSFW"].apply(lambda x: "❌" if x else "✅")

    fig_clean = px.scatter(
        clean_df,
        x="Date_Str",
        y="Clean",
        template="plotly_white"
    )

    st.plotly_chart(fig_clean, use_container_width=True)



st.divider()

col11, col12 = st.columns(2)

# --- SCORE DISTRIBUTION ---
with col11:

    st.subheader("📊 Score Distribution")

    fig_hist = px.histogram(
        df,
        x="Score",
        nbins=10,
        template="plotly_white"
    )

    st.plotly_chart(fig_hist, use_container_width=True)


# --- DISCIPLINE CALENDAR STYLE ---
with col12:

    st.subheader("🔥 Discipline Days Timeline")

    cal_df = df.copy()

    cal_df["Disciplined"] = cal_df["Score"].apply(
        lambda x: "🔥" if x >= 70 else "❌"
    )

    fig_cal = px.scatter(
        cal_df,
        x="Date_Str",
        y="Disciplined",
        template="plotly_white"
    )

    st.plotly_chart(fig_cal, use_container_width=True)

# --- TABLE ---
with st.expander("Xem chi tiết logs"):
    st.dataframe(df.sort_values("Date", ascending=False))