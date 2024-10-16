from absensiMethod import (cek_tanggal_kerja, format_date, format_time, signInPayload,
    string_to_uuid_like, unhadir_absensi, uuid_like_to_string)
from convert import (
    convert_to_excel,
    PDF
)
from flask import (
    Flask,
    redirect,
    url_for,
    render_template,
    request,
    jsonify,
    send_file,
    make_response
)
from flask_wtf.csrf import CSRFProtect
from pymongo.mongo_client import MongoClient
from dotenv import load_dotenv
import os, hashlib, jwt, datetime
from bson import ObjectId
from apscheduler.schedulers.background import BackgroundScheduler
from urllib.parse import urlparse
from io import BytesIO
from openpyxl import load_workbook
from werkzeug.utils import secure_filename
from werkzeug.datastructures import FileStorage
from generate_otp import OtpPasswordGenerator

# buat request post sesuai datetime

# loading environment variables from.env file
load_dotenv()
url = os.getenv("MONGODB_URL")
secretKey = os.getenv("SECRET_KEY")

# connecting to mongodb
client = MongoClient(url)
db = client["absen"]

# inisiasi app
app = Flask(__name__)
# melakukan config
app.config["SECRET_KEY"] = secretKey
# buat csrfprotect
csrf = CSRFProtect(app)

# Tentukan folder untuk menyimpan gambar
UPLOAD_FOLDER = os.path.join(app.root_path, "static/img/user")
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

    # return redirect(url_for('dashboard'))
    return render_template("home.html")


@app.route("/data_karyawan/admin", methods=["GET"])
def data_karyawan():
    cookie = request.cookies.get("token_key")
    request.cookies.get("csrf_token")

    payload = jwt.decode(cookie, secretKey, algorithms=["HS256"])
    data = db.users.find_one(
        {
            "_id": ObjectId(payload["_id"]),
            "jobs": payload["jobs"],
            "role": payload["role"],
        }
    )
    if data["role"] == 1:
        if data["jobs"] == "Admin":
            return render_template("data_karyawan.html", data=data)


