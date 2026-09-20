/* KuCoin Al-Sat Botu — Dashboard İstemci Mantığı */
"use strict";

const API = "/api/v1";
let activeSymbol = "BTC/USDT";

// ---- Yardımcılar ----
async function apiGet(path) {
  try {
    const r = await fetch(API + path);
    if (!r.ok) {
      let msg = `HTTP ${r.status}`;
      try { const j = await r.json(); if (j && j.error) msg = j.error; } catch (_) {}
      return { success: false, data: {}, error: msg, timestamp: Date.now() };
    }
    return await r.json();
  } catch (e) {
    return { success: false, data: {}, error: String(e && e.message || e), timestamp: Date.now() };
  }
}
async function apiSend(path, method, body) {
  try {
    const r = await fetch(API + path, {
      method,
      headers: { "Content-Type": "application/json" },
      body: body ? JSON.stringify(body) : undefined,
    });
    if (!r.ok) {
      let msg = `HTTP ${r.status}`;
      try { const j = await r.json(); if (j && j.error) msg = j.error; } catch (_) {}
      return { success: false, data: {}, error: msg, timestamp: Date.now() };
    }
    return await r.json();
  } catch (e) {
    return { success: false, data: {}, error: String(e && e.message || e), timestamp: Date.now() };
  }
}

function fmtUsdt(v) {
  if (v === null || v === undefined || isNaN(v)) return "-- USDT";
  return Number(v).toLocaleString("en-US", { minimumFractionDigits: 2, maximumFractionDigits: 2 }) + " USDT";
}

