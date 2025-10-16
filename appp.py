# final_full_updated.py
"""
AI-Powered Smart Support & Ticket System
- Sign In / Sign Up
- AI Chatbot
- Ticket Management
- CSV-based Analytics with empty-data safeguards
- Dynamic higher/lower highlights
"""

import os
import uuid
from datetime import datetime, timedelta
import io
import hashlib

import pandas as pd
import numpy as np
import streamlit as st
import matplotlib.pyplot as plt
import seaborn as sns
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter

# ----------------- Configuration -----------------
APP_TITLE = "AI-Powered Smart Support & Ticket System"
PAGE_ICON = "💙"
st.set_page_config(page_title=APP_TITLE, layout="wide", page_icon=PAGE_ICON)

# ----------------- Styling -----------------
st.markdown("""
<style>
.header {background: linear-gradient(90deg, #0b69ff 0%, #00a3ff 100%);
color: white; padding: 14px 18px; border-radius: 8px; margin-bottom: 12px;}
.card {background: #ffffff; border-radius: 8px; padding: 12px; box-shadow: 0 4px 12px rgba(2,6,23,0.06);}
.sidebar .stButton>button { width:100%; }
</style>
""", unsafe_allow_html=True)

# ----------------- Helper Functions -----------------
def sample_tickets_df():
    categories = ["Payment Issue","Login Issue","App Bug","Refund Request","Performance","Other"]
    priorities = ["Low","Medium","High"]
    statuses = ["Open","In Progress","Resolved"]
    data = []
    now = datetime.now()
    for i in range(15):
        data.append({
            "TicketNumber": f"T-{uuid.uuid4().hex[:6].upper()}",
            "Content": f"Sample problem {i+1}",
            "Category": np.random.choice(categories),
            "UserName": f"User{i+1}",
            "UserEmail": f"user{i+1}@example.com",
            "Conversation": f"Conversation log {i+1}",
            "Timestamp": (now - timedelta(hours=np.random.randint(0,48))).strftime("%Y-%m-%d %H:%M:%S"),
            "Priority": np.random.choice(priorities),
            "Status": np.random.choice(statuses)
        })
    return pd.DataFrame(data)

def ensure_columns(df, cols):
    for c in cols:
        if c not in df.columns:
            df[c] = ""
    return df

def ai_suggest_category(problem: str):
    p = problem.lower()
    if "login" in p: return "Login Issue"
    if "payment" in p or "card" in p: return "Payment Issue"
    if "refund" in p: return "Refund Request"
    if "error" in p or "bug" in p or "crash" in p: return "App Bug"
    if "battery" in p or "hang" in p or "slow" in p: return "Performance"
    return "Other"

def ai_respond(problem: str):
    fallback = [
        "1) Restart the device",
        "2) Close background apps and free RAM",
        "3) Check charger/cable",
        "4) Update OS & app(s); if persists, backup & factory reset"
    ]
    return "\n".join(fallback)

def generate_alert_pdf(subject: str, details: str) -> bytes:
    buffer = io.BytesIO()
    c = canvas.Canvas(buffer, pagesize=letter)
    w, h = letter
    c.setFont("Helvetica-Bold", 14)
    c.drawString(40, h - 40, subject)
    c.setFont("Helvetica", 10)
    text = c.beginText(40, h - 70)
    for line in details.splitlines():
        text.textLine(line)
    c.drawText(text)
    c.showPage()
    c.save()
    buffer.seek(0)
    return buffer.read()

# ----------------- Load CSV -----------------
CSV_FILE = "customer_support_tickets.csv"
if os.path.exists(CSV_FILE):
    df = pd.read_csv(CSV_FILE)
else:
    st.warning("CSV file not found. Using sample dataset.")
    df = sample_tickets_df()

st.session_state['tickets_df'] = ensure_columns(df, ['TicketNumber','Content','Category','UserName','UserEmail','Conversation','Timestamp','Priority','Status'])

# ----------------- Authentication -----------------
if 'user' not in st.session_state:
    st.session_state['user'] = None

