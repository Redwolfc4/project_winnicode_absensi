$('#riwayat #triggerEditModal').on('click', function () {
    button_id =  $(this).attr('data-bs-target')
    // imput lama
    status_hadir_lama = $(`#riwayat ${button_id} #status_hadir`).val()
    console.log(status_hadir_lama)
    
    
    // Event listener untuk semua input
    $(`#riwayat ${button_id} #status_hadir`).on("input", checkChanges);

    
    // Fungsi untuk mengecek apakah ada perubahan
    function checkChanges() {
        // imput baru
        status_hadir_baru = $(`#riwayat ${button_id} #status_hadir`).val();
        
        // Jika salah satu input berubah, tombol akan diaktifkan
        if (
          status_hadir_baru !== status_hadir_lama 
        ) {
          $(`#riwayat ${button_id} #submit`).prop("disabled", false);
        } else {
          $(`#riwayat ${button_id} #submit`).prop("disabled", true);
        }
    }
  })