# dasboard magang get
@app.route("/dashboard/magang", methods=["GET"])
def dashboard():
    result = request.args.get("result")
    msg = request.args.get("msg")
    cookie = request.cookies.get("token_key")
    csrf_token = request.cookies.get("csrf_token")

    try:
        payload = jwt.decode(cookie, secretKey, algorithms=["HS256"])
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
            data["tanggal_sekarang"] = (
                datetime.datetime.now().strftime("%d %B %Y").lower()
            )

            table_hadir = db.absen_magang.find_one(
                {
                    "user_id": ObjectId(payload["_id"]),
                    "tanggal_hadir": data["tanggal_sekarang"],
                }
            )

            # cek tanggal pelaksanan kerja
            waktu_sekarang = datetime.datetime.now().time()
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
                # waktu hadir
                waktu_hadir = datetime.datetime.strptime(
                    table_hadir["waktu_hadir"].replace(".", ":"), "%H:%M"
                ).time()
                data["heading-card"] = (
                    data["absen"]["hadir"] + data["absen"]["tidak_hadir"]
                )
                if (
                    table_hadir["status_hadir"] == "1"
                    and waktu_hadir <= waktu_akhir_kerja
                ):
                    data["class-button-hadir"] = "btn-success disabled opacity-100"
                    data["text-button"] = "Hadir"
                elif (
                    table_hadir["status_hadir"] == "1"
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
                    "titleCard": "Tidak Hadir",
                    "textColor": "text-danger",
                    "angkaCard": data["absen"]["tidak_hadir"],
                    "icon": "fa-regular fa-circle-xmark fa-2x text-danger text-opacity-25",
                    "borderLeft": "border-left-danger",
                },
            ]
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
            if data["jobs"] == "Admin" or data["jobs"] == "Manager":
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
                start_index = skip + 1
                end_index = min(skip + table_length, count_data_karyawan_magang)

                # tambah data indeks
                data["total_page"] = (
                    count_data_karyawan_magang + table_length - 1
                ) // table_length
                data["first_table"] = first_table  # table awal
                data["table_length"] = table_length  # table akhir
                data["count_data_karyawan_magang"] = count_data_karyawan_magang

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
                    if len(data_karyawan_magang_new) <= 0:
                        return redirect(
                            url_for("dashboard", msg="Data tidak ditemukan")
                        )
                    data_karyawan_magang = data_karyawan_magang_new
                    end_index = len(data_karyawan_magang)

                data["showing_table_karyawan"] = (
                    f"Showing {start_index} to {end_index} of {count_data_karyawan_magang} entries"
                )

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

    except jwt.ExpiredSignatureError:
        return redirect(url_for("signIn", msg="Session Expired"))
    except jwt.DecodeError:
        return redirect(url_for("signIn", msg="Anda telah logout"))


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
    now = datetime.datetime.now()
    time_now = now.time()
    try:
        csrf_token = request.headers.get("X-CSRF-Token")
        if csrf_token == "" and csrf_token == None:
            raise Exception("csrf token expired")
        userId = request.form.get("user_id")
        status_hadir = request.form.get("status_hadir")
        riwayat_absen = db.absen_magang.find_one(
            {"user_id": ObjectId(userId)}, sort={"_id": -1}
        )  # cek riwayat absen

        if (
            now.date()
            <= datetime.datetime.strptime(
                riwayat_absen["tanggal_hadir"], "%d %B %Y"
            ).date()
            and time_now
            >= datetime.datetime.strptime(riwayat_absen["waktu_hadir"], "%H.%M").time()
        ):
            return jsonify(
                {
                    "result": "unsuccess",
                    "redirect": "/dashboard/magang",
                    "msg": "Anda sudah absen pada tanggal "
                    + riwayat_absen["tanggal_hadir"],
                }
            )

        # jika hadir
        if status_hadir == "1":
            db.users.find_one_and_update(
                {"_id": ObjectId(userId)},
                {
                    "$set": {
                        "absen.hadir": db.users.find_one({"_id": ObjectId(userId)})[
                            "absen"
                        ]["hadir"]
                        + 1
                    }
                },
            )
            db.absen_magang.insert_one(
                {
                    "user_id": ObjectId(userId),
                    "status_hadir": status_hadir,
                    "waktu_hadir": datetime.datetime.now().strftime("%H.%M").lower(),
                    "tanggal_hadir": datetime.datetime.now()
                    .strftime("%d %B %Y")
                    .lower(),
                }
            )

            return jsonify({"result": "success", "redirect": "/dashboard/magang"})
        # jika tidak hadir
        else:
            db.users.update_one(
                {"_id": ObjectId(userId)},
                {
                    "$set": {
                        "absen.tidak_hadir": db.users.find_one(
                            {"_id": ObjectId(userId)}
                        )["absen"]["tidak_hadir"]
                        + 1
                    }
                },
            )
            db.absen_magang.insert_one(
                {
                    "user_id": ObjectId(userId),
                    "status_hadir": status_hadir,
                    "waktu_hadir": datetime.datetime.now().strftime("%H.%M").lower(),
                    "tanggal_hadir": datetime.datetime.now()
                    .strftime("%d %B %Y")
                    .lower(),
                }
            )
            return jsonify({"result": "unsuccess", "redirect": "/dashboard/magang"})
    except Exception as e:
        return jsonify(
            {"result": "Gagal", "redirect": "/dashboard/magang", "msg": str(e)}
        )


# cek data waktu harus lebih atau kurang?kalo ga ga jalan samsek
# gituin args get dari url ini berbahaya
# riwayat absen masih none tidak nampilin waktu riwayat


