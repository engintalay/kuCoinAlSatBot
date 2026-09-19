"""
KuCoin Al-Sat Botu — Modül 2 İndikatör Katmanları (Faz 2a çekirdek).

Her katman, kapanmış OHLCV mumları üzerinden normalize edilmiş feature'lar
üretir. Girdi: pandas DataFrame (kolonlar: timestamp, open, high, low, close,
volume). Çıktı: JSON-serileştirilebilir dict.
"""
