paceOptions = {
  ajax: true,
  document: true,
  eventLag: true,
};

$(window).ready(function () {
  // tampilkan signin setelah load
  if (typeof Pace !== "undefined") {
    Pace.on("done", function () {
      $("section#loading").fadeOut(400, function () {
        $(this).prev().fadeIn(500);
      });
    });
  }

  // untuk button dark mode
  const html = $("html");
  const checkbox = document.querySelector("#darkModeSwitch #hide-checkbox");

  if (localStorage.getItem("darkMode") === "true") {
    // darkmode
    checkbox.checked = false;
  } else if (localStorage.getItem("darkMode") === "false") {
    // non darkmode
    checkbox.checked = true;
  } else {
    // Set default ke cerah
    checkbox.checked = true;
  }

  // === Toggle Dark Mode dan simpan status ke localStorage ===
  $("#darkModeSwitch #hide-checkbox").on("click", function () {
    if (html.attr("data-bs-theme") === "dark") {
      html.removeAttr("data-bs-theme"); // Hapus atribut
      localStorage.setItem("darkMode", "false"); // Simpan status
    } else {
      html.attr("data-bs-theme", "dark"); // Tambah atribut
      localStorage.setItem("darkMode", "true"); // Simpan status
    }
  });
  // end

  // Minta izin untuk menampilkan notifikasi
  if (
    Notification.permission === "default" ||
    Notification.permission === "denied"
  ) {
    Notification.requestPermission();
  }

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
    $(this).fadeOut(200, function () {
      $("section#loading").fadeIn(500);
    });
    email_receive = $("#email").val().trim();
    password_receive = $("#password").val().trim();
    jobs = $("#jobs").val().trim();

    if (email_receive === "" && password_receive === "" && jobs === "None") {
      window.location.replace("/sign-in?msg=Form masih kosong"), 500;
    } else {
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
            $("section#loading").fadeOut(500);

            Swal.fire({
              icon: "success",
              title: "Login Success",
              text: response["msg"],
              timer: 1500,
              willClose: () => {
                window.location.replace(response["redirect"]), 200;
              },
            });
          }
        },
        error: function (xhr, status, error) {
          // Tindakan jika gagal
          $("section#loading").fadeOut(300);
          console.log(xhr, status, error);
          if (xhr.responseJSON.redirect) {
            window.location.replace(xhr.responseJSON.redirect), 500;
          } else {
            window.location.replace("/sign-in?msg=jaringan Error"), 500;
          }
        },
      });
    }
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

  console.log(Notification.permission);

  // countdown otp timer
  countdownOtp();

  // clock
  updateClock();
  // Update the clock every second
  setInterval(updateClock, 1000);

  // notifikasi
  // Cek apakah notifikasi sudah pernah ditampilkan
  if (
    !(
      $(".absensi_kehadiran #status_hadir").hasClass("btn-warning") ||
      $(".absensi_kehadiran #status_hadir").hasClass("btn-success")
    )
  ) {
    localStorage.removeItem("notificationShown");
  }
  const notificationShown = localStorage.getItem("notificationShown");
  // Jika notifikasi belum pernah ditampilkan
  if (!notificationShown) {
    // Tampilkan notifikasi (gunakan fungsi notifikasi di sini)
    notifAbsen();

    // Set nilai di Local Storage agar notifikasi tidak tampil lagi
    localStorage.setItem("notificationShown", "true");
  }
});

