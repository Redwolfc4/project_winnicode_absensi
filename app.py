from absensiMethod import (
    cek_tanggal_kerja,
    format_date,
    format_time,
    signInPayload,
    string_to_uuid_like,
    unhadir_absensi,
    uuid_like_to_string,
    cipher,
    get_time_zone_now,
    is_valid_datetime_format,
)
from convert import convert_to_excel, PDF
import cryptography.fernet as Fernet
from flask import (
    Flask,
    redirect,
    url_for,
    render_template,
    request,
    jsonify,
    send_file,
    make_response,
)
from flask_wtf.csrf import CSRFProtect
from pymongo.mongo_client import MongoClient
from dotenv import load_dotenv
import os, hashlib, jwt, datetime
from bson import ObjectId
from apscheduler.schedulers.background import BackgroundScheduler
from io import BytesIO
from openpyxl import load_workbook
from werkzeug.utils import secure_filename
from werkzeug.datastructures import FileStorage
from generate_otp import (
    FaqGmailSender,
    OtpPasswordGenerator,
    replyGmailSender,
    TaskGmailNotif,
)
from markupsafe import Markup
import certifi

# buat request post sesuai datetime

# loading environment variables from.env file
load_dotenv()
url = os.getenv("MONGODB_URL")
secretKey = os.getenv("SECRET_KEY")

# connecting to mongodb
client = MongoClient(url, tls=True, tlsCAFile=certifi.where())
db = client["absen"]

# inisiasi app
app = Flask(__name__)
# melakukan config
app.config["SECRET_KEY"] = secretKey
# buat csrfprotect
csrf = CSRFProtect(app)

# Tentukan folder untuk menyimpan gambar
UPLOAD_FOLDER = os.path.join("/tmp", "static/img/user")
# Cek apakah path dapat ditulis
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER

# Daftarkan filter ke Jinja
app.jinja_env.filters["format_date"] = format_date
app.jinja_env.filters["format_time"] = format_time


# home
@app.route("/", methods=["GET"])
def home():
    """
    Home Page
    ----------

    This function will return the home.html which is the home page of the application.
    The home page will redirect to the signIn page if the user is not authenticated.
    """

    return render_template("home.html")


# manual book
@app.route("/manual/<path>", methods=["GET"])
def manual_book(path):
    file_path = os.path.join(app.root_path, "static", "doc")
    if not file_path:
        return make_response(jsonify({"redirect": url_for("home")}), 500)
    if path == "1":
        return send_file(
            file_path + "/pdf/manual_admin_subadmin.pdf",
            mimetype="application/pdf",
            as_attachment=True,
            download_name="manual_admin_subadmin_winnicode.pdf",
        )
    elif path == "3":
        return send_file(
            file_path + "/pdf/manual_karyawan_magang.pdf",
            mimetype="application/pdf",
            as_attachment=True,
            download_name="manual_karyawan_magang_winnicode.pdf",
        )
    else:
        return make_response(jsonify({"redirect": url_for("home")}), 500)


# lakukan sign-in
@app.route("/sign-in", methods=["GET", "POST"])
@app.route("/sign-in/", methods=["GET", "POST"])
def signIn():
    """
    Sign In Page
    -------------

    This function will return the signIn.html which is the sign in page of the application

    The page will have a form with input fields for user to fill in and a submit button.
    The form will be sent to the '/sign-in' route as a POST request when the submit button is clicked.

    The page will also have a link to the '/sign-up' route for user to register if they don't have an account yet.

    Returns:
        signIn.html
    """
    if request.method == "POST":
        try:
            email, password, jobs, csrf_token = (
                request.json.get("email"),
                request.json.get("password"),
                request.json.get("jobs"),
                request.headers.get("X-CSRF-Token"),
            )
            if email == "":
                raise Exception("Email cannot empty")
            elif password == "":
                raise Exception("Password cannot empty")
            elif csrf_token == "":
                raise Exception("CSRF Token cannot empty")
            elif jobs == "None":
                raise Exception("Jobs cannot empty")
            else:
                user = db["users"].find_one(
                    {
                        "email": email.lower(),
                        "jobs": jobs,
                    }
                )
                csrf_token = string_to_uuid_like(csrf_token)

                if not csrf_token:
                    raise Exception("encoding Gagal")

                # cek user
                if not user:
                    raise Exception("Wrong email")

                # cek password sama / tidak
                if not (
                    user["password"] == hashlib.sha256(password.encode()).hexdigest()
                ):
                    raise Exception("Wrong password")

                # cek jobs
                if user["jobs"] in ("Magang", "Karyawan"):
                    # cek mulai kerja dan akhir kerja ada/ tidak ada
                    if user["mulai_kerja"] and user["akhir_kerja"]:
                        # jika tanggal kerja tidak sesuai
                        if not cek_tanggal_kerja(
                            user["mulai_kerja"], user["akhir_kerja"]
                        ):
                            raise Exception(
                                "Your account expired or now is not your start work"
                            )
                    else:
                        raise Exception("your account pending, wait at least 24 hours")
                elif user["jobs"] in ("Admin", "Sub Admin"):
                    pass
                else:
                    raise Exception("Wrong jobs")

                # make token jwt
                token = signInPayload(
                    user["_id"],
                    user["jobs"],
                    user["role"],
                    datetime.timedelta(minutes=30),
                )

                # make the jwt
                token = string_to_uuid_like(token)

                # membuat response jsonify true
                resp = make_response(
                    jsonify(
                        {
                            "result": "success",
                            "redirect": "/dashboard",
                            "msg": "Login successful",
                        }
                    ),
                    200,
                )

                # set cookie
                resp.set_cookie(
                    "token_key",
                    token,
                    httponly=True,
                    secure=True,
                    samesite="Lax",
                    expires=get_time_zone_now() + datetime.timedelta(minutes=30),
                )  # ubah secure jadi true saat production
                resp.set_cookie(
                    "csrf_token",
                    csrf_token,
                    httponly=True,
                    secure=True,
                    samesite="Lax",
                    expires=get_time_zone_now() + datetime.timedelta(minutes=30),
                )  # ubah secure jadi true saat production

                # kembalikan responsenya
                return resp

        # handle error
        except Exception as e:
            return jsonify({"redirect": url_for("signIn", msg=e.args[0])}), 500

    # request method get
    msg = request.args.get("msg")
    status = request.args.get("status")
    title = request.args.get("title")

    # ambil dat aadmin keseluruhan
    admin_user_cek = db.users.find(
        {"jobs": "Admin", "departemen": "Superuser", "role": 1}
    )
    # cek apakah memiliki user admin / tidak?
    # jika tidak buat default awalan untuk superuser
    if not admin_user_cek:
        result = db.users.insert_one(
            {
                "nama": "admin",
                "email": "admin@gmail.com".lower(),
                "password": hashlib.sha256("123".strip().encode()).hexdigest(),
                "departement": "Superuser".strip(),
                "jobs": "Admin".strip(),
                "role": 1,
                "photo_profile": "img/default/user.png",
            }
        )
        # jika error ditengah tengah
        if not result:
            msg = "Failed to create default admin"
    return render_template("signIn.html", msg=msg, status=status, title=title)


# lakukan sign-up
@app.route("/sign-up", methods=["GET", "POST"])
@app.route("/sign-up/", methods=["GET", "POST"])
def signUp():
    """
    Sign Up Page
    ------------

    This function will return the signUp.html which is the sign up page of the application

    The page will have a form with input fields for user to fill in and a submit button.
    The form will be sent to the '/sign-up' route as a POST request when the submit button is clicked.

    The page will also have a link to the '/sign-in' route for user to sign in if they already have an account.

    Returns:
        signUp.html
    """
    if request.method == "POST":
        csrf_token, nama, departement, email, password, jobs = request.form.values()
        if nama == "":
            return redirect(url_for("signUp", msg="Nama cannot empty"))
        elif departement == "None":
            return redirect(url_for("signUp", msg="Departement cannot empty"))
        elif jobs == "None":
            return redirect(url_for("signUp", msg="Jobs cannot empty"))
        elif email == "":
            return redirect(url_for("signUp", msg="Email cannot empty"))
        elif password == "":
            return redirect(url_for("signUp", msg="Password cannot empty"))
        elif csrf_token == "":
            return redirect(url_for("signUp", msg="csrf token cannot empty"))

        cek_data = db.users.find_one({"email": email.lower()})
        if cek_data:
            return redirect(url_for("signUp", msg="Account Already Exist"))
        result = db.users.insert_one(
            {
                "nama": nama,
                "departement": departement,
                "jobs": jobs,
                "email": email.lower(),
                "password": hashlib.sha256(password.encode()).hexdigest(),
                "role": 3,
                "nik": "",
                "photo_profile": "img/default/user.png",
                "tempat_lahir": "",
                "tanggal_lahir": "",
                "mulai_kerja": "",
                "akhir_kerja": "",
                "waktu_awal_kerja": "",
                "waktu_akhir_kerja": "",
                "work_hours": 0,
                "absen": {"hadir": 0, "telat": 0, "tidak_hadir": 0, "libur": 0},
            }
        )
        if result:
            return redirect(
                url_for(
                    "signIn", msg="Sign Up Success", status="success", title="SignUp!"
                )
            )
        else:
            return redirect(url_for("signUp", msg="Sign Up Failed"))
    else:
        return render_template("signUp.html", msg=request.args.get("msg"))


# logout
@app.route("/api/auth/logout")
def signOut():
    """
    Sign Out
    --------

    This function handles the sign-out process for a user. It performs the following tasks:

    - Creates a response object with a JSON payload indicating the sign-out was successful.
    - Sets the 'token_key', 'csrf_token', and 'session' cookies to expire immediately, effectively logging the user out.

    Usage:
        This function is automatically called when a GET request is made to the '/api/auth/logout' route.
        It does not require any parameters to be passed and will log the user out by expiring the relevant cookies.

    Returns:
        A response object with a JSON payload containing:
        - status: 'success' indicating the sign-out was successful.
        - redirect: URL to redirect the user to the sign-in page.
        - msg: A message indicating the logout was successful.

        The response will have a status code of 200.
    """
    # Function implementation continues...
    resp = make_response(
        jsonify(
            {"status": "success", "redirect": "/sign-in", "msg": "Logout successful"}
        ),
        200,
    )
    # lakukan hapus cookie
    resp.set_cookie("token_key", expires=0)
    resp.set_cookie("csrf_token", expires=0)
    resp.set_cookie("session", expires=0)
    return resp


# lupa password get and post
@app.route("/sign-in/forget", methods=["GET", "POST"])
def forgetPassword():
    """
    Forget Password
    ===============

    Fungsi ini digunakan untuk proses forget password, berikut adalah cara penggunaannya:

    - Jika request method GET, maka akan menampilkan form untuk penginputan email.
    - Jika request method POST, maka akan mengirimkan email yang berisi link untuk reset password.
    - Jika email yang diinputkan tidak valid, maka akan muncul pesan error.
    - Jika email yang diinputkan valid, maka akan mengirimkan email yang berisi link untuk reset password.
    - Link yang dikirimkan akan berisi token yang akan digunakan untuk reset password.
    """
    if request.method == "POST":
        try:
            # inisisasi data
            csrf_token, email, password_new, password2_new = request.form.values()

            # cek kejadian errur halaman
            if csrf_token == None or csrf_token == "":
                raise ValueError("CSRF token tidak valid atau tidak ditemukan")
            if password_new != password2_new:
                raise ValueError("Password not same")
            if email.endswith("@gmail.com") == False or email == "":
                raise ValueError("Email not valid")

            # eksekusi pasword
            password_hash = hashlib.sha256(password_new.encode()).hexdigest()
            result = db.users.find_one(
                {"email": email.lower(), "jobs": {"$in": ["Magang", "Karyawan"]}}
            )

            # cek lanjutan dan update
            if not result:
                raise Exception("Email not found or jobs not Magang or Karyawan")
            if result["password"] == password_hash:
                raise ValueError("Password is same")
            Otp = OtpPasswordGenerator(email.lower(), result["nama"])
            if not Otp:
                raise Exception("Terjadi kesalahan dalam pembuatan otp")
            jwt_otp = jwt.encode(
                {
                    "otp": Otp.otp,
                    "password_hash": password_hash,
                    "user": str(result["_id"]),
                    "exp": datetime.datetime.utcnow() + datetime.timedelta(minutes=5),
                },
                secretKey,
                algorithm="HS256",
            )
            return redirect(
                url_for(
                    "forgetPasswordOtp",
                    jwt_otp=string_to_uuid_like(jwt_otp),
                    status="berhasil",
                    msg="OTP has been sent to your email",
                )
            )

        except ValueError as e:
            return redirect(url_for("forgetPassword", msg=e.args[0]))
        except Exception as e:
            return redirect(url_for("forgetPassword", msg=e.args[0]))

    # request method get
    msg = request.args.get("msg")
    return render_template("forgetPassword.html", msg=msg)


# bagian otp lupa password
@app.route("/sign-in/forget/otp/<jwt_otp>", methods=["GET", "POST"])
def forgetPasswordOtp(jwt_otp):
    """
    Handle route /sign-in/forget/otp/<jwt_otp>, menampilkan form untuk penginputan OTP yang dikirimkan ke email.

    Parameters:
        jwt_otp (str): token yang berisi OTP yang dikirimkan ke email dan password yang akan diupdate.

    Returns:
        str: render template forgetPasswordOtp.html
    """

    if request.method == "POST":
        try:
            # inisisasi data
            token = jwt_otp
            otp = request.json.get("otp")
            csrf_token = request.headers.get("X-CSRF-TOKEN")

            # cek kejadian errur halaman
            if csrf_token == None or csrf_token == "":
                raise ValueError("CSRF token tidak valid atau tidak ditemukan")
            if otp == None or otp == "":
                raise ValueError("OTP cannot empty")
            if token == None or token == "":
                raise ValueError("Token cannot empty")

            token = uuid_like_to_string(token)
            if not token:
                raise Exception("decode error")
            # terjemahkan jwt
            token_otp = jwt.decode(token, secretKey, algorithms="HS256")

            # cek otp yang dimasukkan sama dengan diberikan sama?
            if int(otp) != token_otp["otp"]:
                raise ValueError("OTP actual not same")

            result = db.users.update_one(
                {
                    "_id": ObjectId(token_otp["user"]),
                },
                {"$set": {"password": token_otp["password_hash"]}},
            )

            # berhasil atau tidak
            if result.modified_count <= 0:
                raise Exception("Terjadi kesalahan Update Password")

            return (
                jsonify(
                    redirect="/sign-in",
                    msg="Password updated",
                    status="success",
                    title="Update Password",
                ),
                200,
            )

        # catch erronya
        except jwt.ExpiredSignatureError:
            return (
                jsonify(redirect=url_for("forgetPassword", msg="Token Kadaluarsa")),
                500,
            )
        except jwt.InvalidTokenError:
            return (
                jsonify(redirect=url_for("forgetPassword", msg="Token TIdak valid")),
                500,
            )
        except ValueError as e:
            return (
                jsonify(
                    redirect=url_for(
                        "forgetPasswordOtp", jwt_otp=jwt_otp, msg=e.args[0]
                    )
                ),
                500,
            )
        except Exception as e:
            return (
                jsonify(
                    redirect=url_for(
                        "forgetPasswordOtp", jwt_otp=jwt_otp, msg=e.args[0]
                    )
                ),
                500,
            )

    # request method get
    result = request.args.get("status")
    msg = request.args.get("msg")
    return render_template(
        "forgetPasswordOtp.html", token=jwt_otp, msg=msg, result=result
    )


