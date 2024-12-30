from flask import make_response, jsonify
from absensiMethod import unhadir_absensi


def handler(request):
    """
    Fungsi ini digunakan untuk melakukan operasi cron task.

    Fungsi ini digunakan untuk melakukan operasi cron task yang berjalan setiap 1 menit sekali.
    Operasi yang dilakukan adalah mengupdate status absensi pegawai yang sudah lewat dari waktu yang ditentukan
    maka statusnya akan diupdate menjadi tidak hadir.

    Returns:
        json: respon dari operasi cron task
    """
    try:
        unhadir_absensi()
        return make_response(jsonify({"message": "success"}), 200)
    except Exception as e:
        return make_response(jsonify({"message": str(e)}), 500)
