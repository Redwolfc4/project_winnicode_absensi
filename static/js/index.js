$(document).ready(function () {
  // membuat saat lebar lebih dari 992 akan toggle clas
  if ($(this).width() >= 992) {
    $("section#signin form").toggleClass("border");
    $("section#signup form").toggleClass("border");
    $("section#forgetPassword form").toggleClass("border");
  }

  $(window).resize(function () {
    if ($(this).width() >= 992) {
      $("section#signin form").removeClass("border");
      $("section#signup form").removeClass("border");
      $("section#forgetPassword form").removeClass("border");
    } else {
      $("section#signin form").addClass("border");
      $("section#signup form").addClass("border");
      $("section#forgetPassword form").addClass("border");
    }
  });
  // end

  // melakukan login form
  $("#signin").submit(function (e) {
    e.preventDefault();
    email_receive = $("#email").val();
    password_receive = $("#password").val();
    jobs = $("#jobs").val();

    $.ajax({
      type: "post",
      url: "/sign-in",
      data: JSON.stringify({
        email: email_receive,
        password: password_receive,
        jobs: jobs,
      }),
      headers: {
        "Content-Type": "application/json",
        "X-CSRF-Token": $("#csrf_token").val(),
      },
      dataType: "json",
      success: function (response) {
        if (response.result == "success") {
          Swal.fire({
            icon: "success",
            title: "Login Success",
            text: response["msg"],
            timer: 1500,
            willClose: () => {
              window.location.replace(response["redirect"]);
            },
          });
        } else {
          window.location.replace(
            response["redirect"] + "?msg=" + response["msg"]
          );
        }
      },
    });
  });

  // back to top
  $(window).on("scroll", function () {
    if ($(this).scrollTop() > 300) {
      $("#btn-back-to-top").addClass("active");
    } else {
      $("#btn-back-to-top").removeClass("active");
    }
  });

  // Smooth scroll to the top when the button is clicked
  $("#btn-back-to-top").on("click", function () {
    window.scrollTo({
      top: 0,
      behavior: "smooth",
    });
  });

  // countdown otp timer
  countdownOtp();

  // clock
  updateClock();
  // Update the clock every second
  setInterval(updateClock, 1000);

  // notifikasi
  notifAbsen();
});

let tepatWaktu;

// trigger countdown
countdownOtp = () => {
  // Mendapatkan URL saat ini
  const path = window.location.pathname;

  // Mengecek apakah path sesuai dengan yang diinginkan
  const regex = /^\/sign-in\/forget\/otp\/([a-zA-Z0-9._-]+)$/;
  const match = path.match(regex);

  if (match) {
    // countdown timer otp
    // Cek apakah ada waktu akhir yang tersimpan di sessionStorage
    let endTime = sessionStorage.getItem("endTime");

    // Jika tidak ada, buat waktu akhir baru (misalnya 5 menit dari sekarang)
    if (!endTime) {
      endTime = new Date().getTime() + 5 * 60 * 1000; // 5 menit
      sessionStorage.setItem("endTime", endTime);
    } else {
      // Jika ada, ubah endTime dari string ke number
      endTime = parseInt(endTime);
    }

    // Fungsi untuk update countdown setiap 1 detik
    const countdown = setInterval(function () {
      let now = new Date().getTime();
      let distance = endTime - now;

      // Hitung menit dan detik yang tersisa
      let minutes = Math.floor((distance % (1000 * 60 * 60)) / (1000 * 60));
      let seconds = Math.floor((distance % (1000 * 60)) / 1000);
      if (minutes == 0) {
        minutes = "";
      } else {
        minutes += "m ";
      }

      // Tampilkan hasil menggunakan jQuery
      $("#countdown-otp-time").html(minutes + seconds + "s ");

      // Jika waktu habis
      if (distance < 0) {
        clearInterval(countdown);
        sessionStorage.removeItem("endTime"); // Hapus waktu akhir dari sessionStorage
        window.location.replace("/sign-in/forget?msg=OTP Expired");
      }
    }, 1000); // Update setiap 1 detik (1000 ms)
  }
};

// update aclock funtion
updateClock = () => {
  // Dapatkan zona waktu secara otomatis berdasarkan lokasi pengguna
  const userTimeZone = moment.tz.guess();
  // Formatkan tanggal dan waktu berdasarkan zona waktu pengguna
  const formattedDate = moment()
    .tz(userTimeZone)
    .format("D MMMM YYYY HH:mm:ss z");

  document.getElementById("clock").textContent = formattedDate;
};