# ballon_faq post
@app.route("/ask", methods=["POST"])
def ask():
    """
    Fungsi ini digunakan untuk menghandle form balonFAQ yang dikirimkan melalui metode POST.

    Fungsi ini akan mengambil nilai dari form yang dikirimkan dan menyimpannya ke dalam collection
    `faq` di database. Jika ada error selama proses, maka fungsi ini akan mengembalikan response
    dengan status 404 dan isi pesan error.

    Parameters:
        csrf_token (str): Token csrf yang dikirimkan melalui form
        name (str): Nama yang dikirimkan melalui form
        email (str): Email yang dikirimkan melalui form
        jobs (str): Jabatan yang dikirimkan melalui form
        departement (str): Departemen yang dikirimkan melalui form
        kendala (str): Kendala yang dikirimkan melalui form

    Returns:
        Response: Response dengan status 200 dan isi pesan success jika proses berhasil, atau response
        dengan status 404 dan isi pesan error jika terjadi error
    """
    try:
        csrf_token = request.headers.get("X-CSRF-TOKEN")
        name, email, jobs, departement, kendala = request.json.values()

        # cek csrf token valid atau tidak
        if csrf_token == "" or csrf_token == None:
            return make_response(
                jsonify({"status": "error", "msg": "your csrf is None"}), 400
            )

        # The above code is performing input validation for the variables `name`, `email`, `jobs`, and
        # `departement`. It checks if any of these variables are empty or None after stripping any
        # leading or trailing whitespaces. If any of the variables are empty or None, it raises an
        # Exception with a corresponding error message indicating that the respective field is empty
        # and prompts the user to enter the required information.
        if name.strip() == "" or name.strip() == None:
            raise Exception("Nama anda Kosong, silahkan masukkan nama anda")
        if email.strip() == "" or email.strip() == None:
            raise Exception("email anda Kosong, silahkan masukkan email anda")
        if jobs.strip() == "" or jobs.strip() == None:
            raise Exception("jobs anda Kosong, silahkan masukkan jobs anda")
        if departement.strip() == "" or departement.strip() == None:
            raise Exception(
                "departement anda Kosong, silahkan masukkan departement anda"
            )
        if kendala.strip() == "" or kendala.strip() == None:
            raise Exception("kendala anda Kosong, silahkan masukkan kendala anda")
        # melakukan pengiroman kendala ke gmail
        result_kirim_email = FaqGmailSender(
            email.strip(),
            name.strip(),
            jobs.strip(),
            departement=departement.strip(),
            kendala=kendala.strip(),
        )
        if not result_kirim_email:
            raise Exception("Gagal mengirim email")

        # tambahakan faq baru ke database
        add_faq_to_db = db.faq.insert_one(
            {
                "message_id": result_kirim_email.message_id,
                "no_ticket": result_kirim_email.uuid_ticket,
                "email": email.strip(),
                "name": name.strip(),
                "jobs": jobs.strip(),
                "departement": departement.strip(),
                "kendala": kendala.strip(),
                "status": "Pending",
            }
        )
        if not add_faq_to_db:
            raise Exception("Gagal menambahkan faq ticket ke database")

        # render sigin dengan status success
        return (
            jsonify(
                {
                    "redirect": url_for(
                        "signIn",
                        msg=Markup(
                            'Pengaduan anda dengan no ticket <b class="poppins-semibold">#'
                            + result_kirim_email.uuid_ticket
                            + "</b> telah kami terima"
                        ),
                        status="success",
                        title="Pengaduan berhasil!",
                    )
                }
            ),
            200,
        )
    # The above code is handling exceptions related to JWT (JSON Web Token) authentication. It catches
    # different types of exceptions that can occur during JWT verification:
    except Exception as e:
        return jsonify({"redirect": url_for("signIn", msg=e.args[0])}), 500


# update my profile
@app.route("/myProfiles", methods=["GET", "POST"])
def myProfiles():
    """
    Update my profile

    Parameters:
    user_id (str): user id of the user who want to update their profile
    nama (str): new name of the user
    email (str): new email of the user
    photo_profile (file): new photo profile of the user
    tempat_lahir (str): new place of birth of the user
    tanggal_lahir (str): new date of birth of the user
    mulai_kerja (str): new start date of work of the user
    akhir_kerja (str): new end date of work of the user
    waktu_awal_kerja (str): new start time of work of the user
    waktu_akhir_kerja (str): new end time of work of the user
    work_hours (int): new total work hours of the user

    Returns:
    Json response with result, redirect, and msg
        result (str): success jika berhasil, unsuccess jika gagal
        redirect (str): url yang akan di redirect
        msg (str): pesan yang akan ditampilkan jika gagal

    Example:
    >>> import requests
    >>> url = 'http://localhost:5000/myProfiles'
    >>> data = {'user_id':'62d8a6d5f2f7f7a3f80f8f8b','nama':'new name','email':'new email','photo_profile':'','tempat_lahir':'','tanggal_lahir':'','mulai_kerja':'','akhir_kerja':'','waktu_awal_kerja':'','waktu_akhir_kerja':'','work_hours':0}
    >>> headers = {'X-CSRF-Token':'b0a2f43a-58a7-4d1e-8b7f-6f5f6f6f6f6f'}
    >>> response = requests.post(url, json=data, headers=headers)
    >>> response.json()
    {'result': 'success', 'redirect': '/dashboard', 'msg': ''}
    """
    if request.method == "POST":
        try:
            # The above code is attempting to retrieve the value of the "token_key" cookie from the
            # request object in a Python web application. It uses the `get` method on the `cookies`
            # attribute of the `request` object to access the value of the "token_key" cookie. If the
            # cookie is present in the request, its value will be stored in the `token_key` variable.
            token_key = request.cookies.get("token_key")
            if token_key == None or token_key == "":
                raise ValueError("Token cannot empty")
            # The code snippet provided is attempting to convert a UUID-like object `token_key` to a
            # string using the `uuid_like_to_string` function. If the resulting `token_key` string is
            # empty, it raises a `ValueError` with the message "decode token error".
            token_key = uuid_like_to_string(token_key)
            if not token_key:
                raise ValueError("decode token error")
            # The above Python code snippet is decoding a JSON Web Token (JWT) using the `jwt.decode`
            # function with the specified secret key and algorithm "HS256". It then checks if the
            # decoded payload's "role" value is not equal to 3. If the condition is met, it retrieves
            # values from the form data (csrf_token, email, nama, and possibly a profile picture file)
            # using `request.form.values()` and `request.files.get("profile-pic")`.
            payloads = jwt.decode(token_key, secretKey, algorithms=["HS256"])
            if payloads["role"] != 3:
                csrf_token, email, nama = request.form.values()
                gambar = request.files.get("profile-pic")
            else:
                gambar = request.files.get("profile-pic")
                csrf_token, email, nama, nik, tempat_lahir, tanggal_lahir = (
                    request.form.values()
                )
                tanggal_lahir = (
                    datetime.datetime.strptime(tanggal_lahir, "%Y-%m-%d")
                    .strftime("%d %B %Y")
                    .lower()
                )

            # The above code is checking if the variable `gambar` is falsy (e.g., None, empty string,
            # 0). If `gambar` is falsy, it retrieves the `photo_profile` field from a document in the
            # `users` collection in a MongoDB database based on the `_id` field provided in the
            # `payloads` dictionary.
            if not gambar:
                gambar = db.users.find_one(
                    {"_id": ObjectId(payloads["_id"])}, {"photo_profile": 1}
                )["photo_profile"]

            # cek csrf token
            if csrf_token == None or csrf_token == "":
                raise ValueError("CSRF token tidak valid atau tidak ditemukan")

            # The above Python code snippet is checking the type of the variable `gambar`. If `gambar`
            # is a string, it sets the `filepath_db` variable to the value of `gambar`. If `gambar` is
            # a `FileStorage` object (typically used for file uploads in Flask), it checks the file
            # extension to ensure it is either ".png", ".jpg", or ".jpeg". If the extension is not
            # valid, it redirects to a URL with a message indicating the extension is not allowed. If
            # the file extension is valid, it secures the filename, saves the file to a specified
            # folder
            if type(gambar) == str:
                filepath_db = gambar
            elif type(gambar) == FileStorage:
                # cek ectension gambar
                if gambar.filename.endswith((".png", ".jpg", ".jpeg")) == False:
                    return redirect(
                        url_for("myProfiles", msg="undefined extension .png .jpg .jpeg")
                    )
                # Amankan nama file
                filename = secure_filename(gambar.filename)
                # Simpan file ke folder yang ditentukan
                filepath = os.path.join(app.config["UPLOAD_FOLDER"], filename)
                gambar.save(filepath)
                filepath_db = "img/user/" + filename
            else:
                return redirect(url_for("myProfiles", msg="Something Wrong Files!"))

            # The above code is updating user information in a MongoDB database based on the role of
            # the user. If the user's role is 3, it updates the user's email, name, ID number, place
            # of birth, date of birth, and profile photo. If the user's role is not 3, it updates the
            # user's email, name, and profile photo. The code uses the `update_one` method from the
            # `db.users` collection in MongoDB to update the user information.
            if payloads["role"] == 3:
                result = db.users.update_one(
                    {
                        "_id": ObjectId(payloads["_id"]),
                    },
                    {
                        "$set": {
                            "email": email.lower(),
                            "nama": nama.title(),
                            "nik": int(nik),
                            "tempat_lahir": tempat_lahir.title(),
                            "tanggal_lahir": tanggal_lahir,
                            "photo_profile": filepath_db,
                        }
                    },
                )
            else:
                result = db.users.update_one(
                    {
                        "_id": ObjectId(payloads["_id"]),
                    },
                    {
                        "$set": {
                            "email": email.lower(),
                            "nama": nama.title(),
                            "photo_profile": filepath_db,
                        }
                    },
                )

            # The above Python code is checking the value of the variable `result`. If `result`
            # evaluates to `True`, it will redirect the user to the "myProfiles" route with a success
            # message "Update Profile Berhasil". If `result` is `False`, it will redirect the user to
            # the "myProfiles" route with a failure message "Update Profile Gagal".
            if result:
                return redirect(
                    url_for(
                        "myProfiles", msg="Update Profile Berhasil", status="success"
                    )
                )
            else:
                return redirect(url_for("myProfiles", msg="Update Profile Gagal"))

        # The above code snippet is handling exceptions in a Python function. It is using a try-except
        # block to catch specific exceptions and then redirecting the user to the "signIn" route with
        # a specific message based on the type of exception caught.
        except jwt.ExpiredSignatureError:
            return redirect(url_for("signIn", msg="Session Expired"))
        except jwt.DecodeError:
            return redirect(url_for("signIn", msg="Anda telah logout"))
        except ValueError as e:
            return redirect(url_for("signIn", msg=e.args[0]))

    # get method
    # The above code snippet is written in Python and it seems to be part of a web application using a
    # framework like Flask or Django. It is trying to retrieve the values of "msg" and "status"
    # parameters from the request arguments. These values are typically passed in the URL query string
    # when a user makes a request to the server. The retrieved values are stored in the variables
    # `msg` and `status` respectively.
    msg = request.args.get("msg")
    status = request.args.get("status")
    try:
        # The above Python code is checking for the presence and validity of CSRF token and token key
        # retrieved from cookies in a web request. If either the CSRF token or token key is missing or
        # empty, it raises a `ValueError` with a corresponding error message indicating that the CSRF
        # token or token key is not valid or not found.
        token_key = request.cookies.get("token_key")
        csrf_token = request.cookies.get("csrf_token")
        if csrf_token == None or csrf_token == "":
            raise ValueError("CSRF token tidak valid atau tidak ditemukan")
        if token_key == None or token_key == "":
            raise ValueError("Token key tidak valid atau tidak ditemukan")

        # decode uuid
        token_key = uuid_like_to_string(token_key)
        csrf_token = uuid_like_to_string(csrf_token)
        if not csrf_token:
            return redirect(url_for("signIn", msg="CSRF Token Expired"))
        if not token_key:
            return redirect(url_for("signIn", msg="Token Key Expired"))

        # decode jwt
        payloads = jwt.decode(token_key, secretKey, algorithms=["HS256"])

        # cek data user
        data = db.users.find_one({"_id": ObjectId(payloads["_id"])})

        # tampilkan
        return render_template("myProfiles.html", data=data, msg=msg, status=status)

    # The above code is handling different exceptions that may occur in a Python application.
    except jwt.ExpiredSignatureError:
        return redirect(url_for("signIn", msg="Session Expired"))
    except jwt.DecodeError:
        return redirect(url_for("signIn", msg="Anda telah logout"))
    except ValueError as ve:
        return redirect(url_for("signIn", msg=ve.args[0]))
    except Exception as e:
        return redirect(url_for("signIn", msg=e.args[0]))


