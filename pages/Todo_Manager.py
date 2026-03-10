import streamlit as st
import pandas as pd
import calendar
from datetime import datetime

st.set_page_config(page_title="Todo Manager", layout="wide")

st.title("🗓️ Monthly Todo Manager")

# -------- MONTH SELECT --------

today = datetime.today()

year = st.selectbox("Year", [2024,2025,2026], index=2)
month = st.selectbox(
    "Month",
    list(calendar.month_name)[1:],
    index=today.month-1
)

month_number = list(calendar.month_name).index(month)

st.divider()

# -------- CALENDAR GENERATE --------

cal = calendar.Calendar(firstweekday=0)
month_days = cal.monthdayscalendar(year, month_number)

weekday_names = ["Mon","Tue","Wed","Thu","Fri","Sat","Sun"]

cols = st.columns(7)

for i,day in enumerate(weekday_names):
    cols[i].markdown(f"**{day}**")

# -------- SESSION STATE --------

if "todos" not in st.session_state:
    st.session_state.todos = {}

# -------- CALENDAR UI --------

for week in month_days:

    cols = st.columns(7)

    for i,day in enumerate(week):

        with cols[i]:

            if day == 0:
                st.write("")
                continue

            date_key = f"{year}-{month_number}-{day}"

            st.markdown(f"### {day}")

            # task input
            task = st.text_input(
                "Task",
                key=f"task_{date_key}"
            )

            done = st.checkbox(
                "Done",
                key=f"done_{date_key}"
            )

            st.session_state.todos[date_key] = {
                "task": task,
                "done": done
            }