$("#riwayat #triggerEditModal").on("click", function () {
  button_id = $(this).attr("data-bs-target");
  // imput lama
  status_hadir_lama = $(`#riwayat ${button_id} #status_hadir`).val();
  console.log(status_hadir_lama);

  // Event listener untuk semua input
  $(`#riwayat ${button_id} #status_hadir`).on("input", checkChanges);

  // Fungsi untuk mengecek apakah ada perubahan
  function checkChanges() {
    // imput baru
    status_hadir_baru = $(`#riwayat ${button_id} #status_hadir`).val();

    // Jika salah satu input berubah, tombol akan diaktifkan
    if (status_hadir_baru !== status_hadir_lama) {
      $(`#riwayat ${button_id} #submit`).prop("disabled", false);
    } else {
      $(`#riwayat ${button_id} #submit`).prop("disabled", true);
    }
  }
});

$("#kelolaAdmin #triggerEditModal").on("click", function () {
  button_id = $(this).attr("data-bs-target");
  // imput lama
  nama_lama = $(`#kelolaAdmin ${button_id} #nama`).val();
  departement_lama = $(`#kelolaAdmin ${button_id} #departement`).val();
  jobs_lama = $(`#kelolaAdmin ${button_id} #jobs`).val();

  // Event listener untuk semua input
  $(`#kelolaAdmin ${button_id} #nama`).on("input", checkChanges);
  $(`#kelolaAdmin ${button_id} #departement`).on("input", checkChanges);
  $(`#kelolaAdmin ${button_id} #jobs`).on("input", checkChanges);

  // Fungsi untuk mengecek apakah ada perubahan
  function checkChanges() {
    // imput baru
    nama_baru = $(`#kelolaAdmin ${button_id} #nama`).val();
    departement_baru = $(`#kelolaAdmin ${button_id} #departement`).val();
    jobs_baru = $(`#kelolaAdmin ${button_id} #jobs`).val();

    // Jika salah satu input berubah, tombol akan diaktifkan
    if (
      nama_baru !== nama_lama||
      departement_baru !== departement_lama||
      jobs_baru !== jobs_lama
    ) {
      $(`#kelolaAdmin ${button_id} #submit`).prop("disabled", false);
    } else {
      $(`#kelolaAdmin ${button_id} #submit`).prop("disabled", true);
    }
  }
});

// add modal 
$('#addAccountAdmin #triggerAddModal').on('click', function () {
  button_id =  $(this).attr('data-bs-target')
  // imput lama
  departement_lama = $(`${button_id} #departement`).val();
  nama_lama = $(`${button_id} #nama`).val();
  jobs_lama = $(`${button_id} #jobs`).val();
  password_lama = $(`${button_id} #password`).val();
  password2_lama = $(`${button_id} #password2`).val();
  // Event listener untuk semua input
  $(`${button_id} #departement`).on("input", checkChanges);
  $(`${button_id} #jobs`).on("input", checkChanges);
  $(`${button_id} #password`).on("input", checkChanges);
  $(`${button_id} #password2`).on("input", checkChanges);
  $(`${button_id} #nama`).on("input", checkChanges);

  
  // Fungsi untuk mengecek apakah ada perubahan
  function checkChanges() {
      // imput baru
      departement_baru = $(`${button_id} #departement`).val();
      nama_baru = $(`${button_id} #nama`).val();
      jobs_baru = $(`${button_id} #jobs`).val();
      password_baru = $(`${button_id} #password`).val();
      password2_baru = $(`${button_id} #password2`).val();
      // Jika salah satu input berubah, tombol akan diaktifkan
      if (
        departement_baru !== departement_lama ||
        jobs_baru !== jobs_lama ||
        password_baru !== password_lama ||
        password2_baru !== password2_lama ||
        nama_baru !== nama_lama 
      ) {
        $(`${button_id} #submit`).prop("disabled", false);
      } else {
        $(`${button_id} #submit`).prop("disabled", true);
      }
  }
})
// end