# mengedit data karyawan melalui admin
@app.route("/dashboard/admin/edit", methods=["POST"])
def dashboardAdminEdit():
    if request.form.get("_method") != "PUT":
        return redirect(url_for("dashboard"))

    csrf_token = request.form.get("csrf_token")

    if csrf_token == "" or csrf_token == None:
        raise ValueError("csrf token expired")
    try:
        jwt.decode(request.cookies.get("token_key"), secretKey, algorithms=["HS256"])
        nama = request.form.get("nama")
        email = request.form.get("email")
        departement = request.form.get("departement")
        jobs = request.form.get("jobs")
        start_date = request.form.get("start_date")
        end_date = request.form.get("end_date")
        start_time = request.form.get("start_time")
        end_time = request.form.get("end_time")

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
    except ValueError as e:
        return redirect(url_for("signIn", msg=e.args[0]))
    except jwt.ExpiredSignatureError:
        return redirect(url_for("signIn", msg="Session Expired"))
    except jwt.DecodeError:
        return redirect(url_for("signIn", msg="Anda telah logout"))


# delete user karyawan / magang melalui admin
@app.route("/dashboard/admin/delete/<id>", methods=["POST"])
def adminDelete(id):
    if request.form.get("_method") != "DELETE":
        return redirect(url_for("dashboard"))
    if request.form.get("csrf_token") == "" or request.form.get("csrf_token") == None:
        raise ValueError("csrf token expired")
    try:
        jwt.decode(request.cookies.get("token_key"), secretKey, algorithms=["HS256"])
        result1 = db.users.delete_one({"_id": ObjectId(id)})
        result2 = db.absen_magang.delete_many({"user_id": ObjectId(id)})
        print(result1.deleted_count, result2.deleted_count)
        if result1.deleted_count > 0 and result2.deleted_count >= 0:
            return redirect(
                url_for(
                    "dashboard",
                    msg="data karyawan / magang berhasil di hapus",
                    result="success",
                )
            )
        return redirect(
            url_for("dashboard", msg="data karyawan / magang gagal di hapus")
        )
    except ValueError as e:
        return redirect(url_for("signIn", msg=e.args[0]))
    except jwt.ExpiredSignatureError:
        return redirect(url_for("signIn", msg="Session Expired"))
    except jwt.DecodeError:
        return redirect(url_for("signIn", msg="Anda telah logout"))


