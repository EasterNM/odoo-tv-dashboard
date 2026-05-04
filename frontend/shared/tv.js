// Odoo ส่งเวลาเป็น UTC string ไม่มี timezone suffix
// ต้องแปลง "2026-05-04 07:54:50" → บวก +07:00 ก่อน new Date()
function odooToDate(iso) {
  if (!iso) return null;
  return new Date(iso.replace(" ", "T") + "+00:00");
}

function startClock() {
  function tick() {
    document.getElementById("clock").textContent =
      new Date().toLocaleTimeString("th-TH", {
        hour: "2-digit", minute: "2-digit", second: "2-digit",
        timeZone: "Asia/Bangkok"
      });
  }
  tick();
  setInterval(tick, 1000);
}

const BKK = "Asia/Bangkok";

function isToday(iso) {
  const d = odooToDate(iso);
  if (!d) return false;
  return d.toLocaleDateString("th-TH", {timeZone: BKK}) ===
         new Date().toLocaleDateString("th-TH", {timeZone: BKK});
}

function fmtTime(iso) {
  const d = odooToDate(iso);
  if (!d) return "-";
  const todayStr = new Date().toLocaleDateString("th-TH", {timeZone: BKK});
  if (d.toLocaleDateString("th-TH", {timeZone: BKK}) === todayStr)
    return d.toLocaleTimeString("th-TH", {hour: "2-digit", minute: "2-digit", timeZone: BKK});
  return d.toLocaleString("th-TH", {day: "2-digit", month: "2-digit", hour: "2-digit", minute: "2-digit", timeZone: BKK});
}

function formatDate(iso) {
  const d = odooToDate(iso);
  if (!d) return "-";
  return d.toLocaleString("th-TH", {
    day: "2-digit", month: "2-digit", year: "numeric",
    hour: "2-digit", minute: "2-digit",
    timeZone: BKK,
  });
}