# dasboard magang get
@app.route("/dashboard", methods=["GET"])
def dashboard():
    """
    Dashboard Magang
    ================

    This function handles requests to the '/dashboard' route, which is used to display the dashboard for interns. It performs the following tasks:

    - Retrieves the 'result' and 'msg' parameters from the request.
    - Checks for the presence and validity of CSRF token and authentication cookies.
    - Decodes JWT token from the cookies to get the user's payload.
    - Retrieves user data from the database based on the payload.
    - Renders the 'change_password.html' template with the user data, result, and message.

    If any validation fails (e.g., expired token, missing cookies), the function redirects the user to the sign-in page with an appropriate message.

    Usage:
    ------
    This function is automatically called when a GET request is made to the '/dashboard' route. It requires valid authentication cookies and a CSRF token to process the request successfully. If the user has the proper role, they can access the intern dashboard.

    Returns:
    --------
    Redirects to the sign-in page with a message if validation fails, or renders the 'change_password.html' template with user data if successful.
    """
    result = request.args.get("result")
    msg = request.args.get("msg")
    cookie = request.cookies.get("token_key")
    csrf_token = request.cookies.get("csrf_token")

    try:
        # cek ada cookie dan csrf token / tidak ?
        if not cookie:
            raise Exception("Cookie Expired")
        if not csrf_token:
            raise Exception("CSRF Token Expired")
        # convet uuid
        cookie = uuid_like_to_string(cookie)
        csrf_token = uuid_like_to_string(csrf_token)

        # convert jwt
        payload = jwt.decode(cookie, secretKey, algorithms=["HS256"])

        # ambil data
        data = db.users.find_one(
            {
                "_id": ObjectId(payload["_id"]),
                "jobs": payload["jobs"],
                "role": payload["role"],
            }
        )

        # cek role dan jobs yang didapat untuk render template
        # bagian magang / karyawan
        if data["role"] == 3:
            # ambiltanggal sekarang
            data["tanggal_sekarang"] = get_time_zone_now().strftime("%d %B %Y").lower()

            # ambil data table absen
            table_hadir = db.absen_magang.find_one(
                {
                    "user_id": ObjectId(payload["_id"]),
                    "tanggal_hadir": data["tanggal_sekarang"],
                }
            )

            # cek tanggal pelaksanan kerja
            waktu_sekarang = get_time_zone_now()
            waktu30menit = waktu_sekarang + datetime.timedelta(minutes=30)
            waktu_sekarang = waktu_sekarang.time()
            waktu_awal_kerja = datetime.datetime.strptime(
                data["waktu_awal_kerja"].replace(".", ":"), "%H:%M"
            ).time()
            waktu_akhir_kerja = datetime.datetime.strptime(
                data["waktu_akhir_kerja"].replace(".", ":"), "%H:%M"
            ).time()

            # customize button berdasarkan jam kerja ,sebelum, dan sesudah tanpa melakukan klik hadir
            if waktu_awal_kerja <= waktu_sekarang:
                # ini saat mulai klik hadir
                if waktu_sekarang <= waktu_akhir_kerja:
                    data["class-button-hadir"] = "btn-primary"
                    data["text-button"] = "Hadir"
                    # dah kelar tapi belum diklik bang
                else:
                    data["class-button-hadir"] = "btn-danger disabled opacity-100"
                    data["text-button"] = "Tidak Hadir"
            else:
                data["class-button-hadir"] = "btn-secondary disabled"
                data["text-button"] = "Belum Absen"

            # ambil anggka heading card dan customize button berdasarkan cek status hadir dan waktu
            if table_hadir:
                # konversi waktu hadir
                waktu_hadir = datetime.datetime.strptime(
                    table_hadir["waktu_hadir"].replace(".", ":"), "%H:%M"
                ).time()
                # membuat jumlah absen dalam rentang kontrak
                data["heading-card"] = (
                    data["absen"]["hadir"] + data["absen"]["tidak_hadir"]
                )
                # saat jam awal dan sudah dapat melakukan absen
                if (
                    table_hadir["status_hadir"] == "1"
                    and waktu_hadir <= waktu_akhir_kerja
                ):
                    data["class-button-hadir"] = "btn-success disabled opacity-100"
                    data["text-button"] = "Hadir"
                # saat jam akhir dan sudah dapat melakukan absen
                elif (
                    table_hadir["status_hadir"] == 2
                    and waktu_hadir <= waktu_akhir_kerja
                ):
                    data["class-button-hadir"] = "btn-warning disabled opacity-100"
                    data["text-button"] = "Telat"
                elif (
                    table_hadir["status_hadir"] in ("1", 2)
                    and waktu_hadir >= waktu_akhir_kerja
                ):
                    data["class-button-hadir"] = "btn-secondary disabled"
                    data["text-button"] = "Selesai"
                else:
                    pass
            else:
                data["heading-card"] = (
                    data["absen"]["hadir"] + data["absen"]["tidak_hadir"] + 1
                )

            # ini buat lihat hadir dan tidak hadir
            data2 = [
                {
                    "titleCard": "Hadir",
                    "textColor": "text-success",
                    "angkaCard": data["absen"]["hadir"],
                    "icon": "fas fa-check fa-2x text-success text-opacity-25",
                    "borderLeft": "border-left-success",
                },
                {
                    "titleCard": "Telat",
                    "textColor": "text-warning",
                    "angkaCard": data["absen"]["telat"],
                    "icon": "fa-solid fa-triangle-exclamation fa-2x text-warning text-opacity-25",
                    "borderLeft": "border-left-warning",
                },
                {
                    "titleCard": "Tidak Hadir",
                    "textColor": "text-danger",
                    "angkaCard": data["absen"]["tidak_hadir"],
                    "icon": "fa-regular fa-circle-xmark fa-2x text-danger text-opacity-25",
                    "borderLeft": "border-left-danger",
                },
                {
                    "titleCard": "Liburan",
                    "textColor": "text-danger-emphasis",
                    "angkaCard": data["absen"]["libur"],
                    "icon": "fa-solid fa-bed fa-2x text-danger-emphasis text-opacity-25",
                    "borderLeft": "border-left-danger-emphasis",
                },
            ]
            # hanya untuk karywan dan magang
            if (data["jobs"] == "Magang") or (data["jobs"] == "Karyawan"):
                return render_template(
                    "dashboard_magang.html",
                    data=data,
                    data2=data2,
                    msg=msg,
                    result=result,
                )
            else:
                return redirect(url_for("signIn", msg="Anda bukan Magang / Karyawan"))
        # bagian admin
        elif data["role"] == 1:
            if data["jobs"] == "Admin" or data["jobs"] == "Sub Admin":
                # panjang table awal
                first_table = request.args.get("page_awal", 1, type=int)
                # panjang table
                table_length = request.args.get("length", 10, type=int)
                # Hitung offset
                skip = (first_table - 1) * table_length
                # atur search
                search = request.args.get("search", default="", type=str)
                data_karyawan_magang_new = []

                # ambil data limit
                data_karyawan_magang = list(
                    db.users.find({"jobs": {"$in": ["Magang", "Karyawan"]}})
                    .skip(skip)
                    .limit(table_length)
                )

                # hitunhg data
                count_data_karyawan_magang = db.users.count_documents(
                    {"jobs": {"$in": ["Magang", "Karyawan"]}}
                )
                # Hitung showing
                if count_data_karyawan_magang == 0:
                    start_index = skip
                else:
                    start_index = skip + 1

                end_index = min(skip + table_length, count_data_karyawan_magang)

                # tambah data indeks
                data["total_page"] = (
                    count_data_karyawan_magang + table_length - 1
                ) // table_length
                data["first_table"] = first_table  # table awal
                data["table_length"] = table_length  # table akhir
                data["count_data_karyawan_magang"] = count_data_karyawan_magang

                # fitur pencarian
                if search != "" and search != None:
                    for data_karyawan in data_karyawan_magang:
                        # cek berdasarkan jobs,role,departement,nama,nik,email,tanggal_lahir,tempat_lahir
                        if (
                            search in data_karyawan["jobs"].lower()
                            or search in str(data_karyawan["role"])
                            or search in data_karyawan["departement"].lower()
                            or search in data_karyawan["nama"].lower()
                            or search in str(data_karyawan["nik"])
                            or search in data_karyawan["email"].lower()
                            or search in data_karyawan["tempat_lahir"].lower()
                            or search in data_karyawan["tanggal_lahir"].lower()
                        ):
                            data_karyawan_magang_new.append(data_karyawan)
                        continue
                    # cek datakaryawan ditemukan atau tidak
                    if len(data_karyawan_magang_new) <= 0:
                        return redirect(
                            url_for("dashboard", msg="Data tidak ditemukan")
                        )
                    # ditemukan
                    data_karyawan_magang = data_karyawan_magang_new
                    end_index = len(data_karyawan_magang)
                # editable showing
                data["showing_table_karyawan"] = (
                    f"Showing {start_index} to {end_index} of {count_data_karyawan_magang} entries"
                )
                # judul
                data["heading_title_body"] = "Dashboard"

                # render
                return render_template(
                    "dashboard_magang.html",
                    data=data,
                    data_karyawan_magang=data_karyawan_magang,
                    msg=msg,
                    search=search,
                    result=result,
                )
            else:
                return redirect(url_for("signIn", msg="Anda bukan administration"))

        else:
            return redirect(url_for("signIn", msg="Anda bukan bagian dari perusahaan"))
    # handle error
    except jwt.ExpiredSignatureError:
        return redirect(url_for("signIn", msg="Session Expired"))
    except jwt.DecodeError:
        return redirect(url_for("signIn", msg="Anda telah logout"))
    except Exception as e:
        return redirect(url_for("signIn", msg=e.args[0]))


# dashboard absen
@app.route("/dashboard/absen", methods=["POST"])
def dashboardAbsen():
    """
    Buat absensi magang berdasarkan tanggal sekarang

    Parameters:
    user_id (str): id user yang diambil dari cookie
    status_hadir (str): status hadir yang diinputkan oleh user
        1 jika hadir
        0 jika tidak hadir
    Returns:
    Json response with result, redirect, and msg
        result (str): success jika berhasil, unsuccess jika gagal
        redirect (str): url yang akan di redirect
        msg (str): pesan yang akan ditampilkan jika gagal

    Example:
    >>> import requests
    >>> url = 'http://localhost:5000/dashboard/absen'
    >>> data = {'user_id':'62d8a6d5f2f7f7a3f80f8f8b','status_hadir':'1'}
    >>> headers = {'X-CSRF-Token':'b0a2f43a-58a7-4d1e-8b7f-6f5f6f6f6f6f'}
    >>> response = requests.post(url, json=data, headers=headers)
    >>> response.json()
    {'result': 'success', 'redirect': '/dashboard/magang', 'msg': ''}
    """
    # ambil tanggal sekarang dan waktu sekarang
    now = get_time_zone_now()
    time_now = now.time()
    try:
        # ambil csrf token
        csrf_token = request.headers.get("X-CSRF-Token")
        csrf = request.cookies.get("csrf_token")
        # cek token
        if csrf_token == "" and csrf_token == None:
            raise Exception("csrf token expired")
        if csrf == "" and csrf == None:
            raise Exception("csrf token cookie expired")
        csrf = uuid_like_to_string(csrf)
        if not csrf:
            raise Exception("CSRF decode error")
        # ambil data dari form
        userId = request.form.get("user_id")
        status_hadir = request.form.get("status_hadir")
        print(status_hadir)

        # ambil riwayat absen
        riwayat_absen = db.absen_magang.find_one(
            {"user_id": ObjectId(userId)}, sort={"_id": -1}
        )

        # cek sudah klik button absen / belum sebelumnya
        if (
            now.date()
            <= datetime.datetime.strptime(
                riwayat_absen["tanggal_hadir"], "%d %B %Y"
            ).date()
            and time_now
            >= datetime.datetime.strptime(riwayat_absen["waktu_hadir"], "%H.%M").time()
        ):
            return (
                jsonify(
                    {
                        "result": "unsuccess",
                        "redirect": url_for(
                            "dashboard",
                            msg="Anda sudah absen pada tanggal "
                            + riwayat_absen["tanggal_hadir"],
                        ),
                    }
                ),
                200,
            )
        # cek status hadir bukan 1 ubah jadi int
        if status_hadir != "1":
            status_hadir = int(status_hadir)

        # jika hadir
        if status_hadir == "1":
            setting = {
                "absen.hadir": db.users.find_one({"_id": ObjectId(userId)})["absen"][
                    "hadir"
                ]
                + 1
            }
        # jika telat
        else:
            setting = {
                "absen.telat": db.users.find_one({"_id": ObjectId(userId)})["absen"][
                    "telat"
                ]
                + 1
            }

        # lakukan update
        result = db.users.find_one_and_update(
            {"_id": ObjectId(userId)},
            {"$set": setting},
        )
        if not result:
            raise Exception("Terjadi kesalahan dalam update jumlah absen ke db")

        # lakukan penambahan absen magang riwayat
        result = db.absen_magang.insert_one(
            {
                "user_id": ObjectId(userId),
                "status_hadir": status_hadir,
                "waktu_hadir": get_time_zone_now().strftime("%H.%M").lower(),
                "tanggal_hadir": get_time_zone_now().strftime("%d %B %Y").lower(),
            }
        )
        if not result:
            raise Exception("Terjadi kesalahan dalam penambahan riwayat ke db")
        # success
        return jsonify({"result": "success", "redirect": "/dashboard"}), 200
    # handle error
    except jwt.ExpiredSignatureError:
        return jsonify({"redirect": url_for("signIn", msg="Session Expired")}), 500
    except jwt.DecodeError:
        return jsonify({"redirect": url_for("signIn", msg="Anda telah logout")}), 500
    except Exception as e:
        if not e.args:
            e.args = [
                "terjadi kesalahan data",
            ]
        return jsonify({"redirect": url_for("signIn", msg=f"{e.args[0]}")}), 500


# change password
@app.route("/change-password", methods=["GET", "POST"])
def change_password():
    """
    Change Password
    ===============

    This function handles requests to the '/change-password' route, which allows users to change their password. It performs the following tasks:

    - GET request: Renders the 'change_password.html' template.
    - POST request: Validates CSRF token and authentication cookies, checks for the presence of X-CSRFToken header, and processes the password change if valid.

    If any validation fails (e.g., expired token, missing cookies), the function returns a JSON response with a status code indicating failure and redirects to the sign-in page with an appropriate message.

    Usage:
    ------
    This function is automatically called when a GET or POST request is made to the '/change-password' route. It requires valid authentication cookies and a CSRF token to process the request successfully.

    Returns:
    --------
    - Renders the 'change_password.html' template on a GET request.
    - On a POST request, returns a JSON response with a status code and redirect URL if validation fails.
    """
    # method post
    if request.method == "POST":
        try:
            # ambil dulu cookie dan headers
            cookie = request.cookies.get("token_key")
            csrf_token = request.cookies.get("csrf_token")
            X_CSRFToken = request.headers.get("X-CSRFToken")
            # cek csrf token
            if csrf_token == None or csrf_token == "":
                return jsonify(
                    {
                        "status": 400,
                        "redirect": url_for("sign-in", msg="CSRF Token Expired"),
                    }
                )
            # cek xcsrf token
            if X_CSRFToken == None or X_CSRFToken == "":
                return jsonify(
                    {
                        "status": 400,
                        "redirect": url_for("sign-in", msg="X-CSRF Token Expired"),
                    }
                )
            # cek cookie
            if cookie == None or cookie == "":
                return jsonify(
                    {
                        "status": 400,
                        "redirect": url_for("sign-in", msg="Cookie Expired"),
                    }
                )

            # ambil dulu convert
            cookie = uuid_like_to_string(cookie)
            csrf_token = uuid_like_to_string(csrf_token)
            if not csrf_token:
                return jsonify(
                    {
                        "status": 401,
                        "redirect": url_for("sign-in", msg="CSRF Token Expired"),
                    }
                )
            if not cookie:
                return jsonify(
                    {
                        "status": 401,
                        "redirect": url_for("sign-in", msg="Cookie Expired"),
                    }
                )

            # decode payload
            payload = jwt.decode(cookie, secretKey, algorithms=["HS256"])
            if payload["role"] not in (1, 3):
                raise Exception("anda tidak punya hak akses")

            # ambil data password di database
            password_db = db.users.find_one(
                {
                    "_id": ObjectId(payload["_id"]),
                    "jobs": payload["jobs"],
                    "role": payload["role"],
                    "password": hashlib.sha256(
                        request.form.get("old_password").encode()
                    ).hexdigest(),
                },
                {"_id": 0, "password": 1},
            )
            # cek sama atau tidak
            if not password_db:
                raise Exception("password lama salah")

            # cek password baru dengan lama
            if (
                hashlib.sha256(request.form.get("new_password").encode()).hexdigest()
                == password_db["password"]
            ):
                raise Exception("password baru tidak boleh sama dengan lama")

            # update password
            result = db.users.update_one(
                {
                    "_id": ObjectId(payload["_id"]),
                    "jobs": payload["jobs"],
                    "role": payload["role"],
                },
                {
                    "$set": {
                        "password": hashlib.sha256(
                            request.form.get("new_password").encode()
                        ).hexdigest()
                    }
                },
            )

            # cek berhasil atau tidak
            if result.modified_count <= 0:
                raise Exception("Gagal merubah password")
            return jsonify(
                {
                    "status": 200,
                    "redirect": url_for(
                        "change_password",
                        msg="Password Berhasil DIubah",
                        result="success",
                    ),
                }
            )
        # atasi error jwt
        except jwt.ExpiredSignatureError:
            return jsonify(
                {"status": 401, "redirect": url_for("signIn", msg="Session Expired")}
            )
        except jwt.DecodeError:
            return jsonify(
                {"status": 408, "redirect": url_for("signIn", msg="Anda telah logout")}
            )
        # atasi error lainnya
        except Exception as e:
            return jsonify(
                {"status": 400, "redirect": url_for("change_password", msg=e.args[0])}
            )

    # method get
    try:
        # ambil data
        cookie = request.cookies.get("token_key")
        csrf_token = request.cookies.get("csrf_token")
        result = request.args.get("result")
        msg = request.args.get("msg")
        # cek ada ga?
        if csrf_token == None or csrf_token == "":
            return redirect(url_for("signIn", msg="csrf token expired"))
        if cookie == None or cookie == "":
            return redirect(url_for("signIn", msg="Cookie Expired"))
        # konvert
        cookie = uuid_like_to_string(cookie)
        csrf_token = uuid_like_to_string(csrf_token)
        # konvert ke 2
        payload = jwt.decode(cookie, secretKey, algorithms=["HS256"])
        data = db.users.find_one(
            {
                "_id": ObjectId(payload["_id"]),
                "jobs": payload["jobs"],
                "role": payload["role"],
            }
        )
        data["heading_title_body"] = "Change Password"
        return render_template(
            "change_password.html", data=data, result=result, msg=msg
        )
    except jwt.ExpiredSignatureError:
        return redirect(url_for("signIn", msg="Session Expired"))
    except jwt.DecodeError:
        return redirect(url_for("signIn", msg="Anda telah logout"))


