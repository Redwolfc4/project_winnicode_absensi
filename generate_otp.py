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
from bson import ObjectId

# If modifying these SCOPES, delete the file token.json
load_dotenv()
# cuman bisa handle 100 data otp


# otp password generator
class OtpPasswordGenerator:
    """
    Klas ini digunakan untuk mengirimkan One-Time Password (OTP) ke email yang ditentukan.

    Parameters:
    - email_receiver (str): Email address yang akan di kirimkan OTP.
    - nickname_receiver (str): Nama user yang menerima OTP (default: "user").

    Contoh penggunaan:
    >>> from generate_otp import OtpPasswordGenerator
    >>> otp = OtpPasswordGenerator("john@example.com", "John Doe")
    >>> otp.send_otp_email()
    """

    SCOPES = [os.getenv("GMAIL_SCOPE")]
    otp = None

    def __init__(self, email_receiver: str, nickname_receiver: str = "user"):
        """
        Klas ini digunakan untuk mengirimkan One-Time Password (OTP) ke email yang ditentukan.

        Parameters:
        - email_receiver (str): Email address yang akan di kirimkan OTP.
        - nickname_receiver (str): Nama user yang menerima OTP (default: "user").

        Contoh penggunaan:
        >>> from generate_otp import OtpPasswordGenerator
        >>> otp = OtpPasswordGenerator("john@example.com", "John Doe")
        >>> otp.otp
        "123456"  # OTP yang di generate
        """
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
        """
        Generate a 6-digit OTP and send it to the receiver's email using Gmail API.

        Parameters:
        email_receiver (str): The receiver's email address.
        nickname_receiver (str): The receiver's nickname.

        Returns:
        str: The generated OTP.

        Example usage:
        otp_generator = OtpPasswordGenerator("john@example.com", "John Doe")
        print(otp_generator.otp)  # Output: 123456
        """
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
        """Authenticate and return the Gmail API service."""
        from app import db

        self.__creds = None
        # Retrieve values from environment
        self.__client_id = os.getenv("GOOGLE_CLIENT_ID")
        self.__client_secret = os.getenv("GOOGLE_CLIENT_SECRET")
        self.__redirect_uris = [os.getenv("GOOGLE_REDIRECT_URIS")]
        self.__token_uri = os.getenv("GOOGLE_TOKEN_URI")
        self.__auth_uri = os.getenv("GOOGLE_AUTH_URI")
        self.__auth_provider_cert_url = os.getenv("GOOGLE_AUTH_PROVIDER_CERT_URL")
        result = db.gmail_service.find_one({}, {"_id": 0})
        if result:
            self.__creds = Credentials.from_authorized_user_info(result, self.SCOPES)

        # If there are no (valid) credentials available, let the user log in.
        if not self.__creds or not self.__creds.valid:
            # expired
            if self.__creds and self.__creds.expired and self.__creds.refresh_token:
                self.__creds.refresh(Request())
                # update the credentials for the next run
                data = json.loads(self.__creds.to_json())
                result = db.gmail_service.find_one({}, {"_id": 1})
                db.gmail_service.update_one({"_id": result["_id"]}, {"$set": data})
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


