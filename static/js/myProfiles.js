// remove cookie
function removeCookies(event){
  event.preventDefault();
  // make loading
  $('section#profile').fadeOut(200,function(){
    $('section#loading').fadeIn(500, function(){
      $.ajax({
        type: "GET",
        url: "/api/auth/logout",
        dataType: "json",
        success: function (response) {
          console.log(response);
          //dapat respose
          $('section#loading').fadeOut(500);
          if (response.status == "success") {
            Swal.fire({
              icon: `${response.status}`,
              title: "Logout!",
              text: `${response.msg}`,
              timer: 3000
            }).then(()=>{
              window.location.replace(response.redirect),200;
            })
          }
          
        },
        error: function(xhr,status,error){
          // Tindakan jika gagal
          console.log(xhr,status,error);
          $('section#loading').fadeOut(500);
          if (xhr.responseJSON.redirect){
            window.location.replace(xhr.responseJSON.redirect),500
          } else {
            window.location.replace("/myProfiles?msg=jaringan Error"),500
          }
        }
      });
    });
  })
}

// update aclock funtion
function updateClock() {
  // Dapatkan zona waktu secara otomatis berdasarkan lokasi pengguna
  const userTimeZone = moment.tz.guess();
  
  // Formatkan tanggal dan waktu berdasarkan zona waktu pengguna
  const formattedDate = moment().tz(userTimeZone).format('D MMMM YYYY HH:mm:ss z');
  
  document.getElementById('clock').textContent = formattedDate;
}

paceOptions = {
  ajax: true,
  document: true,
  eventLag: true,
};

$(window).ready(function() {
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
})