# riwayat kehadiran
@app.route("/riwayat-kehadiran", methods=["GET"])
def riwayat_kehadiran():
    """
    Fungsi ini digunakan untuk menampilkan riwayat kehadiran karyawan dan magang.

    Parameter:
    - Tidak ada parameter

    Return:
    - Halaman riwayat kehadiran karyawan dan magang

    Contoh penggunaan:
    - /riwayat-kehadiran
    """

    try:
        # The above Python code is checking for the presence of a CSRF token and a token key in the
        # request cookies. If the CSRF token is not found (i.e., None), it redirects the user to the
        # "signIn" route with a message indicating that the CSRF token has expired. Similarly, if the
        # token key is not found (i.e., None), it redirects the user to the "signIn" route with a
        # message indicating that the user has been logged out. This code is likely part of a web
        # application's security mechanism to ensure that valid CSRF tokens and user authentication
        # tokens are present before allowing access
        msg = request.args.get("msg")
        result = request.args.get("result")
        csrf_token = request.cookies.get("csrf_token")
        cookies = request.cookies.get("token_key")
        if csrf_token == None:
            return redirect(url_for("signIn", msg="csrf token expired"))
        if cookies == None:
            return redirect(url_for("signIn", msg="Anda Telah logout"))
        # The above Python code snippet is converting `cookies` and `csrf_token` variables from a
        # UUID-like format to a string format using the `uuid_like_to_string` function. It then checks
        # if the `csrf_token` or `cookies` are empty, and if so, it redirects the user to the "signIn"
        # route with a message indicating that either the CSRF token has expired or the cookie has
        # expired.
        cookies = uuid_like_to_string(cookies)
        csrf_token = uuid_like_to_string(csrf_token)
        if not csrf_token:
            return redirect(url_for("signIn", msg="CSRF Token Expired"))
        if not cookies:
            return redirect(url_for("signIn", msg="Cookie Expired"))
        # The above Python code snippet is decoding a JSON Web Token (JWT) from the `cookies` using a
        # `secretKey` with the HS256 algorithm. It then retrieves data from a MongoDB database based
        # on the decoded payload. If the role in the payload is not equal to 1 and the job is not
        # 'admin', it fetches the attendance history (`riwayat_absent`) for a specific user ID.
        # Otherwise, if the conditions are not met, it fetches the attendance history for all users.
        payloads = jwt.decode(cookies, secretKey, algorithms=["HS256"])
        data = db.users.find_one(
            {"_id": ObjectId(payloads["_id"])},
            {
                "_id": 0,
                "jobs": 1,
                "role": 1,
                "nama": 1,
                "departement": 1,
                "photo_profile": 1,
            },
        )
        if not data:
            return redirect(url_for("dashboard", msg="Terjadi kesalahan data"))
        if payloads["role"] != 1 and payloads["jobs"] not in ("Admin", "Sub Admin"):
            riwayat_absent = list(
                db.absen_magang.find(
                    {"user_id": ObjectId(payloads["_id"])},
                    {"_id": 0, "status_hadir": 1, "waktu_hadir": 1, "tanggal_hadir": 1},
                )
            )
        else:
            # gabungkan data riwayat absen karyawan dan magang
            riwayat_absent = list(
                db.absen_magang.aggregate(
                    [
                        {
                            "$lookup": {
                                "from": "users",
                                "localField": "user_id",
                                "foreignField": "_id",
                                "as": "user",
                            }
                        },
                        {"$unwind": "$user"},
                        {
                            "$match": {
                                "user.role": {"$ne": 1},
                                "user.jobs": {"$nin": ["admin"]},
                            }
                        },
                        {"$unset": ["user_id", "user._id", "user.password"]},
                        {
                            "$project": {
                                "_id": 1,
                                "status_hadir": 1,
                                "waktu_hadir": 1,
                                "tanggal_hadir": 1,
                                "user.nama": 1,  # Tampilkan `nama` dari `users`
                                "user.jobs": 1,  # Tampilkan `jobs` dari `users`
                                "user.departement": 1,  # Tampilkan `departement` dari `users`
                                "user.role": 1,  # Tampilkan `role` dari `users`
                                "user.email": 1,
                                "user.nik": 1,
                            }
                        },
                    ]
                )
            )
            if riwayat_absent:
                for i in riwayat_absent:
                    # decrypt id riwayat absen
                    i["_id"] = string_to_uuid_like(
                        cipher.encrypt(str(i["_id"]).encode()).decode()
                    )

        # render template riwayat_kehadiran.html
        return render_template(
            "riwayat_kehadiran.html",
            riwayat_absent=riwayat_absent,
            data=data,
            msg=msg,
            result=result,
        )

    # The above code is a Python snippet that includes multiple `except` blocks to handle different
    # types of exceptions.
    except jwt.ExpiredSignatureError:
        return redirect(url_for("signIn", msg="Session Expired"))
    except jwt.DecodeError:
        return redirect(url_for("signIn", msg="Anda telah logout"))
    except Exception:
        return redirect(url_for("signIn", msg="something went wrong!"))


# riwayat kehadiran post
@app.route("/riwayat-kehadiran/<path1>", methods=["POST"])
@app.route("/riwayat-kehadiran/<path1>/<path2>", methods=["POST"])
def riwayat_kehadiran_post(path1=None, path2=None):
    """
    Handle route /riwayat-kehadiran/<path1> and /riwayat-kehadiran/<path1>/<path2> to edit riwayat kehadiran.

    Args:
        path1 (str): The first path parameter.
        path2 (str): The second path parameter.

    Returns:
        str: redirect to /riwayat-kehadiran if success, otherwise redirect to signIn with appropriate message.

    Usage:
        /riwayat-kehadiran/edit/<id_riwayat_absent> to edit riwayat kehadiran with id <id_riwayat_absent>
    """
    try:
        # lakukan validasi cooke masih ada
        csrf_token = request.cookies.get("csrf_token")
        cookies = request.cookies.get("token_key")
        if csrf_token == None:
            return redirect(url_for("signIn", msg="csrf token expired"))
        if cookies == None:
            return redirect(url_for("signIn", msg="Anda Telah logout"))

        # lakukan decode uuid validasi cookie
        cookies = uuid_like_to_string(cookies)
        csrf_token = uuid_like_to_string(csrf_token)
        if not csrf_token:
            return redirect(url_for("signIn", msg="CSRF Token Expired"))
        if not cookies:
            return redirect(url_for("signIn", msg="Cookie Expired"))

        # lakukan encode payloads
        payloads = jwt.decode(cookies, secretKey, algorithms=["HS256"])
        if not payloads:
            return redirect(url_for("signIn", msg="Anda Telah logout"))

        # jika pathnya edit
        if (
            path1 == "edit"
            and payloads["role"] == 1
            and payloads["jobs"] in ("Admin", "Sub Admin")
        ):
            # method put
            if request.form["__method"] == "PUT":
                # form csrf dimiliki
                if (
                    request.form["__csrf_token"] != None
                    or request.form["__csrf_token"] != ""
                ):

                    # inisiasi form
                    id_riwayat_absent = request.form["__id_riwayat_absent"]
                    nik = int(request.form["nik"])
                    email = request.form["email"]
                    status_hadir = request.form["status_hadir"]

                    # cek status hadir dimiliki dan konversi
                    if status_hadir == None or status_hadir == "":
                        raise Exception("Anda harus memilih status hadir")
                    elif status_hadir != "1":
                        status_hadir = int(status_hadir)

                    # lakukan validasi nik dimikii
                    if nik == None or nik == "":
                        raise Exception("Anda harus mengisi profile terlebih dahulu")

                    # lakukan validasi email dan id_riwayat_absent
                    if "" in (email, id_riwayat_absent) or None in (
                        email,
                        id_riwayat_absent,
                    ):
                        raise Exception("This data is undefined please try again")

                    # decript id riwayat absen
                    absen_magang_id = cipher.decrypt(
                        uuid_like_to_string(id_riwayat_absent).encode()
                    ).decode()

                    # do change it absen_magang
                    update_absen_magang = db.absen_magang.find_one_and_update(
                        {"_id": ObjectId(absen_magang_id)},
                        {"$set": {"status_hadir": status_hadir}},
                    )

                    # cek berhasil diupdate
                    if not update_absen_magang:
                        raise Exception("Gagal update status absent")

                    # lakukan kondisi untuk perubahan status_hadir referrer user
                    if update_absen_magang["status_hadir"] == "1":
                        setting = {
                            "$set": {
                                "absen.hadir": db.users.find_one(
                                    {"_id": update_absen_magang["user_id"]}
                                )["absen"]["hadir"]
                                - 1
                            }
                        }
                    elif update_absen_magang["status_hadir"] == 2:
                        setting = {
                            "$set": {
                                "absen.telat": db.users.find_one(
                                    {"_id": update_absen_magang["user_id"]}
                                )["absen"]["telat"]
                                - 1
                            }
                        }
                    elif update_absen_magang["status_hadir"] == 3:
                        setting = {
                            "$set": {
                                "absen.libur": db.users.find_one(
                                    {"_id": update_absen_magang["user_id"]}
                                )["absen"]["libur"]
                                - 1
                            }
                        }
                    else:
                        setting = {
                            "$set": {
                                "absen.tidak_hadir": db.users.find_one(
                                    {"_id": update_absen_magang["user_id"]}
                                )["absen"]["tidak_hadir"]
                                - 1
                            }
                        }

                    # tambahkan seting absen pada user untuk status
                    if status_hadir == "1":
                        setting["$set"]["absen.hadir"] = (
                            db.users.find_one({"_id": update_absen_magang["user_id"]})[
                                "absen"
                            ]["hadir"]
                            + 1
                        )
                    elif status_hadir == 2:
                        setting["$set"]["absen.telat"] = (
                            db.users.find_one({"_id": update_absen_magang["user_id"]})[
                                "absen"
                            ]["telat"]
                            + 1
                        )
                    elif status_hadir == 3:
                        setting["$set"]["absen.libur"] = (
                            db.users.find_one({"_id": update_absen_magang["user_id"]})[
                                "absen"
                            ]["libur"]
                            + 1
                        )
                    else:
                        setting["$set"]["absen.tidak_hadir"] = (
                            db.users.find_one({"_id": update_absen_magang["user_id"]})[
                                "absen"
                            ]["tidak_hadir"]
                            + 1
                        )

                    # laukan perubahan absen pada user
                    update_absen_user = db.users.find_one_and_update(
                        {"_id": update_absen_magang["user_id"]}, setting
                    )

                    # cek berhasil melakukan update absen pada user
                    if not update_absen_user:
                        raise Exception("Gagal update absent bagian user")

                    return redirect(
                        url_for(
                            "riwayat_kehadiran",
                            msg=f"Riwayat absen atas nama {update_absen_user['nama']} berhasil diupdate",
                            result="success",
                        )
                    )

                else:
                    raise Exception("Please do with page web")
            else:
                raise Exception("This method is not allowed")

        # delete kehadiran kryawan / magang
        elif (
            path1 == "delete"
            and payloads["role"] == 1
            and payloads["jobs"] in ("Admin", "Sub Admin")
        ):
            if request.form["_method"] == "DELETE":
                # form csrf dimiliki
                if (
                    request.form["__csrf_token"] != None
                    or request.form["__csrf_token"] != ""
                ):
                    # inisiasi form yang diperlukan
                    if path2 == None or path2 == "":
                        raise Exception("This data is undefined please try again")

                    # decript id riwayat absen
                    absen_magang_id = cipher.decrypt(
                        uuid_like_to_string(path2).encode()
                    ).decode()

                    # lakukan validasi email dan id_riwayat_absent
                    if not absen_magang_id or absen_magang_id == "":
                        raise Exception(
                            "This data decrypt is undefined please try again"
                        )

                    # cari riwayat absen
                    riwayat_absen = db.absen_magang.find_one_and_delete(
                        {"_id": ObjectId(absen_magang_id)}
                    )

                    # lakukan pengurangan bagian user sesuai id riwayat absen
                    if not riwayat_absen:
                        raise Exception("Riwayat absen tidak ditemukan")

                    # cari user berdasarkan id riwayat absen
                    user = db.users.find_one({"_id": riwayat_absen["user_id"]})

                    # cek user didapatkan atau tidak
                    if not user:
                        raise Exception("User tidak ditemukan")

                    # cek status hadir riwayat absen dalam bentuk angka dan string
                    if riwayat_absen["status_hadir"] == "1":
                        setting = {"$set": {"absen.hadir": user["absen"]["hadir"] - 1}}
                    elif riwayat_absen["status_hadir"] == 2:
                        setting = {"$set": {"absen.telat": user["absen"]["telat"] - 1}}
                    elif riwayat_absen["status_hadir"] == 3:
                        setting = {"$set": {"absen.libur": user["absen"]["libur"] - 1}}
                    else:
                        setting = {
                            "$set": {
                                "absen.tidak_hadir": user["absen"]["tidak_hadir"] - 1
                            }
                        }

                    # lakukan pengurangan pada user
                    delete_absen_user = db.users.find_one_and_update(
                        {"_id": riwayat_absen["user_id"]}, setting
                    )

                    # cek user didapatkan atau tidak
                    if not delete_absen_user:
                        raise Exception("Gagal update absent bagian user")

                    return redirect(
                        url_for(
                            "riwayat_kehadiran",
                            msg=f"Riwayat absen atas nama {delete_absen_user['nama']} berhasil di hapus",
                            result="success",
                        )
                    )
                # error csrf
                raise Exception("Please do with page web")
            # error custom method
            else:
                raise Exception("This method is not allowed")
        # error auth user
        else:
            return redirect(
                url_for("signin", msg="Anda tidak memiliki akses terhadap halaman ini")
            )

    # handle error
    except jwt.ExpiredSignatureError:
        return redirect(url_for("signIn", msg="Session Expired"))
    except jwt.DecodeError:
        return redirect(url_for("signIn", msg="Anda telah logout"))
    except Fernet.InvalidToken:
        return redirect(
            url_for(
                "riwayat_kehadiran", msg="Token update invalid please refresh your page"
            )
        )
    except Exception as e:
        if not e.args:
            e.args = ("terjadi kesalahan data",)
        return redirect(url_for("riwayat_kehadiran", msg=e.args[0]))


