import streamlit as st
import pandas as pd
import plotly.express as px
import altair as alt
from notion_client import Client
from datetime import timedelta

st.set_page_config(page_title="Discipline Tracker", layout="wide")

# ---------------- STYLE ----------------

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

.block-container {
    padding-top: 2rem;
}

</style>
""", unsafe_allow_html=True)

# ---------------- NOTION ----------------

notion = Client(auth=st.secrets["NOTION_TOKEN"])
DATABASE_ID = "31b142ff68fe809c9ec0d8dc27dcea43"

# ---------------- LOAD DATA ----------------

@st.cache_data(ttl=600)
def get_data():

    db = notion.databases.retrieve(database_id=DATABASE_ID)
    data_source_id = db["data_sources"][0]["id"]

    res = notion.data_sources.query(data_source_id=data_source_id)

    rows = []

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
            if field and field.get("date"):
                return pd.to_datetime(field["date"]["start"])
            return None

        def get_c(key):
            return props.get(key, {}).get("checkbox", False)

        gym = get_c("Gym")
        study = get_val("Study_hours")
        pushup = get_val("push_ups")

        wake = get_d("wake_up")
        sleep = get_d("sleep")

        leisure = get_val("leisure_time")
        eat = get_val("Eat_times")

        score = (
            (20 if gym else 0)
            + min(study * 5, 30)
            + min(pushup / 5, 20)
            + (15 if (wake and (wake + timedelta(hours=7)).hour <= 8) else 0)
            + (10 if leisure <= 2 else 0)
            + (5 if eat >= 3 else 0)
        )

        if score >= 70:
            status = "🔥 Disciplined Day"
        elif score >= 50:
            status = "😊 Avg Day"
        else:
            status = "💀 Wasted Day"

        rows.append({
            "Date": props["Date"]["date"]["start"],
            "Score": score,
            "Paid": get_val("Paid"),
            "Gym": gym,
            "Study": study,
            "Status": status,
            "WakeUp": wake,
            "Sleep": sleep
        })

    return pd.DataFrame(rows)


df = get_data()

df["Date"] = pd.to_datetime(df["Date"])
df = df.sort_values("Date")

df["Date_Str"] = df["Date"].dt.strftime("%d/%m")

df["Sleep_Duration"] = (df["WakeUp"] - df["Sleep"]).dt.total_seconds() / 3600
df.loc[df["Sleep_Duration"] < 0, "Sleep_Duration"] += 24

# ---------------- MONTH FILTER ----------------

df["Month"] = df["Date"].dt.strftime("%B %Y")

months = sorted(df["Month"].unique(), reverse=True)

selected_month = st.selectbox("📅 Select Month", months)

df = df[df["Month"] == selected_month]

# ---------------- STREAK CALCULATION ----------------

df["Disciplined"] = df["Score"] >= 70

streak = 0
best = 0

for val in df["Disciplined"]:
    if val:
        streak += 1
        best = max(best, streak)
    else:
        streak = 0

current_streak = 0

for val in reversed(df["Disciplined"].tolist()):
    if val:
        current_streak += 1
    else:
        break

# ---------------- KPI ----------------

st.title("📊 Discipline Control Center")

c1,c2,c3,c4 = st.columns(4)

c1.metric("Avg Score", f"{df['Score'].mean():.1f}")
c2.metric("Total Paid", f"{df['Paid'].sum():,.0f} VNĐ")
c3.metric("🔥 Current Streak", current_streak)
c4.metric("🏆 Best Streak", best)

c5,c6,c7,c8 = st.columns(4)

c5.metric("Gym Days", df["Gym"].sum())
c6.metric("Study Hours", f"{df['Study'].sum():.1f}")
c7.metric("😴 Avg Sleep", f"{df['Sleep_Duration'].mean():.1f}h")
c8.metric("💪 Gym Rate", f"{(df['Gym'].sum()/len(df))*100:.0f}%")

st.divider()

# ---------------- CHART ROW 1 ----------------

col1,col2,col3 = st.columns(3)

with col1:

    st.subheader("Score Trend")

    fig = px.line(df,x="Date_Str",y="Score",markers=True)

    fig.update_yaxes(range=[0,100])

    st.plotly_chart(fig,use_container_width=True)

with col2:

    st.subheader("Day Status")

    status = df["Status"].value_counts().reset_index()
    status.columns=["Status","Days"]

    fig = px.bar(status,x="Status",y="Days",color="Status")

    st.plotly_chart(fig,use_container_width=True)

with col3:

    st.subheader("Daily Spending")

    base = alt.Chart(df).encode(x="Date_Str:O",y="Paid:Q")

    line = base.mark_line()

    st.altair_chart(line,use_container_width=True)

# ---------------- CHART ROW 2 ----------------

col4,col5,col6 = st.columns(3)

with col4:

    st.subheader("Sleep Patterns")

    sleep_df = df[df["Sleep"].notna()].copy()

    sleep_df