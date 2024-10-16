import os
import random
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from email.mime.text import MIMEText
import base64

# If modifying these SCOPES, delete the file token.json

# cumanbisa handle 100 data otp

class OtpPasswordGenerator():
    SCOPES = ['https://www.googleapis.com/auth/gmail.send']
    otp = None
    def __init__(self,email_receiver:str,nickname_receiver:str='user'):
        # Example usage
        self.__receiver_email = f'{nickname_receiver} <{email_receiver}>'
        self.__otp = self.generate_otp()
        print(self.__otp)
        self.send_otp_via_gmail(self.__receiver_email, self.__otp)
        self.otp = self.__otp

    def generate_otp(self):
        # Generate a 6-digit OTP
        
        self.__otp = random.randint(100000, 999999)
        return self.__otp

    def create_message(self,sender, to, subject, message_text):
        """Create a message for an email."""
        self.__message = MIMEText(message_text, 'html')
        self.__message['to'] = to
        self.__message['from'] = sender
        self.__message['subject'] = subject
        self.__raw_message = base64.urlsafe_b64encode(self.__message.as_bytes()).decode()
        return {'raw': self.__raw_message}

    def send_message(self,service, user_id, message):
        """Send an email message."""
        try:
            self.__message = service.users().messages().send(userId = user_id, body = message).execute()
            print(f'Message Id: {self.__message["id"]}')
            return self.__message
        except Exception as error:
            print(f'An error occurred: {error}')
            return None

    def authenticate_gmail_api(self):
        """Authenticate and return the Gmail API service."""
        self.__creds = None
        # The file token.json stores the user's access and refresh tokens, and is
        # created automatically when the authorization flow completes for the first time.
        self.__client_token_path = os.path.join(os.getcwd(),'static','__secret') #ubah jadi app.root
        if os.path.exists(os.path.join(self.__client_token_path,'token_otp.json')):
            self.__creds = Credentials.from_authorized_user_file(os.path.join(self.__client_token_path,'token_otp.json'), self.SCOPES)
        # If there are no (valid) credentials available, let the user log in.
        if not self.__creds or not self.__creds.valid:
            # expired
            if self.__creds and self.__creds.expired and self.__creds.refresh_token:
                self.__creds.refresh(Request())
            else:
                self.__flow = InstalledAppFlow.from_client_secrets_file(os.path.join(self.__client_token_path, 'credentials.json'), self.SCOPES)
                self.__creds = self.__flow.run_local_server(port=900)
            # Save the credentials for the next run
            with open(os.path.join(self.__client_token_path,'token_otp.json'), 'w') as token:
                token.write(self.__creds.to_json())

        # Build the Gmail API service
        self.__service = build('gmail', 'v1', credentials=self.__creds)
        return self.__service

    def send_otp_via_gmail(self,receiver_email, otp):
        """Send OTP via Gmail using Gmail API."""
        self.__service = self.authenticate_gmail_api()
        self.__sender_email = "Winnicode Admin <salahudinkoliq21@gmail.com>"
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
        self.__message = self.create_message(self.__sender_email, receiver_email, self.__subject, self.__body)
        self.send_message(self.__service, 'me', self.__message)
