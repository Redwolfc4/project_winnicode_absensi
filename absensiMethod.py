import base64
import datetime
import jwt
from bson import ObjectId
from cryptography.fernet import Fernet
import requests
import datetime
import re
from werkzeug.datastructures import FileStorage

# Generate a key for encryption (this should be securely stored)
key = Fernet.generate_key()
cipher = Fernet(key)


# upload img with imgbb
def upload_to_imgbb(file: FileStorage, imgbb_api_key: str):
    """Fungsi untuk upload gambar ke Imgbb"""

    # check if file is provided
    if not file:
        return {"status": "failed", "message": "No file provided"}

    # # Read the image file and encode it to base64
    # image_data = base64.b64encode(file.read()).decode("utf-8")
    # print(image_data)

    # cek url
    url = "https://api.imgbb.com/1/upload"
    # buat payload
    files = {
        "image": (file.filename, file.stream, file.content_type),
    }
    response = requests.post(f"{url}?key={imgbb_api_key}", files=files)
    if response.status_code == 200:
        data = response.json()
        print(data["status"])
        if data["status"] == 200:
            return {
                "status": "success",
                "url": data["data"]["image"]["url"].replace("i.ibb.co", "i.ibb.co.com"),
                "filename": data["data"]["image"]["filename"],
            }
    return {"status": "failed"}


# ambil waktu berdasarkan api
def get_time_zone_now(location: str = "asia/jakarta"):
    url = f"https://www.timeapi.io/api/time/current/zone?timeZone={location}"
    waktu_str = requests.get(url).json()["dateTime"]
    waktu_sekarang = datetime.datetime.fromisoformat(waktu_str)
    return waktu_sekarang


def is_valid_datetime_format(value):
    # Pola regex untuk "YYYY-MM-DDTHH:MM"
    pattern = r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}$"
    return bool(re.match(pattern, value))


# tidak hadir untuk magang / karyawan
def unhadir_absensi():
    """
    Fungsi untuk mengupdate status tidak hadir untuk magang/karyawan setiap 1 jam sekali.

    Pemanggilan:
    Fungsi ini dipanggil oleh BackgroundScheduler yang di jalankan di dalam file app.py.
    BackgroundScheduler ini di setting agar menjalankan fungsi ini setiap 1 jam sekali.

    Parameter:
    Tidak ada parameter yang dibutuhkan.

    Return:
    Tidak ada nilai return yang dihasilkan oleh fungsi ini.

    Contoh:
    Fungsi ini akan dijalankan setiap 1 jam sekali dan akan mengupdate status tidak hadir
    untuk magang/karyawan yang tidak hadir.
    """

    from app import db

    users = db.users.find({"role": 3})  # nanti diubah bisa role 2 dan 3
    now = get_time_zone_now()
    time_now = now.time()
    print("Server sedang berjalan dilatar belakang")
    # db.absen_magang.delete_many({'tanggal_hadir':now.strftime('%d %B %Y').lower()})

    # cek table users
    if users:
        for user in users:
            mulai_kerja = user["mulai_kerja"]
            akhir_kerja = user["akhir_kerja"]
            waktu_akhir_kerja = user["waktu_akhir_kerja"]
            user_id = user["_id"]

            # cek mulai kerja dan akhir kerja user
            if mulai_kerja != "" and akhir_kerja != "":
                # cek tanggal sekarang dengan rentang kerja
                if cek_tanggal_kerja(mulai_kerja, akhir_kerja):
                    riwayat_absen = db.absen_magang.find_one(
                        {"user_id": user_id}, sort={"_id": -1}
                    )  # cek riwayat absen
                    # cek table riwayat absen pernah di insert atau tidak sama sekali sesuai dengan
                    if riwayat_absen:
                        last_absen = datetime.datetime.strptime(
                            riwayat_absen["tanggal_hadir"], "%d %B %Y"
                        )
                        # apakah tanggal riwayat sama dengan sekarang
                        if last_absen.date() < now.date():
                            # apakah jam riwayat lebih dari waktu akhir kerja
                            if (
                                time_now
                                > datetime.datetime.strptime(
                                    waktu_akhir_kerja, "%H.%M"
                                ).time()
                            ):
                                db.absen_magang.insert_one(
                                    {
                                        "user_id": ObjectId(user_id),
                                        "status_hadir": 0,
                                        "waktu_hadir": datetime.datetime.now()
                                        .strftime("%H.%M")
                                        .lower(),
                                        "tanggal_hadir": datetime.datetime.now()
                                        .strftime("%d %B %Y")
                                        .lower(),
                                    }
                                )
                                db.users.find_one_and_update(
                                    {"_id": ObjectId(user_id)},
                                    {
                                        "$set": {
                                            "absen.tidak_hadir": db.users.find_one(
                                                {"_id": ObjectId(user_id)}
                                            )["absen"]["tidak_hadir"]
                                            + 1
                                        }
                                    },
                                )
                    # non riwayat absen
                    else:
                        # apakah jam riwayat lebih dari waktu akhir kerja
                        if (
                            time_now
                            > datetime.datetime.strptime(
                                waktu_akhir_kerja, "%H.%M"
                            ).time()
                        ):
                            db.absen_magang.insert_one(
                                {
                                    "user_id": ObjectId(user_id),
                                    "status_hadir": 0,
                                    "waktu_hadir": datetime.datetime.now()
                                    .strftime("%H.%M")
                                    .lower(),
                                    "tanggal_hadir": datetime.datetime.now()
                                    .strftime("%d %B %Y")
                                    .lower(),
                                }
                            )
                            db.users.find_one_and_update(
                                {"_id": ObjectId(user_id)},
                                {
                                    "$set": {
                                        "absen.hadir": db.users.find_one(
                                            {"_id": ObjectId(user_id)}
                                        )["absen"]["tidak_hadir"]
                                        + 1
                                    }
                                },
                            )