# lakukan sign-in
@app.route("/sign-in", methods=["GET", "POST"])
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
        email, password, jobs, csrf_token = (
            request.json.get("email"),
            request.json.get("password"),
            request.json.get("jobs"),
            request.headers.get("X-CSRF-Token"),
        )
        if email == "":
            return jsonify(
                {"result": False, "redirect": "/sign-in", "msg": "Email cannot empty"}
            )
        elif password == "":
            return jsonify(
                {
                    "result": False,
                    "redirect": "/sign-in",
                    "msg": "Password cannot empty",
                }
            )
        elif jobs == "None":
            return jsonify(
                {"result": False, "redirect": "/sign-in", "msg": "Jobs cannot empty"}
            )
        else:
            try:
                user = db["users"].find_one(
                    {
                        "email": email.lower(),
                        "jobs": jobs,
                    }
                )

                # cek user
                if user:
                    if (
                        user["password"]
                        == hashlib.sha256(password.encode()).hexdigest()
                    ):
                        if user["jobs"] == "Magang" or user["jobs"] == "Karyawan":
                            if (
                                user["mulai_kerja"] != None
                                and user["akhir_kerja"] != None
                            ):
                                if cek_tanggal_kerja(
                                    user["mulai_kerja"], user["akhir_kerja"]
                                ):
                                    token = signInPayload(
                                        user["_id"],
                                        user["jobs"],
                                        user["role"],
                                        datetime.timedelta(minutes=30),
                                    )

                                    resp = make_response(
                                        jsonify(
                                            {
                                                "result": "success",
                                                "redirect": "/dashboard/magang",
                                                "msg": "Login successful",
                                            }
                                        )
                                    )
                                    resp.set_cookie(
                                        "token_key",
                                        token,
                                        httponly=True,
                                        secure=True,
                                        samesite="Strict",
                                        expires=datetime.datetime.now()
                                        + datetime.timedelta(minutes=30),
                                    )  # ubah secure jadi true saat production
                                    resp.set_cookie(
                                        "csrf_token",
                                        csrf_token,
                                        httponly=True,
                                        secure=True,
                                        samesite="Lax",
                                        expires=datetime.datetime.now()
                                        + datetime.timedelta(minutes=30),
                                    )  # ubah secure jadi true saat production
                                    return resp

                                else:
                                    return jsonify(
                                        {
                                            "result": False,
                                            "redirect": "/sign-in",
                                            "msg": "Your account expired",
                                        }
                                    )
                            else:
                                return jsonify(
                                    {
                                        "result": False,
                                        "redirect": "/sign-in",
                                        "msg": "date is empty, please contact admin / manager",
                                    }
                                )
                        elif user["jobs"] == "Admin":
                            token = signInPayload(
                                user["_id"],
                                user["jobs"],
                                user["role"],
                                datetime.timedelta(hours=24),
                            )
                            resp = make_response(
                                jsonify(
                                    {
                                        "result": "success",
                                        "redirect": "/dashboard/magang",
                                        "msg": "Login successful",
                                    }
                                )
                            )
                            resp.set_cookie(
                                "token_key",
                                token,
                                httponly=True,
                                secure=True,
                                samesite="Lax",
                                expires=datetime.datetime.now()
                                + datetime.timedelta(minutes=30),
                            )  # ubah secure jadi true saat production
                            resp.set_cookie(
                                "csrf_token",
                                csrf_token,
                                httponly=True,
                                secure=True,
                                samesite="Lax",
                                expires=datetime.datetime.now()
                                + datetime.timedelta(minutes=30),
                            )  # ubah secure jadi true saat production
                            return resp
                        else:
                            return jsonify(
                                {
                                    "result": False,
                                    "redirect": "/sign-in",
                                    "msg": "Wrong jobs/jobs maintenance",
                                }
                            )
                    else:
                        return jsonify(
                            {
                                "result": False,
                                "redirect": "/sign-in",
                                "msg": "Wrong password",
                            }
                        )
                else:
                    return jsonify(
                        {"result": False, "redirect": "/sign-in", "msg": "Wrong email"}
                    )
            except ValueError as e:
                return jsonify(
                    {
                        "result": False,
                        "redirect": "/sign-in",
                        "msg": "your account pending, wait at least 24 hours",
                    }
                )

    # request method get
    msg = request.args.get("msg")
    status = request.args.get("status")
    title = request.args.get("title")
    return render_template("signIn.html", msg=msg, status=status, title=title)


@app.route("/api/auth/logout")
def signOut():
    resp = make_response(
        jsonify(
            {"status": "success", "redirect": "/sign-in", "msg": "Logout successful"}
        ),
        200,
    )
    resp.set_cookie("token_key", expires=0)
    resp.set_cookie("csrf_token", expires=0)
    return resp