def auth_ui():
    st.markdown("<div class='card'>", unsafe_allow_html=True)
    st.subheader("Welcome — Sign in or Sign up")
    tab = st.radio("", ["Sign In", "Sign Up"], horizontal=True)
    if tab == "Sign Up":
        with st.form("signup"):
            name = st.text_input("Full name")
            email = st.text_input("Email")
            pwd = st.text_input("Password", type="password")
            submit = st.form_submit_button("Create account")
        if submit:
            st.success("Account creation simulated (demo).")
    else:
        with st.form("signin"):
            email = st.text_input("Email", key="signin_email")
            pwd = st.text_input("Password", type="password", key="signin_pwd")
            submit = st.form_submit_button("Sign in")
        if submit:
            st.session_state['user'] = {'email': email or "demo@example.com", 'name': email or "Demo User"}
            st.success("Signed in (demo)")
            st.rerun()
    st.markdown("</div>", unsafe_allow_html=True)

if not st.session_state.get('user'):
    auth_ui()
    st.stop()

current_user = st.session_state['user']

# ----------------- Sidebar -----------------
st.sidebar.markdown(f"<div style='padding:8px;border-radius:6px;background:#eaf4ff'><strong style='color:#0b69ff'>{APP_TITLE}</strong></div>", unsafe_allow_html=True)
confidence_threshold = st.sidebar.slider("Confidence Threshold", 0.0, 1.0, 0.7, step=0.05)
st.sidebar.markdown("---")
st.sidebar.caption("Analytics based on CSV; AI model fixed internally.")

# ----------------- Tabs -----------------
tabs = st.tabs(["Query Resolution", "AI Chatbot Support", "Ticket Management", "Data Export", "Analytics"])

# ----------------- Query Resolution -----------------
with tabs[0]:
    st.markdown("<div class='header'>Query Resolution / AI Suggestions</div>", unsafe_allow_html=True)
    problem_input = st.text_area("Describe your problem:", height=100)
    if st.button("Get AI Suggestions"):
        if problem_input.strip():
            category = ai_suggest_category(problem_input)
            ai_reply = ai_respond(problem_input)
            st.markdown(f"**Suggested Category:** {category}")
            st.markdown(f"**AI Response / Steps:**\n{ai_reply}")
        else:
            st.warning("Please type your query.")

# ----------------- AI Chatbot -----------------
with tabs[1]:
    st.markdown("<div class='header'>AI Chatbot</div>", unsafe_allow_html=True)
    user_msg = st.text_input("Send message to AI Support", key="ai_chat_input")
    if st.button("Send"):
        if user_msg.strip():
            reply = ai_respond(user_msg)
            if 'chat_history' not in st.session_state:
                st.session_state['chat_history'] = []
            st.session_state['chat_history'].append({"user": user_msg, "ai": reply})
    if 'chat_history' in st.session_state:
        for msg in st.session_state['chat_history']:
            st.markdown(f"**You:** {msg['user']}")
            st.markdown(f"**AI:** {msg['ai']}")

# ----------------- Ticket Management -----------------
with tabs[2]:
    st.markdown("<div class='header'>Ticket Management</div>", unsafe_allow_html=True)
    tickets_df = st.session_state['tickets_df']
    st.markdown("### Tickets")
    for i, row in tickets_df.sort_values(by='Timestamp', ascending=False).iterrows():
        with st.expander(f"{row['TicketNumber']} - {row['Category']} - {row['Status']}"):
            st.write(f"**Reported by:** {row['UserName']} ({row['UserEmail']})")
            st.write(f"**Priority:** {row['Priority']}")
            st.write(f"**Content:** {row['Content']}")
            st.write(f"**Conversation:** {row['Conversation']}")
            st.write(f"**Timestamp:** {row['Timestamp']}")

    st.markdown("### Create New Ticket")
    with st.form("new_ticket_form"):
        t_name = st.text_input("Your Name", value=current_user['name'])
        t_email = st.text_input("Email", value=current_user['email'])
        t_problem = st.text_area("Problem / Issue", height=80)
        t_priority = st.select_slider("Priority", options=["Low","Medium","High"])
        submit_ticket = st.form_submit_button("Create Ticket")
    if submit_ticket and t_problem.strip():
        t_number = f"T-{uuid.uuid4().hex[:6].upper()}"
        t_category = ai_suggest_category(t_problem)
        t_row = [t_number, t_problem, t_category, t_name, t_email, t_problem, datetime.now().strftime("%Y-%m-%d %H:%M:%S"), t_priority, "Open"]
        st.session_state['tickets_df'] = st.session_state['tickets_df'].append(pd.Series(t_row, index=st.session_state['tickets_df'].columns), ignore_index=True)
        st.success(f"Ticket created: {t_number}")

