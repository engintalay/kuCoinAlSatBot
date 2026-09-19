/* KuCoin Al-Sat Botu — Dashboard İstemci Mantığı */
"use strict";

const API = "/api/v1";

// ---- Yardımcılar ----
async function apiGet(path) {
  const r = await fetch(API + path);
  return r.json();
}
async function apiSend(path, method, body) {
  const r = await fetch(API + path, {
    method,
    headers: { "Content-Type": "application/json" },
    body: body ? JSON.stringify(body) : undefined,
  });
  return r.json();
}

function fmtUsdt(v) {
  if (v === null || v === undefined || isNaN(v)) return "-- USDT";
  return Number(v).toLocaleString("en-US", { minimumFractionDigits: 2, maximumFractionDigits: 2 }) + " USDT";
}

function toast(message, type = "success") {
  const c = document.getElementById("toast-container");
  const el = document.createElement("div");
  el.className = `toast ${type}`;
  el.textContent = message;
  c.appendChild(el);
  setTimeout(() => el.remove(), 4000);
  setFooterLog(message);
}

function setFooterLog(msg) {
  document.getElementById("footer-log").textContent = msg;
  document.getElementById("footer-updated").textContent =
    "Son Güncelleme: " + new Date().toLocaleTimeString("tr-TR");
}

// ---- Görünüm geçişleri ----
document.querySelectorAll(".nav-item").forEach((item) => {
  item.addEventListener("click", () => {
    document.querySelectorAll(".nav-item").forEach((n) => n.classList.remove("active"));
    document.querySelectorAll(".view").forEach((v) => v.classList.remove("active"));
    item.classList.add("active");
    const view = item.dataset.view;
    document.getElementById("view-" + view).classList.add("active");
    if (view === "account") loadBalances();
    if (view === "orders") loadOpenOrders();
  });
});

// ---- Bağlantı & durum ----
async function loadStatus() {
  try {
    const res = await apiGet("/account/status");
    const conn = document.getElementById("dash-conn");
    const fConn = document.getElementById("footer-conn");
    const fLat = document.getElementById("footer-latency");
    if (res.success) {
      conn.textContent = "🟢 Bağlı";
      conn.className = "card-value signal-bullish";
      fConn.textContent = "🟢 Bağlantı: CANLI";
      fLat.textContent = "Gecikme: " + (res.data.latency_ms ?? "--") + " ms";
      if (res.data.warning) toast(res.data.warning, "warning");
    } else {
      conn.textContent = "🔴 Hata";
      conn.className = "card-value signal-bearish";
      fConn.textContent = "🔴 Bağlantı: KOPUK";
    }
  } catch (e) {
    document.getElementById("footer-conn").textContent = "🔴 Bağlantı: HATA";
  }
}

// ---- Portföy özeti ----
async function loadSummary() {
  const res = await apiGet("/account/summary");
  if (res.success) {
    document.getElementById("dash-total").textContent = fmtUsdt(res.data.total_portfolio_usdt);
    document.getElementById("dash-free").textContent = fmtUsdt(res.data.free_usdt);
    document.getElementById("header-portfolio-usdt").textContent = fmtUsdt(res.data.total_portfolio_usdt);
  }
}

// ---- Ticker ----
async function loadTicker(symbol = "BTC/USDT") {
  const res = await apiGet("/market/ticker?symbol=" + encodeURIComponent(symbol));
  const el = document.getElementById("dash-ticker");
  if (res.success) {
    const d = res.data;
    const chg = d.change_percentage_24h ?? 0;
    const cls = chg >= 0 ? "up" : "down";
    el.innerHTML = `
      <span>Fiyat: <b>${d.last_price}</b></span>
      <span>24s Yüksek: ${d.high_24h}</span>
      <span>24s Düşük: ${d.low_24h}</span>
      <span class="${cls}">Değişim: ${chg}%</span>
      <span>Hacim: ${Number(d.volume_24h).toFixed(2)}</span>`;
  } else {
    el.textContent = "Ticker alınamadı.";
  }
}

