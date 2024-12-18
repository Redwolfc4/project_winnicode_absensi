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

// remove cookie
function removeCookies(event) {
  event.preventDefault();
  // make loading
  $("section#profile").fadeOut(200, function () {
    $("section#loading").fadeIn(500, function () {
      $.ajax({
        type: "GET",
        url: "/api/auth/logout",
        dataType: "json",
        success: function (response) {
          console.log(response);
          //dapat respose
          $("section#loading").fadeOut(500);
          if (response.status == "success") {
            Swal.fire({
              icon: `${response.status}`,
              title: "Logout!",
              text: `${response.msg}`,
              timer: 3000,
            }).then(() => {
              window.location.replace(response.redirect), 200;
            });
          }
        },
        error: function (xhr, status, error) {
          // Tindakan jika gagal
          console.log(xhr, status, error);
          $("section#loading").fadeOut(500);
          if (xhr.responseJSON.redirect) {
            window.location.replace(xhr.responseJSON.redirect), 500;
          } else {
            window.location.replace("/myProfiles?msg=jaringan Error"), 500;
          }
        },
      });
    });
  });
}

// update aclock funtion
function updateClock() {
  // Dapatkan zona waktu secara otomatis berdasarkan lokasi pengguna
  const userTimeZone = moment.tz.guess();

  // Formatkan tanggal dan waktu berdasarkan zona waktu pengguna
  const formattedDate = moment()
    .tz(userTimeZone)
    .format("D MMMM YYYY HH:mm:ss z");

  document.getElementById("clock").textContent = formattedDate;
}

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
        $(this).prev().fadeIn(400);
      });
    });
  }
  // Update the clock every second
  updateClock();
  setInterval(updateClock, 1000);
});
