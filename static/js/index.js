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
          // $.cookie("token_key", response.token_key, { expires: 1, path: "/" });
          // $.cookie("csrf_token", response["csrf_token"], {
          //   expires: 1,
          //   path: "/",
          // });
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
});

// trigger submit absen
function submitAbsen(action) {
  if (action == "hadir") {
    $("#status_hadir").val(1);
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
      "X-CSRF-Token": $("#csrf_token").val(),
    },
    dataType: "json",
    success: function (response) {
      console.log(response);
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

$(document).ready(function () {
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
});
