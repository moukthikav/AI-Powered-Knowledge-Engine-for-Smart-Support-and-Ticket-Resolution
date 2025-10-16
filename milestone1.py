import gspread
from google.oauth2.service_account import Credentials
import datetime
import re

# --- Google Sheets Setup ---
SCOPE = ["https://www.googleapis.com/auth/spreadsheets",
         "https://www.googleapis.com/auth/drive.readonly"]
CREDS = Credentials.from_service_account_file('Credentials.json', scopes=SCOPE)
GSPREAD_CLIENT = gspread.authorize(CREDS)

def append_to_sheet(ticket_id, ticket_content, ticket_timestamp, ticket_by, category):
    try:
        ticket_data = GSPREAD_CLIENT.open("TicketDatabase").sheet1
        row = [ticket_id, ticket_content, category, ticket_timestamp, ticket_by]
        ticket_data.append_row(row)
        return True
    except Exception as e:
        print(f"Error appending row: {e}")
        return False

def get_valid_timestamp():
    while True:
        ts = input("Enter Ticket Timestamp (leave blank for now): ")
        if not ts:
            return datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        for fmt in ("%d/%m/%Y %H:%M:%S", "%Y-%m-%d %H:%M:%S"):
            try:
                return datetime.datetime.strptime(ts, fmt).strftime("%Y-%m-%d %H:%M:%S")
            except ValueError:
                continue
        print("Invalid timestamp format. Try again.")

def get_valid_email():
    while True:
        email = input("Enter Ticket By (email): ")
        if re.match(r"[^@]+@[^@]+\.[^@]+", email):
            return email
        print("Invalid email. Try again.")

if __name__ == '__main__':
    ticket_id = input("Enter Ticket ID: ")
    ticket_content = input("Enter Ticket Content: ")
    ticket_timestamp = get_valid_timestamp()
    ticket_by = get_valid_email()
    category = input("Enter Ticket Category: ")

    if append_to_sheet(ticket_id, ticket_content, ticket_timestamp, ticket_by, category):
        print("Record added successfully!")
    else:
        print("Failed to add record.")
