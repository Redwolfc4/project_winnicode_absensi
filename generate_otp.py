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
        print(self.__otp)
        self.send_otp_via_gmail(self.__receiver_email, self.__otp)
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
        from app import app,db

        """Authenticate and return the Gmail API service."""
        self.__creds = None
        # Retrieve values from environment
        self.__client_id = os.getenv('GOOGLE_CLIENT_ID')
        self.__client_secret = os.getenv('GOOGLE_CLIENT_SECRET')
        self.__redirect_uris = [os.getenv('GOOGLE_REDIRECT_URIS')]
        self.__token_uri = os.getenv('GOOGLE_TOKEN_URI')
        self.__auth_uri = os.getenv('GOOGLE_AUTH_URI')
        self.__auth_provider_cert_url = os.getenv('GOOGLE_AUTH_PROVIDER_CERT_URL')
        
        result = db.token_otp.find_one({},{'_id':0})
        if result:
            self.__creds = Credentials.from_authorized_user_info(
                result, self.SCOPES
            )
        
        # If there are no (valid) credentials available, let the user log in.
        if not self.__creds or not self.__creds.valid:
            # expired
            if self.__creds and self.__creds.expired and self.__creds.refresh_token:
                self.__creds.refresh(Request())
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
                print('jalan')
            # Save the credentials for the next run
            
            data = json.loads(self.__creds.to_json())
            db.token_otp.insert_one(data)
            
        # Build the Gmail API service
        self.__service = build("gmail", "v1", credentials=self.__creds)
        return self.__service

    def send_otp_via_gmail(self, receiver_email, otp):
        """Send OTP via Gmail using Gmail API."""
        self.__service = self.authenticate_gmail_api()
        self.__sender_email = os.getenv("GMAIL_SENDER")
        self.__subject = "Your OTP Code"
        # Menggunakan HTML untuk menampilkan OTP dalam format tebal
        self.__body = f"""
        <html>
            <body>
                <p>Your One-Time Password (OTP) is: <strong>{otp}</strong></p>
            </body>
        </html>
        """
        # Create and send the email
        self.__message = self.create_message(
            self.__sender_email, receiver_email, self.__subject, self.__body
        )
        self.send_message(self.__service, "me", self.__message)
