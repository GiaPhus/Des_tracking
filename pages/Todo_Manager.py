import streamlit as st
import pandas as pd
from datetime import datetime
import calendar

st.set_page_config(page_title="Todo Manager", layout="wide")

st.title("📝 Monthly Todo Manager")

# -----------------------------
# SESSION INIT
# -----------------------------

APP_VERSION = "2"

if "version" not in st.session_state or st.session_state.version != APP_VERSION:
    st.session_state.todos = {}
    st.session_state.version = APP_VERSION

if "todos" not in st.session_state or not isinstance(st.session_state.todos, dict):
    st.session_state.todos = {}

# -----------------------------
# MONTH SELECT
# -----------------------------

today = datetime.today()

col1, col2 = st.columns(2)

with col1:
    year = st.selectbox("Year", list(range(2023, 2030)), index=3)

with col2:
    month = st.selectbox("Month", list(range(1, 13)), index=today.month - 1)

num_days = calendar.monthrange(year, month)[1]

# -----------------------------
# KPI CALCULATION
# -----------------------------

total_tasks = 0
done_tasks = 0
best_streak = 0
current_streak = 0
temp = 0

daily_completion = {}

for day, tasks in st.session_state.todos.items():

    if not isinstance(tasks, list) or len(tasks) == 0:
        continue

    done = sum(1 for t in tasks if isinstance(t, dict) and t.get("done"))

    total_tasks += len(tasks)
    done_tasks += done

    completion = done / len(tasks)

    daily_completion[day] = completion

    if completion == 1:
        temp += 1
        best_streak = max(best_streak, temp)
    else:
        temp = 0

for day in sorted(daily_completion.keys(), reverse=True):
    if daily_completion[day] == 1:
        current_streak += 1
    else:
        break

completion_rate = (done_tasks / total_tasks * 100) if total_tasks else 0

# -----------------------------
# KPI DISPLAY
# -----------------------------

c1, c2, c3 = st.columns(3)

c1.metric("Tasks Done", done_tasks)
c2.metric("Completion Rate", f"{completion_rate:.0f}%")
c3.metric("🔥 Current Streak", current_streak)

c4, c5 = st.columns(2)

c4.metric("🏆 Best Streak", best_streak)
c5.metric("Total Tasks", total_tasks)

st.divider()

# -----------------------------
# CALENDAR GRID
# -----------------------------

st.subheader("📅 Monthly Tasks")

cols = st.columns(7)

weekdays = ["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"]

for i in range(7):
    cols[i].markdown(f"**{weekdays[i]}**")

week = 0
cols = st.columns(7)

for day in range(1, num_days + 1):

    col = cols[(day - 1) % 7]

    with col:

        st.markdown(f"### {day}")

        key = f"{year}-{month}-{day}"

        if key not in st.session_state.todos:
            st.session_state.todos[key] = []

        tasks = st.session_state.todos[key]

        # render tasks
        for i, task in enumerate(tasks):

            if not isinstance(task, dict):
                continue

            c1, c2, c3 = st.columns([0.15, 0.70, 0.15])

            with c1:
                done = st.checkbox(
                    "",
                    value=task.get("done", False),
                    key=f"{key}-{i}"
                )
                task["done"] = done

            with c2:
                st.write(task.get("task", ""))

            with c3:
                if st.button("🗑️", key=f"del-{key}-{i}", help="Delete task"):
                    st.session_state.todos[key].pop(i)
                    st.rerun()

        # add new task
        new_task = st.text_input(
            "Task",
            key=f"input-{key}"
        )

        if st.button("Add", key=f"btn-{key}"):

            if new_task:

                st.session_state.todos[key].append(
                    {"task": new_task, "done": False}
                )

                st.rerun()

    if day % 7 == 0:
        cols = st.columns(7)

st.divider()

# -----------------------------
# GITHUB STYLE HEATMAP
# -----------------------------

st.subheader("🟩 Productivity Map")

heat_data = []

for day in range(1, num_days + 1):

    key = f"{year}-{month}-{day}"

    tasks = st.session_state.todos.get(key, [])

    if not tasks:
        value = 0
    else:
        done = sum(1 for t in tasks if isinstance(t, dict) and t.get("done"))
        value = done / len(tasks)

    heat_data.append({
        "day": day,
        "value": value
    })

heat_df = pd.DataFrame(heat_data)

import plotly.express as px

fig = px.scatter(
    heat_df,
    x="day",
    y=[1]*len(heat_df),
    color="value",
    color_continuous_scale="Greens",
)

fig.update_traces(marker=dict(size=20))

fig.update_layout(
    yaxis_visible=False,
    xaxis_title="Day of Month",
    height=200
)

st.plotly_chart(fig, use_container_width=True)