function escapeHtml(s) {
  if (s === null || s === undefined) return "";
  return String(s)
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#039;");
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

let systemLogs = [];
function setFooterLog(msg) {
  document.getElementById("footer-log").textContent = msg;
  const timeStr = new Date().toLocaleTimeString("tr-TR");
  document.getElementById("footer-updated").textContent =
    "Son Güncelleme: " + timeStr;
  systemLogs.push(`[${timeStr}] ${msg}`);
  if (systemLogs.length > 50) systemLogs.shift();
  const logBox = document.getElementById("diagnostics-log-box");
  if (logBox) {
    logBox.textContent = systemLogs.join("\n");
    logBox.scrollTop = logBox.scrollHeight;
  }
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
  if (view === "settings") loadSettings();
  if (view === "analysis") loadAnalysis();
  if (view === "issues") { loadIssues(); loadDiagnostics(); }
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
  bracket: { t: "Akıllı Paket Emir", d: "Analiz motorunun ATR/seviye hesabından otomatik Giriş + TP1 (%50) + TP2 (%50) + Stop-Loss üretir. Sadece USDT tutarı girin, tek tıkla tüm paket iletilir." },
  regime: { t: "Piyasa Geneli Rejim", d: "BTC Dominance, toplam piyasa değeri ve stablecoin dominansından risk-on/risk-off ortamını ve altseason ipucunu üretir (CoinGecko verisi)." },
  "bug-report": { t: "Hata & Sorun Bildirimi", d: "Sistemde karşılaştığınız hataları buradan doğrudan kaydedebilirsiniz. Bildirimler sistem teşhis günlüğüne işlenir ve çözümleriyle birlikte takip edilir." },
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

// ---- Analiz & Seviyeli Mum Grafiği ----
document.getElementById("analysis-run").addEventListener("click", loadAnalysis);

let lastAnalysisSetup = null;

async function loadAnalysis() {
  const symbol = (document.getElementById("analysis-symbol").value || "BTC/USDT").trim();
  const marketType = (document.getElementById("analysis-market-type") || {}).value || "spot";
  const tf = (document.getElementById("analysis-tf") || {}).value || "1h";
  const sideChoice = (document.getElementById("analysis-side") || {}).value || "auto";

  setFooterLog(`Analiz çalıştırılıyor (${symbol} - ${marketType.toUpperCase()} - ${tf})...`);

  // 1. Puanlama Analizi
  const res = await apiGet(`/market/analysis/score?symbol=${encodeURIComponent(symbol)}&timeframe=${tf}&market_type=${marketType}`);
  if (!res.success) {
    toast("Analiz başarısız: " + (res.error || ""), "error");
    return;
  }

  const s = res.data.score;
  const sig = document.getElementById("analysis-signal");
  sig.textContent = s.signal;
  sig.className = "card-value signal-" + s.signal.toLowerCase().replace(/_/g, "-");
  document.getElementById("analysis-score").textContent = `${s.bull_score} / ${s.bear_score}`;

  const mBadge = document.getElementById("analysis-market-badge");
  if (mBadge) mBadge.textContent = `Piyasa: ${marketType.toUpperCase()}`;

  const derivInfo = document.getElementById("analysis-derivatives-info");
  if (derivInfo) {
    if (marketType === "futures") {
      derivInfo.textContent = "KuCoin Vadeli (USDT-M Perpetual)";
    } else if (marketType === "margin") {
      derivInfo.textContent = "KuCoin Marjin (5x Kaldıraç)";
    } else {
      derivInfo.textContent = "KuCoin Spot İşlem Çifti";
    }
  }

  // Sade İnsan-Okunabilir Özet Kartı
  const sumCard = document.getElementById("analysis-simple-summary-card");
  if (sumCard && s.simple_summary) {
    sumCard.style.display = "flex";
    const sm = s.simple_summary;
    const statusEl = document.getElementById("analysis-plain-status");
    if (statusEl) statusEl.textContent = sm.status || "Piyasa Durumu";

    const riskEl = document.getElementById("analysis-plain-risk");
    if (riskEl) {
      const lvl = (sm.risk_level || "Düşük").toLowerCase();
      riskEl.className = "plain-summary-risk " + (lvl === "yüksek" ? "risk-high" : (lvl === "orta" ? "risk-med" : "risk-low"));
      riskEl.textContent = `🛡️ Risk: ${sm.risk_level || "Düşük"}`;
    }

    const adviceEl = document.getElementById("analysis-plain-advice");
    if (adviceEl) adviceEl.textContent = sm.advice || "";

    const mktEl = document.getElementById("analysis-plain-market");
    if (mktEl) mktEl.textContent = `🏛️ ${sm.market_label || "KuCoin"}`;

    const rTxtEl = document.getElementById("analysis-plain-risk-text");
    if (rTxtEl) rTxtEl.textContent = `🔎 ${sm.risk_text || ""}`;
  }

  // Detaylı & Eğitici Gerekçe Tablo Satırları (Yan yana görünüm)
  const reasonsGrid = document.getElementById("analysis-reasons-grid");
  if (reasonsGrid) {
    if (s.reasons_detail && s.reasons_detail.length > 0) {
      reasonsGrid.innerHTML = s.reasons_detail.map((rd) => {
        const isBull = rd.type === "bullish";
        const isBear = rd.type === "bearish";
        const typeBadge = isBull
          ? `<span class="reason-badge bullish">🟢 Boğa (AL)</span>`
          : (isBear ? `<span class="reason-badge bearish">🔴 Ayı (SAT)</span>` : `<span class="reason-badge">⚪ Nötr</span>`);
        return `
          <div class="reason-row-item ${rd.type || 'bullish'}">
            <div class="reason-cell cell-ind">
              <div class="cell-title">🏷️ ${escapeHtml(rd.indicator || 'Teknik Gösterge')}</div>
              ${typeBadge}
              <div class="cell-summary">${escapeHtml(rd.summary || '')}</div>
            </div>
            <div class="reason-cell cell-why">
              <span class="mobile-label">🔍 Neden Oldu?</span>
              <div class="cell-text">${escapeHtml(rd.condition || rd.why || '')}</div>
            </div>
            <div class="reason-cell cell-shows">
              <span class="mobile-label">📊 İndikatör Neyi Gösterir?</span>
              <div class="cell-text">${escapeHtml(rd.meaning || rd.shows || '')}</div>
            </div>
            <div class="reason-cell cell-impact">
              <span class="mobile-label">⚡ Neye Sebep Olur?</span>
              <div class="cell-text">${escapeHtml(rd.impact || rd.causes || '')}</div>
            </div>
          </div>
        `;
      }).join("");
    } else {
      reasonsGrid.innerHTML = `<div class="hint">Herhangi bir teknik gerekçe tetiklenmedi.</div>`;
    }
  }

  // Detaylı Risk Uyarısı Tablo Satırları
  const warnGrid = document.getElementById("analysis-warnings-grid");
  if (warnGrid) {
    if (s.warnings_detail && s.warnings_detail.length > 0) {
      warnGrid.innerHTML = s.warnings_detail.map((wd) => `
        <div class="warning-row-item">
          <div class="reason-cell cell-ind">
            <div class="cell-title">⚠️ ${escapeHtml(wd.warning || wd.summary || 'Risk Uyarısı')}</div>
            <span class="reason-badge bearish">Risk Filtresi</span>
          </div>
          <div class="reason-cell cell-why">
            <span class="mobile-label">🔍 Neden Oluştu?</span>
            <div class="cell-text">${escapeHtml(wd.why || wd.condition || '')}</div>
          </div>
          <div class="reason-cell cell-shows">
            <span class="mobile-label">📊 Neyi Gösterir?</span>
            <div class="cell-text">${escapeHtml(wd.meaning || wd.shows || '')}</div>
          </div>
          <div class="reason-cell warning-advice-cell">
            <span class="mobile-label">⚡ Tehlikesi & Korunma</span>
            <div class="cell-text"><b>Tehlike:</b> ${escapeHtml(wd.impact || wd.causes || '')}</div>
            <div class="cell-text" style="margin-top:4px; color:#ffab00;"><b>🛡️ Korunma:</b> ${escapeHtml(wd.advice || '')}</div>
          </div>
        </div>
      `).join("");
    } else {
      warnGrid.innerHTML = `<div class="hint">Piyasada şu an aktif bir risk veya sahte sinyal uyarısı bulunmuyor.</div>`;
    }
  }

  // Geriye dönük uyumluluk için liste elemanları
  const legacyReasons = document.getElementById("analysis-reasons");
  if (legacyReasons) {
    legacyReasons.innerHTML =
      (s.reasons || []).map((r) => `<li>${escapeHtml(r)}</li>`).join("") || "<li>Gerekçe yok</li>";
  }
  const legacyWarnings = document.getElementById("analysis-warnings");
  if (legacyWarnings) {
    legacyWarnings.innerHTML =
      (s.warnings || []).map((w) => `<li>${escapeHtml(w)}</li>`).join("") || "<li>Uyarı yok</li>";
  }

  // 2. Yön Belirleme (Auto veya Manuel)
  let calcSide = sideChoice;
  if (calcSide === "auto") {
    calcSide = (s.signal && s.signal.includes("BEAR")) ? "sell" : "buy";
  }

  // 3. Trade Setup Seviyeleri
  const setupRes = await apiGet(`/market/trade-setup?symbol=${encodeURIComponent(symbol)}&timeframe=${tf}&side=${calcSide}&market_type=${marketType}&leverage=5.0`);
  let tradeSetup = null;
  if (setupRes.success && setupRes.data.trade_setup) {
    tradeSetup = setupRes.data.trade_setup;
    lastAnalysisSetup = { symbol, side: calcSide, ...tradeSetup };
    renderAnalysisSetup(calcSide, tradeSetup, marketType);
    const toBracketBtn = document.getElementById("analysis-to-bracket-btn");
    if (toBracketBtn) toBracketBtn.style.display = "inline-block";
  } else {
    const sc = document.getElementById("analysis-setup-content");
    if (sc) sc.innerHTML = `<div class="hint">İşlem seviyeleri hesaplanamadı.</div>`;
  }

  // 4. Analiz Mum Grafiği & Seviyeleri Çiz
  await loadAnalysisChart(symbol, tf, marketType, tradeSetup, calcSide);

  toast(`Analiz tamamlandı: ${s.signal} (${marketType.toUpperCase()})`, "success");
}

function renderAnalysisSetup(side, ts, marketType) {
  const container = document.getElementById("analysis-setup-content");
  if (!container) return;
  const isBuy = side === "buy";
  const dirLabel = isBuy ? "🟢 LONG (ALIŞ)" : "🔴 SHORT (SATIŞ)";
  const riskDiff = Math.abs(ts.entry_price - ts.stop_loss_price);
  const riskPct = ((riskDiff / ts.entry_price) * 100).toFixed(2);
  const tp1Diff = Math.abs(ts.tp1_price - ts.entry_price);
  const tp1Pct = ((tp1Diff / ts.entry_price) * 100).toFixed(2);
  const tp2Diff = Math.abs(ts.tp2_price - ts.entry_price);
  const tp2Pct = ((tp2Diff / ts.entry_price) * 100).toFixed(2);

  let html = `
    <div class="setup-tile">
      <span class="label">İşlem Yönü</span>
      <span class="val ${isBuy ? 'tp' : 'sl'}">${dirLabel}</span>
      <span class="sub">ATR: ${ts.atr}</span>
    </div>
    <div class="setup-tile">
      <span class="label">Giriş Seviyesi</span>
      <span class="val entry">${ts.entry_price}</span>
      <span class="sub">Hedef Giriş</span>
    </div>
    <div class="setup-tile">
      <span class="label">Stop-Loss (SL)</span>
      <span class="val sl">${ts.stop_loss_price}</span>
      <span class="sub">-%${riskPct} Risk</span>
    </div>
    <div class="setup-tile">
      <span class="label">Hedef 1 (TP1 %50)</span>
      <span class="val tp">${ts.tp1_price}</span>
      <span class="sub">+%${tp1Pct} (1.5R)</span>
    </div>
    <div class="setup-tile">
      <span class="label">Hedef 2 (TP2 %50)</span>
      <span class="val tp">${ts.tp2_price}</span>
      <span class="sub">+%${tp2Pct} (3.0R)</span>
    </div>
    <div class="setup-tile">
      <span class="label">Risk / Kazanç</span>
      <span class="val">1 : ${ts.risk_reward_ratio}</span>
      <span class="sub">Optimal Oran</span>
    </div>
  `;

  if (ts.est_liquidation_price) {
    html += `
      <div class="setup-tile">
        <span class="label">Tahmini Likidasyon</span>
        <span class="val liq">${ts.est_liquidation_price}</span>
        <span class="sub">%${ts.liquidation_distance_percent} Mesafe (5x)</span>
      </div>
    `;
  }

  container.innerHTML = html;
}

// "Bu Seviyelerle Akıllı Paket Emir Oluştur" buton dinleyicisi
const toBracketBtnEl = document.getElementById("analysis-to-bracket-btn");
if (toBracketBtnEl) {
  toBracketBtnEl.addEventListener("click", () => {
    if (!lastAnalysisSetup) return;
    switchView("orders");
    document.getElementById("bracket-symbol").value = lastAnalysisSetup.symbol;
    document.getElementById("bracket-side").value = lastAnalysisSetup.side;
    bracketSetup = {
      entry_price: lastAnalysisSetup.entry_price,
      stop_loss_price: lastAnalysisSetup.stop_loss_price,
      tp1_price: lastAnalysisSetup.tp1_price,
      tp2_price: lastAnalysisSetup.tp2_price,
      risk_reward_ratio: lastAnalysisSetup.risk_reward_ratio,
    };
    const box = document.getElementById("bracket-levels");
    if (box) {
      box.innerHTML = `
        <div class="level-row"><span>Giriş</span><b>${bracketSetup.entry_price}</b></div>
        <div class="level-row up"><span>TP1 (%50)</span><b>${bracketSetup.tp1_price}</b></div>
        <div class="level-row up"><span>TP2 (%50)</span><b>${bracketSetup.tp2_price}</b></div>
        <div class="level-row down"><span>Stop-Loss</span><b>${bracketSetup.stop_loss_price}</b></div>
        <div class="level-row"><span>Risk/Ödül</span><b>1 : ${bracketSetup.risk_reward_ratio}</b></div>`;
    }
    const subBtn = document.getElementById("bracket-submit");
    if (subBtn) subBtn.disabled = false;
    toast("Analiz seviyeleri Akıllı Paket Emir formuna aktarıldı!", "success");
  });
}

// Analiz Sekmesi SVG Mum Grafiği & Seviye Çizgileri
async function loadAnalysisChart(symbol, timeframe, marketType, setup, side) {
  const wrap = document.getElementById("analysis-candle-chart");
  const tag = document.getElementById("analysis-chart-tag");
  if (tag) tag.textContent = `${symbol} (${timeframe} - ${marketType.toUpperCase()})`;
  if (!wrap) return;

  const res = await apiGet(`/market/candles?symbol=${encodeURIComponent(symbol)}&timeframe=${timeframe}&limit=50&market_type=${marketType}`);
  if (!res.success || !res.data.candles || !res.data.candles.length) {
    wrap.textContent = "Grafik verisi alınamadı.";
    return;
  }

  const candles = res.data.candles;
  const W = Math.max(680, candles.length * 13);
  const H = 280, padTop = 25, padBottom = 25, padLeft = 65, padRight = 85;

  let allPrices = [];
  candles.forEach((c) => { allPrices.push(c.high); allPrices.push(c.low); });
  if (setup) {
    if (setup.entry_price) allPrices.push(setup.entry_price);
    if (setup.stop_loss_price) allPrices.push(setup.stop_loss_price);
    if (setup.tp1_price) allPrices.push(setup.tp1_price);
    if (setup.tp2_price) allPrices.push(setup.tp2_price);
    if (setup.est_liquidation_price) allPrices.push(setup.est_liquidation_price);
  }

  const maxP = Math.max(...allPrices);
  const minP = Math.min(...allPrices);
  const range = maxP - minP || 1;

  const y = (p) => padTop + (H - padTop - padBottom) * (1 - (p - minP) / range);
  const innerW = W - padLeft - padRight;
  const cw = innerW / candles.length;

  let svg = `<svg viewBox="0 0 ${W} ${H}" preserveAspectRatio="none" style="width:100%;height:100%;">`;
  svg += `<line class="chart-axis" x1="${padLeft}" y1="${H - padBottom}" x2="${W - padRight}" y2="${H - padBottom}"/>`;
  svg += `<text class="chart-label" x="5" y="${y(maxP) + 4}">${maxP.toFixed(2)}</text>`;
  svg += `<text class="chart-label" x="5" y="${y(minP) - 2}">${minP.toFixed(2)}</text>`;

  // Mumlar
  candles.forEach((c, i) => {
    const x = padLeft + i * cw + cw / 2;
    const cls = c.close >= c.open ? "candle-up" : "candle-down";
    svg += `<line class="${cls}" x1="${x}" y1="${y(c.high)}" x2="${x}" y2="${y(c.low)}" stroke-width="1.2"/>`;
    const bodyTop = y(Math.max(c.open, c.close));
    const bodyH = Math.max(1.5, Math.abs(y(c.open) - y(c.close)));
    svg += `<rect class="${cls}" x="${x - cw * 0.35}" y="${bodyTop}" width="${cw * 0.7}" height="${bodyH}"/>`;
  });

  // Yatay İşlem Seviyeleri (Trade Setup Çizgileri)
  if (setup) {
    const x1 = padLeft;
    const x2 = W - padRight;
    const textX = W - padRight + 5;

    // Giriş (Entry)
    if (setup.entry_price) {
      const yEntry = y(setup.entry_price);
      svg += `<line class="chart-level-entry" x1="${x1}" y1="${yEntry}" x2="${x2}" y2="${yEntry}"/>`;
      svg += `<text class="chart-level-text entry" x="${textX}" y="${yEntry + 3}">GİRİŞ: ${setup.entry_price}</text>`;
    }
    // Stop Loss (SL)
    if (setup.stop_loss_price) {
      const ySL = y(setup.stop_loss_price);
      svg += `<line class="chart-level-sl" x1="${x1}" y1="${ySL}" x2="${x2}" y2="${ySL}"/>`;
      svg += `<text class="chart-level-text sl" x="${textX}" y="${ySL + 3}">SL: ${setup.stop_loss_price}</text>`;
    }
    // TP1
    if (setup.tp1_price) {
      const yTP1 = y(setup.tp1_price);
      svg += `<line class="chart-level-tp" x1="${x1}" y1="${yTP1}" x2="${x2}" y2="${yTP1}"/>`;
      svg += `<text class="chart-level-text tp" x="${textX}" y="${yTP1 + 3}">TP1: ${setup.tp1_price}</text>`;
    }
    // TP2
    if (setup.tp2_price) {
      const yTP2 = y(setup.tp2_price);
      svg += `<line class="chart-level-tp" x1="${x1}" y1="${yTP2}" x2="${x2}" y2="${yTP2}"/>`;
      svg += `<text class="chart-level-text tp" x="${textX}" y="${yTP2 + 3}">TP2: ${setup.tp2_price}</text>`;
    }
    // Likidasyon (Futures/Margin)
    if (setup.est_liquidation_price) {
      const yLiq = y(setup.est_liquidation_price);
      if (yLiq >= 0 && yLiq <= H) {
        svg += `<line class="chart-level-liq" x1="${x1}" y1="${yLiq}" x2="${x2}" y2="${yLiq}"/>`;
        svg += `<text class="chart-level-text liq" x="${textX}" y="${yLiq + 3}">LİQ: ${setup.est_liquidation_price}</text>`;
      }
    }
  }

  svg += `</svg>`;
  wrap.innerHTML = svg;
}


// ---- Emirler ----
document.getElementById("order-submit").addEventListener("click", async () => {
  const body = {
    symbol: document.getElementById("order-symbol").value,
    side: document.getElementById("order-side").value,
    order_type: document.getElementById("order-type").value,
    amount: parseFloat(document.getElementById("order-amount").value),
    price: parseFloat(document.getElementById("order-price").value) || null,
    market_type: document.getElementById("order-market-type").value,
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
    tbody.innerHTML = res.data.orders.map((o) => {
      const mt = (o.market_type || "spot").toLowerCase();
      const mtLabel = { spot: "Spot", margin: "Margin", futures: "Futures" }[mt] || mt;
      return `
      <tr>
        <td>${o.id}</td><td>${o.symbol}</td>
        <td><span class="market-badge market-${mt}">${mtLabel}</span></td>
        <td>${o.side}</td><td>${o.type}</td>
        <td>${o.amount}</td><td>${o.price}</td><td>${o.status}</td>
        <td>
          <button class="btn-mini btn-edit" data-id="${o.id}" data-price="${o.price}" data-amount="${o.amount}">Düzenle</button>
          <button class="btn-mini" data-id="${o.id}">İptal</button>
        </td>
      </tr>`;
    }).join("");
    tbody.querySelectorAll(".btn-mini:not(.btn-edit)").forEach((b) =>
      b.addEventListener("click", () => cancelOrder(b.dataset.id)));
    tbody.querySelectorAll(".btn-edit").forEach((b) =>
      b.addEventListener("click", () => openEditModal(b.dataset.id, b.dataset.price, b.dataset.amount)));
  } else {
    tbody.innerHTML = `<tr><td colspan="9">Açık emir yok.</td></tr>`;
  }
}

// ---- Emir Düzenleme Modalı (Amend) ----
function openEditModal(id, price, amount) {
  const modal = document.getElementById("edit-modal");
  document.getElementById("edit-id").value = id;
  document.getElementById("edit-price").value = price;
  document.getElementById("edit-amount").value = amount;
  modal.hidden = false;
}
document.getElementById("edit-cancel").addEventListener("click", () => {
  document.getElementById("edit-modal").hidden = true;
});
document.getElementById("edit-save").addEventListener("click", async () => {
  const id = document.getElementById("edit-id").value;
  const body = {
    price: parseFloat(document.getElementById("edit-price").value) || null,
    amount: parseFloat(document.getElementById("edit-amount").value) || null,
  };
  const res = await apiSend("/orders/" + encodeURIComponent(id), "PUT", body);
  if (res.success) {
    toast("Emir güncellendi", "success");
    document.getElementById("edit-modal").hidden = true;
    loadOpenOrders();
  } else {
    toast("Güncelleme başarısız: " + (res.error || ""), "error");
  }
});

async function cancelOrder(id) {
  const res = await apiSend(`/orders/${id}`, "DELETE");
  if (res.success) { toast("Emir iptal edildi", "success"); loadOpenOrders(); }
  else toast("İptal başarısız", "error");
}

function updateModeBadge(mode) {
  const badge = document.getElementById("mode-badge");
  if (!badge) return;
  const isLive = mode === "live";
  badge.textContent = isLive ? "⚡ LIVE KUCOIN" : "🧪 SIMULATION";
  badge.className = "mode-badge " + (isLive ? "live" : "sim");
  badge.title = isLive
    ? "Canlı KuCoin modu aktif (Gerçek bakiye & emirler). Tıkla: Simülasyon moduna geç"
    : "Simülasyon (Paper) modu aktif ($10.000 sanal USDT). Tıkla: Canlı moda geç";
}

// ---- Ayarlar & Watchlist ----
async function loadSettings() {
  const res = await apiGet("/settings");
  if (!res.success) return;
  const s = res.data;
  document.getElementById("set-mode").value = s.default_mode;
  document.getElementById("set-symbol").value = s.default_symbol;
  document.getElementById("set-tf").value = s.default_timeframe;
  document.getElementById("set-maxorder").value = (s.risk && s.risk.max_order_usdt) || 1000;
  renderWatchlist(s.watchlist || []);
  if (s.default_mode) updateModeBadge(s.default_mode);
}

function renderWatchlist(list) {
  const ul = document.getElementById("watchlist");
  ul.innerHTML = list.map((sym) => `
    <li style="display:flex;justify-content:space-between;align-items:center">
      <span>${sym}</span>
      <button class="btn-mini" data-watch="${sym}">Çıkar</button>
    </li>`).join("") || "<li>İzleme listesi boş</li>";
  ul.querySelectorAll("[data-watch]").forEach((b) =>
    b.addEventListener("click", () => removeWatch(b.dataset.watch)));
  populateSymbolChoices();  // sembol dropdown'larını güncel tut
}

document.getElementById("settings-save").addEventListener("click", async () => {
  const newMode = document.getElementById("set-mode").value;
  const body = {
    default_mode: newMode,
    default_symbol: document.getElementById("set-symbol").value,
    default_timeframe: document.getElementById("set-tf").value,
    risk: { max_order_usdt: parseFloat(document.getElementById("set-maxorder").value) || 1000 },
  };
  const res = await apiSend("/settings", "POST", body);
  if (res.success) {
    // orders.mode'u da senkronize olarak geçir
    await apiSend("/orders/switch-mode", "POST", { mode: newMode });
    updateModeBadge(newMode);
    const modeLabel = newMode === "live" ? "⚡ CANLI (LIVE KUCOIN)" : "🧪 SİMÜLASYON (SIMULATION)";
    toast(`Ayarlar kaydedildi! Çalışma modu: ${modeLabel}`, "success");
    loadSummary();
    loadStatus();
    loadOpenOrders();
    loadDiagnostics();
  } else {
    toast("Ayar kaydı başarısız: " + (res.error || ""), "error");
  }
});

// Başlıktaki #mode-badge rozetine tıklayarak doğrudan canlı/simülasyon geçişi
const modeBadgeEl = document.getElementById("mode-badge");
if (modeBadgeEl) {
  modeBadgeEl.style.cursor = "pointer";
  modeBadgeEl.addEventListener("click", async () => {
    const isLive = modeBadgeEl.classList.contains("live");
    const targetMode = isLive ? "paper" : "live";
    const confirmMsg = isLive
      ? "Simülasyon (Paper Trading) moduna geçmek istiyor musunuz?"
      : "⚡ DİKKAT: CANLI (LIVE KUCOIN) moduna geçmek üzeresiniz!\nGerçek bakiye ve gerçek emirler kullanılacaktır. Onaylıyor musunuz?";
    if (!confirm(confirmMsg)) return;

    const res = await apiSend("/orders/switch-mode", "POST", { mode: targetMode });
    if (res.success) {
      updateModeBadge(targetMode);
      const sel = document.getElementById("set-mode");
      if (sel) sel.value = targetMode;
      const label = targetMode === "live" ? "⚡ CANLI (LIVE KUCOIN)" : "🧪 SİMÜLASYON (SIMULATION)";
      toast(`Çalışma modu değiştirildi: ${label}`, "success");
      loadSummary();
      loadStatus();
      loadOpenOrders();
      loadDiagnostics();
    } else {
      toast("Mod değiştirilemedi: " + (res.error || ""), "error");
    }
  });
}

document.getElementById("watch-add").addEventListener("click", async () => {
  const sym = document.getElementById("watch-symbol").value.trim();
  if (!sym) return;
  const res = await apiSend("/settings/watchlist", "POST", { symbol: sym });
  if (res.success) { renderWatchlist(res.data.watchlist); toast(`${sym} eklendi`, "success"); document.getElementById("watch-symbol").value = ""; }
});

async function removeWatch(sym) {
  const res = await apiSend("/settings/watchlist/" + encodeURIComponent(sym), "DELETE");
  if (res.success) { renderWatchlist(res.data.watchlist); toast(`${sym} çıkarıldı`, "warning"); }
}

// ---- Akıllı Paket Emir (Bracket) ----
let bracketSetup = null;
document.getElementById("bracket-load").addEventListener("click", async () => {
  const symbol = document.getElementById("bracket-symbol").value;
  const side = document.getElementById("bracket-side").value;
  const marketType = document.getElementById("bracket-market-type").value;
  const res = await apiGet(`/market/trade-setup?symbol=${encodeURIComponent(symbol)}&side=${side}&market_type=${marketType}`);
  const box = document.getElementById("bracket-levels");
  if (res.success) {
    bracketSetup = res.data.trade_setup;
    const s = bracketSetup;
    box.innerHTML = `
      <div class="level-row"><span>Giriş</span><b>${s.entry_price}</b></div>
      <div class="level-row up"><span>TP1 (%50)</span><b>${s.tp1_price}</b></div>
      <div class="level-row up"><span>TP2 (%50)</span><b>${s.tp2_price}</b></div>
      <div class="level-row down"><span>Stop-Loss</span><b>${s.stop_loss_price}</b></div>
      <div class="level-row"><span>Risk/Ödül</span><b>1 : ${s.risk_reward_ratio}</b></div>`;
    document.getElementById("bracket-submit").disabled = false;
    toast("Seviyeler hesaplandı", "success");
  } else {
    box.textContent = "Seviyeler hesaplanamadı: " + (res.error || "");
    document.getElementById("bracket-submit").disabled = true;
  }
});

document.getElementById("bracket-submit").addEventListener("click", async () => {
  if (!bracketSetup) return;
  const body = {
    symbol: document.getElementById("bracket-symbol").value,
    side: document.getElementById("bracket-side").value,
    usdt_amount: parseFloat(document.getElementById("bracket-usdt").value) || 0,
    entry_price: bracketSetup.entry_price,
    stop_loss_price: bracketSetup.stop_loss_price,
    tp1_price: bracketSetup.tp1_price,
    tp2_price: bracketSetup.tp2_price,
    market_type: document.getElementById("bracket-market-type").value,
  };
  const res = await apiSend("/orders/bracket", "POST", body);
  if (res.success) {
    toast(`Paket emir iletildi (${res.data.bracket_id}) — risk ${res.data.risk_usdt} USDT`, "success");
    loadOpenOrders();
  } else {
    toast("Paket emir reddedildi: " + (res.error || ""), "error");
  }
});

const POPULAR_SYMBOLS = [
  "BTC/USDT", "ETH/USDT", "SOL/USDT", "XRP/USDT", "DOGE/USDT",
  "BNB/USDT", "ADA/USDT", "AVAX/USDT", "LINK/USDT", "SUI/USDT",
  "PEPE/USDT", "NEAR/USDT", "LTC/USDT", "DOT/USDT", "TRX/USDT",
  "APT/USDT", "INJ/USDT", "ARB/USDT", "OP/USDT", "TIA/USDT"
];

// ---- Sembol girişlerini watchlist + popüler koinler ile besleme ----
async function populateSymbolChoices() {
  const res = await apiGet("/settings");
  const watchlist = (res.success && res.data.watchlist && res.data.watchlist.length > 0)
    ? res.data.watchlist
    : ["BTC/USDT", "ETH/USDT", "SOL/USDT"];

  const allSymbols = Array.from(new Set([...watchlist, ...POPULAR_SYMBOLS]));
  const dl = document.getElementById("symbol-choices");
  if (dl) dl.innerHTML = allSymbols.map((s) => `<option value="${s}"></option>`).join("");

  // Analiz dropdown combo'sunu doldur
  const sel = document.getElementById("analysis-symbol-select");
  const input = document.getElementById("analysis-symbol");
  if (sel) {
    let html = `<optgroup label="👁️ İzleme Listesi (Watchlist)">`;
    watchlist.forEach((s) => {
      html += `<option value="${s}">${s}</option>`;
    });
    html += `</optgroup><optgroup label="🔥 Popüler KuCoin Çiftleri">`;
    POPULAR_SYMBOLS.filter((s) => !watchlist.includes(s)).forEach((s) => {
      html += `<option value="${s}">${s}</option>`;
    });
    html += `</optgroup><option value="custom">➕ Diğer / Özel Sembol...</option>`;
    sel.innerHTML = html;

    const currentVal = (input && input.value) ? input.value.trim() : "BTC/USDT";
    if (allSymbols.includes(currentVal)) {
      sel.value = currentVal;
    } else {
      sel.value = "custom";
    }
  }

  // Hızlı Koin Seçim Çiplerini oluştur
  const chipsContainer = document.getElementById("analysis-quick-chips");
  if (chipsContainer) {
    const quickCoins = ["BTC/USDT", "ETH/USDT", "SOL/USDT", "XRP/USDT", "DOGE/USDT", "BNB/USDT", "SUI/USDT", "AVAX/USDT", "PEPE/USDT"];
    const currentVal = (input && input.value) ? input.value.trim() : "BTC/USDT";
    chipsContainer.innerHTML = quickCoins.map((sym) => {
      const activeCls = sym === currentVal ? "active" : "";
      const label = sym.replace("/USDT", "");
      return `<button type="button" class="quick-chip ${activeCls}" data-sym="${sym}">${label}</button>`;
    }).join("");

    chipsContainer.querySelectorAll(".quick-chip").forEach((btn) => {
      btn.addEventListener("click", () => {
        const targetSym = btn.dataset.sym;
        if (input) input.value = targetSym;
        if (sel) sel.value = targetSym;
        chipsContainer.querySelectorAll(".quick-chip").forEach((b) => b.classList.remove("active"));
        btn.classList.add("active");
        loadAnalysis();
      });
    });
  }
}

// Analiz Sembol Dropdown & Input senkronizasyonu
const analysisSelect = document.getElementById("analysis-symbol-select");
const analysisInput = document.getElementById("analysis-symbol");

if (analysisSelect && analysisInput) {
  analysisSelect.addEventListener("change", () => {
    if (analysisSelect.value === "custom") {
      analysisInput.focus();
      analysisInput.select();
    } else {
      analysisInput.value = analysisSelect.value;
      const chips = document.querySelectorAll("#analysis-quick-chips .quick-chip");
      chips.forEach((c) => {
        if (c.dataset.sym === analysisSelect.value) c.classList.add("active");
        else c.classList.remove("active");
      });
      loadAnalysis();
    }
  });

  analysisInput.addEventListener("focus", () => {
    analysisInput.select();
  });

  analysisInput.addEventListener("change", () => {
    const val = analysisInput.value.trim().toUpperCase();
    analysisInput.value = val;
    if (analysisSelect) {
      const options = Array.from(analysisSelect.options).map((o) => o.value);
      if (options.includes(val)) {
        analysisSelect.value = val;
      } else {
        analysisSelect.value = "custom";
      }
    }
    const chips = document.querySelectorAll("#analysis-quick-chips .quick-chip");
    chips.forEach((c) => {
      if (c.dataset.sym === val) c.classList.add("active");
      else c.classList.remove("active");
    });
  });
}

// ---- Mini Watchlist Widget + Öneri Kartları ----
async function loadMiniWatchlist() {
  const box = document.getElementById("mini-watchlist");
  if (!box) return;
  const setRes = await apiGet("/settings");
  if (!setRes.success) { box.textContent = "İzleme listesi yüklenemedi: " + (setRes.error || ""); return; }
  const list = setRes.data.watchlist || [];
  if (!list.length) { box.textContent = "İzleme listesi boş."; return; }
  const cells = await Promise.all(list.map(async (sym) => {
    const t = await apiGet("/market/ticker?symbol=" + encodeURIComponent(sym));
    if (!t.success) return `<div class="mini-coin"><span>${sym}</span><span>--</span></div>`;
    const chg = t.data.change_percentage_24h ?? 0;
    const cls = chg >= 0 ? "up" : "down";
    return `<div class="mini-coin" data-sym="${sym}">
      <span>${sym}</span>
      <span>${t.data.last_price}</span>
      <span class="${cls}">${chg}%</span></div>`;
  }));
  box.innerHTML = cells.join("") || "İzleme listesi boş.";
  // koin seçince dashboard o koine geçsin
  box.querySelectorAll(".mini-coin[data-sym]").forEach((el) =>
    el.addEventListener("click", () => { activeSymbol = el.dataset.sym; loadTicker(activeSymbol); loadChart(activeSymbol); toast(`Aktif: ${activeSymbol}`, "success"); }));
}

async function loadMarketRegime() {
  const res = await apiGet("/market/regime");
  const box = document.getElementById("market-regime");
  if (!box) return;
  if (res.success) {
    const d = res.data;
    const regCls = d.regime === "RISK_ON" ? "up" : d.regime === "RISK_OFF" ? "down" : "";
    box.innerHTML = `
      <span class="${regCls}"><b>${d.regime}</b></span>
      <span>BTC.D: ${d.btc_dominance}%</span>
      <span>Stablecoin.D: ${d.stablecoin_dominance}%</span>
      <span>24s MCap: ${d.market_cap_change_24h_pct}%</span>
      ${d.altseason_hint ? '<span class="up">Altseason ipucu</span>' : ''}`;
  } else {
    box.textContent = "Piyasa geneli verisi alınamadı.";
  }
}

async function loadRecommendations() {
  const res = await apiGet("/orders/recommendations");
  const box = document.getElementById("reco-cards");
  if (res.success && res.data.count) {
    box.innerHTML = res.data.recommendations.map((r) => `
      <div class="reco-card glass ${r.severity}">
        <span>${r.message}</span>
        <button class="btn-mini" data-reco="${r.order_id}">✖ Yoksay</button>
      </div>`).join("");
    box.querySelectorAll("[data-reco]").forEach((b) =>
      b.addEventListener("click", () => b.closest(".reco-card").remove()));
  } else {
    box.innerHTML = "";
  }
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
  // Her widget bağımsız yüklenir; biri başarısız olursa diğerleri etkilenmez.
  await Promise.allSettled([
    loadStatus(),
    loadSummary(),
    loadTicker(activeSymbol),
    loadMiniWatchlist(),
    loadMarketRegime(),
    loadRecommendations(),
  ]);
}
function startPolling() {
  if (pollTimer) return;
  refreshDashboard();
  pollTimer = setInterval(refreshDashboard, 15000);
}
function stopPolling() {
  if (pollTimer) { clearInterval(pollTimer); pollTimer = null; }
}

// ============================================================================
// Hata Raporlama ve Sorun Takibi (Issue Tracker)
// ============================================================================
let activeIssueFilter = "all";

async function loadIssues(filter = activeIssueFilter) {
  activeIssueFilter = filter;
  const url = filter === "all" ? "/issues" : `/issues?status=${encodeURIComponent(filter)}`;
  const res = await apiGet(url);
  const container = document.getElementById("issues-list");
  if (!container) return;

  if (res.success) {
    const totalEl = document.getElementById("issues-total-count");
    const openEl = document.getElementById("issues-open-count");
    const resEl = document.getElementById("issues-resolved-count");
    if (totalEl) totalEl.textContent = res.total ?? res.data.length;
    if (openEl) openEl.textContent = res.open_count ?? 0;
    if (resEl) resEl.textContent = res.resolved_count ?? 0;

    const list = res.data || [];
    if (list.length === 0) {
      container.innerHTML = `<div class="card-value" style="font-size:0.9rem; color:var(--text-muted); text-align:center; padding:1.5rem;">Bu filtreye uygun hata kaydı bulunamadı.</div>`;
      return;
    }

    const catMap = {
      analysis: "📈 Analiz Ekranı",
      orders: "📋 Emirler & Akıllı Paket",
      account: "👛 Hesap & Bakiye",
      settings: "⚙️ Ayarlar & Watchlist",
      chart: "📊 Grafik",
      api: "🔌 API",
      general: "🛠️ Genel"
    };

    const sevMap = {
      critical: { t: "Kritik", cls: "severity-critical" },
      high: { t: "Yüksek", cls: "severity-high" },
      medium: { t: "Orta", cls: "severity-medium" },
      low: { t: "Düşük", cls: "severity-low" }
    };

    const statusMap = {
      open: { t: "Açık", cls: "status-open" },
      in_progress: { t: "İnceleniyor", cls: "status-in_progress" },
      resolved: { t: "Çözüldü", cls: "status-resolved" },
      closed: { t: "Kapatıldı", cls: "status-closed" }
    };

    container.innerHTML = list.map((item) => {
      const sev = sevMap[item.severity] || { t: item.severity, cls: "severity-medium" };
      const stat = statusMap[item.status] || { t: item.status, cls: "status-open" };
      const cat = catMap[item.category] || item.category;

      return `
        <div class="issue-card" data-id="${item.id}">
          <div class="issue-header" data-toggle="${item.id}">
            <div class="issue-title-wrap">
              <span class="issue-id-badge">#${item.id}</span>
              <span class="issue-title-text">${escapeHtml(item.title)}</span>
            </div>
            <div class="issue-badges">
              <span class="badge-severity ${sev.cls}">${sev.t}</span>
              <span class="badge-status ${stat.cls}">${stat.t}</span>
              <span class="chevron" id="chevron-${item.id}">▼</span>
            </div>
          </div>
          <div class="issue-details" id="details-${item.id}">
            <div class="issue-field">
              <span class="issue-field-label">Kategori</span>
              <span>${cat}</span>
            </div>
            <div class="issue-field">
              <span class="issue-field-label">Hata Açıklaması</span>
              <span>${escapeHtml(item.description)}</span>
            </div>
            ${item.steps_to_reproduce ? `
              <div class="issue-field">
                <span class="issue-field-label">Tekrarlama Adımları</span>
                <span style="white-space:pre-wrap;">${escapeHtml(item.steps_to_reproduce)}</span>
              </div>` : ''}
            ${item.expected_behavior ? `
              <div class="issue-field">
                <span class="issue-field-label">Beklenen Davranış</span>
                <span>${escapeHtml(item.expected_behavior)}</span>
              </div>` : ''}
            ${item.actual_behavior ? `
              <div class="issue-field">
                <span class="issue-field-label">Gerçekleşen Davranış</span>
                <span>${escapeHtml(item.actual_behavior)}</span>
              </div>` : ''}
            ${item.resolution_note ? `
              <div class="issue-resolution-box">
                <b>💡 Çözüm Açıklaması:</b><br/>${escapeHtml(item.resolution_note)}
              </div>` : ''}
            ${item.system_info ? `
              <div class="issue-field">
                <span class="issue-field-label">Sistem / Ortam</span>
                <span style="font-size:0.75rem; color:var(--text-muted);">${escapeHtml(item.system_info)}</span>
              </div>` : ''}
            <div class="issue-actions">
              ${item.status !== "resolved" ? `
                <button type="button" class="btn btn-sm btn-buy btn-issue-action" data-action="resolved" data-id="${item.id}">✅ Çözüldü Olarak İşaretle</button>` : ''}
              ${item.status === "open" ? `
                <button type="button" class="btn btn-sm btn-accent btn-issue-action" data-action="in_progress" data-id="${item.id}">🔍 İnceleniyor Yap</button>` : ''}
              ${item.status === "resolved" ? `
                <button type="button" class="btn btn-sm btn-issue-action" data-action="open" data-id="${item.id}">🔄 Yeniden Aç</button>` : ''}
              <button type="button" class="btn btn-sm btn-sell btn-issue-delete" data-id="${item.id}">🗑️ Sil</button>
            </div>
          </div>
        </div>`;
    }).join("");

    // Akordeon aç/kapa
    container.querySelectorAll(".issue-header").forEach((hdr) => {
      hdr.addEventListener("click", () => {
        const id = hdr.dataset.toggle;
        const det = document.getElementById("details-" + id);
        const chev = document.getElementById("chevron-" + id);
        if (det) {
          const isHidden = det.style.display === "none";
          det.style.display = isHidden ? "flex" : "none";
          if (chev) chev.textContent = isHidden ? "▲" : "▼";
        }
      });
    });

    // Durum güncelleme butonları
    container.querySelectorAll(".btn-issue-action").forEach((btn) => {
      btn.addEventListener("click", async (e) => {
        e.stopPropagation();
        const id = btn.dataset.id;
        const nextStatus = btn.dataset.action;
        let note = null;
        if (nextStatus === "resolved") {
          note = prompt("Çözüm açıklaması eklemek ister misiniz?", "Gerekli düzeltmeler yapıldı ve doğrulandı.");
        }
        const patchRes = await apiSend(`/issues/${id}`, "PATCH", { status: nextStatus, resolution_note: note });
        if (patchRes.success) {
          toast(`Hata #${id} durumu '${nextStatus}' olarak güncellendi.`, "success");
          loadIssues();
          loadDiagnostics();
        } else {
          toast("Güncelleme başarısız: " + (patchRes.error || ""), "error");
        }
      });
    });

    // Silme butonları
    container.querySelectorAll(".btn-issue-delete").forEach((btn) => {
      btn.addEventListener("click", async (e) => {
        e.stopPropagation();
        const id = btn.dataset.id;
        if (!confirm(`Hata #${id} kaydını silmek istediğinize emin misiniz?`)) return;
        const delRes = await apiSend(`/issues/${id}`, "DELETE");
        if (delRes.success) {
          toast(`Hata #${id} silindi.`, "success");
          loadIssues();
          loadDiagnostics();
        } else {
          toast("Silme başarısız: " + (delRes.error || ""), "error");
        }
      });
    });

  } else {
    container.innerHTML = `<div class="card-value" style="color:var(--danger)">Hatalar yüklenemedi: ${res.error || ""}</div>`;
  }
}

// Filtre butonları
document.querySelectorAll(".issue-filter-bar button").forEach((btn) => {
  btn.addEventListener("click", () => {
    document.querySelectorAll(".issue-filter-bar button").forEach((b) => b.classList.remove("active"));
    btn.classList.add("active");
    loadIssues(btn.dataset.filter);
  });
});

// Yeni Hata Bildir Formu
const issueForm = document.getElementById("issue-form");
if (issueForm) {
  issueForm.addEventListener("submit", async (e) => {
    e.preventDefault();
    const title = document.getElementById("issue-title").value.trim();
    const category = document.getElementById("issue-category").value;
    const severity = document.getElementById("issue-severity").value;
    const description = document.getElementById("issue-description").value.trim();
    const steps = document.getElementById("issue-steps").value.trim() || null;
    const expected = document.getElementById("issue-expected").value.trim() || null;
    const actual = document.getElementById("issue-actual").value.trim() || null;
    const autoEnv = document.getElementById("issue-auto-env").checked;

    let sysInfo = null;
    if (autoEnv) {
      const modeText = document.getElementById("mode-badge") ? document.getElementById("mode-badge").textContent.trim() : "sim";
      sysInfo = `Tarayıcı: ${navigator.userAgent.slice(0, 80)}... | Ekran: ${window.innerWidth}x${window.innerHeight} | Mod: ${modeText}`;
    }

    const payload = {
      title,
      category,
      severity,
      description,
      steps_to_reproduce: steps,
      expected_behavior: expected,
      actual_behavior: actual,
      system_info: sysInfo
    };

    const res = await apiSend("/issues", "POST", payload);
    if (res.success) {
      toast(`Hata #${res.data.id} kaydedildi! Teşekkürler.`, "success");
      issueForm.reset();
      document.getElementById("issue-auto-env").checked = true;
      loadIssues();
      loadDiagnostics();
    } else {
      toast("Hata kaydedilemedi: " + (res.error || ""), "error");
    }
  });
}

// Sistem Teşhis & Canlı Log
async function loadDiagnostics() {
  const diagRes = await apiGet("/system/diagnostics");
  const summaryEl = document.getElementById("diagnostics-summary");
  if (diagRes.success && summaryEl) {
    const d = diagRes.data;
    summaryEl.innerHTML = `
      <div class="diag-item"><div class="diag-label">İşletim Sistemi / Platform</div><div class="diag-val">${escapeHtml(d.platform || "--")}</div></div>
      <div class="diag-item"><div class="diag-label">Python Sürümü</div><div class="diag-val">${escapeHtml(d.python_version || "--")}</div></div>
      <div class="diag-item"><div class="diag-label">İşlem Modu</div><div class="diag-val">${d.orders_mode === "live" ? "⚡ LIVE" : "🧪 SIMULATION"}</div></div>
      <div class="diag-item"><div class="diag-label">Borsa Bağlantısı</div><div class="diag-val">${d.exchange_connected ? "🟢 Bağlı" : "🟡 Simülasyon / Test"}</div></div>
      <div class="diag-item"><div class="diag-label">İzleme Listesi (Watchlist)</div><div class="diag-val">${d.watchlist_count ?? 0} Adet Koin</div></div>
      <div class="diag-item"><div class="diag-label">Toplam Bildirim / Açık</div><div class="diag-val">${d.total_issues} / ${d.open_issues}</div></div>
    `;
  }
}

// Teşhis bilgilerini panoya kopyalama
const btnCopyDiag = document.getElementById("btn-copy-diagnostics");
if (btnCopyDiag) {
  btnCopyDiag.addEventListener("click", async () => {
    const diagRes = await apiGet("/system/diagnostics");
    const info = {
      diagnostics: diagRes.data,
      recent_logs: systemLogs,
      client_timestamp: new Date().toISOString()
    };
    navigator.clipboard.writeText(JSON.stringify(info, null, 2));
    toast("Teşhis ve log bilgileri panoya kopyalandı.", "success");
  });
}

async function loadMode() {
  const res = await apiGet("/orders/mode");
  if (res.success && res.data.mode) {
    updateModeBadge(res.data.mode);
    const sel = document.getElementById("set-mode");
    if (sel) sel.value = res.data.mode;
  }
}

// İlk yükleme
loadMode();
loadStatus();
loadSummary();
loadTicker();
loadChart();
populateSymbolChoices();
setInterval(() => loadChart(), 60000);  // grafik 60sn'de bir yenilenir
connectWebSocket();