# This class likely sends emails with frequently asked questions (FAQs) using Gmail
class FaqGmailSender(OtpPasswordGenerator):
    """
    Class FaqGmailSender digunakan untuk mengirimkan email ke helpdesk@winnicode.com
    dengan format yang sesuai dengan kebutuhan FAQ.

    Contoh penggunaan:
    >>> from generate_otp import FaqGmailSender
    >>> faq = FaqGmailSender("john.doe@example.com", "John Doe", "Admin", "Superuser", "Tidak ada internet")
    >>> faq.send_faq_via_gmail()
    """

    uuid_ticket = None
    message_id = None

    def __init__(
        self,
        email_receiver: str = "",
        nickname_receiver: str = "user",
        jobs: str = "",
        departement: str = "",
        kendala: str = "",
    ):
        """
        Class FaqGmailSender digunakan untuk mengirimkan email ke helpdesk@winnicode.com
        dengan format yang sesuai dengan kebutuhan FAQ.

        Parameters:
        email_receiver (str): Email address yang akan di kirimkan email.
        nickname_receiver (str): Nama user yang mengirimkan email.
        jobs (str): Pekerjaan user yang mengirimkan email.
        departement (str): Departemen user yang mengirimkan email.
        kendala (str): Kendala yang dihadapi user.

        Contoh penggunaan:
        sender = FaqGmailSender(email_receiver="john@example.com", nickname_receiver="John Doe", jobs="Software Engineer", departement="IT", kendala="Gagal login ke sistem")
        sender.send_faq_email()
        """
        from app import db
        from absensiMethod import string_to_uuid_like

        self.__email_receiver = email_receiver
        self.__nickname_receiver = nickname_receiver
        self.__jobs = jobs
        self.__departement = departement
        self.__kendala = kendala

        # Check if any input is empty
        if not all(
            [
                self.__email_receiver.strip(),
                self.__nickname_receiver.strip(),
                self.__jobs.strip(),
                self.__departement.strip(),
                self.__kendala.strip(),
            ]
        ):
            print("Some input values are empty. Existing...")
            return None

        # Generate UUID for the ticket
        while True:
            self.__uuid_tiket = string_to_uuid_like(str(random.randint(0, 9999999)))
            result = db.faq.find_one({"no_ticket": self.__uuid_tiket})
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
        """
        Mengirimkan email melalui Gmail API dengan menggunakan credential yang
        sudah di set sebelumnya.

        Parameter:
            receiver_email (str): Alamat email penerima yang akan dikirimkan email.
            subject (str): Subyek email yang akan dikirimkan.
            body (str): Isi email yang akan dikirimkan dalam format HTML.

        Returns:
            str: Message ID dari email yang telah dikirimkan.
        """
        self.message_id = super().send_otp_via_gmail(
            receiver_email=receiver_email, subject=subject, body=body
        )  # jangan kupa ubah ke string to uuid


# This class likely sends replies to Gmail messages
class replyGmailSender(OtpPasswordGenerator):
    """
    Class untuk mengirimkan balasan email ke pengguna melalui Gmail API.

    Method yang tersedia:
    - __init__(self, message_id: dict=None): Konstruktor untuk kelas ReplyGmailSender.
        Parameter:
            message_id (dict): message id yang akan di reply.
    - service_gmail_api(self): Authenticate to Gmail API and return a Gmail API service instance.
    - reply_message_make(self, name: str = None, email: str = None, no_ticket: str = None): Buatkan body email untuk balasan.

    Parameter:
        - name (str): Nama pengguna yang akan di balas.
        - email (str): Email pengguna yang akan di balas.
        - no_ticket (str): Nomor ticket yang akan di balas.
    """

    def __init__(self, message_id: dict = None):
        """
        Konstruktor untuk kelas ReplyGmailSender

        Parameters:
        message_id (dict): message id yang akan di reply

        Returns:
        None
        """
        if message_id is None:
            return None
        self.__message_id = message_id

    def service_gmail_api(self):
        """Authenticate to Gmail API and return a Gmail API service instance.

        This method will authenticate to Gmail API using the credentials in the environment.
        If the credentials are valid, it will return a Gmail API service instance.
        If the credentials are invalid, it will raise an error.

        Returns:
            A Gmail API service instance.
        """

        self.__service = super().authenticate_gmail_api()

    def reply_message_make(
        self,
        name: str = None,
        email: str = None,
        no_ticket: str = None,
        body: str = None,
    ):
        """
        Buatkan body email untuk balasan.

        Parameters:
        - name (str): Nama pengguna yang akan di balas.
        - email (str): Email pengguna yang akan di balas.
        - no_ticket (str): Nomor ticket yang akan di balas.

        Returns:
        str: body email yang akan di gunakan untuk reply.

        Contoh:
        reply = ReplyGmailSender(message_id={"id": "1234567890abcdef"})
        body = reply.reply_message_make(name="John Doe", email="john@example.com", no_ticket="TCKT-12345")
        print(body)
        """
        if email is None and no_ticket is None and body is None:
            return None

        self.__name = name
        self.__email = email
        self.__no_ticket = no_ticket

        self.__body = f"""
        <html>
        <body>
            <div class='d-flex flex-column gap-2 align-items-center'>
                <p class='poppins-regular'>Hi Coders {self.__name},</p>
                {body}
                <div class='d-flex flex-column gap-1 align-items-center'>
                    <p class='poppins-regular'>Regards,</p>
                    <p class='poppins-regular'>Winnicode Support Team</p>
                </div>
            </div>
        </body>
        </html>
        """

        self.__subject = "Re: Winnicode helpdesk ticket # " + self.__no_ticket

        # Create a reply message
        self.__reply_message = MIMEText(self.__body, "html")
        if self.__name is None:
            self.__reply_message["to"] = f"{self.__email}"
        else:
            self.__reply_message["to"] = f"{self.__name} <{self.__email}>"
        self.__reply_message["from"] = os.getenv("GMAIL_SENDER")
        self.__reply_message["subject"] = self.__subject
        self.__reply_message["In-Reply-To"] = self.__message_id["id"]
        self.__reply_message["References"] = self.__message_id["id"]
        self.__raw_message = base64.urlsafe_b64encode(
            self.__reply_message.as_bytes()
        ).decode()
        self.__raw_body = {
            "raw": self.__raw_message,
            "threadId": self.__message_id["threadId"],
        }  # Memastikan email masuk ke dalam thread}
        self.__is_reply_created = True  # Set flag ke True

    def send_reply_message(self):
        """
        Kirimkan email balasan.

        Returns:
        dict: Berisi informasi tentang email yang terkirim.

        Contoh:
        reply = ReplyGmailSender(message_id={"id": "1234567890abcdef"})
        reply.reply_message_make(name="John Doe", email="john@example.com", no_ticket="TCKT-12345")
        response = reply.send_reply_message()
        print(response)
        """
        if not self.__is_reply_created:
            raise Exception(
                "Reply message has not been created. Call reply_message_make first."
            )

        self.__response = (
            self.__service.users()
            .messages()
            .send(userId="me", body=self.__raw_body)
            .execute()
        )
        print(f"Reply sent successfully!")
        print(f"Message ID: {self.__response['id']}")
        print(f"Thread ID: {self.__response['threadId']}")

        if self.__response:
            return self.__response
        else:
            return None


