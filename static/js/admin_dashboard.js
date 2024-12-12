// edit modal
$("#dashboard1 #triggerEditModal").on("click", function () {
  button_id = $(this).attr("data-bs-target");
  // imput lama
  departement_lama = $(`#dashboard1 ${button_id} #departement`).val();
  tempat_lahir_lama = $(`#dashboard1 ${button_id} #tempat_lahir`).val();
  tanggal_lahir_lama = $(`#dashboard1 ${button_id} #tanggal_lahir`).val();
  jobs_lama = $(`#dashboard1 ${button_id} #jobs`).val();
  start_date_lama = $(`#dashboard1 ${button_id} #start_date`).val();
  end_date_lama = $(`#dashboard1 ${button_id} #end_date`).val();
  start_time_lama = $(`#dashboard1 ${button_id} #start_time`).val();
  end_time_lama = $(`#dashboard1 ${button_id} #end_time`).val();
  // Event listener untuk semua input
  $(`#dashboard1 ${button_id} #departement`).on("input", checkChanges);
  $(`#dashboard1 ${button_id} #jobs`).on("input", checkChanges);
  $(`#dashboard1 ${button_id} #start_date`).on("input", checkChanges);
  $(`#dashboard1 ${button_id} #end_date`).on("input", checkChanges);
  $(`#dashboard1 ${button_id} #start_time`).on("input", checkChanges);
  $(`#dashboard1 ${button_id} #end_time`).on("input", checkChanges);
  $(`#dashboard1 ${button_id} #tempat_lahir`).on("input", checkChanges);
  $(`#dashboard1 ${button_id} #tanggal_lahir`).on("input", checkChanges);

  // Fungsi untuk mengecek apakah ada perubahan
  function checkChanges() {
    // imput baru
    departement_baru = $(`#dashboard1 ${button_id} #departement`).val();
    tempat_lahir_baru = $(`#dashboard1 ${button_id} #tempat_lahir`).val();
    tanggal_lahir_baru = $(`#dashboard1 ${button_id} #tanggal_lahir`).val();
    jobs_baru = $(`#dashboard1 ${button_id} #jobs`).val();
    start_date_baru = $(`#dashboard1 ${button_id} #start_date`).val();
    end_date_baru = $(`#dashboard1 ${button_id} #end_date`).val();
    start_time_baru = $(`#dashboard1 ${button_id} #start_time`).val();
    end_time_baru = $(`#dashboard1 ${button_id} #end_time`).val();
    // Jika salah satu input berubah, tombol akan diaktifkan
    if (
      departement_baru !== departement_lama ||
      jobs_baru !== jobs_lama ||
      start_date_baru !== start_date_lama ||
      end_date_baru !== end_date_lama ||
      start_time_baru !== start_time_lama ||
      end_time_baru !== end_time_lama ||
      tempat_lahir_baru !== tempat_lahir_lama ||
      tanggal_lahir_baru !== tanggal_lahir_lama
    ) {
      $(`#dashboard1 ${button_id} #submit`).prop("disabled", false);
    } else {
      $(`#dashboard1 ${button_id} #submit`).prop("disabled", true);
    }
  }
});
// end

table_length = $("#dashboard1 select#dataTable_length");
table_length.on("change", function (e) {
  window.location.replace("/dashboard?length=" + e.target.value);
});

search_karyawan = () => {
  $("#dashboard1 #search").val();
  if ($("#dashboard1 #search").val().trim() == "") {
    window.location.replace("/dashboard");
  } else {
    window.location.replace(
      "/dashboard?search=" + $("#dashboard1 #search").val()
    );
  }
};

// enter generate
$("#dashboard1 #search").on("keypress", function (e) {
  if (e.key == "Enter") {
    search_karyawan();
  }
});

// hover generate

button = $("#dashboard1 .fa-download").parent();
button.hover(
  function () {
    $(this).children("i,span").addClass("fa-beat-fade");
  },
  function () {
    // out
    $(this).children("i,span").removeClass("fa-beat-fade");
  }
);