# riwayat bantuan
@app.route("/riwayat-bantuan", methods=["GET"])
def riwayat_bantuan():
    """
    Riwayat Bantuan
    ---------------

    This function handles requests to the '/riwayat-bantuan' route, which is used to display the
    history of assistance requests. It performs the following tasks:

    - Checks for the presence and validity of CSRF token and authentication cookies.
    - Decodes JWT token from the cookies to get the user's payload.
    - Validates the user's role to ensure they have the appropriate access.
    - Retrieves status and message parameters from the request.
    - Handles any exceptions that may occur during processing.

    If any validation fails (e.g., expired token, missing cookies), the function redirects the user
    to the sign-in page with an appropriate message.

    Usage:
        This function is automatically called when a GET request is made to the '/riwayat-bantuan'
        route. It requires valid authentication cookies and a CSRF token to process the request
        successfully. If the user has the proper role, they can access the assistance history.

    Returns:
        Redirects to the sign-in page with a message if validation fails, or processes the request
        to display the assistance history if successful.
    """

    # Function implementation continues...
    # The above Python code snippet is checking for the presence and validity of a CSRF token and a
    # cookie in a web request. Here is a breakdown of the code:
    cookie = request.cookies.get("token_key")
    csrf_token = request.cookies.get("csrf_token")
    if csrf_token == None:
        return redirect(url_for("signIn", msg="csrf token expired"))
    if cookie == None:
        return redirect(url_for("signIn", msg="Anda Telah logout"))

    # convert this to data real and check if success or not
    cookie = uuid_like_to_string(cookie)
    csrf_token = uuid_like_to_string(csrf_token)
    if not csrf_token:
        return redirect(url_for("signIn", msg="CSRF Token Expired"))
    if not cookie:
        return redirect(url_for("signIn", msg="Cookie Expired"))

    try:
        status = request.args.get("status")
        msg = request.args.get("msg")

        # decode payload
        payloads = jwt.decode(cookie, secretKey, algorithms=["HS256"])
        if payloads["role"] != 1:
            return redirect(url_for("dashboard", msg="Anda tidak memiliki akses"))
        data = db.users.find_one(
            {"_id": ObjectId(payloads["_id"])},
            {
                "_id": 0,
                "jobs": 1,
                "role": 1,
                "nama": 1,
                "departement": 1,
                "photo_profile": 1,
            },
        )
        if not data:
            return redirect(url_for("dashboard", msg="Terjadi kesalahan data"))
        # take data all
        data_faq_all = list(db.faq.find({}))
        if data_faq_all:
            for i in data_faq_all:
                i["_id"] = string_to_uuid_like(
                    cipher.encrypt(str(i["_id"]).encode()).decode()
                )
                if not i["_id"]:
                    raise Exception("Terjadi Kesalahan Data dalam encrypt")
                if i["status"] == "Pending":
                    i["selectClass"] = (
                        "border-warning border-2 rounded p-2 bg-transparent text-warning"
                    )
                elif i["status"] == "Diproses":
                    i["selectClass"] = (
                        "border-info border-2 rounded p-2 bg-transparent text-info"
                    )
                elif i["status"] == "Selesai":
                    i["selectClass"] = (
                        "border-success border-2 rounded p-2 bg-transparent text-success"
                    )
        return render_template(
            "riwayat_bantuan.html",
            data=data,
            riwayat_bantuan=data_faq_all,
            result=status,
            msg=msg,
        )

    # The above code is handling exceptions related to JWT (JSON Web Token) authentication. It catches
    # different types of exceptions that can occur during JWT verification:
    except jwt.ExpiredSignatureError:
        return redirect(url_for("signIn", msg="Session Expired"))
    except jwt.DecodeError:
        return redirect(url_for("signIn", msg="Anda telah logout"))
    except Fernet.InvalidToken:
        return redirect(
            url_for(
                "riwayat_bantuan", msg="Token update invalid please refresh your page"
            )
        )
    except IndexError as e:
        return redirect(url_for("riwayat_bantuan", msg=e.args[0]))
    except Exception as e:
        return redirect(url_for("riwayat_bantuan", msg=e.args[0]))


@app.route("/update-status-bantuan", methods=["POST"])
def riwayat_bantuan_post():
    # The above Python code snippet is checking for the presence and validity of a CSRF token and a
    # cookie in a web request. Here is a breakdown of the code:
    cookie = request.cookies.get("token_key")
    csrf_token = request.cookies.get("csrf_token")
    if csrf_token == None:
        return jsonify({"redirect": url_for("signIn", msg="csrf token expired")}), 500
    if cookie == None:
        return jsonify({"redirect": url_for("signIn", msg="Anda Telah logout")}), 500

    # convert this to data real and check if success or not
    cookie = uuid_like_to_string(cookie)
    csrf_token = uuid_like_to_string(csrf_token)
    if not csrf_token or not cookie:
        return (
            jsonify({"redirect": url_for("signIn", msg="convert token failed!")}),
            500,
        )
    try:
        # ambil data headers terlebih dahulu
        x_request, x_csrf = (
            request.headers.get("X-Requested-With"),
            request.headers.get("X-CSRF-TOKEN"),
        )
        if not x_request or not x_csrf or x_request != "XMLHttpRequest":
            return (
                jsonify({"redirect": url_for("signIn", msg="Terjadi kesalahan data")}),
                500,
            )

        status, id_status = request.json.values()
        if (
            not status
            and not id_status
            and type(status) != str
            and type(id_status) != str
        ):
            raise Exception("Terjadi Kesalahan dalam pengiriman data")

        # decode payload
        payloads = jwt.decode(cookie, secretKey, algorithms=["HS256"])
        if payloads["role"] != 1:
            return (
                jsonify(
                    {"redirect": url_for("dashboard", msg="Anda tidak memiliki akses")}
                ),
                500,
            )

        # decript id riwayat absen
        status_id = cipher.decrypt(uuid_like_to_string(id_status).encode()).decode()

        # pemgambilan data message_id dari db faq
        message_id = db.faq.find_one(
            {"_id": ObjectId(status_id)},
            {"_id": 0, "message_id": 1, "email": 1, "no_ticket": 1, "name": 1},
        )
        # cek ditemukan / tidak
        if not message_id:
            raise Exception("Terjadi Kesalahan dalam pengambilan data")

        # sesuaikan status untuk body gmail kirim
        if status == "Diproses":
            body = f"""
            <p class='poppins-regular'>Thanks for contacts our help, Your inquiry was still in the processing stage, please wait for <strong> 2 x 24 hours </strong> for our response</p>
            """
        elif status == "Selesai":
            body = f"""
            <p class='poppins-regular'>Thanks for your waiting, Your inquiry has been resolved, Hopefully the solution we provide can help you.
            </p>
            <p class='poppins-regular'>If you have any questions, please contact us at <a class='text-info' href='{url_for("signIn",_external=True)}'>Signin</a></p>
            """
        else:
            raise Exception("Terjadi Kesalahan dalam status")

        # kirim pesan ke gmail untuk update status
        reply_message = replyGmailSender(message_id["message_id"])
        reply_message.service_gmail_api()
        reply_message.reply_message_make(
            name=message_id["name"],
            email=message_id["email"],
            no_ticket=message_id["no_ticket"],
            body=body,
        )
        response = reply_message.send_reply_message()
        # cek response yang didapatkan
        if not response:
            raise Exception("Terjadi Kesalahan dalam reply email")
        # update proses riwayatnya
        if status == "Diproses":
            result = db.faq.find_one_and_update(
                {"_id": ObjectId(status_id)},
                {
                    "$set": {
                        "status": status,
                        "message_id": {
                            "id": response["id"],
                            "threadId": response["threadId"],
                        },
                    }
                },
                {"_id": 0, "no_ticket": 1, "name": 1},
            )
        elif status == "Selesai":
            result = db.faq.find_one_and_delete(
                {"_id": ObjectId(status_id)}, {"_id": 0, "no_ticket": 1, "name": 1}
            )
        else:
            raise Exception("Terjadi Kesalahan status")
        # Cek apakah update berhasil
        if not result:
            raise Exception("Data status tidak ditemukan dan gagal di update")

        return (
            jsonify(
                {
                    "redirect": url_for(
                        "riwayat_bantuan",
                        msg=Markup(
                            f"Status bantuan dengan no <span class='poppins-semibold'>'#{result['no_ticket']}'</span> bernama <span class='poppins-semibold'>{result['name']}</span> berhasil di update"
                        ),
                        status="success",
                    )
                }
            ),
            200,
        )

    # The above code is handling exceptions related to JWT (JSON Web Token) authentication. It catches
    # different types of exceptions that can occur during JWT verification:
    except jwt.ExpiredSignatureError:
        return jsonify({"redirect": url_for("signIn", msg="Session Expired")}), 500
    except jwt.DecodeError:
        return jsonify({"redirect": url_for("signIn", msg="Anda telah logout")}), 500
    except Fernet.InvalidToken:
        return (
            jsonify(
                {
                    "redirect": url_for(
                        "riwayat_bantuan",
                        msg="Token update invalid please refresh your page",
                    )
                }
            ),
            500,
        )
    except Exception as e:
        return jsonify({"redirect": url_for("riwayat_bantuan", msg=e.args[0])}), 500
    except IndexError as e:
        return jsonify({"redirect": url_for("riwayat_bantuan", msg=e.args[0])}), 500


@app.route("/kelola-admin", methods=["GET"])
@app.route("/kelola-admin/", methods=["GET"])
@app.route("/kelola-admin/<path1>", methods=["POST"])
@app.route("/kelola-admin/<path1>/<path2>", methods=["POST"])
def kelola_admin(path1=None, path2=None):
    """
    Kelola Admin
    ===========

    Fungsi ini digunakan untuk mengelola data admin, berikut adalah cara penggunaannya:

    - Jika request method GET, maka akan menampilkan data admin.
    - Jika request method POST, maka akan mengupdate atau menambahkan data admin.
    - Jika parameter path1 bernilai "create", maka akan menambahkan data admin.
    - Jika parameter path1 bernilai "update", maka akan mengupdate data admin.
    - Jika parameter path1 bernilai "delete", maka akan menghapus data admin.
    - Jika parameter path1 bernilai "show", maka akan menampilkan data admin berdasarkan parameter path2.

    Contoh pemakaiannya:
    >>> import requests
    >>> url = 'http://localhost:5000/kelola-admin'
    >>> data = {
    ...     'nama':'admin baru',
    ...     'email':'adminbaru@example.com',
    ...     'password':'password',
    ...     'role':1
    ... }
    >>> response = requests.post(url, data=data)
    >>> response.url
    'http://localhost:5000/kelola-admin?msg=data+admin+berhasil+ditambahkan&result=success'
    """
    try:
        # The above Python code is checking for the presence of a CSRF token and a token key in the
        # request cookies. If the CSRF token is not found (i.e., None), it redirects the user to the
        # "signIn" route with a message indicating that the CSRF token has expired. Similarly, if the
        # token key is not found (i.e., None), it redirects the user to the "signIn" route with a
        # message indicating that the user has been logged out. This code is likely part of a web
        # application's security mechanism to ensure that valid CSRF tokens and user authentication
        # tokens are present before allowing access
        csrf_token = request.cookies.get("csrf_token")
        cookies = request.cookies.get("token_key")
        if csrf_token == None:
            return redirect(url_for("signIn", msg="csrf token expired"))
        if cookies == None:
            return redirect(url_for("signIn", msg="Anda Telah logout"))
        # The above Python code snippet is converting `cookies` and `csrf_token` variables from a
        # UUID-like format to a string format using the `uuid_like_to_string` function. It then checks
        # if the `csrf_token` or `cookies` are empty, and if so, it redirects the user to the "signIn"
        # route with a message indicating that either the CSRF token has expired or the cookie has
        # expired.
        cookies = uuid_like_to_string(cookies)
        csrf_token = uuid_like_to_string(csrf_token)
        if not csrf_token:
            return redirect(url_for("signIn", msg="CSRF Token Expired"))
        if not cookies:
            return redirect(url_for("signIn", msg="Cookie Expired"))
        # The above Python code snippet is decoding a JSON Web Token (JWT) from the `cookies` using a
        # `secretKey` with the HS256 algorithm. It then retrieves data from a MongoDB database based
        # on the decoded payload. If the role in the payload is not equal to 1 and the job is not
        # 'admin', it fetches the attendance history (`riwayat_absent`) for a specific user ID.
        # Otherwise, if the conditions are not met, it fetches the attendance history for all users.
        payloads = jwt.decode(cookies, secretKey, algorithms=["HS256"])

        # The above Python code is checking the HTTP request method. If the method is 'POST', it then
        # checks the value of the variable `path1`. If `path1` is equal to 'edit', it executes some
        # code (not shown in the snippet). If `path1` is equal to 'delete', it executes some other
        # code (not shown in the snippet). If `path1` is not equal to 'edit' or 'delete', it does
        # nothing.
        if request.method == "POST":
            # ubah data
            if path1 == "edit":
                # The above code is unpacking the values from the `request.form` object into the
                # variables `method`, `csrf_form`, `id_data_user_admin`, `nama`, `email`,
                # `departement`, and `jobs`. This allows you to access the form data submitted in a
                # Python web application using Flask or a similar framework.
                (
                    method,
                    csrf_form,
                    id_data_user_admin,
                    nama,
                    email,
                    departement,
                    jobs,
                ) = request.form.values()

                # The above Python code snippet is performing input validation and conditional checks
                # based on certain conditions. Here is a breakdown of what the code is doing:
                if method != "PUT":
                    return redirect(
                        url_for("kelola_admin", msg="This method form not allowed")
                    )
                if csrf_form == None or csrf_form == "":
                    return redirect(
                        url_for("kelola_admin", msg="Your request not in page")
                    )
                if id_data_user_admin == None or id_data_user_admin == "":
                    raise Exception("This data is invalid")
                if nama == None or nama == "":
                    raise ValueError("Your name cannot be empty")
                if email == None or nama == "":
                    raise ValueError("Your email cannot be empty")
                if departement == None or departement == "":
                    raise ValueError("Your departement cannot be selected")
                if jobs == None or jobs == "":
                    raise ValueError("Your jobs cannot be selected")
                if payloads["role"] != 1 and payloads["jobs"] not in ("Admin"):
                    raise Exception("Anda tidak memiliki hak akses")

                # cari departement
                departement_payloads = db.users.find_one(
                    {"_id": ObjectId(payloads["_id"])}, {"_id": 0, "departement": 1}
                )
                # jika bukan departemen superuser
                if departement_payloads["departement"] not in ("Superuser"):
                    raise Exception("Anda tidak memiliki hak akses")

                # decript id riwayat absen
                user_admin_id = cipher.decrypt(
                    uuid_like_to_string(id_data_user_admin).encode()
                ).decode()

                # cek ada / tidak
                if not user_admin_id:
                    raise ValueError("Terjadi kesalahan dalam encode decrypt")

                # update database
                result = db.users.find_one_and_update(
                    {"_id": ObjectId(user_admin_id)},
                    {
                        "$set": {
                            "nama": nama,
                            "email": email,
                            "jobs": jobs,
                            "departement": departement,
                        }
                    },
                    {"_id": 0, "nama": 1},
                )

                # lakukan pengecekan dalam perubahan data
                if not result:
                    raise ValueError("Data atas nama " + nama + " failed patch")
                return redirect(
                    url_for(
                        "kelola_admin",
                        msg="Data atas nama " + result["nama"] + " success edit",
                        result="success",
                    )
                )

            # delete data
            elif path1 == "delete":
                # jika path2 tidak diinisialisasi
                if path2 == None:
                    return redirect(url_for("notFound"))

                # cari departement
                departement_payloads = db.users.find_one(
                    {"_id": ObjectId(payloads["_id"])}, {"_id": 0, "departement": 1}
                )

                # cek role=1 dan jobs = admin
                if (
                    payloads["role"] != 1
                    and payloads["jobs"] not in ("Admin")
                    and departement_payloads["departement"] not in ("Superuser")
                ):
                    raise ("Anda tidak memiliki hak akses")

                # ambil form data
                method, csrf_form = request.form.values()

                # The code snippet provided is written in Python and it checks two conditions.
                if method != "DELETE":
                    return redirect(url_for("notFound"))
                if csrf_form == None or csrf_form == "":
                    return redirect(url_for("signIn", msg="Your request not in page"))

                # decript id user admin id
                user_admin_id_delete = cipher.decrypt(
                    uuid_like_to_string(path2).encode()
                ).decode()

                # cek ada / tidak
                if not user_admin_id_delete:
                    raise ValueError("Terjadi kesalahan dalam encode decrypt")

                # delete data
                result = db.users.find_one_and_delete(
                    {"_id": ObjectId(user_admin_id_delete)}
                )

                # lakukan pengecekan dalam perubahan data
                if not result:
                    raise Exception(
                        "Data atas nama " + result["nama"] + " failed delete"
                    )
                return redirect(
                    url_for(
                        "kelola_admin",
                        msg="Data atas nama " + result["nama"] + " success delete",
                        result="success",
                    )
                )

            # selain itu
            else:
                raise Exception("this path url doesnt exist")

        # The above code is attempting to retrieve a value from the query parameters of a request in a
        # web application. It is trying to get the value associated with the key 'msg' from the
        # request arguments.
        msg = request.args.get("msg")
        result = request.args.get("result")

        # ambil data untuk navbar
        data = db.users.find_one(
            {"_id": ObjectId(payloads["_id"])},
            {
                "_id": 0,
                "jobs": 1,
                "role": 1,
                "nama": 1,
                "photo_profile": 1,
                "departement": 1,
            },
        )
        if not data:
            raise Exception("Terjadi kesalahan data")

        # cek apakah dia bukan tipe admin
        if (
            payloads["role"] != 1
            or payloads["jobs"] not in ("Admin")
            or data["departement"] not in ("Superuser")
        ):
            return redirect(url_for("notFound"))

        # cari data admin
        data_admin_all = list(
            db.users.find(
                {
                    "jobs": {"$in": ["Admin", "Sub Admin"]},
                    "role": 1,
                    "_id": {"$ne": ObjectId(payloads["_id"])},
                },
                {"password": 0, "role": 0},
            )
        )

        # cek data admin_all
        if data_admin_all:
            for i in data_admin_all:
                i["_id"] = string_to_uuid_like(
                    cipher.encrypt(str(i["_id"]).encode()).decode()
                )
                if not i["_id"]:
                    raise Exception("Terjadi Kesalahan Data dalam encrypt")

        # render template get
        return render_template(
            "kelolaAdmin.html",
            data=data,
            data_user_admin=data_admin_all,
            msg=msg,
            result=result,
        )

    # handle error
    except jwt.ExpiredSignatureError:
        return redirect(url_for("signIn", msg="Session Expired"))
    except jwt.DecodeError:
        return redirect(url_for("signIn", msg="Anda telah logout"))
    except Fernet.InvalidToken:
        return redirect(
            url_for("kelola_admin", msg="Token update invalid please refresh your page")
        )
    except ValueError as e:
        return redirect(
            url_for("kelola_admin", msg=e.args[0] if e.args else "value error occurred")
        )
    except Exception as e:
        return redirect(
            url_for(
                "dashboard", msg=e.args[0] if e.args else "An unexpected error occurred"
            )
        )
    except IndexError as e:
        return redirect(
            url_for("kelola_admin", msg=e.args[0] if e.args else "Index error occurred")
        )


