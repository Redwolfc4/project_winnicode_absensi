// remove cookie
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

// update aclock funtion
function updateClock() {
  // Dapatkan zona waktu secara otomatis berdasarkan lokasi pengguna
  const userTimeZone = moment.tz.guess();
  
  // Formatkan tanggal dan waktu berdasarkan zona waktu pengguna
  const formattedDate = moment().tz(userTimeZone).format('D MMMM YYYY HH:mm:ss z');
  
  document.getElementById('clock').textContent = formattedDate;
}

$(document).ready(function() {
  // Update the clock every second
  updateClock();
  setInterval(updateClock, 1000);
})