class TaskGmailNotif(OtpPasswordGenerator):

    message_id = None

    def __init__(self, task_id_new: ObjectId, path: str, **kwargs):
        """
        API Endpoint: /task_gmail_notif
        -----------------------------
        description: API untuk mengirimkan notifikasi task ke email yang terdaftar di Winnicode.
        parameters:
        - in: path
          name: task_id_new
          required: false
          description: ID task yang akan di notifikasi
          schema:
            type: string
        - in: query
          name: path
          required: false
          description: Path untuk mengarahkan halaman
          schema:
            type: string
        responses:
        - 200 OK: Sukses mengirimkan notifikasi task
        - 400 Bad Request: Request tidak valid
        - 500 Internal Server Error: Terjadi kesalahan di server
        examples:
        - parameters:
            - name: task_id_new
              value: "1234567890abcdef"
            - name: path
              value: "/task"
          response:
            - Sukses mengirimkan notifikasi task
        - parameters:
            - name: task_id_new
              value: "1234567890abcdef"
            - name: path
              value: "/task"
          response:
            - Gagal mengirimkan notifikasi task
        """

        from app import db, url_for  # import db
        from absensiMethod import string_to_uuid_like

        self.__task_id_new = task_id_new
        self.path = path

        if not self.__task_id_new:
            print("task_id_new kosong silahkan coba lagi")
            raise Exception("Error Database 1")

        self.__uuid_ticket = string_to_uuid_like(str(self.__task_id_new))
        if not self.__uuid_ticket:
            raise Exception("Decode Error")

        self.__pipeline = [
            {"$match": {"_id": ObjectId(self.__task_id_new)}},  # Hanya user_id tertentu
            {
                "$lookup": {
                    "from": "users",  # Koleksi yang akan digabungkan
                    "localField": "user_id",  # Field di koleksi orders
                    "foreignField": "_id",  # Field di koleksi users
                    "as": "user",  # Nama field hasil penggabungan
                }
            },
            {"$unwind": "$user"},  # Opsional: Memisahkan array menjadi objek individu
            {"$unset": ["_id", "user_id", "user._id", "user.password"]},
            {
                "$project": {
                    "taskName": 1,
                    "description_task": 1,
                    "link_input": 1,
                    "deadline": 1,
                    "user.nama": 1,  # Tampilkan `nama` dari `users`
                    "user.jobs": 1,  # Tampilkan `jobs` dari `users`
                    "user.departement": 1,  # Tampilkan `departement` dari `users`
                    "user.email": 1,
                }
            },
        ]

        # ambil datanya dari db task dan foreign user
        self.__results = list(db.tasks.aggregate(self.__pipeline))

        # jika gagal didapatkan
        if not self.__results:
            print("data gagal didapatkan dari db tasks dan users")
            raise Exception("Database Error 2")

        if self.path == "add":
            self.desc = "<p class='poppins-regular'> Kamu memiliki Task baru dengan detail sebagai berikut: </p>"

        elif self.path == "edit":
            if kwargs:
                if kwargs["newValue"] == True:
                    self.desc = "<p class='poppins-regular'> Task kamu telah di <span class='poppins-semibold'>Accepted</span> dengan detail sebagai berikut: </p>"
                else:
                    self.desc = "<p class='poppins-regular'> Task kamu telah di <span class='poppins-semibold'>Rejected</span> dengan detail sebagai berikut: </p>"
            else:
                self.desc = "<p class='poppins-regular'> Task kamu telah di update dengan detail sebagai berikut: </p>"

        # perulangan data aggregate
        for self.__result in self.__results:
            # Set email subject
            self.__subject = (
                f"Winnicode Tasks #{self.__uuid_ticket} : {self.__result['taskName']}"
            )

            # buat table link saat linkinput diisi
            self.__table_link = (
                f"""
            <tr>
                <td style="border: none; padding: 8px; font-weight:bold;">Link Pengerjaan</td>
                <td style="border: none; padding: 8px;"><a href="{self.__result['link_input'].strip()}">{self.__result['link_input'].strip()}</a></td>
            </tr>
            
            """
                if self.__result["link_input"]
                else ""
            )

            # Set email body
            self.__body = f"""
            <html>
            <body>
                <div class='d-flex flex-column gap-2 align-items-center'>
                    <div class='d-flex flex-column gap-1 align-items-center'>
                        <p class='poppins-regular'>Hi  <strong>{self.__result['user']['nama'].strip()}</strong></p> 
                        <p class='poppins-regular'>{self.__result['user']['jobs'].strip()} - {self.__result['user']['departement'].strip()}</p>
                    </div>
                    {self.desc}
                    <table style="border-collapse: collapse; width: 100%;">
                        <tr>
                            <td style="border: none; padding: 8px; font-weight:bold;">Task Name</td>
                            <td style="border: none; padding: 8px;">{self.__result['taskName'].strip()}</td>
                        </tr>
                        <tr>
                            <td style="border: none; padding: 8px; font-weight:bold;">Description task</td>
                            <td style="border: none; padding: 8px;">{self.__result['description_task'].strip()}</td>
                        </tr>
                        <tr>
                            <td style="border: none; padding: 8px; font-weight:bold;">Deadline</td>
                            <td style="border: none; padding: 8px;">{self.__result['deadline'].strftime('%Y-%m-%d %H:%M:%S')}</td>
                        </tr>
                        {self.__table_link}
                    </table>
                    <p class='poppins-regular'> Untuk melihat lebih lanjut, anda dapat langsung mengunjungi <a href='{url_for('task',_external=True)}' target='_blank' style='text-decoration: none; color: #ff66c4'>Absensi<span style='color: black;'>Ku</span></a> </p>
                </div>
            </body>
            </html>
            """

            # kirim datanya
            self.send_add_task_gmail_notif(
                receiver_email=self.__result["user"]["email"],
                subject=self.__subject,
                body=self.__body,
            )

    def send_add_task_gmail_notif(self, receiver_email: str, subject: str, body: str):
        """
        Kirimkan notifikasi task ke email user yang bersangkutan

        Parameters:
        receiver_email (str): Email address yang akan di kirimkan email.
        subject (str): Subject email yang akan di kirimkan.
        body (str): Body email yang akan di kirimkan.

        Returns:
        str: Message ID jika berhasil, None jika gagal.

        Examples:
        >>> from generate_otp import TaskGmailNotif
        >>> task = TaskGmailNotif(task_id_new=ObjectId, path="add")
        >>> message_id = task.send_add_task_gmail_notif(receiver_email="john.doe@example.com", subject="Tasks Winnicode", body="<p>ini adalah contoh body email</p>")
        >>> print(message_id)
        <Message-ID>
        """

        self.message_id = super().send_otp_via_gmail(
            receiver_email=receiver_email, subject=subject, body=body
        )  # jangan kupa ubah ke string to uuid


