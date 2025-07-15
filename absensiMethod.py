import base64
import datetime
import jwt
from bson import ObjectId
import requests
import datetime
import re
# import certifi
from werkzeug.datastructures import FileStorage
from generate_otp import AbsensiNotify


# upload img with imgbb
def upload_to_imgbb(file: FileStorage, imgbb_api_key: str):
    """Upload gambar ke Imgbb dan return url gambar yang di upload

    Args:
        file (FileStorage): File yang akan di upload
        imgbb_api_key (str): Api key Imgbb

    Returns:
        dict: Berisi status dan url gambar yang di upload

    Raises:
        Exception: Jika tidak ada file yang di upload

    Examples:
        >>> from flask import request
        >>> from app import upload_to_imgbb
        >>> file = request.files['image']
        >>> imgbb_api_key = "your_imgbb_api_key"
        >>> response = upload_to_imgbb(file, imgbb_api_key)
        >>> print(response)
        {
            'status': 'success',
            'url': 'https://i.ibb.co.com/your-image-url.jpg',
            'filename': 'your-image-filename.jpg'
        }
    """

    # check if file is provided
    if not file:
        return {"status": "failed", "message": "No file provided"}

    # cek url
    url = "https://api.imgbb.com/1/upload"
    # buat payload
    files = {
        "image": (file.filename, file.stream, file.content_type),
    }
    response = requests.post(f"{url}?key={imgbb_api_key}", files=files)
    if response.status_code == 200:
        data = response.json()
        if data["status"] == 200:
            return {
                "status": "success",
                "url": data["data"]["image"]["url"].replace("i.ibb.co", "i.ibb.co.com"),
                "filename": data["data"]["image"]["filename"],
            }
    return {"status": "failed"}


# ambil waktu berdasarkan api
def get_time_zone_now(location: str = "asia/jakarta"):
    """
    API untuk mengambil waktu sekarang berdasarkan lokasi timezone.

    Parameter:
        location (str): Lokasi timezone yang akan diambil waktu sekarangnya. Default: "asia/jakarta".

    Response:
        datetime.datetime: Waktu sekarang berdasarkan lokasi timezone yang di request.

    Contoh:
        >>> import pytz
        >>> tz = pytz.timezone(location)
        >>> print("Waktu sekarang ({}):".format(location), waktu_sekarang)
        datetime.datetime(2023, 3, 14, 10, 32, 45)
    """

    # Zona waktu Indonesia Barat (WIB)
    import pytz
    tz = pytz.timezone(location)
    waktu_sekarang = datetime.datetime.now(tz).replace(tzinfo=None)  # timezone-aware, lalu ubah ke naive untuk keseragaman
    print("Waktu sekarang ({}):".format(location), waktu_sekarang)
    return waktu_sekarang


def is_valid_datetime_format(value):
    """
    API untuk memeriksa apakah datetime format yang diberikan valid atau tidak.

    Parameter:
        value (str): String datetime yang akan di cek validitasnya.

    Response:
        bool: True jika datetime formatnya valid, False jika tidak.

    Contoh:
        >>> import requests
        >>> response = requests.get("https://absensi.winnicode.com/api/valid_datetime?value=2023-03-14T10:32")
        >>> print(response.json())
        True
    """

    # Pola regex untuk "YYYY-MM-DDTHH:MM"
    pattern = r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}$"
    
    return bool(re.match(pattern, value))

def build_target(now: datetime, target_time) -> datetime:
    """Padukan jam‑menit target ke tanggal hari ini (atau besok)."""
    today_target = datetime.datetime.combine(now.date(), target_time)
    if today_target < now:           # kalau sudah lewat hari ini, pakai besok
        today_target += datetime.timedelta(days=1)
    return today_target

def pick_delta(diff: datetime.timedelta) -> int | None:
    breakpoints = [30, 5, 0, -5, -10, -15, -20]        # satuan: menit
    for bp in breakpoints:
        if bp >= 0:                                    # masa sebelum target
            if diff <= datetime.timedelta(minutes=bp):
                return bp
        else:                                          # masa sesudah target
            if diff <= datetime.timedelta(minutes=bp):          # diff negatif lebih besar ⇒ lebih lampau
                return bp
    return None

