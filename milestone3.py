import streamlit as st
import pandas as pd
from datetime import datetime
from langchain_groq import ChatGroq
import os
import random
import string

# ----------------- File paths -----------------
BASE_DIR = os.path.dirname(__file__)
TICKETS_FILE = os.path.join(BASE_DIR, "tickets_log.csv")
CONVO_FILE = os.path.join(BASE_DIR, "conversations.csv")

# ----------------- LLM Setup -----------------
llm = ChatGroq(
    model="llama-3.1-8b-instant",
    temperature=0,
    api_key="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"
)

# ----------------- Ticket ID Generator -----------------
def get_next_ticket_id():
    if not os.path.exists(TICKETS_FILE):
        return "TICKET01"
    df = pd.read_csv(TICKETS_FILE)
    if df.empty:
        return "TICKET01"
    last_id = df.iloc[-1]["TicketID"]
    prefix = ''.join(filter(str.isalpha, last_id))
    number = int(''.join(filter(str.isdigit, last_id))) + 1
    if number > 99:
        prefix = ''.join(random.choices(string.ascii_uppercase, k=6))
        number = 1
    return f"{prefix}{number:02d}"

# ----------------- Logging -----------------
def log_ticket(ticket_id, name, email, problem, priority):
    ticket_data = {
        "TicketID": ticket_id,
        "Name": name,
        "Email": email,
        "Problem": problem,
        "Priority": priority,
        "Timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    }
    if os.path.exists(TICKETS_FILE):
        df = pd.read_csv(TICKETS_FILE)
        df = pd.concat([df, pd.DataFrame([ticket_data])], ignore_index=True)
    else:
        df = pd.DataFrame([ticket_data])
    df.to_csv(TICKETS_FILE, index=False)

def log_conversation(ticket_id, sender, message, feedback=""):
    convo_data = {
        "TicketID": ticket_id,
        "Sender": sender,
        "Message": message,
        "Feedback": feedback,
        "Timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    }
    if os.path.exists(CONVO_FILE):
        df = pd.read_csv(CONVO_FILE)
        df = pd.concat([df, pd.DataFrame([convo_data])], ignore_index=True)
    else:
        df = pd.DataFrame([convo_data])
    df.to_csv(CONVO_FILE, index=False)

def get_conversation(ticket_id):
    if os.path.exists(CONVO_FILE):
        df = pd.read_csv(CONVO_FILE)
        return df[df["TicketID"] == ticket_id].to_dict("records")
    return []

# ----------------- Streamlit UI -----------------
st.set_page_config(page_title="🎟️ Smart Ticket System", layout="wide", page_icon="🎟️")
st.markdown("<h1 style='text-align:center;color:purple'>🎟️ Smart Ticket System</h1>", unsafe_allow_html=True)

# ----------------- Ticket Creation -----------------
if "ticket_id" not in st.session_state:
    with st.form("ticket_form"):
        name = st.text_input("Your Name")
        email = st.text_input("Your Email")
        problem = st.text_area("Describe your problem", height=80)
        priority = st.selectbox("Priority", ["Low", "Medium", "High"])
        submitted = st.form_submit_button("Create Ticket")

    if submitted:
        if not name or not email or not problem:
            st.error("Please fill all fields!", icon="⚠️")
        else:
            ticket_id = get_next_ticket_id()
            st.session_state.ticket_id = ticket_id
            st.session_state.name = name
            st.session_state.email = email
            st.session_state.priority = priority

            log_ticket(ticket_id, name, email, problem, priority)
            log_conversation(ticket_id, "User", problem)

            st.session_state.chat_memory = get_conversation(ticket_id)
            st.success(f"✅ Ticket {ticket_id} created. Start chatting below!", icon="🎟️")

# ----------------- Live Ticket Chat -----------------
if "ticket_id" in st.session_state:
    ticket_id = st.session_state.ticket_id
    chat_memory = st.session_state.get("chat_memory", get_conversation(ticket_id))

    st.subheader(f"💬 Conversation for Ticket {ticket_id}")

    # Display conversation
    for msg in chat_memory:
        color = "#2e7d32" if msg["Sender"] == "User" else "#1565c0"
        emoji = "👤" if msg["Sender"] == "User" else "🤖"
        feedback_text = f" | Feedback: {msg['Feedback']}" if msg.get("Feedback") else ""
        st.markdown(
            f"<div style='background-color:{color};color:white;padding:8px;border-radius:6px;margin:4px 0;'>{emoji} {msg['Message']}{feedback_text}</div>",
            unsafe_allow_html=True,
        )

    # Chat input
    with st.form("chat_form", clear_on_submit=True):
        user_msg = st.text_input("Type your message...")
        send_btn = st.form_submit_button("Send")

    if send_btn and user_msg:
        # Log user message
        log_conversation(ticket_id, "User", user_msg)
        chat_memory.append({"TicketID": ticket_id, "Sender": "User", "Message": user_msg, "Feedback": ""})

        # AI generates step-by-step solution
        ai_prompt = f"""
        You are a smart support assistant.
        User's message: {user_msg}
        Provide a clear, numbered step-by-step solution.
        End with: Was this helpful? (Yes/No)
        """
        try:
            ai_response = llm.predict(ai_prompt).strip()
        except Exception:
            ai_response = "⚠️ AI is not responding. Try again later."

        log_conversation(ticket_id, "Agent", ai_response)
        chat_memory.append({"TicketID": ticket_id, "Sender": "Agent", "Message": ai_response, "Feedback": ""})

        st.session_state.chat_memory = chat_memory
        st.rerun()  # ✅ replaced experimental_rerun

# ----------------- Feedback Buttons -----------------
if "ticket_id" in st.session_state:
    chat_memory = st.session_state.get("chat_memory", [])
    if chat_memory:
        last_msg = chat_memory[-1]
        if last_msg["Sender"] == "Agent" and "Was this helpful?" in last_msg["Message"]:
            col1, col2 = st.columns(2)
            with col1:
                if st.button("Yes"):
                    last_msg["Feedback"] = "Yes"
                    df = pd.read_csv(CONVO_FILE)
                    df.loc[df.index[-1], "Feedback"] = "Yes"
                    df.to_csv(CONVO_FILE, index=False)
            with col2:
                if st.button("No"):
                    last_msg["Feedback"] = "No"
                    df = pd.read_csv(CONVO_FILE)
                    df.loc[df.index[-1], "Feedback"] = "No"
                    df.to_csv(CONVO_FILE, index=False)