# kelola admin export
@app.route("/kelola-admin/<path1>", methods=["GET"])
@app.route("/kelola-admin/<path1>/", methods=["GET"])
def kelola_admin_export(path1):
    """
    Kelola Admin Export
    ===================

    Functionality:
    --------------
    This function handles requests to the '/kelola-admin/<path1>' route, enabling admin users to export
    data in either Excel or PDF format. It validates user permissions and checks for valid cookies and
    CSRF tokens before processing the export request.

    Parameters:
    ------------
    - path1 (str): The export format, either 'excel' or 'pdf'.

    Validations:
    ------------
    - Ensures the user has the 'admin' role.
    - Confirms the user's department is either 'Superuser' or 'Subuser'.
    - Validates the presence of a valid CSRF token and authentication cookie.

    Returns:
    --------
    - Redirects to 'notFound' if the path is not 'excel' or 'pdf'.
    - Redirects to 'signIn' with appropriate messages if validation fails.
    - Returns the generated export file if successful.

    Usage:
    ------
    >>> import requests
    >>> url = 'http://localhost:5000/kelola-admin/excel'
    >>> response = requests.get(url)
    >>> response.status_code
    200

    >>> url = 'http://localhost:5000/kelola-admin/pdf'
    >>> response = requests.get(url)
    >>> response.status_code
    200
    """
    if path1 not in ["excel", "pdf"]:
        return redirect(url_for("notFound"))
    try:
        # ambil cookie dan payload
        cookie = request.cookies.get("token_key")
        csrf_token = request.cookies.get("csrf_token")
        if csrf_token == None:
            return redirect(url_for("signIn", msg="csrf token expired"))
        if cookie == None or cookie == "":
            return redirect(url_for("signIn", msg="Anda Telah logout"))
        cookie = uuid_like_to_string(cookie)
        if not cookie:
            return redirect(url_for("signIn", msg="Cookie Expired"))
        csrf_token = uuid_like_to_string(csrf_token)
        if not csrf_token:
            return redirect(url_for("signIn", msg="CSRF Token Expired"))
        # decode payload
        payloads = jwt.decode(cookie, secretKey, algorithms=["HS256"])

        # The above Python code is checking if certain conditions are met before raising an exception
        # with the message "Anda tidak punya akses" which translates to "You do not have access" in
        # English. The conditions being checked are:
        # 1. The value of the "role" key in the payloads dictionary is not equal to 1.
        # 2. The value of the "jobs" key in the payloads dictionary is not equal to "admin".
        # 3. The value of the "departement" key in the payloads dictionary is not in the tuple
        # ("Superuser", "Subuser").

        data_user = db.users.find_one(
            {"_id": ObjectId(payloads["_id"])},
            {
                "_id": 0,
                "jobs": 1,
                "role": 1,
                "nama": 1,
                "photo_profile": 1,
                "departement": 1,
            },
        )

        if (
            payloads["role"] != 1
            and payloads["jobs"] != "admin"
            and data_user["departement"] != "Superuser"
        ):
            raise Exception("Anda tidak punya akses")

        # cek database
        result = list(
            db.users.find(
                {"jobs": {"$in": ["Admin", "Sub Admin"]}},
                {"_id": 0, "password": 0, "role": 0},
            )
        )
        if result == None or result == "" or not result:
            return redirect(url_for("kelola_admin", msg="Data user not found"))
        # save excel data
        file_path = os.path.join(app.root_path, "static", "doc")
        wb = load_workbook(file_path + "/excel/template_kelola_admin.xlsx")
        ws = wb.active
        column_widths, start, stop = convert_to_excel(
            ws, result=result, currentPage="Kelola Admin"
        )

        # Cek apakah path dapat ditulis
        if not os.access(file_path, os.W_OK):
            # Jika tidak bisa menulis ke folder static, simpan ke /tmp
            print("Tidak dapat menulis ke folder static. Menyimpan ke /tmp...")
            file_path = "/tmp"
            os.makedirs(os.path.join(file_path, "excel"), exist_ok=True)
            os.makedirs(os.path.join(file_path, "pdf"), exist_ok=True)
            file_path = os.path.join(file_path)
        # save for extractor excel
        wb.save(file_path + "/excel/data_admin_sub_admin.xlsx")
        # excel
        if path1 == "excel":
            # Save the modified workbook to BytesIO
            output = BytesIO()
            wb.save(output)
            # Mengirim file Excel sebagai response download
            output.seek(0)
            return send_file(
                output,
                mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                as_attachment=True,
                download_name="data_admin_sub_admin_winnicode.xlsx",
            )

        # pdf
        elif path1 == "pdf":
            # The above code is written in Python and seems to be using a library called "PDF" to
            # create a PDF document. It specifies the page size as A4 and then adds a new page to the
            # PDF. Finally, it calls the `create_pdf` method with parameters `start - 1`, `stop`,
            # `column_widths`, and `ws` to generate content in the PDF document.
            pdf = PDF("portrait", "mm", "A4")
            pdf.add_page()
            pdf.create_pdf(
                start - 1, stop, column_widths, ws, currentPage="Kelola Admin"
            )
            # Buat objek BytesIO
            outputs = BytesIO()
            pdf.output(file_path + "/pdf/data_admin_sub_admin.pdf")
            # Kirim file PDF sebagai attachment
            return send_file(
                file_path + "/pdf/data_admin_sub_admin.pdf",
                mimetype="application/pdf",
                as_attachment=True,
                download_name="data_admin_sub_admin_winnicode.pdf",
            )

        # jika tidak ada
        else:
            return redirect(url_for("notFound"))

    # handle error
    except jwt.ExpiredSignatureError:
        return redirect(url_for("signIn", msg="Session Expired"))
    except jwt.DecodeError:
        return redirect(url_for("signIn", msg="Anda telah logout"))
    except Exception as e:
        return redirect(url_for("dashboard", msg=e.args[0]))


# add account admin / sub admin
@app.route("/dashboard/admin/create-account", methods=["POST"])
def dashboardAdminCreateAccount():
    """
    Create new account admin / sub admin

    Parameters:
    - nama (str): nama dari akun yang akan dibuat
    - email (str): email dari akun yang akan dibuat
    - password (str): password dari akun yang akan dibuat
    - role (int): role dari akun yang akan dibuat, 1 untuk admin dan 2 untuk sub admin

    Returns:
    - redirect to dashboard with message "akun berhasil dibuat" if success
    - redirect to dashboard with message "akun gagal dibuat" if failed

    Pemakaian:
    >>> import requests
    >>> url = 'http://localhost:5000/dashboard/admin/create-account'
    >>> data = {
    ...     'nama':'admin baru',
    ...     'email':'adminbaru@example.com',
    ...     'password':'password',
    ...     'role':1
    ... }
    >>> response = requests.post(url, data=data)
    >>> response.url
    'http://localhost:5000/dashboard?msg=akun+berhasil+dibuat&result=success'
    """
    try:
        # The above Python code is checking for the presence of a CSRF token and a token key in the
        # request cookies. If the CSRF token is not found (i.e., None), it redirects the user to the
        # "signIn" route with a message indicating that the CSRF token has expired. Similarly, if the
        # token key is not found (i.e., None), it redirects the user to the "signIn" route with a
        # message indicating that the user has been logged out. This code is likely part of a web
        # application's security mechanism to ensure that valid CSRF tokens and user authentication
        # tokens are present before allowing access
        csrf_token = request.cookies.get("csrf_token")
        cookies = request.cookies.get("token_key")
        if csrf_token == None:
            return redirect(url_for("signIn", msg="csrf token expired"))
        if cookies == None:
            return redirect(url_for("signIn", msg="Anda Telah logout"))
        # The above Python code snippet is converting `cookies` and `csrf_token` variables from a
        # UUID-like format to a string format using the `uuid_like_to_string` function. It then checks
        # if the `csrf_token` or `cookies` are empty, and if so, it redirects the user to the "signIn"
        # route with a message indicating that either the CSRF token has expired or the cookie has
        # expired.
        cookies = uuid_like_to_string(cookies)
        csrf_token = uuid_like_to_string(csrf_token)
        if not csrf_token:
            return redirect(url_for("signIn", msg="CSRF Token Expired"))
        if not cookies:
            return redirect(url_for("signIn", msg="Cookie Expired"))
        # The above Python code snippet is decoding a JSON Web Token (JWT) from the `cookies` using a
        # `secretKey` with the HS256 algorithm. It then retrieves data from a MongoDB database based
        # on the decoded payload. If the role in the payload is not equal to 1 and the job is not
        # 'admin', it fetches the attendance history (`riwayat_absent`) for a specific user ID.
        # Otherwise, if the conditions are not met, it fetches the attendance history for all users.
        payload = jwt.decode(cookies, secretKey, algorithms=["HS256"])
        # cek payload
        if not payload:
            raise Exception("Invalid token")

        data_user = db.users.find_one(
            {"_id": ObjectId(payload["_id"])},
            {"_id": 0, "departement": 1, "jobs": 1, "role": 1},
        )

        # cek hak akses selama cookie
        if (
            payload["role"] != 1
            and payload["jobs"] not in ("Admin")
            and data_user["departement"] not in ("Superuser")
        ):
            raise Exception("Anda tidak memiliki akses")

        # inisiasi validasi inputan
        csrf_token, nama, email, departement, jobs, password, password2 = (
            request.form.values()
        )

        # validasi terlebih dahulu kosong atau tidak
        if csrf_token.strip() == "" or csrf_token == None:
            raise Exception("Your request not in page")
        if nama.strip() == "" or nama == None:
            raise ValueError("your name is empty, please insert in")
        if email.strip() == "" or email == None:
            raise ValueError("your email is empty, please insert in")
        if departement.strip() == "" or departement == None:
            raise ValueError("your departement is empty, please insert in")
        if jobs.strip() == "" or jobs == None:
            raise ValueError("your jobs is empty, please insert in")
        if password.strip() == "" or password == None:
            raise ValueError("your password is empty, please insert in")
        if password2.strip() == "" or password2 == None:
            raise ValueError("your confirm password is empty, please insert in")

        # jika tidak lanjut kesini
        # cek inputan password dengan konfirm password sama atau tidak
        if password.strip() != password2.strip():
            raise ValueError("your password and confirm password not same")

        # cek email apakah sudah ada di database
        if db.users.find_one({"email": email.strip(), "nama": nama.strip()}):
            raise ValueError("email or name already exist")

        # ambil callback insert user
        result = db.users.insert_one(
            {
                "nama": nama.strip(),
                "email": email.strip().lower(),
                "password": hashlib.sha256(password.strip().encode()).hexdigest(),
                "departement": departement.strip(),
                "jobs": jobs.strip(),
                "role": 1,
                "photo_profile": "img/default/user.png",
            }
        )
        # berhasi/ tidak
        if not result:
            raise ValueError("Data tidak berhasil disimpan")
        # render
        return redirect(
            url_for(
                "kelola_admin",
                msg="Data atas nama " + str(nama.strip()) + " Berhasil Disimpan",
                result="success",
            )
        )
    # handling error
    except jwt.ExpiredSignatureError:
        return redirect(url_for("signIn", msg="Session Expired"))
    except jwt.DecodeError:
        return redirect(url_for("signIn", msg="Anda telah logout"))
    except ValueError as e:
        return redirect(url_for("kelola_admin", msg=e.args[0]))
    except Exception as e:
        return redirect(url_for("dashboard", msg=e.args[0]))


