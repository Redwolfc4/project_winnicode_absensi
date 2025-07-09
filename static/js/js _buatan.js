// Jika waktu tersisa 20 menit setelah absensi dibuka, kirim notifikasi browser
if (
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
// Jika waktu tersisa 15 menit setelah absensi dibuka, kirim notifikasi browser
else if (
  countdownTime <= -15 * 60 &&
  Notification.permission === "granted" &&
  tepatWaktu != true
) {
  tepatWaktu = true;
  new Notification("Absensi Alert!", {
    body: "Waktu absensi sudah memasuki 15 menitan, segera lakukan absensi!",
  });
}
// Jika waktu tersisa 10 menit setelah absensi dibuka, kirim notifikasi browser
else if (
  countdownTime <= -10 * 60 &&
  Notification.permission === "granted" &&
  tepatWaktu != false
) {
  tepatWaktu = true;
  new Notification("Absensi Alert!", {
    body: "Waktu absensi sudah memasuki 10 menitan, segera lakukan absensi!",
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
// Jika waktu tersisa 5 menit sebelum absensi dibuka, kirim notifikasi browser
else if (
  countdownTime <= 5 * 60 &&
  Notification.permission === "granted" &&
  tepatWaktu != true
) {
  new Notification("Absensi Alert!", {
    body: "Waktu tinggal 5 menit, persiapan untuk absensi!",
  });
}
// Jika waktu tersisa 20 menit,sebelum absensi dibuka kirim notifikasi browser
else if (
  countdownTime <= 20 * 60 &&
  Notification.permission === "granted" &&
  tepatWaktu != true
) {
  new Notification("Absensi Alert!", {
    body: "Waktu tinggal 20 menit, persiapan untuk absensi!",
  });
}
// Jika waktu tersisa 30 menit,sebelum absensi dibuka kirim notifikasi browser
else if (
  countdownTime == 30 * 60 &&
  Notification.permission === "granted" &&
  tepatWaktu != true
) {
  new Notification("Absensi Alert!", {
    body: "Waktu tinggal 30 menit, persiapan untuk absensi!",
  });
}