# notif absensi kirim gmail
class AbsensiNotify(OtpPasswordGenerator):

    message_id = None

    def __init__(
        self,
        email_receiver: str = "",
        angka_delta: int = None,
    ):
        """
        Kirimkan notifikasi absensi ke email user yang bersangkutan

        Parameters:
        email_receiver (str): Email address yang akan di kirimkan email.
        angka_delta (int): Jumlah menit yang tersisa untuk melakukan absensi.

        Returns:
        str: Message ID jika berhasil, None jika gagal.

        Examples:
        >>> from generate_otp import AbsensiNotify
        >>> notif = AbsensiNotify(email_receiver="john.doe@example.com", angka_delta=10)
        >>> message_id = notif.send_notif_gmail_absensi()
        >>> print(message_id)
        <Message-ID>
        """
        from app import db,url_for

        self.__email_receiver = email_receiver
        self.__angka_delta = angka_delta

        # Check if any input is empty
        if not self.__email_receiver.strip() or angka_delta is None:
            print("Some input values are empty. Existing...")
            return None

        self.__subject = "Absensiku Notif Kehadiran"

        # Create email body template with user details
        if self.__angka_delta > 0:
            self.__body = f"""
                Waktu tinggal {self.__angka_delta } menit, persiapan untuk melakukan absensi di <a href='{url_for('dashboard',_external=True)}' target='_blank' style='text-decoration: none; color: #ff66c4'>Absensi<span style='color: black;'>Ku</span></a>
            """
        elif self.__angka_delta  == 0:
            self.__body = f"""
                Absensi telah dimulai, segera lakukan absensi di <a href='{url_for('dashboard',_external=True)}' target='_blank' style='text-decoration: none; color: #ff66c4'>Absensi<span style='color: black;'>Ku</span></a> sekarang
            """
        elif self.__angka_delta  == -20:
            self.__body = f"""
                <p class='poppins-regular'>Waktu absensi Habis, Anda memasuki telat!.</p> 
                
                <p class='poppins-regular'>Jika anda merasa telat karena kendala, silahan hubungi melalui faq kami untuk perubahan absensi.</p> 
            """

        else:
            self.__body = f"""
                Waktu tinggal {(self.__angka_delta )} menit, segera lakukan absensi di <b>AbsensiKu<b> sekarang
            """

        self.send_absensiNotify_via_gmail(
            self.__email_receiver, self.__subject, self.__body
        )

    # lakukan pengiriman email
    def send_absensiNotify_via_gmail(self, receiver_email, subject, body):
        """
        Kirimkan notifikasi absensi ke email user yang bersangkutan

        Parameters:
        receiver_email (str): Email address yang akan di kirimkan email.
        subject (str): Subject email yang akan di kirimkan.
        body (str): Body email yang akan di kirimkan.

        Returns:
        str: Message ID jika berhasil, None jika gagal.

        Examples:
        >>> from generate_otp import AbsensiNotify
        >>> notif = AbsensiNotify(email_receiver="john.doe@example.com", angka_delta=10)
        >>> message_id = notif.send_absensiNotify_via_gmail(receiver_email="john.doe@example.com", subject="Absensiku Notif Kehadiran", body="<p>ini adalah contoh body email</p>")
        >>> print(message_id)
        <Message-ID>
        """
        self.message_id = super().send_otp_via_gmail(
            receiver_email=receiver_email, subject=subject, body=body
        )  # jangan kupa ubah ke string to uuid
