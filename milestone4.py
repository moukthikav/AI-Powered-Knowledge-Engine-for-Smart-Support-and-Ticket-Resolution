"""
Milestone 4 - Integration & Reporting Hub (merged with Milestone 3 email + Slack)
Save as: milestone4_dashboard.py
Run: streamlit run milestone4_dashboard.py
"""

import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
import os
import smtplib
import requests
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime

st.set_page_config(page_title="📊 Support Analytics & Alerts", layout="wide")

# ---------------- CONFIG (from environment recommended) ----------------
EMAIL_USER = os.getenv("ALERT_EMAIL_USER", "")
EMAIL_PASS = os.getenv("ALERT_EMAIL_PASS", "")  # App Password recommended
EMAIL_TO   = os.getenv("ALERT_EMAIL_TO", "")
SLACK_WEBHOOK_URL = os.getenv("SLACK_WEBHOOK_URL", "")
GOOGLE_SHEETS_CREDENTIALS = os.getenv("GOOGLE_SHEETS_CREDENTIALS", "credentials.json")

# File paths (adjust if needed)
BASE_DIR = os.path.dirname(__file__) if "__file__" in globals() else "."
TICKETS_FILE = os.path.join(BASE_DIR, "tickets_log.csv")       # same as Milestone 3
CONVO_FILE = os.path.join(BASE_DIR, "conversations.csv")
RECOMM_FILE = os.path.join(BASE_DIR, "recommendation_log.csv")

# Thresholds / rules
CONTENT_GAP_THRESHOLD = float(os.getenv("CONTENT_GAP_THRESHOLD", 0.30))  # 30% default

# ---------------- Utility: safe CSV loader ----------------
def load_csv(path, **kwargs):
    if os.path.exists(path):
        try:
            df = pd.read_csv(path, **kwargs)
            return df
        except Exception as e:
            st.warning(f"Failed to read {path}: {e}")
            return pd.DataFrame()
    else:
        return pd.DataFrame()

# ----------------- EMAIL / SLACK FUNCTIONS -----------------
def send_email(subject: str, body: str, recipient: str):
    if not EMAIL_USER or not EMAIL_PASS:
        st.error("Email credentials are not configured. Set ALERT_EMAIL_USER and ALERT_EMAIL_PASS env vars.")
        return False
    try:
        msg = MIMEMultipart()
        msg["From"] = EMAIL_USER
        msg["To"] = recipient
        msg["Subject"] = subject
        msg.attach(MIMEText(body, "plain"))

        with smtplib.SMTP_SSL("smtp.gmail.com", 465, timeout=20) as server:
            server.login(EMAIL_USER, EMAIL_PASS)
            server.sendmail(EMAIL_USER, recipient, msg.as_string())
        st.success(f"Email sent to {recipient}")
        return True
    except Exception as e:
        st.error(f"Email send error: {e}")
        return False

def send_slack_alert(message: str):
    if not SLACK_WEBHOOK_URL:
        st.error("Slack webhook URL not configured. Set SLACK_WEBHOOK_URL env var.")
        return False
    try:
        payload = {"text": message}
        resp = requests.post(SLACK_WEBHOOK_URL, json=payload, timeout=10)
        if resp.status_code == 200:
            st.success("Slack alert posted")
            return True
        else:
            st.error(f"Slack error: {resp.status_code} - {resp.text}")
            return False
    except Exception as e:
        st.error(f"Slack send error: {e}")
        return False

# ----------------- Analytics / Gap Detection -----------------
def preprocess_tickets(df: pd.DataFrame):
    if df.empty:
        return df
    # Try to standardize common column names
    cols = [c.lower().strip() for c in df.columns]
    df.columns = cols
    # If timestamp column exists try to parse
    for possible in ["timestamp", "time", "created_at"]:
        if possible in df.columns:
            try:
                df[possible] = pd.to_datetime(df[possible])
                df["parsed_timestamp"] = df[possible]
            except Exception:
                pass
            break
    # fallback: try to parse first column if looks like timestamp
    if "parsed_timestamp" not in df.columns:
        for c in df.columns:
            if "time" in c or "date" in c:
                try:
                    df["parsed_timestamp"] = pd.to_datetime(df[c])
                    break
                except Exception:
                    continue
    return df