// ---- Bakiyeler ----
async function loadBalances() {
  const res = await apiGet("/account/balances");
  const tbody = document.querySelector("#balances-table tbody");
  if (res.success && res.data.balances.length) {
    tbody.innerHTML = res.data.balances.map((a) => `
      <tr>
        <td>${a.symbol}</td><td>${a.free}</td><td>${a.used}</td><td>${a.total}</td>
        <td>${a.price_usdt}</td><td>${a.usdt_value}</td><td>${a.portfolio_share_percent}%</td>
      </tr>`).join("");
  } else {
    tbody.innerHTML = `<tr><td colspan="7">Varlık bulunamadı.</td></tr>`;
  }
}

// ---- Analiz ----
document.getElementById("analysis-run").addEventListener("click", loadAnalysis);
async function loadAnalysis() {
  const symbol = document.getElementById("analysis-symbol").value;
  const tf = document.getElementById("analysis-tf").value;
  setFooterLog("Analiz çalıştırılıyor...");
  const res = await apiGet(`/market/analysis/score?symbol=${encodeURIComponent(symbol)}&timeframe=${tf}`);
  if (res.success) {
    const s = res.data.score;
    const sig = document.getElementById("analysis-signal");
    sig.textContent = s.signal;
    sig.className = "card-value signal-" + s.signal.toLowerCase().replace(/_/g, "-");
    document.getElementById("analysis-score").textContent = `${s.bull_score} / ${s.bear_score}`;
    document.getElementById("analysis-reasons").innerHTML =
      (s.reasons || []).map((r) => `<li>${r}</li>`).join("") || "<li>Gerekçe yok</li>";
    document.getElementById("analysis-warnings").innerHTML =
      (s.warnings || []).map((w) => `<li>${w}</li>`).join("") || "<li>Uyarı yok</li>";
    toast(`Analiz: ${s.signal}`, "success");
  } else {
    toast("Analiz başarısız: " + (res.error || ""), "error");
  }
}

// ---- Emirler ----
document.getElementById("order-submit").addEventListener("click", async () => {
  const body = {
    symbol: document.getElementById("order-symbol").value,
    side: document.getElementById("order-side").value,
    order_type: document.getElementById("order-type").value,
    amount: parseFloat(document.getElementById("order-amount").value),
    price: parseFloat(document.getElementById("order-price").value) || null,
  };
  const res = await apiSend("/orders/create", "POST", body);
  if (res.success) {
    toast(`Emir oluşturuldu: ${res.data.status}`, "success");
    loadOpenOrders();
  } else {
    toast("Emir reddedildi: " + (res.error || ""), "error");
  }
});

async function loadOpenOrders() {
  const res = await apiGet("/orders/open");
  const tbody = document.querySelector("#open-orders-table tbody");
  if (res.success && res.data.count) {
    tbody.innerHTML = res.data.orders.map((o) => `
      <tr>
        <td>${o.id}</td><td>${o.symbol}</td><td>${o.side}</td><td>${o.type}</td>
        <td>${o.amount}</td><td>${o.price}</td><td>${o.status}</td>
        <td><button class="btn-mini" data-id="${o.id}">İptal</button></td>
      </tr>`).join("");
    tbody.querySelectorAll(".btn-mini").forEach((b) =>
      b.addEventListener("click", () => cancelOrder(b.dataset.id)));
  } else {
    tbody.innerHTML = `<tr><td colspan="8">Açık emir yok.</td></tr>`;
  }
}

async function cancelOrder(id) {
  const res = await apiSend(`/orders/${id}`, "DELETE");
  if (res.success) { toast("Emir iptal edildi", "success"); loadOpenOrders(); }
  else toast("İptal başarısız", "error");
}

// ---- Panic Stop ----
document.getElementById("panic-btn").addEventListener("click", async () => {
  if (!confirm("PANIC STOP: Tüm açık emirler iptal edilecek ve bot durdurulacak. Emin misiniz?")) return;
  const res = await apiSend("/orders/panic-stop", "POST");
  if (res.success) {
    toast(`Panic Stop: ${res.data.cancelled_orders} emir iptal edildi, bot durdu.`, "warning");
    loadOpenOrders();
  } else {
    toast("Panic Stop başarısız", "error");
  }
});

// ---- Başlangıç + periyodik yenileme ----
async function refreshDashboard() {
  await loadStatus();
  await loadSummary();
  await loadTicker();
}
refreshDashboard();
setInterval(refreshDashboard, 15000);  // 15 saniyede bir
