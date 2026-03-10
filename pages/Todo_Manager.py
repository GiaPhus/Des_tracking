import streamlit as st
import pandas as pd
import calendar
from datetime import datetime

st.set_page_config(page_title="Todo Manager", layout="wide")

st.title("📝 Monthly Todo Manager")

# -----------------------------
# SESSION STORAGE
# -----------------------------

if "todos" not in st.session_state:
    st.session_state.todos = {}

today = datetime.today()
year = today.year
month = today.month

month_name = today.strftime("%B")

st.subheader(f"{month_name} {year}")

# -----------------------------
# KPI CALCULATION
# -----------------------------

total_tasks = 0
done_tasks = 0

daily_completion = {}

for day, tasks in st.session_state.todos.items():

    if len(tasks) == 0:
        continue

    done = sum(t["done"] for t in tasks)

    total_tasks += len(tasks)
    done_tasks += done

    daily_completion[day] = done / len(tasks)

completion_rate = 0 if total_tasks == 0 else done_tasks / total_tasks * 100

# streak logic
streak = 0
best = 0
current = 0

for day in sorted(daily_completion.keys()):

    if daily_completion[day] >= 0.8:
        current += 1
        best = max(best, current)
    else:
        current = 0

streak = current

c1, c2, c3 = st.columns(3)

with c1:
    st.metric("Task Completion", f"{completion_rate:.0f}%")

with c2:
    st.metric("🔥 Todo Streak", streak)

with c3:
    st.metric("🏆 Best Streak", best)

st.divider()

# -----------------------------
# CALENDAR
# -----------------------------

cal = calendar.monthcalendar(year, month)

days = ["Mon","Tue","Wed","Thu","Fri","Sat","Sun"]

cols = st.columns(7)

for i, d in enumerate(days):
    cols[i].markdown(f"**{d}**")

for week in cal:

    cols = st.columns(7)

    for i, day in enumerate(week):

        with cols[i]:

            if day == 0:
                st.write("")
                continue

            day_key = f"{year}-{month}-{day}"

            if day_key not in st.session_state.todos:
                st.session_state.todos[day_key] = []

            st.markdown(f"### {day}")

            # add task
            new_task = st.text_input(
                "Task",
                key=f"input_{day_key}"
            )

            if st.button("Add", key=f"add_{day_key}"):

                if new_task:
                    st.session_state.todos[day_key].append({
                        "task": new_task,
                        "done": False
                    })

            # render tasks
            for idx, task in enumerate(st.session_state.todos[day_key]):

                done = st.checkbox(
                    task["task"],
                    value=task["done"],
                    key=f"{day_key}_{idx}"
                )

                st.session_state.todos[day_key][idx]["done"] = done

st.divider()

# -----------------------------
# GITHUB STYLE MAP
# -----------------------------

st.subheader("🟩 Productivity Map")

map_cols = st.columns(31)

for day in range(1, 32):

    if day > calendar.monthrange(year, month)[1]:
        continue

    day_key = f"{year}-{month}-{day}"

    rate = daily_completion.get(day_key, 0)

    if rate == 0:
        color = "#eeeeee"
    elif rate < 0.5:
        color = "#b7e4c7"
    elif rate < 0.8:
        color = "#52b788"
    else:
        color = "#2d6a4f"

    map_cols[day-1].markdown(
        f"""
        <div style="
        height:25px;
        background:{color};
        border-radius:4px;
        margin:2px">
        </div>
        """,
        unsafe_allow_html=True
    )