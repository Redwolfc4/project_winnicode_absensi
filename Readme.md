
![Logo](https://i.ibb.co.com/Nr4prRB/absensiku-logo.png)


[![GitHub Watchers](https://img.shields.io/github/watchers/RedwolfC4/project_winnicode_absensi?style=flat&logo=github)](https://github.com/RedwolfC4/project_winnicode_absensi/watchers) [![GitHub Stars](https://img.shields.io/github/stars/RedwolfC4/project_winnicode_absensi?style=flat&logo=github)](https://github.com/RedwolfC4/project_winnicode_absensi/stargazers) [![GitHub Forks](https://img.shields.io/github/forks/RedwolfC4/project_winnicode_absensi?style=flat&logo=github)](https://github.com/RedwolfC4/project_winnicode_absensi/network/members)![Python](https://img.shields.io/badge/Python_3.12.5-3776AB?style=flat&logo=python&logoColor=white)
![HTML5](https://img.shields.io/badge/HTML5-E34F26?style=flat&logo=html5&logoColor=white)
![CSS3](https://img.shields.io/badge/CSS3-1572B6?style=flat&logo=css3&logoColor=white)
![JavaScript](https://img.shields.io/badge/JavaScript-F7DF1E?style=flat&logo=javascript&logoColor=black)
![jQuery](https://img.shields.io/badge/jQuery_3.7.1-0769AD?style=flat&logo=jquery&logoColor=white)
![Bootstrap](https://img.shields.io/badge/Bootstrap_5.3.3-563D7C?style=flat&logo=bootstrap&logoColor=white)

# AbsensiKu Project`s

&nbsp;&nbsp;&nbsp;Merupakan sebuah proyek website absensi yang berguna untuk otomatisasi kehadiran dalam meningkatkan efisiensi, transparansi dan akurasi pengelolaan waktu dan kehadiran karyawan serta memungkinkan pengelolaan sumber daya manusia yang lebih optimal. Fitur yang ditawarkan berbagai macam mulai dari rekap kehadiran sampai progress tugas yang diberikan serta website ini dikembangkan dengan menggunakan framework **Flask**.




## Screenshots

![AbsensiKu](https://i.ibb.co.com/vzfgQWm/Screenshot-2024-12-26-142502.png)


## Features
- **Landing Page**, halaman awal dalam memulai website ini.
- **Autentikasi**, 
    - **Login**, autentikasi masuk untuk *(Admin | Sub Admin | Karyawan | Magang)* dengan berbagai departement,  
    - **Forget Password**, mengubah password diluar akun untuk *(Karyawan | Magang)*
    - **Signup**, pendaftaran akun untuk *(Karyawan | Magang)*.
- **Documentation Api**, mendukung pengembangan website agar mengetahui kegunaan setiap ednpoint.
- **Dashboard**, mendukung dalam merekap absensi serta jumlah riwayat *(Karyawan | Magang)* serta melakukan manajemen akun Karyawan/Magang *(Admin | Sub Admin)*.
- **Ubah Password**, dapat melakukan perubahan password *(Admin | Sub Admin | Karyawan | Magang)*.
- **Riwayat Kehadiran**, dapat melihat lebih detai riwayat kehadiran dengan menyesuaikan tanggal *(Admin | Sub Admin | Karyawan | Magang)*.
- **Riwayat Bantuan**, dapat melihat kendala yang dialami oleh berbagai user *(Admin | Sub Admin)*.
- **Kelola Admin**, dapat memanajemen admin /Sub Admin (CRUD) *(Admin (Superuser))*.
- **Task**, menngelola dalam progress task yang diberikan *(Karyawan | Magang)* serta melakukan penambahan, diterima task dan menhapus task jika sudah lama *(Admin | Sub Admin)*.
- **My Profiles**, digunakan untuk melakukan perubahan data akun sendiri*(Admin | Sub Admin | Karyawan | Magang)*.



## API Reference

#### Get all items

```http
  GET /apidocs
```
&nbsp;&nbsp;&nbsp;Merupakan endpoint menuju api lebih detail

## Color Reference

| Color             | Hex                                                                |
| ----------------- | ------------------------------------------------------------------ |
| Primary Color | ![#ff66c4](https://via.placeholder.com/10/ff66c4?text=+) #ff66c4 |
| Primary Color Hover | ![#fa1fa6](https://via.placeholder.com/10/fa1fa6?text=+) #fa1fa6 |


## Demo

- [Vercel](https://absensiku.vercel.app/)
- [Railway](https://absensiku.up.railway.app/) **Terbatas**


## Environment Variables

Dalam menjalankan project ini, kamu perlu menggantikan `.env_copy` menjadi `.env` dan mengisi sesuai dengan ketentuan di template tersebut


## Tech Stack

**Client:** HTML, CSS, JS, Jquery, Bootstrap

**Server:** Flask(Python)


## Installation
&nbsp;&nbsp;&nbsp;Syarat wajib instalasi yang diperlukan sebagai berikut : 

- **Python**, melakukan instalasi terlebih dahulu versi [3.12.5](https://www.python.org/downloads/release/python-3125/). untuk cara downloadnya bisa [klik disini](https://dqlab.id/cara-download-python-lengkap-dengan-panduan-setupnya)
- **Visual Studio Code**, versi berapapun. untuk cara downloadnya bisa [klik disini](https://www.elztech.com/cara-download-dan-installasi-visual-studio-code/)
- **Browser**
- **MongoDb Account**, melakukan pembuatan akun MongoDb terlebih dahulu. untuk cara downloadnya bisa [klik disini](https://youtu.be/2_98lTrB5NI?si=0aH2uL3DCRozgC9n) dan melakukan copy url [disini langkahnya](https://youtu.be/daMxiBS0odk?si=RddUBy8T0spblCnO)
- **ImgBB**, melakukan pembuatan akun imgbb terlebih dahulu. [klik disini](https://imgbb.com/) kemudian copy keynya [disini](https://imgbb.com/account/settings/api) untuk cara downloadnya bisa [klik disini](https://youtu.be/xYOUJHXHj1s?si=9bKGEdrVDSFxQsvE)
## Run Locally

Clone the project

```bash
git clone https://github.com/Redwolfc4/project_winnicode_absensi.git
```

Undo initialization
```bash
#bash
rm -rf .git

#windows
rmdir /s .git
```

Go to the project directory

```bash
cd project_winnicode_absensi
```

Membuat dan menjalankan Virtual Environment
```bash
python3 -m venv venv

#pastikan anda berada di root directory untuk menjalankan

#windows
venv\Scripts\activate

#macOS / Linux
source venv/bin/activate

#Mematikan virtual jika tidak dipakai
deactivate
```


Install dependencies

```bash
pip install -r requirements.txt
```

Konfigurasi Environtment Variabel
&nbsp;&nbsp;&nbsp;silahkan melakukan perubahan .env_local menjadi .env file lalu konfigurasi. untuk melakukan
konfigurasi anda dapat menghubungi saya melalui [whatsapp](wa.me/62895359530117?text=saya%20ingin%20meminta%20credential%20anda?) atau [email saya](mailto:salahudinkoliq10@gmail.com) dikarenakan bersifat kredensial dan tidak bisa diunggah ke github.


Start the server

```bash
#python2 not sarankan
python2 app.py

#python3
python3 app.py
```

and klik here

`http://127.0.0.1:8080`


## Running Tests

To run tests, run the following command

```
#python2 not sarankan
python2 app.py

#python3
python3 app.py

```

and klik here

`http://127.0.0.1:8080`


## Authors

- [@Salahudin Kholik Prasetyono](https://github.com/Redwolfc4)


## Support

For support, email [salahudinkoliq10@gmail.com](mailto:salahudinkoliq10@gmail.com)


## Feedback

If you have any feedback, please reach out to us at [salahudinkoliq10@gmail.com](mailto:salahudinkoliq10@gmail.com)


## Contributing

Kami menerima kontribusi dari komunitas terbuka untuk meningkatkan aplikasi ini. Jika Anda menemukan masalah, bug, atau memiliki saran untuk peningkatan, silakan buat issue baru dalam repositori ini atau ajukan pull request.