def countdown_time(a: datetime.datetime, b: datetime.datetime, email: str):
    from app import db

    """
    Countdown Timer
    =
    API untuk menghitung waktu yang tersisa hingga waktu tertentu.

    Parameter:
        a (datetime.datetime): Waktu sekarang.
        b (datetime.datetime): Waktu target.
        email (str): email target
    """
    # inisiasi angka deltanya
    angka_delta_pilih = None
    result = None

    # lakukan synkron terhadap data yang didapat
    now = a
    target =  build_target(now, b.time())
    diff = target - now
    
    angka_delta_pilih = pick_delta(diff)
    print(angka_delta_pilih)

    # cek jika angka_delta pilih diluar kondisi
    if angka_delta_pilih is None:
        return False

    # Cari dokumen berdasarkan email
    existing_doc = db.angka_notif.find_one({"email": email})

    # Jika dokumen ada, cek angka_delta
    if existing_doc:
        # Jika angka_delta sama, lewati update
        if existing_doc.get("angka_delta") == angka_delta_pilih:
            print("Angka delta sama, tidak ada perubahan.")
            result = False
        else:
            # Update angka_delta jika berbeda
            result = db.angka_notif.find_one_and_update(
                {"email": email},
                {"$set": {"angka_delta": angka_delta_pilih}},
                return_document=True,
            )
            print("Dokumen diperbarui:", result)
    else:
        # Jika dokumen tidak ditemukan, tambahkan dokumen baru
        result = db.angka_notif.insert_one(
            {"email": email, "angka_delta": angka_delta_pilih}
        )
        print("Dokumen baru ditambahkan.")

    # cek berhasil dilakukan atau tidak
    if not result:
        return False

    # kirimkan angka delta pilih terbaru untuk dieksekusi ke gmail
    return angka_delta_pilih


# tidak hadir untuk magang / karyawan
def unhadir_absensi():
    from app import db
    users = list(db.users.find({"role": 3}))  # bisa diperluas ke role 2 juga
    now = get_time_zone_now()
    time_now = now.time()
    print("Server sedang berjalan dilatar belakang")

    if users:
        for user in users:
            email_user = user.get("email")
            mulai_kerja = user.get("mulai_kerja")
            akhir_kerja = user.get("akhir_kerja")
            waktu_awal_kerja = user.get("waktu_awal_kerja")
            waktu_akhir_kerja = user.get("waktu_akhir_kerja")
            user_id = user.get("_id")

            if not user.get("nik"):
                raise Exception('Data NIK belum terisi')
            
            print('\n\n'+email_user)

            if mulai_kerja and akhir_kerja:
                if cek_tanggal_kerja(mulai_kerja, akhir_kerja):
                    riwayat_absen = db.absen_magang.find_one({"user_id": user_id}, sort={"_id": -1})

                    angka_delta_pilih = countdown_time(
                        a=now,
                        b=datetime.datetime.strptime(waktu_awal_kerja, "%H.%M"),
                        email=email_user,
                    )
                    print('angka delta = ',angka_delta_pilih)
                    if angka_delta_pilih:
                        AbsensiNotify(email_user, angka_delta_pilih)

                    akhir_kerja_time = datetime.datetime.strptime(waktu_akhir_kerja, "%H.%M").time()

                    if riwayat_absen:
                        last_absen = datetime.datetime.strptime(riwayat_absen["tanggal_hadir"], "%d %B %Y")

                        if last_absen.date() < now.date() and time_now > akhir_kerja_time:
                            print('jalan1')
                            db.absen_magang.insert_one({
                                "user_id": ObjectId(user_id),
                                "status_hadir": 0,
                                'waktu_keluar':'',
                                'ket_keluar':'',
                                "waktu_hadir": now.strftime("%H.%M").lower(),
                                "tanggal_hadir": now.strftime("%d %B %Y").lower(),
                            })
                            db.users.find_one_and_update(
                                {"_id": ObjectId(user_id)},
                                {"$inc": {"absen.tidak_hadir": 1}}
                            )
                    else:
                        if time_now > akhir_kerja_time:
                            print('jalan2')
                            db.absen_magang.insert_one({
                                "user_id": ObjectId(user_id),
                                "status_hadir": 0,
                                'waktu_keluar':'',
                                'ket_keluar':'',
                                "waktu_hadir": now.strftime("%H.%M").lower(),
                                "tanggal_hadir": now.strftime("%d %B %Y").lower(),
                            })
                            db.users.find_one_and_update(
                                {"_id": ObjectId(user_id)},
                                {"$inc": {"absen.tidak_hadir": 1}}
                            )
        print('sudah diluar')

    return "berhasil ya!"

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

    Parameters:
        awal_kerja_str (str): string tanggal awal kerja dalam format Hari NamaBulan Tahun
        akhir_kerja_str (str): string tanggal akhir kerja dalam format Hari NamaBulan Tahun

    Returns:
        bool: True jika tanggal sekarang berada diantara awal_kerja dan akhir_kerja, False jika sebaliknya
    """
    format_tanggal = "%d %B %Y"
    awal_kerja = datetime.datetime.strptime(awal_kerja_str, format_tanggal).date()
    akhir_kerja = datetime.datetime.strptime(akhir_kerja_str, format_tanggal).date()
    tanggal_sekarang = get_time_zone_now().date()

    return awal_kerja <= tanggal_sekarang <= akhir_kerja


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