# mengedit data karyawan melalui admin
@app.route("/dashboard/admin/edit", methods=["POST"])
def dashboardAdminEdit():
    """
    Mengedit data karyawan melalui admin
    ====================================

    Fungsi ini digunakan untuk mengedit data karyawan melalui admin. Data yang dapat diubah
    meliputi nama, email, departemen, pekerjaan, tanggal mulai dan akhir kerja, serta waktu
    mulai dan akhir kerja.

    Cara Penggunaan:
    ----------------
    1. Pastikan method form adalah PUT.
    2. Kirimkan data yang akan diubah melalui form dengan field:
        - nama (str): Nama karyawan yang akan diedit.
        - email (str): Email karyawan yang akan diedit.
        - departement (str): Departemen karyawan.
        - jobs (str): Pekerjaan karyawan.
        - start_date (str): Tanggal mulai kerja dalam format 'YYYY-MM-DD'.
        - end_date (str): Tanggal akhir kerja dalam format 'YYYY-MM-DD'.
        - start_time (str): Waktu mulai kerja dalam format 'HH:MM'.
        - end_time (str): Waktu akhir kerja dalam format 'HH:MM'.
    3. Pastikan csrf_token dan token_key cookies tersedia dan valid.

    Returns:
    --------
    - Jika berhasil, redirect ke dashboard dengan pesan sukses.
    - Jika gagal, redirect ke dashboard dengan pesan error.

    Example:
    --------
    >>> from flask import Flask, url_for
    >>> app = Flask(__name__)
    >>> with app.test_request_context():
    >>>     print(url_for('dashboardAdminEdit'))
    '/dashboard/admin/edit'
    """
    # apakah method put /nukan
    if request.form.get("_method") != "PUT":
        return redirect(url_for("dashboard"))

    # cek csrf token
    csrf_token = request.form.get("csrf_token")
    # cek cookie token
    cookies = request.cookies.get("token_key")

    # ambil data
    nama = request.form.get("nama")
    email = request.form.get("email")
    departement = request.form.get("departement")
    jobs = request.form.get("jobs")
    start_date = request.form.get("start_date")
    end_date = request.form.get("end_date")
    start_time = request.form.get("start_time")
    end_time = request.form.get("end_time")

    # cek kosong / tidak
    if csrf_token == "" or csrf_token == None:
        raise ValueError("csrf token expired")
    try:
        # cek string kosong atau tidak
        if (
            nama == ""
            or email == ""
            or departement == "None"
            or jobs == "None"
            or start_date == ""
            or end_date == ""
            or start_time == ""
            or end_time == ""
        ):
            return redirect(
                url_for("dashboard", msg="data tidak boleh ada yang kosong")
            )
        # decode uuid
        cookies = uuid_like_to_string(cookies)

        # cek berhasul / tidak
        if not cookies:
            raise ValueError("CSRF decode error")
        # decode jwt
        payloads = jwt.decode(cookies, secretKey, algorithms=["HS256"])

        data_user = db.users.find_one(
            {"_id": ObjectId(payloads["_id"])},
            {"_id": 0, "departement": 1, "jobs": 1, "role": 1},
        )

        if not data_user:
            raise Exception("Data user akses tidak ditemukan")

        # cek hak akses selama cookie
        if (
            payloads["role"] != 1
            and payloads["jobs"] not in ("Admin")
            and data_user["departement"] not in ("Superuser")
        ):
            raise Exception("Anda tidak memiliki akses")

        # lakukan update
        result = db.users.update_one(
            {"email": email, "nama": nama},
            {
                "$set": {
                    "departement": departement,
                    "mulai_kerja": datetime.datetime.strptime(start_date, "%Y-%m-%d")
                    .strftime("%d %B %Y")
                    .lower(),
                    "akhir_kerja": datetime.datetime.strptime(end_date, "%Y-%m-%d")
                    .strftime("%d %B %Y")
                    .lower(),
                    "waktu_awal_kerja": datetime.datetime.strptime(start_time, "%H:%M")
                    .strftime("%H.%M")
                    .lower(),
                    "waktu_akhir_kerja": datetime.datetime.strptime(end_time, "%H:%M")
                    .strftime("%H.%M")
                    .lower(),
                    "jobs": jobs,
                    "work_hours": (
                        datetime.datetime.strptime(end_time, "%H:%M")
                        - datetime.datetime.strptime(start_time, "%H:%M")
                    ).seconds
                    // 3600,
                }
            },
        )
        # berhasil atau tidak dalam melakukan update user
        if result.matched_count > 0:
            return redirect(
                url_for(
                    "dashboard",
                    msg="data karyawan / magang berhasil di edit",
                    result="success",
                )
            )
        return redirect(
            url_for("dashboard", msg="data karyawan / magang gagal di edit")
        )
    # handle error
    except jwt.ExpiredSignatureError:
        return redirect(url_for("signIn", msg="Session Expired"))
    except jwt.DecodeError:
        return redirect(url_for("signIn", msg="Anda telah logout"))
    except ValueError as e:
        return redirect(url_for("signIn", msg=e.args[0]))
    except Exception as e:
        return redirect(url_for("kelola_admin", msg=e.args[0]))


# delete user karyawan / magang melalui admin
@app.route("/dashboard/admin/delete/<id>", methods=["POST"])
def adminDelete(id):
    """
    Delete user karyawan / magang melalui admin

    Parameters:
    id (str): id user yang akan dihapus

    Returns:
    redirect to dashboard with message "data karyawan / magang berhasil di hapus" if success
    redirect to dashboard with message "data karyawan / magang gagal di hapus" if failed

    Pemakaian:
    >>> import requests
    >>> url = 'http://localhost:5000/dashboard/admin/delete/62d8a6d5f2f7f7a3f80f8f8b'
    >>> response = requests.post(url, data={'_method':'DELETE'})
    >>> response.url
    'http://localhost:5000/dashboard?msg=data+karyawan+%2F+magang+berhasil+di+hapus&result=success'
    """
    # The above code is checking if the value of the "_method" key in the request form is not equal to
    # "DELETE". If the condition is true, the code inside the if block will be executed.
    if request.form.get("_method") != "DELETE":
        return redirect(url_for("dashboard"))
    # cek cookie token
    cookies = request.cookies.get("token_key")
    try:
        # The above Python code is checking if the value of the "csrf_token" parameter in the form
        # data is an empty string or None. If the value is empty or None, it raises a ValueError with
        # the message "csrf token expired". This is a common security measure to ensure that a valid
        # CSRF token is present in the form data to prevent CSRF attacks.
        if (
            request.form.get("csrf_token") == ""
            or request.form.get("csrf_token") == None
        ):
            raise ValueError("csrf token expired")
        # decode uuid
        cookies = uuid_like_to_string(cookies)

        # The code is checking if the variable `cookies` is falsy. If `cookies` is falsy, the
        # condition will evaluate to `True`, otherwise it will evaluate to `False`.
        if not cookies:
            raise ValueError("decode error")

        # The above code is using the `jwt.decode` function to decode a JSON Web Token (JWT) stored in
        # the `cookies` variable using the specified `secretKey` and algorithm "HS256". This function
        # will verify the signature of the JWT and return the decoded payload if the signature is
        # valid.
        payloads = jwt.decode(cookies, secretKey, algorithms=["HS256"])

        data_user = db.users.find_one(
            {"_id": ObjectId(payloads["_id"])},
            {"_id": 0, "departement": 1, "jobs": 1, "role": 1},
        )
        if not data_user:
            raise Exception("Data anda tidak ditemukan")

        # cek hak akses selama cookie
        if (
            payloads["role"] != 1
            and payloads["jobs"] not in ("Admin")
            and data_user["departement"] in ("Superuser")
        ):
            raise Exception("Anda tidak memiliki akses")

        # The above code is written in Python and it is performing two operations using MongoDB
        # database:
        result1 = db.users.delete_one({"_id": ObjectId(id)})
        result2 = db.absen_magang.delete_many({"user_id": ObjectId(id)})

        # The above Python code is checking if the `deleted_count` attribute of `result1` is greater
        # than 0 and the `deleted_count` attribute of `result2` is greater than or equal to 0. If both
        # conditions are met, it will redirect the user to the "dashboard" route with a success
        # message indicating that employee/intern data has been successfully deleted.
        if result1.deleted_count > 0 and result2.deleted_count >= 0:
            return redirect(
                url_for(
                    "dashboard",
                    msg="data karyawan / magang berhasil di hapus",
                    result="success",
                )
            )

        # The above code is a Python code snippet that is using the Flask framework. It is performing
        # a redirect to the "dashboard" route with a message parameter "msg" set to "data karyawan /
        # magang gagal di hapus". This means that it is redirecting the user to the dashboard route
        # with a message indicating that the deletion of employee/intern data has failed.
        return redirect(
            url_for("dashboard", msg="data karyawan / magang gagal di hapus")
        )
    # The above code is handling different exceptions that may occur in a Python application.
    except jwt.DecodeError:
        return redirect(url_for("signIn", msg="Anda telah logout"))
    except jwt.ExpiredSignatureError:
        return redirect(url_for("signIn", msg="Session Expired"))
    except ValueError as e:
        return redirect(url_for("signIn", msg=e.args[0]))


@app.route("/dashboard/admin/<path>", methods=["GET"])
def export(path):
    """
    export(path)

    Parameter:
    - path: path yang akan di export

    Fungsi:
    - Fungsi ini digunakan untuk mengexport data dalam bentuk excel atau pdf.
    - Fungsi ini hanya dapat diakses oleh admin.

    Contoh pemakaian:
    - /dashboard/admin/excel
    - /dashboard/admin/pdf
    """
    if path not in ["excel", "pdf"]:
        return redirect(url_for("notFound"))
    try:
        # ambil cookie dan payload
        cookie = request.cookies.get("token_key")
        csrf_token = request.cookies.get("csrf_token")
        if csrf_token == None:
            return redirect(url_for("signIn", msg="csrf token expired"))
        if cookie == None or cookie == "":
            return redirect(url_for("signIn", msg="Anda Telah logout"))
        cookie = uuid_like_to_string(cookie)
        if not cookie:
            return redirect(url_for("signIn", msg="Cookie Expired"))
        csrf_token = uuid_like_to_string(csrf_token)
        if not csrf_token:
            return redirect(url_for("signIn", msg="CSRF Token Expired"))
        # decode payload
        payloads = jwt.decode(cookie, secretKey, algorithms=["HS256"])

        # The above Python code is checking if certain conditions are met before raising an exception
        # with the message "Anda tidak punya akses" which translates to "You do not have access" in
        # English. The conditions being checked are:
        # 1. The value of the "role" key in the payloads dictionary is not equal to 1.
        # 2. The value of the "jobs" key in the payloads dictionary is not equal to "admin".
        # 3. The value of the "departement" key in the payloads dictionary is not in the tuple
        # ("Superuser", "Subuser").
        if (
            payloads["role"] != 1
            and payloads["jobs"] != "admin"
            and payloads["departement"] not in ("Superuser", "Sub user")
        ):
            raise Exception("Anda tidak punya akses")
        # cek database
        result = list(
            db.users.find(
                {"jobs": {"$in": ["Karyawan", "Magang"]}},
                {"_id": 0, "password": 0, "role": 0, "work_hours": 0},
            )
        )
        if result == None or result == "" or not result:
            raise Exception("Data user not found")
        # save excel data
        file_path = os.path.join(app.root_path, "static", "doc")
        wb = load_workbook(file_path + "/excel/template_data_karyawan.xlsx")
        ws = wb.active
        column_widths, start, stop = convert_to_excel(ws, result=result)

        # Cek apakah path dapat ditulis
        if not os.access(file_path, os.W_OK):
            # Jika tidak bisa menulis ke folder static, simpan ke /tmp
            file_path = "/tmp"
            os.makedirs(os.path.join(file_path, "excel"), exist_ok=True)
            os.makedirs(os.path.join(file_path, "pdf"), exist_ok=True)
            file_path = os.path.join(file_path)
            print("Tidak dapat menulis ke folder static. Menyimpan ke /tmp...")

        # save for extractor excel
        wb.save(file_path + "/excel/data_karyawan.xlsx")
        # excel
        if path == "excel":
            # Save the modified workbook to BytesIO
            output = BytesIO()
            wb.save(output)
            # Mengirim file Excel sebagai response download
            output.seek(0)
            return send_file(
                output,
                mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                as_attachment=True,
                download_name="data_karyawan_winnicode.xlsx",
            )
        # pdf
        elif path == "pdf":
            # The above code is written in Python and seems to be using a library called "PDF" to
            # create a PDF document. It specifies the page size as A4 and then adds a new page to the
            # PDF. Finally, it calls the `create_pdf` method with parameters `start - 1`, `stop`,
            # `column_widths`, and `ws` to generate content in the PDF document.
            pdf = PDF("L", "mm", "A4")
            pdf.add_page()
            pdf.create_pdf(start - 1, stop, column_widths, ws)
            # Buat objek BytesIO
            output = BytesIO()
            pdf.output(file_path + "/pdf/data_karyawan.pdf")
            # Kirim file PDF sebagai attachment
            return send_file(
                file_path + "/pdf/data_karyawan.pdf",
                mimetype="application/pdf",
                as_attachment=True,
                download_name="data_karyawan_winnicode.pdf",
            )
        else:
            return redirect(url_for("notFound"))
    # The above code is handling exceptions related to JWT (JSON Web Token) authentication. It catches
    # different types of exceptions that can occur during JWT verification:
    except jwt.ExpiredSignatureError:
        return redirect(url_for("signIn", msg="Session Expired"))
    except jwt.DecodeError:
        return redirect(url_for("signIn", msg="Anda telah logout"))
    except Exception as e:
        return redirect(url_for("dashboard", msg=e.args[0]))