def detect_content_gaps(tickets_df: pd.DataFrame, convos_df: pd.DataFrame, recomm_df: pd.DataFrame):
    """
    Example rule:
      - Identify categories (or problems) with many tickets but low recommendation usage
      - For simplicity: detect if proportion of tickets mentioning 'refund' and not having recommendations > threshold
    """
    if tickets_df.empty:
        return {"gap_rate": 0.0, "details": "No tickets found."}

    # Look for refund related tickets (simple keyword approach)
    ticket_text_col = None
    for c in tickets_df.columns:
        if any(x in c for x in ["problem", "issue", "description", "message"]):
            ticket_text_col = c
            break

    if ticket_text_col is None:
        return {"gap_rate": 0.0, "details": "No problem/description column found in tickets."}

    refund_mask = tickets_df[ticket_text_col].astype(str).str.contains("refund", case=False, na=False)
    refund_tickets = tickets_df[refund_mask]
    refund_count = len(refund_tickets)
    total = len(tickets_df)
    gap_rate = (refund_count / total) if total > 0 else 0.0

    # Check how many refund tickets have recommendations in recomm_df
    recommended_for_refund = 0
    if not recomm_df.empty:
        # Attempt to match ticket ids
        if "Ticket ID" in recomm_df.columns or "TicketID" in recomm_df.columns:
            col_match = "Ticket ID" if "Ticket ID" in recomm_df.columns else "TicketID"
            recomm_tkt_ids = recomm_df[col_match].astype(str).unique()
            recommended_for_refund = refund_tickets.iloc[:,0].astype(str).isin(recomm_tkt_ids).sum()
        else:
            # fallback: look by keyword in recommended column
            if "Problem" in recomm_df.columns and "Recommended" in recomm_df.columns:
                rec_mask = recomm_df["Problem"].astype(str).str.contains("refund", case=False, na=False)
                recommended_for_refund = rec_mask.sum()
    details = f"{refund_count} refund-like tickets out of {total} total tickets."
    return {"gap_rate": gap_rate, "details": details, "refund_count": refund_count, "recommended_count": recommended_for_refund}

# ----------------- Data Loading -----------------
tickets_df_raw = load_csv(TICKETS_FILE, on_bad_lines='skip')
convos_df_raw  = load_csv(CONVO_FILE, on_bad_lines='skip')
recomm_df_raw  = load_csv(RECOMM_FILE, names=["Time","Ticket ID","Problem","Recommended","Clicked"], on_bad_lines='skip', quotechar='"')

tickets_df = preprocess_tickets(tickets_df_raw)
convos_df = convos_df_raw
recomm_df = recomm_df_raw

# ----------------- Streamlit UI -----------------
st.title("📊 Support Analytics & Reporting Hub (Milestone 4)")

col1, col2 = st.columns([3,1])