# lakukan sigin payload
def signInPayload(a, b, c, d):
    from app import secretKey

    """
    Fungsi untuk membuat payload token JWT untuk keperluan login
    
    Parameters:
    a (ObjectId): ID dari user yang login
    b (str): jobs dari user yang login
    c (int): role dari user yang login
    d (datetime.timedelta): durasi waktu berlaku dari token
    
    Returns:
    str: token JWT yang telah dibuat
    
    Examples:
    >>> signInPayload(ObjectId("5f8c0c8b3b9b5c002f3e93e5"), "Magang", 3, datetime.timedelta(days=1))
    'eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.eyJfaWQiOiI1ZjhjMGM4YjNiOWI1YzAwMmYzZTkyZSIsImpvYnMiOiJNYWdhbiIsInJvbGUiOjMsImV4cCI6MTYwMjQ4NzQ4NX0.1wDQ7Z4qJz0yN1Xm8ZQ0Qk3nT4Xj9rS5uP3oK2hR6g'
    """

    payloads = {
        "_id": str(a),
        "jobs": b,
        "role": c,
        "exp": datetime.datetime.utcnow() + d,
    }
    token = jwt.encode(payloads, secretKey, algorithm="HS256")
    return token


# buat filter kustom untuk mengubah format waktu
def format_time(value):
    """
    Filter kustom untuk mengubah format waktu dari string ke format datetime

    Parameters:
    value (str): string waktu dalam format Jam.Menit

    Returns:
    str: string waktu dalam format HH:MM
    """

    # Konversi string '10.00' ke format datetime
    date_obj = datetime.datetime.strptime(value, "%H.%M")
    # Ubah format ke 'HH:MM'
    return date_obj.strftime("%H:%M")


