import os
from flask import Flask, request
from twilio.twiml.voice_response import VoiceResponse, Gather
from twilio.rest import Client
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)

# --- CONFIGURATION ---
twilio_client = Client(os.getenv("TWILIO_ACCOUNT_SID"), os.getenv("TWILIO_AUTH_TOKEN"))
twilio_number = os.getenv("TWILIO_PHONE_NUMBER")

# Google Sheets Setup
scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
creds = ServiceAccountCredentials.from_json_keyfile_name("creds.json", scope)
gc = gspread.authorize(creds)
sheet = gc.open(os.getenv("GOOGLE_SHEET_NAME"))
leads_sheet = sheet.worksheet("Leads")
interested_sheet = sheet.worksheet("Interested")

# --- BOT LOGIC ---

@app.route("/voice", methods=['POST'])
def voice():
    """Initial greeting when the user picks up"""
    response = VoiceResponse()
    
    # Hindi Introduction
    hindi_intro = "Namaste! Hamare paas special services available hain. Kya aap hamara ye service lena chahete ho? Kripya Haan ya Nahi kahein."
    
    gather = Gather(input='speech', action='/handle_response', language='hi-IN', timeout=3)
    gather.say(hindi_intro, language='hi-IN', voice='Polly.Aditi')
    response.append(gather)
    
    return str(response)

@app.route("/handle_response", methods=['POST'])
def handle_response():
    response = VoiceResponse()
    user_speech = request.values.get('SpeechResult', '').lower()
    user_phone = request.values.get('To', 'Unknown') 

    print(f"--- WEBHOOK TRIGGERED ---")
    print(f"AI heard: '{user_speech}'")

    # Adding the Hindi script words for 'Yes' (हां, हाँ, जी)
    positive_words = ["haan", "ha", "yes", "हां", "हाँ", "जी", "interested"]
    
    # Checking if any of these words are in what the user said
    is_interested = any(word in user_speech for word in positive_words)

    if is_interested:
        print("MATCH FOUND: User said YES in Hindi/English!")
        response.say("Thank you for your interest! Hamari team aapse jald hi baat karegi.", language='hi-IN', voice='Polly.Aditi')
        
        try:
            from datetime import datetime
            now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            
            # Update the sheet
            interested_sheet.append_row([user_phone, now, f"User said: {user_speech}"])
            print("SUCCESS: Data saved to Google Sheet!")
        except Exception as e:
            print(f"SHEET ERROR: {e}")
        
    else:
        print("NO MATCH: User's response didn't contain 'Yes' keywords.")
        response.say("Koi baat nahi, it's alright. Thank you!", language='hi-IN', voice='Polly.Aditi')

    return str(response)

# Function to trigger calls to the list
def start_calling():
    numbers = leads_sheet.col_values(2)[1:] # Gets numbers from Column B
    for num in numbers:
        print(f"Calling {num}...")
        twilio_client.calls.create(
            url="https://unmired-conflictedly-daphne.ngrok-free.dev/voice", # We will get this in the next step
            to=num,
            from_=twilio_number
        )

if __name__ == "__main__":
    # 1. Starting the Flask server in the background
    import threading
    import time
    
    print("--- Starting Server ---")
    server_thread = threading.Thread(target=app.run, kwargs={'port': 5000, 'use_reloader': False})
    server_thread.daemon = True
    server_thread.start()
    
    # 2. Giving server-2 seconds to warm up
    time.sleep(2)
    
    # 3. Trigger the calls to my list
    print("--- Starting Outbound Calls ---")
    try:
        start_calling()
    except Exception as e:
        print(f"Error starting calls: {e}")

    # Keep the main script alive so the server stays up
    while True:
        time.sleep(1)