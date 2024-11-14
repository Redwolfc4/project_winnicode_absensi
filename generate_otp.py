import flask
import os
import random
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from email.mime.text import MIMEText
import base64
from dotenv import load_dotenv
import os
import json
from absensiMethod import string_to_uuid_like

# If modifying these SCOPES, delete the file token.json
load_dotenv()
# cuman bisa handle 100 data otp


class OtpPasswordGenerator:
    SCOPES = [os.getenv("GMAIL_SCOPE")]
    otp = None

    def __init__(self, email_receiver: str, nickname_receiver: str = "user"):
        # Example usage
        self.__receiver_email = f"{nickname_receiver} <{email_receiver}>"
        self.__otp = self.generate_otp()
        self.__subject = "Your OTP Code"
        # Menggunakan HTML untuk menampilkan OTP dalam format tebal
        self.__body = f"""
        <html>
            <body>
                <p>Your One-Time Password (OTP) is: <strong>{self.__otp}</strong></p>
            </body>
        </html>
        """
        self.send_otp_via_gmail(self.__receiver_email, self.__subject, self.__body)
        self.otp = self.__otp

    def generate_otp(self):
        # Generate a 6-digit OTP

        self.__otp = random.randint(100000, 999999)
        return self.__otp

    def create_message(self, sender, to, subject, message_text):
        """Create a message for an email."""
        self.__message = MIMEText(message_text, "html")
        self.__message["to"] = to
        self.__message["from"] = sender
        self.__message["subject"] = subject
        self.__raw_message = base64.urlsafe_b64encode(
            self.__message.as_bytes()
        ).decode()
        return {"raw": self.__raw_message}

    def send_message(self, service, user_id, message):
        """Send an email message."""
        try:
            self.__message = (
                service.users().messages().send(userId=user_id, body=message).execute()
            )
            print(f'Message Id: {self.__message["id"]}')
            return self.__message
        except Exception as error:
            print(f"An error occurred: {error}")
            return None

    def authenticate_gmail_api(self):
        from app import db

        """Authenticate and return the Gmail API service."""
        self.__creds = None
        # Retrieve values from environment
        self.__client_id = os.getenv('GOOGLE_CLIENT_ID')
        self.__client_secret = os.getenv('GOOGLE_CLIENT_SECRET')
        self.__redirect_uris = [os.getenv('GOOGLE_REDIRECT_URIS')]
        self.__token_uri = os.getenv('GOOGLE_TOKEN_URI')
        self.__auth_uri = os.getenv('GOOGLE_AUTH_URI')
        self.__auth_provider_cert_url = os.getenv('GOOGLE_AUTH_PROVIDER_CERT_URL')
        
        result = db.gmail_service.find_one({},{'_id':0})
        if result:
            self.__creds = Credentials.from_authorized_user_info(
                result, self.SCOPES
            )

        
        # If there are no (valid) credentials available, let the user log in.
        if not self.__creds or not self.__creds.valid: 
            # expired
            if self.__creds and self.__creds.expired and self.__creds.refresh_token:
                self.__creds.refresh(Request())
                # update the credentials for the next run
                data = json.loads(self.__creds.to_json())
                result = db.gmail_service.find_one({},{'_id':1})
                db.gmail_service.update_one({'_id':result['_id']},data) 
            else:
                self.__flow = InstalledAppFlow.from_client_config(
                    {
                        "installed": {
                            "client_id": self.__client_id,
                            "client_secret": self.__client_secret,
                            "auth_uri": self.__auth_uri,
                            "token_uri": self.__token_uri,
                            "auth_provider_x509_cert_url": self.__auth_provider_cert_url,
                            "redirect_uris": self.__redirect_uris,
                        }
                    },
                    self.SCOPES,
                )
                self.__creds = self.__flow.run_local_server(port=901)
                
                # Save the credentials for the next run
                data = json.loads(self.__creds.to_json())
                db.gmail_service.insert_one(data)
            
        # Build the Gmail API service
        self.__service = build("gmail", "v1", credentials=self.__creds)
        return self.__service

    def send_otp_via_gmail(self, receiver_email, subject, body):
        """Send OTP via Gmail using Gmail API."""
        self.__service = self.authenticate_gmail_api()
        self.__sender_email = os.getenv("GMAIL_SENDER")
        self.__subject = subject
        # Menggunakan HTML untuk menampilkan OTP dalam format tebal
        self.__body = body
        # Create and send the email
        self.__message = self.create_message(
            self.__sender_email, receiver_email, self.__subject, self.__body
        )
        return self.send_message(self.__service, "me", self.__message)

class FaqGmailSender(OtpPasswordGenerator):
    uuid_ticket = None
    message_id = None
    def __init__(self, email_receiver: str = '', nickname_receiver: str = "user", jobs: str = '', departement: str = '', kendala: str = ''):
        from app import db
        self.__email_receiver = email_receiver
        self.__nickname_receiver = nickname_receiver
        self.__jobs = jobs
        self.__departement = departement
        self.__kendala = kendala

        # Check if any input is empty
        if not all([self.__email_receiver.strip(), self.__nickname_receiver.strip(), self.__jobs.strip(), self.__departement.strip(), self.__kendala.strip()]):
            print("Some input values are empty. Exiting...")
            return None
    
        # Generate UUID for the ticket
        while True:
            self.__uuid_tiket = string_to_uuid_like(str(random.randint(0, 9999999)))
            result = db.faq.find_one({'no_ticket':self.__uuid_tiket})
            if not result:
                self.uuid_ticket = self.__uuid_tiket
                break
        # Set email subject
        self.__subject = f"Bantuan No Ticket #{self.__uuid_tiket}"

        # Create email body template with user details
        self.__body = f"""
        <html>
            <body>
                <section>
                    <p>Kendala anda telah kami rekam yaitu:</p>
                    <table style="border-collapse: collapse; width: 100%;">
                        <tr>
                            <td style="border: none; padding: 8px; font-weight:bold;">Nama</td>
                            <td style="border: none; padding: 8px;">{self.__nickname_receiver.strip()}</td>
                        </tr>
                        <tr>
                            <td style="border: none; padding: 8px; font-weight:bold;">Jobs</td>
                            <td style="border: none; padding: 8px;">{self.__jobs.strip()}</td>
                        </tr>
                        <tr>
                            <td style="border: none; padding: 8px; font-weight:bold;">Departement</td>
                            <td style="border: none; padding: 8px;">{self.__departement.strip()}</td>
                        </tr>
                        <tr>
                            <td style="border: none; padding: 8px; font-weight:bold;">Kendala</td>
                            <td style="border: none; padding: 8px;">{self.__kendala.strip()}</td>
                        </tr>
                    </table>
                </section>
            </body>
        </html>
        """
        self.send_faq_via_gmail(self.__email_receiver, self.__subject, self.__body)

    # lakukan pengiriman email
    def send_faq_via_gmail(self, receiver_email, subject, body):
        self.message_id = super().send_otp_via_gmail(receiver_email=receiver_email, subject=subject, body=body) # jangan kupa ubah ke string to uuid
