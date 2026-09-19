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
function switchView(view) {
  document.querySelectorAll(".nav-item").forEach((n) => n.classList.remove("active"));
  document.querySelectorAll(".view").forEach((v) => v.classList.remove("active"));
  const nav = document.querySelector(`.nav-item[data-view="${view}"]`);
  if (nav) nav.classList.add("active");
  const sec = document.getElementById("view-" + view);
  if (sec) sec.classList.add("active");
  if (view === "account") loadBalances();
  if (view === "orders") loadOpenOrders();
}

document.querySelectorAll(".nav-item").forEach((item) => {
  item.addEventListener("click", () => switchView(item.dataset.view));
});
// Header'daki "Nasıl Kullanılır?" linki
document.querySelectorAll(".guide-link").forEach((l) =>
  l.addEventListener("click", () => switchView("guide")));

// ---- Bağlamsal Info Düğmeleri (GLOBAL_STANDARDS 2.3) ----
const INFO_TEXT = {
  portfolio: { t: "Portföy Özeti", d: "Trade + Main hesaplarınızdaki tüm varlıkların anlık USDT karşılığı toplamıdır. Paper modda sanal bakiyeyi gösterir." },
  mode: { t: "Çalışma Modu", d: "🧪 SIMULATION: $10.000 sanal USDT ile sıfır riskli test. ⚡ LIVE: gerçek KuCoin hesabınızdan gerçek emir. Varsayılan güvenli moddur." },
  panic: { t: "Panic Stop", d: "Acil durum butonu: tek tıkla tüm açık emirleri iptal eder ve botu durdurur. Bot durunca yeni emir kabul edilmez." },
  score: { t: "Bileşik Skor & Sinyal", d: "Trend/momentum/güç/hacim/yapı katmanlarından 0-100 boğa & ayı puanı. ≥80 güçlü, 60-80 normal sinyal, altı nötr." },
  mtf: { t: "Multi-Timeframe (MTF)", d: "4H rejim → 1H kurulum → 15m tetikleyici hiyerarşisi. Üç zaman dilimi uyumlu olmadan işlem önerilmez." },
  smc: { t: "Smart Money Concepts", d: "BOS (yapı kırılımı), CHoCH (karakter değişimi), FVG (fiyat boşluğu) gibi kurumsal fiyat hareketi sinyalleri." },
  orders: { t: "Emir Verme", d: "Market: anlık fiyattan. Limit: hedef fiyattan. Bakiyenizden fazla emir pre-trade risk kontrolüyle engellenir." },
};

