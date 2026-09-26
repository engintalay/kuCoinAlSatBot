/**
 * KuCoin Al-Sat Botu — Giriş Ekranı JS (Faz 1 Task 9)
 */

const form = document.getElementById("login-form");
const errorBox = document.getElementById("login-error");
const totpField = document.getElementById("totp-field");
const loginBtn = document.getElementById("login-btn");

function showError(msg) {
  errorBox.textContent = msg;
  errorBox.style.display = "block";
}
function hideError() { errorBox.style.display = "none"; }

form.addEventListener("submit", async (e) => {
  e.preventDefault();
  hideError();
  loginBtn.disabled = true;
  loginBtn.textContent = "Giriş yapılıyor…";

  const body = {
    username: document.getElementById("login-username").value.trim(),
    password: document.getElementById("login-password").value,
  };
  const totp = document.getElementById("login-totp").value.trim();
  if (totp) body.totp_code = totp;

  try {
    const res = await fetch("/api/v1/auth/login", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      credentials: "include",   // cookie alabilmek için
      body: JSON.stringify(body),
    });
    const data = await res.json();

    if (data.success) {
      window.location.href = "/";
      return;
    }

    // 2FA gerekli ise TOTP alanını göster
    if (data.data && data.data.totp_required) {
      totpField.style.display = "block";
      document.getElementById("login-totp").focus();
      showError(data.error || "2FA kodu gerekli.");
    } else {
      showError(data.error || "Giriş başarısız.");
    }
  } catch (err) {
    showError("Sunucuya bağlanılamadı: " + err.message);
  } finally {
    loginBtn.disabled = false;
    loginBtn.textContent = "Giriş Yap";
  }
});