with col1:
    st.subheader("Data Overview")
    st.write("Tickets file:", TICKETS_FILE)
    st.write("Conversations file:", CONVO_FILE)
    st.write("Recommendation log:", RECOMM_FILE)
    st.write("Last loaded at:", datetime.now().strftime("%Y-%m-%d %H:%M:%S"))

    if tickets_df.empty:
        st.warning("No ticket data available. Create tickets first (Milestone 3).")
    else:
        # Ticket counts
        st.markdown("### 🎟️ Ticket Summary")
        st.write(f"Total tickets: **{len(tickets_df)}**")
        # Show first few rows
        st.dataframe(tickets_df.head(10))

        # Tickets by Priority (if exists)
        priority_col = None
        for c in tickets_df.columns:
            if "priority" in c:
                priority_col = c
                break
        if priority_col:
            st.markdown("#### Tickets by Priority")
            fig, ax = plt.subplots()
            sns.countplot(data=tickets_df, x=priority_col, ax=ax)
            ax.set_xlabel("Priority")
            st.pyplot(fig)
        else:
            st.info("No 'Priority' column found in tickets.")

        # Trend over time
        if "parsed_timestamp" in tickets_df.columns:
            st.markdown("#### Tickets Over Time")
            time_series = tickets_df.groupby(tickets_df["parsed_timestamp"].dt.date).size()
            fig2, ax2 = plt.subplots()
            time_series.plot(kind="line", marker="o", ax=ax2)
            ax2.set_xlabel("Date")
            ax2.set_ylabel("Ticket count")
            st.pyplot(fig2)

        # Recommendation stats
        st.markdown("### 📚 Recommendation Log Summary")
        if not recomm_df.empty:
            st.write("Total recommendation log rows:", len(recomm_df))
            # show top recommended articles
            if "Recommended" in recomm_df.columns:
                rec_counts = recomm_df["Recommended"].value_counts().head(10)
                st.write("Top recommended articles:")
                st.dataframe(rec_counts)
        else:
            st.info("No recommendation log data found.")

with col2:
    st.subheader("Quick Actions")
    st.write("Use the buttons below to run detection and send alerts or reports.")

    if st.button("🔍 Run Content Gap Detection & Alert"):
        with st.spinner("Running gap detection..."):
            gap = detect_content_gaps(tickets_df, convos_df, recomm_df)
            st.write("Gap detection result:")
            st.write(gap["details"])
            st.write(f"Gap rate: {gap['gap_rate']*100:.2f}%")
            if gap["gap_rate"] >= CONTENT_GAP_THRESHOLD:
                msg = f"⚠️ Content Gap Alert: {gap['gap_rate']*100:.2f}% of tickets match rule (e.g. refund). Details: {gap['details']}"
                # Slack + Email alert
                slack_ok = send_slack_alert(msg)
                email_ok = send_email(
                    subject=f"⚠️ Content Gap Alert - {datetime.now().strftime('%Y-%m-%d')}",
                    body=msg + "\n\nAuto-generated by Support Analytics Hub.",
                    recipient=EMAIL_TO
                )
                st.write("Alert results:", {"slack": slack_ok, "email": email_ok})
            else:
                st.success("No major content gap detected (below threshold).")

    if st.button("📧 Send Summary Report (email to support)"):
        # Build a short summary
        total_tickets = len(tickets_df)
        top_issues = "N/A"
        if not recomm_df.empty and "Recommended" in recomm_df.columns:
            top_issues = recomm_df["Recommended"].value_counts().head(5).to_json()
        body = f"""
Support Summary Report - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

Total tickets: {total_tickets}
Top recommended items (from recommendation log): {top_issues}

Files:
- Tickets: {TICKETS_FILE}
- Recommendations: {RECOMM_FILE}

This is an automated summary from the Support Analytics Hub.
"""
        ok = send_email(subject=f"Support Summary - {datetime.now().strftime('%Y-%m-%d')}",
                        body=body, recipient=EMAIL_TO)
        if ok:
            st.success("Summary email sent.")

    if st.button("🔔 Send Test Notification (Slack + Email)"):
        test_msg = f"Test alert from Support Hub at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
        s_ok = send_slack_alert(test_msg)
        e_ok = send_email(subject="Test alert from Support Hub", body=test_msg, recipient=EMAIL_TO)
        st.write({"slack_ok": s_ok, "email_ok": e_ok})

# ----------------- Footer / Settings -----------------
st.markdown("---")
st.subheader("Settings & Environment Check")
st.write("Email user:", EMAIL_USER if EMAIL_USER else "Not configured")
st.write("Email recipient (support):", EMAIL_TO if EMAIL_TO else "Not configured")
st.write("Slack webhook configured:", bool(SLACK_WEBHOOK_URL))
st.write("Google sheets credentials path:", GOOGLE_SHEETS_CREDENTIALS)

st.caption("Notes: Use Gmail App Password for ALERT_EMAIL_PASS. Keep credentials in environment variables or a .env file; do not commit them to git.")