@app.route("/sign-in/forget", methods=["GET", "POST"])
def forgetPassword():
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
            password_hash = hashlib.sha256(password_new.encode("utf-8")).hexdigest()
            result = db.users.find_one(
                {"email": email.lower(), "jobs": {"$in": ["Magang", "Karyawan"]}}
            )

            # cek lanjutan dan update
            if not result:
                raise Exception("Email not found or jobs not Magang or Karyawan")
            if result["password"] == password_hash:
                raise ValueError("Password is same")

            Otp = OtpPasswordGenerator(email.lower(), result["nama"])
            jwt_otp = jwt.encode(
                {
                    "email": email.lower(),
                    "otp": Otp.otp,
                    "password_hash": password_hash,
                    "user": str(result["_id"]),
                    "jobs": result["jobs"],
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


@app.route("/sign-in/forget/otp/<jwt_otp>", methods=["GET", "POST"])
def forgetPasswordOtp(jwt_otp):
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
            # terjemahkan jwt
            token_otp = jwt.decode(token, secretKey, algorithms="HS256")

            if int(otp) != token_otp["otp"]:
                raise ValueError("OTP actual not same")
            
            result = db.users.update_one(
                {
                    "email": token_otp["email"].lower(),
                    "_id": ObjectId(token_otp["user"]),
                },
                {"$set": {"password": token_otp["password_hash"]}},
            )

            # berhasil atau tidak
            if result.modified_count <= 0:
                raise Exception("Terjadi kesalahan Update Password")
            return jsonify(
                redirect="/sign-in",
                msg="Password updated",
                status="success",
                title="Update Password",
            )

        # catch erronya
        except ValueError as e:
            return jsonify(
                redirect=url_for("forgetPasswordOtp", jwt_otp=jwt_otp, msg=e.args[0])
            )
        except Exception as e:
            return jsonify(
                redirect=url_for("forgetPasswordOtp", jwt_otp=jwt_otp, msg=e.args[0])
            )
        except jwt.ExpiredSignatureError:
            return jsonify(redirect=url_for("forgetPassword", msg="Token Kadaluarsa"))
        except jwt.InvalidTokenError:
            return jsonify(redirect=url_for("forgetPassword", msg="Token TIdak valid"))

    # request method get
    result = request.args.get("status")
    msg = request.args.get("msg")
    return render_template(
        "forgetPasswordOtp.html", token=jwt_otp, msg=msg, result=result
    )


# lakukan sign-up
@app.route("/sign-up", methods=["GET", "POST"])
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
                "password": hashlib.sha256(password.encode("utf-8")).hexdigest(),
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
                "absen": {"hadir": 0, "tidak_hadir": 0},
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


# update my profile
@app.route("/myProfiles", methods=["GET", "POST"])
def myProfiles():
    if request.method == "POST":
        try:
            token_key = request.cookies.get("token_key")
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

            if not gambar:
                gambar = db.users.find_one(
                    {"_id": ObjectId(payloads["_id"])}, {"photo_profile": 1}
                )["photo_profile"]
            print(gambar)

            # cek csrf token
            if csrf_token == None or csrf_token == "":
                raise ValueError("CSRF token tidak valid atau tidak ditemukan")

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
                print(filename)
                # Simpan file ke folder yang ditentukan
                filepath = os.path.join(app.config["UPLOAD_FOLDER"], filename)
                gambar.save(filepath)
                filepath_db = "img/user/" + filename
            else:
                return redirect(url_for("myProfiles", msg="Something Wrong Files!"))

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
            if result:
                return redirect(
                    url_for(
                        "myProfiles", msg="Update Profile Berhasil", status="success"
                    )
                )
            else:
                return redirect(url_for("myProfiles", msg="Update Profile Gagal"))
        except ValueError as e:
            return redirect(url_for("signIn", msg=e.args[0]))
        except jwt.ExpiredSignatureError:
            return redirect(url_for("signIn", msg="Session Expired"))
        except jwt.DecodeError:
            return redirect(url_for("signIn", msg="Anda telah logout"))

    msg = request.args.get("msg")
    status = request.args.get("status")
    try:
        token_key = request.cookies.get("token_key")
        csrf_token = request.cookies.get("csrf_token")
        if csrf_token == None or csrf_token == "":
            raise ValueError("CSRF token tidak valid atau tidak ditemukan")
        payloads = jwt.decode(token_key, secretKey, algorithms=["HS256"])
        data = db.users.find_one({"_id": ObjectId(payloads["_id"])})

        return render_template("myProfiles.html", data=data, msg=msg, status=status)

    except ValueError as ve:
        return redirect(url_for("signIn", msg=ve.args[0]))
    except jwt.ExpiredSignatureError:
        return redirect(url_for("signIn", msg="Session Expired"))
    except jwt.DecodeError:
        return redirect(url_for("signIn", msg="Anda telah logout"))


@app.route("/task/magang", methods=["GET"])
def task():
    cookie = request.cookies.get("token_key")
    csrf_token = request.cookies.get("csrf_token")
    if csrf_token == None:
        return redirect(url_for("signIn", msg="csrf token expired"))

    try:
        payload = jwt.decode(cookie, secretKey, algorithms=["HS256"])
        data = db.users.find_one(
            {
                "_id": ObjectId(payload["_id"]),
                "jobs": payload["jobs"],
                "role": payload["role"],
            }
        )
        return render_template("task_magang.html", data=data)
    except jwt.ExpiredSignatureError:
        return redirect(url_for("signIn", msg="Session Expired"))
    except jwt.DecodeError:
        return redirect(url_for("signIn", msg="Anda telah logout"))


@app.route("/dashboard/admin/<path>", methods=["GET"])
def export(path):
    if path not in ["excel", "csv", "pdf", "print"]:
        return redirect(url_for("notFound", path=path))
    try:
        # ambil cookie dan payload
        cookie = request.cookies.get("token_key")
        payloads = jwt.decode(cookie, secretKey, algorithms=["HS256"])
        if (
            payloads["role"] != 1
            and payloads["jobs"] != "admin"
            and payloads["departement"] not in ("Superuser", "Subuser")
        ):
            return Exception("Anda tidak punya akses")
        # cek database
        result = list(
            db.users.find(
                {"jobs": {"$in": ["Karyawan", "Magang"]}},
                {"_id": 0, "password": 0, "role": 0, "work_hours": 0},
            )
        )

        # save excel data
        file_path = os.path.join(app.root_path, "static", "doc")
        wb = load_workbook(file_path + "\\excel\\template_data_karyawan.xlsx")
        ws = wb.active

        column_widths, start, stop = convert_to_excel(ws, result=result)
        # save for extractor pdf
        wb.save(file_path + "\\excel\\data_karyawan.xlsx")

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
            pdf = PDF("L", "mm", "A4")
            pdf.add_page()
            pdf.create_pdf(start - 1, stop, column_widths, ws)
            # Buat objek BytesIO
            output = BytesIO()
            pdf.output(file_path + "\\pdf\\data_karyawan.pdf")

            # Kirim file PDF sebagai attachment
            return send_file(
                file_path + "\\pdf\\data_karyawan.pdf",
                as_attachment=False,
                download_name="data_karyawan_winnicode.pdf",
                mimetype="application/pdf",
            )
        else:
            return redirect(url_for("notFound", path=path))

    # except Exception as e:
    #     return redirect(url_for('dashboard',msg = e.args[0]))
    except jwt.ExpiredSignatureError:
        return redirect(url_for("signIn", msg="Session Expired"))
    except jwt.DecodeError:
        return redirect(url_for("signIn", msg="Anda telah logout"))


# melakukan error handler csrf
@app.errorhandler(400)
def handle_csrf_error(e):
    return jsonify({"error": "CSRF token tidak valid atau tidak ditemukan"}), 400


# routing all
@app.route("/<path>", methods=["GET"])
@app.route("/<path>/<argument>", methods=["GET"])
@app.route("/<path>/<argument>/<argument2>", methods=["GET"])
@app.route("/<path>/<argument>/<argument2>/<argument3>", methods=["GET"])
def notFound(path=None, argument=None, argument2=None, argument3=None):
    previous = request.referrer
    data = {"next": "/", "previous": urlparse(previous).path if previous else previous}
    return render_template("notFound.html", data=data)


# stating app
if __name__ == "__main__":
    # # Menjadwalkan pengecekan absensi setiap menit
    delete_absen = BackgroundScheduler()
    delete_absen.add_job(
        func=unhadir_absensi, trigger="interval", hours=1
    )  # interval hours/minute/second. date run_date .cron day_of_week,hours,minutes
    delete_absen.start()
    app.run(port=900, debug=True)
    # DEBUG is SET to TRUE. CHANGE FOR PROD


# atur tanggal dan waktu saat ganti beda lagi bentukannya sama setintervalkan waktu 10 jam