# Buat filter kustom untuk mengubah format tanggal
def format_date(value):
    """
    Filter kustom untuk mengubah format tanggal dari string ke format datetime

    Parameters:
    value (str): string tanggal dalam format Hari NamaBulan Tahun

    Returns:
    str: string tanggal dalam format YYYY-MM-DD
    """
    # Konversi string '12 May 2003' ke format datetime
    date_obj = datetime.datetime.strptime(value, "%d %B %Y")
    # Ubah format ke 'YYYY-MM-DD'
    return date_obj.strftime("%Y-%m-%d")


# kurangin tanggal hari ini sama tanggal mulai awal
def cek_tanggal_kerja(awal_kerja_str: str, akhir_kerja_str: str):
    """
    Mengecek apakah tanggal sekarang berada diantara awal_kerja dan akhir_kerja.

    Fungsi ini digunakan untuk mengecek apakah tanggal sekarang berada diantara
    tanggal awal_kerja dan akhir_kerja.

    Parameters:
        awal_kerja_str (str): string tanggal awal kerja dalam format Hari NamaBulan Tahun
        akhir_kerja_str (str): string tanggal akhir kerja dalam format Hari NamaBulan Tahun

    Contoh pemanggilan:
        >>> cek_tanggal_kerja("1 Januari 2022", "31 Januari 2022")
        True

    Returns:
    bool: True jika tanggal sekarang berada diantara awal_kerja dan akhir_kerja, False jika sebaliknya
    """
    # Mengonversi string tanggal menjadi objek datetime
    format_tanggal = "%d %B %Y"  # Format: Hari NamaBulan Tahun
    awal_kerja = datetime.datetime.strptime(awal_kerja_str, format_tanggal)
    akhir_kerja = datetime.datetime.strptime(akhir_kerja_str, format_tanggal)

    tanggal_sekarang = get_time_zone_now()

    # apakah awal kerja > tanggal_sekarang > akhir kerja
    if (tanggal_sekarang - awal_kerja >= datetime.timedelta(days=0)) and (
        akhir_kerja - tanggal_sekarang >= datetime.timedelta(days=0)
    ):
        return True
    else:
        return False


# Fungsi untuk mengonversi string menjadi bentuk UUID-like
def string_to_uuid_like(data: str):
    """
    Mengonversi string menjadi bentuk UUID-like.

    Fungsi ini digunakan untuk mengonversi string menjadi bentuk UUID-like yang
    dapat digunakan sebagai identifier yang unik.

    Parameters:
        data (str): string yang akan di konversi

    Returns:
        str: string yang telah di konversi menjadi bentuk UUID-like

    Example:
        >>> string_to_uuid_like("John Doe")
        'am9obj1vZGUK'
    """

    # Encode data ke bytes
    encoded_bytes = base64.urlsafe_b64encode(data.encode("utf-8")).rstrip(b"=")

    # Generate UUID dengan format 8-4-4-4-12 karakter
    uuid_like = f"{encoded_bytes[:8].decode()}-{encoded_bytes[8:12].decode()}-{encoded_bytes[12:16].decode()}-{encoded_bytes[16:20].decode()}-{encoded_bytes[20:].decode()}"
    return uuid_like


# Fungsi untuk mendekonversi kembali dari UUID-like ke string asli
def uuid_like_to_string(uuid_like: str):
    """
    Mendekonversi UUID-like kembali ke string asli.

    Fungsi ini digunakan untuk mendekonversi UUID-like yang dihasilkan oleh fungsi
    `string_to_uuid_like` kembali ke string asli.

    Parameters:
        uuid_like (str): UUID-like yang akan di dekoversi

    Returns:
        str: string asli yang di dekoversi dari UUID-like

    Example:
        >>> uuid_like_to_string("am9obj1vZGUK")
        'John Doe'
    """
    # Gabungkan UUID-like kembali ke string base64
    cleaned_uuid = uuid_like.replace("-", "")

    # Decode dari base64 ke string asli
    padded_base64 = cleaned_uuid + "=="  # Base64 harus punya padding yang valid
    decoded_bytes = base64.urlsafe_b64decode(padded_base64)

    return decoded_bytes.decode("utf-8")