let tepatWaktu = null;

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
  // const userTimeZone = moment.tz.guess();
  const userTimeZone = "Asia/Jakarta";
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
        // Jika waktu tersisa 30 menit,sebelum absensi dibuka kirim notifikasi browser
        if (
          countdownTime == 30 * 60 &&
          Notification.permission === "granted" &&
          tepatWaktu != true
        ) {
          new Notification("Absensi Alert!", {
            body: "Waktu tinggal 30 menit, persiapan untuk absensi!",
          });
        }
        // Jika waktu tersisa 5 menit sebelum absensi dibuka, kirim notifikasi browser
        else if (
          countdownTime >= 5 * 60 &&
          Notification.permission === "granted" &&
          tepatWaktu != true
        ) {
          new Notification("Absensi Alert!", {
            body: "Waktu tinggal 5 menit, persiapan untuk absensi!",
          });
        }
        // Jika waktu tersisa 20 menit setelah absensi dibuka, kirim notifikasi browser
        else if (
          countdownTime < -20 * 60 &&
          Notification.permission === "granted" &&
          tepatWaktu != false
        ) {
          tepatWaktu = false;
          new Notification("Absensi Alert!", {
            body: "Waktu absensi Habis, Anda memasuki telat!",
          });
          clearInterval(countdown);
        }
        // Jika waktu tersisa 10 menit setelah absensi dibuka, kirim notifikasi browser
        else if (
          countdownTime >= -10 * 60 &&
          Notification.permission === "granted" &&
          tepatWaktu != false
        ) {
          tepatWaktu = true;
          new Notification("Absensi Alert!", {
            body: "Waktu absensi sudah memasuki 10 menitan, segera lakukan absensi!",
          });
        }
        // Jika waktu tersisa 15 menit setelah absensi dibuka, kirim notifikasi browser
        else if (
          countdownTime >= -15 * 60 &&
          Notification.permission === "granted" &&
          tepatWaktu != true
        ) {
          tepatWaktu = true;
          new Notification("Absensi Alert!", {
            body: "Waktu absensi sudah memasuki 15 menitan, segera lakukan absensi!",
          });
        }
        // Jika waktu tersisa 5 menit setelah absensi dibuka, kirim notifikasi browser
        else if (
          countdownTime >= -5 * 60 &&
          Notification.permission === "granted" &&
          tepatWaktu != true
        ) {
          tepatWaktu = true;
          new Notification("Absensi Alert!", {
            body: "Waktu sudah dalam kurang dari 5 menit, segera lakukan absensi!",
          });
        }
        // Jika waktu tersisa >5 menit setelah absensi dibuka, kirim notifikasi browser
        else if (
          countdownTime <= -5 * 60 &&
          Notification.permission === "granted" &&
          tepatWaktu != true
        ) {
          tepatWaktu = true;
          new Notification("Absensi Alert!", {
            body: "Waktu sudah dalam 5 menit, segera lakukan absensi!",
          });
        }
        // Jika waktu habis
        else if (
          countdownTime == 0 &&
          tepatWaktu != true &&
          Notification.permission === "granted"
        ) {
          tepatWaktu = true;
          new Notification("Absensi Alert!", {
            body: "Waktu absensi sudah dibuka, silahkan absensi dalam kurun 20 menit !",
          });
        }
      }, 1000); // Jalankan setiap detik (1000 ms)
    },
    error: function (xhr, status, error) {
      // Tindakan jika gagal
      console.log(xhr, status, error);
    },
  });
};
// trigger submit absen
function submitAbsen(action, e) {
  e.preventDefault();
  // Ambil parent `section#menu`
  const parentMenu = $(e.target).closest("section#menu");
  let status_hadir;

  if (parentMenu.length < 0) {
    return;
  }
  parentMenu.fadeOut(200, function () {
    $("section#loading").fadeIn(500);
  });

  console.log(tepatWaktu, action);
  if (!tepatWaktu) {
    return;
  }
  if (!action) {
    return;
  }

  if (action == "hadir" && tepatWaktu == true) {
    status_hadir = 1;
  } else if (action == "hadir" && tepatWaktu == false) {
    status_hadir = 2;
  }
  console.log(status_hadir);

  $.ajax({
    type: "post",
    url: "/dashboard/absen",
    data: {
      user_id: $("#user_id").val(),
      status_hadir: status_hadir,
    },
    headers: {
      "X-CSRF-Token": $("#csrf_token1").val(),
    },
    dataType: "json",
    success: function (response) {
      // Tindakan jika berhasil
      $("section#loading").fadeOut(300);
      if (response.result == "success") {
        Swal.fire({
          icon: "success",
          title: "Absen",
          text: "Anda sudah melakukan absen hari ini, terimakasih",
          timer: 3000,
          willClose: () => {
            window.location.replace(response["redirect"]), 200;
          },
        });
      } else {
        window.location.replace(response["redirect"]), 200;
      }
    },
    error: function (xhr, status, error) {
      // Tindakan jika gagal
      $("section#loading").fadeOut(300);
      console.log(xhr, status, error);
      if (xhr.readyState === 0) {
        // Request never sent (network error)
        window.location.replace(
          "/dashboard/magang?msg=Network Error - Request failed to send"
        );
      } else if (xhr.responseJSON) {
        // Server responded with JSON
        if (xhr.responseJSON.redirect) {
          window.location.replace(xhr.responseJSON.redirect);
        } else {
          window.location.replace(
            "/dashboard/magang?msg=Server Error: " +
              (xhr.responseJSON.message || "Unknown error")
          );
        }
      } else {
        // Server responded with non-JSON or empty response
        window.location.replace(
          "/dashboard/magang?msg=Server Error - Invalid response"
        );
      }
    },
  });
}

const manualBook = (data) => {
  $.ajax({
    type: "GET",
    url: `/manual/${data}`,
    xhrFields: {
      responseType: "blob", // Untuk menerima file sebagai Blob
    },
    success: function (response, status, xhr) {
      console.log("otw diberikan");
      console.log(response);
      // Mendapatkan nama file dari header respons
      const disposition = xhr.getResponseHeader("Content-Disposition");
      const fileName = disposition
        ? disposition.split("filename=")[1].replace(/"/g, "")
        : "downloaded_file.pdf";
      console.log(disposition);

      // Membuat Blob URL dan mengunduh file
      const url = window.URL.createObjectURL(response);
      const a = document.createElement("a");
      a.href = url;
      a.download = fileName; // Nama file dari header
      document.body.appendChild(a);
      a.click();
      a.remove();
      console.log(url, a);
    },
    error: function (xhr, status, error) {
      console.log(xhr, status, error);
      if (xhr.responseJSON) {
        window.location.replace(xhr.responseJSON.redirect), xhr.status;
      }
    },
  });
};