# ----------------- Data Export -----------------
with tabs[3]:
    st.markdown("<div class='header'>Data Export</div>", unsafe_allow_html=True)
    df = st.session_state['tickets_df']
    st.download_button("Download CSV", df.to_csv(index=False).encode('utf-8'), "tickets.csv", "text/csv")
    pdf_bytes = generate_alert_pdf("Tickets Snapshot", "\n".join(df['Content'].tolist()))
    st.download_button("Download PDF", pdf_bytes, "tickets.pdf", "application/pdf")

# ----------------- Analytics -----------------
with tabs[4]:
    st.markdown("<div class='header'>Analytics / Dashboard</div>", unsafe_allow_html=True)
    df = st.session_state['tickets_df']

    if df.empty:
        st.warning("No ticket data available.")
    else:
        df['Timestamp_dt'] = pd.to_datetime(df['Timestamp'], errors='coerce')
        df['Date'] = df['Timestamp_dt'].dt.date
        df['Hour'] = df['Timestamp_dt'].dt.hour

        # Tickets by Category
        st.markdown("### Tickets by Category")
        counts = df['Category'].value_counts()
        if not counts.empty:
            st.bar_chart(counts)
            max_cat = counts.idxmax()
            min_cat = counts.idxmin()
            st.markdown(f"**Most reported category:** {max_cat}")
            st.markdown(f"**Least reported category:** {min_cat}")
        else:
            st.info("No category data")

        # Tickets by Status
        st.markdown("### Tickets by Status")
        status_counts = df['Status'].value_counts()
        if not status_counts.empty:
            st.line_chart(status_counts)
        else:
            st.info("No status data")

        # Tickets per Day / Hour with empty checks
        tickets_per_day = df.groupby('Date')['TicketNumber'].count()
        tickets_per_hour = df.groupby('Hour')['TicketNumber'].count()

        col1, col2 = st.columns(2)
        with col1:
            st.markdown("**Tickets per Day**")
            fig, ax = plt.subplots()
            if not tickets_per_day.empty:
                tickets_per_day.plot(kind='line', marker='o', ax=ax)
                ax.fill_between(tickets_per_day.index, tickets_per_day.values, alpha=0.2)
            else:
                ax.text(0.5,0.5,"No data",ha='center',va='center',fontsize=12)
            st.pyplot(fig)

        with col2:
            st.markdown("**Tickets per Hour**")
            fig, ax = plt.subplots()
            if not tickets_per_hour.empty:
                tickets_per_hour.plot(kind='bar', color='#0b69ff', ax=ax)
            else:
                ax.text(0.5,0.5,"No data",ha='center',va='center',fontsize=12)
                ax.set_xticks([])
            st.pyplot(fig)

        # Heatmap Category vs Priority
        st.markdown("### Category vs Priority Heatmap")
        pivot = pd.crosstab(df['Category'], df['Priority'])
        fig, ax = plt.subplots(figsize=(6,4))
        if not pivot.empty:
            sns.heatmap(pivot, annot=True, cmap="Blues", fmt="d", ax=ax)
        else:
            ax.text(0.5,0.5,"No data",ha='center',va='center')
        st.pyplot(fig)

        # Top reporters / common issues
        col3, col4 = st.columns(2)
        with col3:
            top_users = df['UserName'].value_counts().head(5)
            if not top_users.empty:
                st.write("**Top 5 Reporters**")
                st.dataframe(top_users)
            else:
                st.info("No user data")
        with col4:
            top_issues = df['Content'].value_counts().head(5)
            if not top_issues.empty:
                st.write("**Most Common Issues**")
                st.dataframe(top_issues)
            else:
                st.info("No content data")

# ----------------- Footer -----------------
st.markdown("<div style='padding:12px; text-align:center; color:#0b69ff;'>Smart Support & Ticket System — powered by Streamlit</div>", unsafe_allow_html=True)