const popover = document.getElementById("info-popover");
document.addEventListener("click", (e) => {
  const btn = e.target.closest(".info-btn");
  if (btn) {
    const info = INFO_TEXT[btn.dataset.info];
    if (!info) return;
    popover.innerHTML = `<div class="info-title">${info.t}</div><div>${info.d}</div>`;
    popover.hidden = false;
    const r = btn.getBoundingClientRect();
    popover.style.top = (r.bottom + 8) + "px";
    popover.style.left = Math.max(8, Math.min(r.left, window.innerWidth - 320)) + "px";
    e.stopPropagation();
  } else if (!e.target.closest("#info-popover")) {
    popover.hidden = true;
  }
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

// ---- SVG Candlestick Grafik ----
async function loadChart(symbol = "BTC/USDT", timeframe = "1h") {
  const res = await apiGet(`/market/candles?symbol=${encodeURIComponent(symbol)}&timeframe=${timeframe}&limit=60`);
  const wrap = document.getElementById("candle-chart");
  if (!res.success || !res.data.candles.length) {
    wrap.textContent = "Grafik verisi alınamadı.";
    return;
  }
  const candles = res.data.candles;
  const W = Math.max(600, candles.length * 10);
  const H = 260, pad = 30;
  const highs = candles.map((c) => c.high);
  const lows = candles.map((c) => c.low);
  const maxP = Math.max(...highs), minP = Math.min(...lows);
  const range = maxP - minP || 1;
  const cw = (W - 2 * pad) / candles.length;
  const y = (p) => pad + (H - 2 * pad) * (1 - (p - minP) / range);

  let svg = `<svg viewBox="0 0 ${W} ${H}" preserveAspectRatio="none">`;
  svg += `<line class="chart-axis" x1="${pad}" y1="${H - pad}" x2="${W - pad}" y2="${H - pad}"/>`;
  svg += `<text class="chart-label" x="2" y="${y(maxP)}">${maxP.toFixed(2)}</text>`;
  svg += `<text class="chart-label" x="2" y="${y(minP)}">${minP.toFixed(2)}</text>`;

  candles.forEach((c, i) => {
    const x = pad + i * cw + cw / 2;
    const cls = c.close >= c.open ? "candle-up" : "candle-down";
    svg += `<line class="${cls}" x1="${x}" y1="${y(c.high)}" x2="${x}" y2="${y(c.low)}" stroke-width="1"/>`;
    const bodyTop = y(Math.max(c.open, c.close));
    const bodyH = Math.max(1, Math.abs(y(c.open) - y(c.close)));
    svg += `<rect class="${cls}" x="${x - cw * 0.3}" y="${bodyTop}" width="${cw * 0.6}" height="${bodyH}"/>`;
  });
  svg += `</svg>`;
  wrap.innerHTML = svg;
  document.getElementById("chart-symbol").textContent = symbol;
}

// ---- WebSocket canlı akış (polling'e fallback'li) ----
let ws = null;
function connectWebSocket() {
  try {
    const proto = location.protocol === "https:" ? "wss" : "ws";
    ws = new WebSocket(`${proto}://${location.host}/ws/live?symbol=BTC/USDT`);

    ws.onmessage = (evt) => {
      const msg = JSON.parse(evt.data);
      stopPolling();  // WS çalışıyorsa polling'e gerek yok
      if (msg.ticker) {
        const d = msg.ticker;
        const chg = d.change_percentage_24h ?? 0;
        const cls = chg >= 0 ? "up" : "down";
        document.getElementById("dash-ticker").innerHTML = `
          <span>Fiyat: <b>${d.last_price}</b></span>
          <span>24s Yüksek: ${d.high_24h}</span>
          <span>24s Düşük: ${d.low_24h}</span>
          <span class="${cls}">Değişim: ${chg}%</span>
          <span>Hacim: ${Number(d.volume_24h).toFixed(2)}</span>`;
      }
      if (msg.summary) {
        document.getElementById("dash-total").textContent = fmtUsdt(msg.summary.total_portfolio_usdt);
        document.getElementById("dash-free").textContent = fmtUsdt(msg.summary.free_usdt);
        document.getElementById("header-portfolio-usdt").textContent = fmtUsdt(msg.summary.total_portfolio_usdt);
      }
      if (msg.mode) {
        const badge = document.getElementById("mode-badge");
        const live = msg.mode === "live";
        badge.textContent = live ? "⚡ LIVE KUCOIN" : "🧪 SIMULATION";
        badge.className = "mode-badge " + (live ? "live" : "sim");
      }
      document.getElementById("footer-conn").textContent = "🟢 Bağlantı: CANLI (WS)";
      setFooterLog("Canlı veri güncellendi (WebSocket).");
    };

    ws.onclose = () => {
      document.getElementById("footer-conn").textContent = "🟡 WS kapandı — polling'e geçildi";
      startPolling();  // fallback
      setTimeout(connectWebSocket, 5000);  // GLOBAL_STANDARDS 4.1: yeniden bağlan
    };
    ws.onerror = () => { try { ws.close(); } catch (e) {} };
  } catch (e) {
    startPolling();
  }
}

// ---- Başlangıç + periyodik yenileme (WS yoksa fallback) ----
let pollTimer = null;
async function refreshDashboard() {
  await loadStatus();
  await loadSummary();
  await loadTicker();
}
function startPolling() {
  if (pollTimer) return;
  refreshDashboard();
  pollTimer = setInterval(refreshDashboard, 15000);
}
function stopPolling() {
  if (pollTimer) { clearInterval(pollTimer); pollTimer = null; }
}

// İlk yükleme
loadStatus();
loadSummary();
loadTicker();
loadChart();
setInterval(() => loadChart(), 60000);  // grafik 60sn'de bir yenilenir
connectWebSocket();
