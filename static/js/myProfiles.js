nama_lama = $("#profile form #nama").val();
nik_lama = $("#profile form #nik").val();
tempat_lahir_lama = $("#profile form #tempat_lahir").val();
tanggal_lahir_lama = $("#profile form #tanggal_lahir").val();
gambar_lama = $("#profile form #profile-pic").val();

// Fungsi untuk mengecek apakah ada perubahan
function checkChanges() {
  const nama_baru = $("#profile form #nama").val();
  const nik_baru = $("#profile form #nik").val();
  const tempat_lahir_baru = $("#profile form #tempat_lahir").val();
  const tanggal_lahir_baru = $("#profile form #tanggal_lahir").val();
  const gambar_baru = $("#profile form #profile-pic").val();

  // Jika salah satu input berubah, tombol akan diaktifkan
  if (
    nama_baru !== nama_lama ||
    nik_baru !== nik_lama ||
    tempat_lahir_baru !== tempat_lahir_lama ||
    tanggal_lahir_baru !== tanggal_lahir_lama ||gambar_lama !== gambar_baru
  ) {
    $("#profile form #submit").prop("disabled", false);
    $("#profile form #reset").prop("disabled", false);
  } else {
    $("#profile form #submit").prop("disabled", true);
    $("#profile form #reset").prop("disabled", true);
  }
}

// Event listener untuk semua input
$("#profile form #nama").on("input", checkChanges);
$("#profile form #nik").on("input", checkChanges);
$("#profile form #tempat_lahir").on("input", checkChanges);
$("#profile form #tanggal_lahir").on("input", checkChanges);
$("#profile form #profile-pic").on("input", checkChanges);

// reset
$("#profile form #reset").click(function () {
  window.location.reload()
});

// preview gambar sebelum upload
$('#profile form #profile-pic').on('change', function() {
  const file = this.files[0];
  if (file) {
    const reader = new FileReader();
    reader.onload = function(e) {
      $('#profile form #profile-pic-preview').attr('src', e.target.result);
    }
    reader.readAsDataURL(file);
  }
});

function removeCookies(event){
  event.preventDefault();

  $.ajax({
    type: "GET",
    url: "/api/auth/logout",
    dataType: "json",
    success: function (response) {
      console.log(response);
      if (response.status == "success") {
        Swal.fire({
          icon: `${response.status}`,
          title: "Logout!",
          text: `${response.msg}`,
          timer: 3000
        }).then(()=>{
          window.location.replace(response.redirect);
        })
      }
      
    }
  });
}