# task page
@app.route("/task", methods=["GET"])
def task():

    # The above Python code snippet is checking for the presence and validity of a CSRF token and a
    # cookie in a web request. Here is a breakdown of the code:
    cookie = request.cookies.get("token_key")
    csrf_token = request.cookies.get("csrf_token")
    if csrf_token == None:
        return redirect(url_for("signIn", msg="csrf token expired"))
    if cookie == None:
        return redirect(url_for("signIn", msg="Anda Telah logout"))

    # decode uuid
    cookie = uuid_like_to_string(cookie)
    csrf_token = uuid_like_to_string(csrf_token)
    if not csrf_token:
        return redirect(url_for("signIn", msg="CSRF Token Expired"))
    if not cookie:
        return redirect(url_for("signIn", msg="Cookie Expired"))

    # check status dan msg
    result = request.args.get("status")
    msg = request.args.get("msg")

    try:
        path1 = request.args.get("path1")
        table_heading = []
        data_user_all = []

        # decode payload
        payload = jwt.decode(cookie, secretKey, algorithms=["HS256"])
        # ambil data dari db
        data = db.users.find_one(
            {
                "_id": ObjectId(payload["_id"]),
                "jobs": payload["jobs"],
                "role": payload["role"],
            }
        )
        # jika data kosong
        if not data:
            return redirect(url_for("signIn", msg="Anda bukan bagian dari WinniCode"))

        # admin /sub admin
        if payload["role"] == 1 and payload["jobs"] in ("Admin", "Sub Admin"):
            # user selain payload
            data_user_for_add = list(
                db.users.find(
                    {
                        "_id": {"$ne": ObjectId(payload["_id"])},
                        "role": {"$ne": 1},
                    },  # bukan id payload dan rolwnya bukan angka 1
                    {
                        "_id": 0,
                        "nama": 1,
                        "email": 1,
                        "jobs": 1,
                        "departement": 1,
                    },  # ambil nama , email, jobs dan depratement
                )
            )

            # ambil data ynag ditampilkan
            # path1 kosong
            if not path1:
                data_user_all = list(
                    db.users.aggregate(
                        [
                            {"$match": {"jobs": {"$nin": ["Admin", "Sub Admin"]}}},
                            {
                                "$group": {
                                    "_id": "$jobs",
                                    "document": {"$first": "$$ROOT"},
                                }
                            },
                            {"$replaceRoot": {"newRoot": "$document"}},
                            {"$project": {"_id": 1, "jobs": 1}},
                        ]
                    )
                )
            # path 1 karyawan / magang
            elif path1 in ("Karyawan", "Magang"):
                data_user_all = list(
                    db.users.find(
                        {"jobs": path1},
                        {"_id": 1, "nama": 1, "email": 1, "departement": 1},
                    )
                )

            # selain itu
            else:
                data_user_all = list(
                    db.tasks.find(
                        {"user_id": ObjectId(uuid_like_to_string(str(path1)))},
                        {"user_id": 0},
                    )
                )

        # karyawan / magang
        elif payload["role"] == 3 and payload["jobs"] in ("Karyawan", "Magang"):
            data_user_all = list(
                db.tasks.find(
                    {"user_id": ObjectId(payload["_id"])},
                    {"accepted": 0, "user_id": 0},
                )
            )

        # iterasiins
        for user in data_user_all:
            user["_id"] = string_to_uuid_like(str(user["_id"]))
            table_heading = [x for x in user.keys() if x != "_id"]
            if payload["role"] == 3 and payload["jobs"] in ("Karyawan", "Magang"):
                if get_time_zone_now() >= user["deadline"]:
                    user["dataSort"] = "true"

        # tampilkan
        return render_template(
            "task.html",
            data=data,
            enumerate=enumerate,
            list=list,
            type=type,
            datetime=datetime.datetime,
            path1=path1,
            data_user_all=data_user_all,
            table_heading=table_heading,
            result=result,
            data_user_for_add=data_user_for_add if payload["role"] == 1 else [],
            msg=msg,
        )
    # The above code is handling exceptions related to JWT (JSON Web Token) in a Python application.
    # Specifically, it is catching `jwt.ExpiredSignatureError` and `jwt.DecodeError` exceptions. If
    # either of these exceptions is raised, the code redirects the user to the "signIn" route with a
    # message indicating either "Session Expired" or "Anda telah logout" (depending on the specific
    # exception caught). This is likely part of a mechanism to handle expired or invalid JWT tokens
    # during user authentication or authorization processes.
    except jwt.ExpiredSignatureError:
        return redirect(url_for("signIn", msg="Session Expired"))
    except jwt.DecodeError:
        return redirect(url_for("signIn", msg="Anda telah logout"))
    except Exception as e:
        return redirect(
            url_for(
                "dashboard", msg=e.args[0] if e.args else "An unexpected error occurred"
            )
        )


@app.route("/task/<path>", methods=["POST"])
def task_post_admin(path):
    try:
        # The above Python code snippet is checking for the presence and validity of a CSRF token and a
        # cookie in a web request. Here is a breakdown of the code:
        cookie = request.cookies.get("token_key")
        csrf_token = request.cookies.get("csrf_token")
        if csrf_token == None:
            return redirect(url_for("signIn", msg="csrf token expired"))
        if cookie == None:
            return redirect(url_for("signIn", msg="Anda Telah logout"))

        # decode uuid
        cookie = uuid_like_to_string(cookie)
        csrf_token = uuid_like_to_string(csrf_token)
        if not csrf_token:
            return redirect(url_for("signIn", msg="CSRF Token Expired"))
        if not cookie:
            return redirect(url_for("signIn", msg="Cookie Expired"))

        # decode payload
        payload = jwt.decode(cookie, secretKey, algorithms=["HS256"])

        if payload["role"] != 1 and payload["jobs"] not in ("Admin", "Sub Admin"):
            raise Exception("Anda tidak memiliki hak akses")

        # ambil data dari db
        data = db.users.find_one(
            {
                "_id": ObjectId(payload["_id"]),
                "jobs": payload["jobs"],
                "role": payload["role"],
            }
        )

        if not data:
            raise Exception("Anda tidak memiliki hak akses")

        if path == "add":
            # ambil datajsonnnya
            data_json = request.json

            # cek datajosn yang bintang
            for key, value in data_json.items():
                if key != "link_input" and not data_json[key]:
                    raise Exception("form {} wajib diisi".format(key))

            # ambil result id yang bukan role 1 sesuai dengan email json
            result = db.users.find_one(
                {
                    "email": data_json["send_to_user"],
                    "role": {"$ne": 1},
                    "jobs": data_json["jobs"],
                    "departement": data_json["departement"],
                },
                {"_id": 1},
            )

            # result didapatakan?
            if not result:
                print("Terjadi kesalahan dalam pengambilan user di database")
                raise Exception("Terjadi kesalahan pada database")

            data_json["deadline"] = datetime.datetime.strptime(
                data_json["deadline"], "%Y-%m-%dT%H:%M"
            )

            # melakukan penambahan
            result = db.tasks.insert_one(
                {
                    key: value
                    for key, value in data_json.items()
                    if key not in ("send_to_user", "jobs", "departement")
                }
                | {
                    "user_id": result["_id"],
                    "accepted": False,
                    "status_task": "Pending",
                }
            )

            # cek berhasil ditambah?
            if not result:
                print("terjadi kesalahan data dalam penambahan data ditabel task")
                raise Exception("Terjadi kesalahan pada database")

            task_id_new = result.inserted_id

            # kirim ke class task gmail notif
            TaskGmailNotif(task_id_new, path)

            # buat response
            response = make_response(
                jsonify(
                    {
                        "redirect": url_for(
                            "task", status="success", msg="Task Berhasil dibuat"
                        )
                    }
                ),
                200,
            )

            # tambahkan headers
            response.headers["CSRF_TOKEN"] = csrf_token
            response.headers["Content-Type"] = "Application/json"
            return response

        # edit
        elif path == "edit":
            # ambil data json
            rowId, inputId, newValue = request.json.values()

            # cek nilai json tak kosong
            if not rowId and not inputId and not newValue:
                raise Exception("form wajib diisi")

            # decode row id
            rowId = uuid_like_to_string(str(rowId))
            if not rowId:
                raise Exception("Decode Error")

            # new value bila str True and False
            if newValue in ("True", "False"):
                newValue = True if newValue == "True" else False

            if is_valid_datetime_format(newValue):
                newValue = datetime.datetime.strptime(newValue, "%Y-%m-%dT%H:%M")

            # edit database berdasarkan id
            result = db.tasks.find_one_and_update(
                {"_id": ObjectId(rowId)}, {"$set": {inputId: newValue}}
            )

            # cek result
            if not result:
                raise Exception("Terjadi kesalahan pada database")

            # ambil task id
            task_id_new = result["_id"]

            # kirim ke class task gmail notif
            TaskGmailNotif(task_id_new, path, newValue=newValue)

            # buat response
            return make_response(
                jsonify({"redirect": url_for("task", msg="Task Berhasil diubah")}), 200
            )

        elif path == "delete":
            # ambil data json
            rowId = request.json.get("id")
            rowId = uuid_like_to_string(str(rowId))

            # cek nilai json tak kosong
            if not rowId:
                raise Exception("form wajib diisi")

            # edit database berdasarkan id
            result = db.tasks.delete_one({"_id": ObjectId(rowId)})

            # cek result
            if not result:
                raise Exception("Terjadi kesalahan pada database")

            # buat response
            return make_response(
                jsonify({"redirect": True}),
                200,
            )

        else:
            raise Exception("Path doesn`t exists")
    # The above code is handling exceptions related to JWT (JSON Web Token) in a Python application.
    # Specifically, it is catching `jwt.ExpiredSignatureError` and `jwt.DecodeError` exceptions. If
    # either of these exceptions is raised, the code redirects the user to the "signIn" route with a
    # message indicating either "Session Expired" or "Anda telah logout" (depending on the specific
    # exception caught). This is likely part of a mechanism to handle expired or invalid JWT tokens
    # during user authentication or authorization processes.
    except jwt.ExpiredSignatureError:
        return make_response(
            jsonify({"redirect": url_for("signIn", msg="Session Expired")}), 500
        )
    except jwt.DecodeError:
        return make_response(
            jsonify({"redirect": url_for("signIn", msg="Anda telah logout")}), 500
        )
    except Exception as e:
        # jikakosong
        if not e.args:
            return make_response(
                jsonify(
                    {
                        "redirect": url_for(
                            "dashboard", msg="An unexpected error occurred"
                        )
                    }
                ),
                500,
            )
        return make_response(jsonify({"redirect": url_for("task", msg=e.args[0])}), 500)


@app.route("/task/user/<path>", methods=["POST"])
def task_post_user(path):
    try:
        # The above Python code snippet is checking for the presence and validity of a CSRF token and a
        # cookie in a web request. Here is a breakdown of the code:
        cookie = request.cookies.get("token_key")
        csrf_token = request.cookies.get("csrf_token")
        if csrf_token == None:
            return redirect(url_for("signIn", msg="csrf token expired"))
        if cookie == None:
            return redirect(url_for("signIn", msg="Anda Telah logout"))

        # decode uuid
        cookie = uuid_like_to_string(cookie)
        csrf_token = uuid_like_to_string(csrf_token)
        if not csrf_token:
            return redirect(url_for("signIn", msg="CSRF Token Expired"))
        if not cookie:
            return redirect(url_for("signIn", msg="Cookie Expired"))

        # decode payload
        payload = jwt.decode(cookie, secretKey, algorithms=["HS256"])

        if payload["role"] == 1 and payload["jobs"] not in ("Karyawan", "Magang"):
            raise Exception("Anda tidak memiliki hak akses")

        data = db.users.find_one(
            {
                "_id": ObjectId(payload["_id"]),
                "jobs": payload["jobs"],
                "role": payload["role"],
            }
        )

        if not data:
            raise Exception("Anda tidak memiliki hak akses")

        if path == "edit":
            # The above Python code is checking if the `X-CSRFToken` and `Content-Type` headers are
            # present in the request headers. If either of these headers is missing (`csrf_token` or
            # `contents` is `None`), the code will execute the block inside the `if` statement.
            csrf_token = request.headers.get("X-CSRFToken")
            contents = request.headers.get("Content-Type")
            if not csrf_token or not contents:
                raise Exception("anda melakukan ajax diluar")

            # The code snippet is written in Python and it is extracting the values of `task_id` and
            # `status_task_new` from a JSON request. It then checks if either `task_id` or
            # `status_task_new` is empty (evaluates to False).
            task_id, status_task_new = request.json.values()
            if not task_id or not status_task_new:
                raise Exception("Ada kesalahan dalam meload data task")

            # The code snippet is attempting to convert a UUID-like object to a string representation
            # using the `uuid_like_to_string` function. If the conversion is successful (i.e., the
            # resulting string is not empty), the code proceeds with the next steps.
            task_id_conv = uuid_like_to_string(str(task_id))
            if not task_id_conv:
                raise Exception("Terjadi kesalahan dalam mengonvert data task")

            # The above Python code is querying a MongoDB database to find a specific task document
            # based on the user ID and task ID provided. It retrieves the '_id' and 'status_task'
            # fields of the found document. If no document is found (status_task_old is None), it
            # prints an error message indicating that there was an issue retrieving the status of the
            # old task from the database.
            status_task_old = db.tasks.find_one(
                {"user_id": data["_id"], "_id": ObjectId(task_id_conv)},
                {"_id": 1, "status_task": 1},
            )
            if not status_task_old:
                print("Terjadi kesalahan dalam pengambil status task old di db")
                raise Exception("Terjadi kesalahan di db")

            # The code is checking if the value of the 'status_task' key in the dictionary
            # `status_task_old` is equal to the value of the variable `status_task_new`. If they are
            # equal, the condition will be true.
            if status_task_old["status_task"] == status_task_new:
                raise Exception("Tidak ada perubahan status task")

            # The above code is updating a document in a MongoDB collection called "tasks". It is
            # finding a document with a specific "_id" and "user_id" that matches the provided values,
            # and then updating the "status_task" field with a new value specified by
            # "status_task_new". If the update is successful, the result will contain information
            # about the update operation.
            result = db.tasks.update_one(
                {"_id": ObjectId(task_id_conv), "user_id": data["_id"]},
                {"$set": {"status_task": status_task_new}},
            )
            if not result:
                raise Exception("Terjadi kesalahan dalam update db")

            # The above code is creating a response with a JSON object that includes a redirect URL
            # for a specific task with a success status message. The response is returned with a
            # status code of 200 (OK).
            return make_response(
                jsonify(
                    {
                        "redirect": url_for(
                            "task", status="success", msg="status berhasil di update"
                        )
                    }
                ),
                200,
            )

    # The above code is handling exceptions related to JWT (JSON Web Token) in a Python application.
    # Specifically, it is catching `jwt.ExpiredSignatureError` and `jwt.DecodeError` exceptions. If
    # either of these exceptions is raised, the code redirects the user to the "signIn" route with a
    # message indicating either "Session Expired" or "Anda telah logout" (depending on the specific
    # exception caught). This is likely part of a mechanism to handle expired or invalid JWT tokens
    # during user authentication or authorization processes.
    except jwt.ExpiredSignatureError:
        return make_response(
            jsonify({"redirect": url_for("signIn", msg="Session Expired")}), 500
        )
    except jwt.DecodeError:
        return make_response(
            jsonify({"redirect": url_for("signIn", msg="Anda telah logout")}), 500
        )
    except Exception as e:
        # jikakosong
        if not e.args:
            return make_response(
                jsonify(
                    {
                        "redirect": url_for(
                            "dashboard", msg="An unexpected error occurred"
                        )
                    }
                ),
                500,
            )
        return make_response(jsonify({"redirect": url_for("task", msg=e.args[0])}), 500)


# melakukan error handler csrf
@app.errorhandler(400)
def handle_csrf_error(e):
    """This function is used to handle 400 Bad Request error which is usually caused by CSRF token validation failure.

    Args:
        e (Exception): The exception object that contains the error message.

    Returns:
        Response: A JSON response containing the error message.
    """
    return jsonify({"error": e}), 400


@app.route("/404")
@app.errorhandler(404)
def notFound(error=None):
    """
    This function is used to handle 404 Not Found error. It is usually caused by a request to a URL that does not exist on the server.

    Args:
        error (Exception): The exception object that contains the error message.

    Returns:
        Response: A rendered HTML template with a 404 error message.
    """
    print("error", error)
    data = {"next": "/", "previous": "javascript:history.back()"}
    return render_template("notFound.html", data=data), 404


# stating app
if __name__ == "__main__":
    # # Menjadwalkan pengecekan absensi setiap menit
    delete_absen = BackgroundScheduler()
    delete_absen.add_job(
        func=unhadir_absensi, trigger="interval", minutes=1
    )  # interval hours/minute/second. date run_date .cron day_of_week,hours,minutes
    delete_absen.start()
    app.run(port=8080, debug=True)  # ssl_context =  adhoc adalah sertifikat self signed
    # DEBUG is SET to TRUE. CHANGE FOR PROD
