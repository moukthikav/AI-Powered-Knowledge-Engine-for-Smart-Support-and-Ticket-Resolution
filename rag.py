# pip install streamlit gspread google-auth langchain sentence-transformers faiss-cpu langchain-groq scikit-learn pandas

import streamlit as st
import gspread
from google.oauth2.service_account import Credentials
from datetime import datetime
from langchain.embeddings import HuggingFaceEmbeddings
from langchain.vectorstores import FAISS
from langchain.schema import Document
from langchain_groq import ChatGroq
from langchain.prompts import ChatPromptTemplate
from sklearn.metrics import accuracy_score, confusion_matrix
import pandas as pd

# ----------------- Google Sheets Setup -----------------
SCOPE = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive"
]
CREDS = Credentials.from_service_account_file("Credentials.json", scopes=SCOPE)
GSPREAD_CLIENT = gspread.authorize(CREDS)
SHEET = GSPREAD_CLIENT.open("TicketDatabase").sheet1

# ----------------- Auto Ticket ID -----------------
def get_next_ticket_id():
    rows = SHEET.get_all_values()
    if len(rows) <= 1 or not rows[-1][0].startswith("TICKET-"):
        return "TICKET-1"
    last_id = rows[-1][0]
    try:
        number = int(last_id.split("-")[1])
    except (IndexError, ValueError):
        number = 0
    return f"TICKET-{number + 1}"

# ----------------- Insert Ticket with strict uniqueness -----------------
def insert_ticket(name, problem, email, category):
    rows = SHEET.get_all_values()
    if len(rows) > 1:
        data = rows[1:]
        for row in data:
            existing_ticket = dict(zip(rows[0], row))
            if existing_ticket.get("Ticket By") == name:
                return "name_exists"
            if existing_ticket.get("Email") == email:
                return "email_exists"
    ticket_id = get_next_ticket_id()
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    SHEET.append_row([ticket_id, problem, category, timestamp, name, email])
    return ticket_id

# ----------------- Problem-Suggestions -----------------
problems = [
    {"problem": "payment failed", "suggestion": "⚠️ Please wait a few seconds and try again. If it still fails, contact your bank or payment provider."},
    {"problem": "cannot login", "suggestion": "🔑 Make sure your username and password are correct. Try resetting your password if needed."},
    {"problem": "app crashing", "suggestion": "📱 Restart the app or reinstall it. Make sure your device OS is up to date."},
    {"problem": "refund request", "suggestion": "💰 You can request a refund from your orders section. Contact support if it takes longer than 3 days."},
]

docs = [Document(page_content=p["problem"], metadata={"suggestion": p["suggestion"]}) for p in problems]
embeddings = HuggingFaceEmbeddings(model_name="sentence-transformers/all-MiniLM-L6-v2")
vectordb = FAISS.from_documents(docs, embeddings)
retriever = vectordb.as_retriever(search_kwargs={"k": 1})

# ----------------- Groq LLM for category classification -----------------
llm = ChatGroq(
    model="llama-3.1-8b-instant",
    temperature=0,
    api_key="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"
)

categories = ["Payment Issue", "Login Issue", "App Bug", "Refund Request", "Other"]

# ----------------- Few-shot prompt with examples -----------------
category_prompt_template = """
You are an expert support ticket classifier.
Classify the following ticket into exactly one of these categories: {categories}.

Ticket: "{ticket_text}"
Return only the exact category name.
"""
category_prompt = ChatPromptTemplate.from_template(category_prompt_template)

# ----------------- Cache LLM classification for speed -----------------
@st.cache_data(show_spinner=False)
def classify_category_cached(ticket_text):
    return llm.predict(category_prompt.format(categories=", ".join(categories), ticket_text=ticket_text))

# ----------------- Optimized Pilot Dataset -----------------
pilot_data = [
    {"text": "My credit card payment keeps failing", "expected": "Payment Issue"},
    {"text": "Payment unsuccessful, keeps showing error", "expected": "Payment Issue"},
    {"text": "Transaction declined, bank error", "expected": "Payment Issue"},
    {"text": "I cannot login, password not working", "expected": "Login Issue"},
    {"text": "Forgot my password and cannot login", "expected": "Login Issue"},
    {"text": "App closes unexpectedly on startup", "expected": "App Bug"},
    {"text": "App crashes when opening a new page", "expected": "App Bug"},

]

@st.cache_data(show_spinner=False)
def pilot_predictions():
    y_pred = [classify_category_cached(d["text"]) for d in pilot_data]
    y_true = [d["expected"] for d in pilot_data]
    acc = accuracy_score(y_true, y_pred)
    cm = confusion_matrix(y_true, y_pred, labels=categories)
    return acc, cm, y_true, y_pred

# ----------------- Streamlit UI -----------------
st.title("💡 Smart Support & Ticket System ")

st.write("Enter your details and describe your problem. A ticket will be created with AI suggestions and categorized automatically!")

if "conversation" not in st.session_state:
    st.session_state.conversation = []

with st.form("ticket_form"):
    name = st.text_input("Your Name")
    email = st.text_input("Your Email")
    problem = st.text_area("Describe your problem")
    submitted = st.form_submit_button("Submit Ticket")

    if submitted:
        if not name or not email or not problem:
            st.error("Please fill all fields!")
        else:
            category = classify_category_cached(problem)
            ticket_id = insert_ticket(name, problem, email, category)

            if ticket_id == "name_exists":
                st.error("⚠️ This name is already registered. Please check your details!")
            elif ticket_id == "email_exists":
                st.error("⚠️ This email is already registered. Please check your details!")
            elif ticket_id is None:
                st.error("⚠️ A ticket with the same name, email, and problem already exists!")
            else:
                st.success(f"✅ Your ticket has been created! Ticket ID: {ticket_id}")
                st.info(f"📂 Ticket Category: {category}")
                st.session_state.conversation.append(f"Ticket {ticket_id} created for {name}.")

                results = retriever.get_relevant_documents(problem)
                if results:
                    suggestion = results[0].metadata.get("suggestion", "No suggestion found.")
                    st.info(f"💡 Suggested Action: {suggestion}")
                else:
                    st.info("💡 No suggestion found. Please wait for support to contact you.")

# ----------------- Pilot Validation Section -----------------
st.subheader("Pilot Dataset Validation for Category Accuracy")
if st.button("Run Validation"):
    acc, cm, y_true, y_pred = pilot_predictions()
    st.write(f"✅ Accuracy on pilot dataset: **{acc*100:.2f}%**")
    df_cm = pd.DataFrame(cm, index=categories, columns=categories)
    st.write("Confusion Matrix:")
    st.dataframe(df_cm)
    validation_results = pd.DataFrame({
        "Ticket Text": [d["text"] for d in pilot_data],
        "Expected Category": y_true,
        "Predicted Category": y_pred
    })
    st.write("Detailed Results:")
    st.dataframe(validation_results)