notifAbsen = () => {
  // ambil waktu absensi user
  const [hours_absent, minute_absent] = document
    .getElementById("work_hours")
    .textContent.split(" ")[1]
    .split(".")
    .map(Number);
  const date_absent = document.getElementById("date").textContent.split(":")[1];
  const time_absent = date_absent + " " + hours_absent + ":" + minute_absent;

  // tentukan timezone server
  const options = {
    timeZone: "Asia/Jakarta", // Zona waktu WIB
  };
  // Minta izin untuk menampilkan notifikasi
  if (
    Notification.permission === "default" ||
    Notification.permission === "denied"
  ) {
    Notification.requestPermission();
  }
  // Mengambil waktu server sekarang
  $.ajax({
    url: `https://www.timeapi.io/api/time/current/zone?timeZone=${options.timeZone}`,
    type: "GET",
    headers: {
      Accept: "application/json",
      "Content-Type": "application/json",
    },
    success: function (response) {
      // dapatkan respon waktu sekarang
      convertZone = new Date(response.dateTime);
      // conver waktu user ke format Date
      entry_time = moment(time_absent, "DD MMMM YYYY HH:mm").toDate();
      // ubah jadi detik
      countdownTime = Math.floor((entry_time - convertZone) / 1000);
      // jalankan setiap 1 detik
      const countdown = setInterval(() => {
        countdownTime--;
        console.log(countdownTime);
        console.log(Notification.permission);
        console.log(tepatWaktu)
        console.log(-5>-10)
        console.log('jalan')
        // Jika waktu tersisa 30 menit,sebelum absensi dibuka kirim notifikasi browser
        if (countdownTime == 30 * 60 && Notification.permission === "granted" && tepatWaktu != true) {
          tepatWaktu = true
          new Notification("Absensi Alert!", {
            body: "Waktu tinggal 30 menit, persiapan untuk absensi!",
          });
        }
        // Jika waktu tersisa 5 menit sebelum absensi dibuka, kirim notifikasi browser
        else if (countdownTime >= 5 * 60 && Notification.permission === "granted" && tepatWaktu != true) {
          tepatWaktu = true;
          new Notification("Absensi Alert!", {
            body: "Waktu tinggal 5 menit, persiapan untuk absensi!",
          });
        }
        // Jika waktu tersisa 20 menit setelah absensi dibuka, kirim notifikasi browser
        else if (countdownTime < -20 * 60 && Notification.permission === "granted" && tepatWaktu != false) {
          tepatWaktu = false;
          new Notification("Absensi Alert!", {
            body: "Waktu absensi Habis, Anda memasuki telat!",
          });
          clearInterval(countdown);
        }
        // Jika waktu tersisa 5 menit setelah absensi dibuka, kirim notifikasi browser
        else if (countdownTime >= -5 * 60 && Notification.permission === "granted" && tepatWaktu != true) {
          tepatWaktu = true;
          new Notification("Absensi Alert!", {
            body: "Waktu sudah dalam 5 menit, segera lakukan absensi!",
          });
        }
        // Jika waktu tersisa >5 menit setelah absensi dibuka, kirim notifikasi browser
        else if (countdownTime <= -5 * 60 && Notification.permission === "granted" && tepatWaktu != true) {
          tepatWaktu = true;
          new Notification("Absensi Alert!", {
            body: "Waktu sudah dalam 5 menit, segera lakukan absensi!",
          });
        }
        // Jika waktu habis
        else if (countdownTime == 0 && tepatWaktu != true && Notification.permission === "granted") {
          tepatWaktu = true;
          new Notification("Absensi Alert!", {
            body: "Waktu absensi sudah dibuka, silahkan absensi dalam kurun 20 menit !",
          });
        }
      }, 1000); // Jalankan setiap detik (1000 ms)
    },
  });
};
// trigger submit absen
function submitAbsen(action) {
  if (action == "hadir" && tepatWaktu == true) {
    $("#status_hadir").val(1);
  } else if (action == "hadir" && tepatWaktu == false) {
    $("#status_hadir").val(2);
  } else {
    $("#status_hadir").val(0);
  }

  $.ajax({
    type: "post",
    url: "/dashboard/absen",
    data: {
      user_id: $("#user_id").val(),
      status_hadir: $("#status_hadir").val(),
    },
    headers: {
      "X-CSRF-Token": $("#csrf_token1").val(),
    },
    dataType: "json",
    success: function (response) {
      if (response.result == "success") {
        Swal.fire({
          icon: "success",
          title: "Absen",
          text: "Anda sudah melakukan absen hari ini, terimakasih",
          timer: 3000,
          willClose: () => {
            window.location.replace(response["redirect"]);
          },
        });
      } else {
        window.location.replace(
          response["redirect"] + "?msg=" + response["msg"]
        );
      }
    },
  });
}
