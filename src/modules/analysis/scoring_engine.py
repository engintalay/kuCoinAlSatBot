"""
Composite Scoring Engine (MODULE_2_SPEC 4.2 & 4.3).

İndikatör katmanı çıktılarından (trend, momentum, strength, volatility,
structure) ağırlıklı 0-100 boğa/ayı skoru üretir; risk filtrelerini uygular
ve insan-okunabilir gerekçelerle bir sinyal durumu döndürür.

Not: Türev (Katman 8) veri kaynağı bu fazda mevcut olmadığından ilgili
puan satırları hesaba katılmaz; skor mevcut feature'lar üzerinden 100'e
normalize edilir.
"""


def _score_trend(trend: dict) -> tuple[float, float, list]:
    bull = bear = 0.0
    reasons = []
    if not trend:
        return bull, bear, reasons
    regime, cross = trend.get("regime"), trend.get("cross")
    if regime == "BULLISH" and cross == "GOLDEN_CROSS":
        bull += 15; reasons.append("Fiyat EMA200 üstünde ve EMA50>EMA200 (Golden Cross)")
    elif regime == "BEARISH" and cross == "DEATH_CROSS":
        bear += 15; reasons.append("Fiyat EMA200 altında ve EMA50<EMA200 (Death Cross)")

    st = trend.get("supertrend")
    if st:
        if st.get("direction") == 1:
            bull += 5; reasons.append("Supertrend bullish")
        elif st.get("direction") == -1:
            bear += 5; reasons.append("Supertrend bearish")

    ich = trend.get("ichimoku")
    if ich:
        if ich.get("position") == "ABOVE_CLOUD":
            bull += 5; reasons.append("Fiyat Ichimoku bulutu üzerinde")
        elif ich.get("position") == "BELOW_CLOUD":
            bear += 5; reasons.append("Fiyat Ichimoku bulutu altında")
    return bull, bear, reasons


def _score_momentum(mom: dict) -> tuple[float, float, list]:
    bull = bear = 0.0
    reasons = []
    if not mom:
        return bull, bear, reasons
    rsi = mom.get("rsi")
    if rsi and rsi.get("slope_3_bars") is not None:
        if rsi["value"] > 50 and rsi["slope_3_bars"] > 0:
            bull += 8; reasons.append(f"RSI {rsi['value']} > 50 ve yükseliyor")
        elif rsi["value"] < 50 and rsi["slope_3_bars"] < 0:
            bear += 8; reasons.append(f"RSI {rsi['value']} < 50 ve düşüyor")

    macd = mom.get("macd")
    if macd:
        hist = macd.get("histogram")
        if hist is not None and hist > 0:
            bull += 7; reasons.append("MACD histogram pozitif")
        elif hist is not None and hist < 0:
            bear += 7; reasons.append("MACD histogram negatif")
    return bull, bear, reasons


def _score_structure(struct: dict) -> tuple[float, float, list]:
    bull = bear = 0.0
    reasons = []
    if not struct:
        return bull, bear, reasons
    if struct.get("bos") == "BULLISH":
        bull += 12; reasons.append("Bullish BOS (yapı yukarı kırıldı)")
    elif struct.get("bos") == "BEARISH":
        bear += 12; reasons.append("Bearish BOS (yapı aşağı kırıldı)")

    fvg = struct.get("fvg") or []
    if any(g.get("type") == "BULLISH" for g in fvg):
        bull += 8; reasons.append("Aktif Bullish FVG")
    if any(g.get("type") == "BEARISH" for g in fvg):
        bear += 8; reasons.append("Aktif Bearish FVG")
    return bull, bear, reasons


def _score_strength(strength: dict) -> tuple[float, float, list]:
    bull = bear = 0.0
    reasons = []
    if not strength:
        return bull, bear, reasons
    adx = strength.get("adx")
    if adx and adx.get("value") is not None and adx["value"] > 25:
        # ADX yön vermez; +DI/-DI yönü ile ağırlığı taraflara dağıt.
        if adx.get("plus_di") is not None and adx.get("minus_di") is not None:
            if adx["plus_di"] > adx["minus_di"]:
                bull += 5; reasons.append(f"ADX {adx['value']} güçlü trend (+DI>−DI)")
            else:
                bear += 5; reasons.append(f"ADX {adx['value']} güçlü trend (−DI>+DI)")
    return bull, bear, reasons


def _score_volume(volume: dict) -> tuple[float, float, list]:
    """Hacim & akış puanlaması (spec 4.2: RVOL+VWAP, CMF, OBV)."""
    bull = bear = 0.0
    reasons = []
    if not volume:
        return bull, bear, reasons

    rvol = volume.get("rvol") or {}
    vwap = volume.get("vwap") or {}
    if rvol.get("regime") == "HIGH" and vwap.get("price_above_vwap") is True:
        bull += 10; reasons.append("Yüksek RVOL ve fiyat VWAP üstünde")
    elif rvol.get("regime") == "HIGH" and vwap.get("price_above_vwap") is False:
        bear += 10; reasons.append("Yüksek RVOL ve fiyat VWAP altında")

    cmf = volume.get("cmf") or {}
    if cmf.get("regime") == "INFLOW":
        bull += 5; reasons.append("CMF net sermaye girişi")
    elif cmf.get("regime") == "OUTFLOW":
        bear += 5; reasons.append("CMF net sermaye çıkışı")

    obv = volume.get("obv") or {}
    if obv.get("above_ema20") is True:
        bull += 5; reasons.append("OBV EMA20 üzerinde")
    elif obv.get("above_ema20") is False:
        bear += 5; reasons.append("OBV EMA20 altında")

    return bull, bear, reasons


def _score_derivatives(derivatives: dict | None) -> tuple[float, float, list]:
    """Türev piyasa puanlaması (Katman 8: funding rate & open interest)."""
    bull = bear = 0.0
    reasons = []
    if not derivatives or not derivatives.get("available"):
        return bull, bear, reasons

    fr = derivatives.get("funding_rate") or {}
    st = fr.get("status")
    val = fr.get("value")
    if st == "OVERHEATED_SHORT":
        bull += 10
        reasons.append(f"Negatif fonlama ({val}): Short tarafı sıkışık, yukarı tepki potansiyeli")
    elif st == "OVERHEATED_LONG":
        bear += 10
        reasons.append(f"Aşırı pozitif fonlama ({val}): Long tarafı kalabalık, long squeeze riski")
    elif st == "NORMAL" and val is not None:
        reasons.append(f"Fonlama oranı dengeli ({val})")

    oi = derivatives.get("open_interest") or {}
    if oi.get("amount") is not None:
        reasons.append(f"Açık pozisyon hacmi: {oi['amount']:,.0f}")

    return bull, bear, reasons


def _risk_filters(indicators: dict, market_type: str = "spot") -> list:
    """Sahte sinyal / risk filtreleri (spec 3.3, 3.5). Uyarı listesi döndürür."""
    warnings = []
    strength = indicators.get("strength") or {}
    adx = strength.get("adx") or {}
    chop = strength.get("choppiness") or {}
    vol = indicators.get("volatility") or {}

    if adx.get("value") is not None and adx["value"] < 20:
        warnings.append("Düşük ADX (<20): Trend zayıf, range riski.")
    if chop.get("regime") == "CONSOLIDATION":
        warnings.append("Choppiness yüksek: Konsolidasyon/yatay bant.")
    if adx.get("regime") == "OVEREXTENDED":
        warnings.append("ADX aşırı yüksek (>40): Trend tükenme/klimaks riski.")
    bk = vol.get("bollinger_keltner") or {}
    if bk.get("squeeze") == "SQUEEZE_ON":
        warnings.append("Bollinger/Keltner Squeeze aktif: Düşük volatilite, patlama beklentisi.")

    # Piyasa türü özel risk uyarıları
    if market_type == "futures":
        deriv = indicators.get("derivatives") or {}
        fr = deriv.get("funding_rate") or {}
        if fr.get("status") in ("OVERHEATED_LONG", "OVERHEATED_SHORT"):
            warnings.append(f"Vadeli Uyarı: Aşırı fonlama oranı ({fr.get('status')}) — ani tasfiye (liquidation cascade) riski.")
    elif market_type == "margin":
        warnings.append("Marjin Uyarısı: Kaldıraçlı borçlanma — teminat seviyesini ve faiz yükünü izleyin.")

    return warnings


REASON_EXPLANATIONS = {
    # Trend
    "Golden Cross": {
        "indicator": "EMA 50 / 200 Hareketli Ortalama (Trend Yönü)",
        "condition": "Fiyat 200 periyotluk ana ortalamanın üzerinde ve EMA50, EMA200'ü yukarı kesti (Golden Cross).",
        "meaning": "Piyasanın uzun vadeli ana yönünün güçlü biçimde yukarı döndüğünü ve kurumsal yatırımcıların alım yaptığını gösterir.",
        "impact": "Satış baskısının kırılmasına, geri çekilmelerin güçlü alım fırsatı olarak karşılanmasına ve yükselişin sürmesine sebep olur.",
        "type": "bullish",
    },
    "Death Cross": {
        "indicator": "EMA 50 / 200 Hareketli Ortalama (Trend Yönü)",
        "condition": "Fiyat 200 periyotluk ana ortalamanın altında ve EMA50, EMA200'ü aşağı kesti (Death Cross).",
        "meaning": "Piyasanın uzun vadeli ana trendinin düşüşe geçtiğini ve satıcıların piyasaya hakim olduğunu gösterir.",
        "impact": "Yükseliş tepkilerinin satışla karşılanmasına ve düşüş dalgasının derinleşmesine sebep olur.",
        "type": "bearish",
    },
    "Supertrend bullish": {
        "indicator": "Supertrend (Volatilite Takip Göstergesi)",
        "condition": "Fiyat dinamik volatilite stop bandının üzerine çıktı ve indikatör yeşil (AL) durumuna geçti.",
        "meaning": "ATR oynaklığına göre dinamik trend takip seviyesinin korunduğunu ve alıcıların kontrolü ele aldığını gösterir.",
        "impact": "Trend boyunca pozisyon taşımaya zemin hazırlar; olası ani düşüşlerde dinamik destek görevi görür.",
        "type": "bullish",
    },
    "Supertrend bearish": {
        "indicator": "Supertrend (Volatilite Takip Göstergesi)",
        "condition": "Fiyat dinamik volatilite bandını aşağı kırdı ve indikatör kırmızı (SAT) durumuna geçti.",
        "meaning": "Dinamik destek kırılmış, düşüş ivmesinin trend haline geldiğini gösterir.",
        "impact": "Yeni alımların riskli olmasına ve kısa vadeli satış baskısının sürmesine sebep olur.",
        "type": "bearish",
    },
    "Ichimoku bulutu üzerinde": {
        "indicator": "Ichimoku Kinko Hyo (Kumo Bulut Dengesi)",
        "condition": "Fiyat Senkou Span A ve B bulut katmanlarının üzerine çıktı.",
        "meaning": "Orta vadeli denge seviyesinin alıcılar lehine aşıldığını ve piyasanın pozitif bölgeye girdiğini gösterir.",
        "impact": "Bulutun üst sınırı güçlü bir destek tabanı oluşturarak yükseliş hareketini destekler.",
        "type": "bullish",
    },
    "Ichimoku bulutu altında": {
        "indicator": "Ichimoku Kinko Hyo (Kumo Bulut Dengesi)",
        "condition": "Fiyat bulut katmanının altına indi.",
        "meaning": "Orta vadeli denge bozulmuş, satıcı baskısının baskın olduğunu gösterir.",
        "impact": "Olası yükselişlerde bulut güçlü bir tavan/direnç oluşturur ve fiyatın toparlanmasını zorlaştırır.",
        "type": "bearish",
    },
    # Momentum
    "> 50 ve yükseliyor": {
        "indicator": "RSI (Göreceli Güç Endeksi)",
        "condition": "RSI 50 denge seviyesinin üzerinde ve son mumlarda yukarı yönlü yükseliyor.",
        "meaning": "Son 14 mumdaki alım hızının satış hızından daha kuvvetli arttığını (alıcı iştahını) gösterir.",
        "impact": "Fiyatın yukarı yönlü ivme kazanmasına ve alım baskısının sürmesine sebep olur.",
        "type": "bullish",
    },
    "< 50 ve düşüyor": {
        "indicator": "RSI (Göreceli Güç Endeksi)",
        "condition": "RSI 50 denge seviyesinin altında ve momentum aşağı yönlü zayıflıyor.",
        "meaning": "Piyasadaki alım isteğinin zayıfladığını ve satıcıların fiyatı aşağı ittiğini gösterir.",
        "impact": "Fiyatın alt destekleri test etmesine ve düşüş eğiliminin devam etmesine sebep olur.",
        "type": "bearish",
    },
    "MACD histogram pozitif": {
        "indicator": "MACD (Fiyat İvmesi & Momentum)",
        "condition": "Hızlı hareketli ortalama yavaş ortalamanın üzerine çıktı, histogram sıfırın üzerinde genişliyor.",
        "meaning": "Kısa vadeli fiyat ivmesinin hızlandığını ve trend gücünün arttığını gösterir.",
        "impact": "Alım baskısının hızlanmasına, yukarı yönlü mumların büyümesine sebep olur.",
        "type": "bullish",
    },
    "MACD histogram negatif": {
        "indicator": "MACD (Fiyat İvmesi & Momentum)",
        "condition": "Hızlı ortalama yavaş ortalamanın altında, histogram sıfırın altında negatif bölgede.",
        "meaning": "Kısa vadeli satış baskısının güçlendiğini ve düşüş hızının arttığını gösterir.",
        "impact": "Fiyatın aşağı yönlü kaymasına ve alıcıların çekimser kalmasına sebep olur.",
        "type": "bearish",
    },
    # Structure (SMC)
    "Bullish BOS": {
        "indicator": "SMC - BOS (Piyasa Yapısı Kırılımı)",
        "condition": "Fiyat önceki swing tepe noktasını hacimle kırarak daha yüksek bir tepe (Higher High) yaptı.",
        "meaning": "Kurumsal büyük sermayenin trendi yukarı yönde genişletmeye devam ettiğini gösterir.",
        "impact": "Yükseliş trendinin geçerliliğini teyit eder; kırılan seviye geri çekilmelerde alım desteği olur.",
        "type": "bullish",
    },
    "Bearish BOS": {
        "indicator": "SMC - BOS (Piyasa Yapısı Kırılımı)",
        "condition": "Fiyat önceki swing dip seviyesini aşağı kırarak daha düşük bir dip (Lower Low) yaptı.",
        "meaning": "Satıcıların piyasa tabanını delerek düşüş yapısını sürdürdüğünü gösterir.",
        "impact": "Stop patlatmalarına ve düşüş trendinin bir alt destek seviyesine kadar uzamasına sebep olur.",
        "type": "bearish",
    },
    "Bullish FVG": {
        "indicator": "SMC - FVG (Adil Değer Boşluğu)",
        "condition": "Fiyatta ani bir agresif alım mumu oluştu ve 1. ile 3. mum arasında doldurulmamış fiyat boşluğu kaldı.",
        "meaning": "Kurumsal alıcıların çok hızlı işlem yaptığını ve likidite dengesizliği oluştuğunu gösterir.",
        "impact": "Fiyat bu boşluk bölgesine geri çekildiğinde alıcıların tekrar devreye girmesine ve yukarı sıçramaya sebep olur.",
        "type": "bullish",
    },
    "Bearish FVG": {
        "indicator": "SMC - FVG (Adil Değer Boşluğu)",
        "condition": "Agresif satış mumu sonrası aşağı yönlü dengesizlik boşluğu oluştu.",
        "meaning": "Satıcıların piyasayı tek taraflı domine ettiğini ve alıcıların kaçtığını gösterir.",
        "impact": "Fiyat bu boşluğa doğru toparlanmaya çalıştığında güçlü satış direnciyle karşılaşmasına sebep olur.",
        "type": "bearish",
    },
    # Strength
    "+DI>−DI": {
        "indicator": "ADX & DMI (Yükseliş Trend Gücü)",
        "condition": "ADX 25 eşiğini aştı ve pozitif yönsel gösterge (+DI), negatif göstergenin (-DI) üzerine çıktı.",
        "meaning": "Piyasanın yatayda sıkışmadığını, net ve güçlü bir yükseliş trendi içinde olduğunu gösterir.",
        "impact": "Yükseliş yönünde açılan pozisyonların sahte kırılımlara takılma riskini azaltır ve hedefe ulaşmasını kolaylaştırır.",
        "type": "bullish",
    },
    "−DI>+DI": {
        "indicator": "ADX & DMI (Düşüş Trend Gücü)",
        "condition": "ADX 25 eşiğini aştı ve negatif yönsel gösterge (-DI), pozitif göstergenin (+DI) üzerine çıktı.",
        "meaning": "Piyasada güçlü bir satış baskısı olduğunu ve düşüş trendinin ivme kazandığını gösterir.",
        "impact": "Fiyatın aşağı yönlü hareketinin sertleşmesine ve yükseliş tepkilerinin satış fırsatı olarak ezilmesine sebep olur.",
        "type": "bearish",
    },
    # Volume
    "Yüksek RVOL ve fiyat VWAP üstünde": {
        "indicator": "RVOL & VWAP (Hacimli Kurumsal Alım)",
        "condition": "İşlem hacmi 20 günlük ortalamanın belirgin üzerinde ve fiyat günün hacim ağırlıklı ortalamasının üstünde.",
        "meaning": "Yükselişin küçük yatırımcı spekülasyonu değil, kurumsal büyük sermaye girişiyle gerçekleştiğini gösterir.",
        "impact": "Trendin gerçek alımlarla desteklendiğini kanıtlar; sahte kırılım (fakeout) ihtimalini düşürür.",
        "type": "bullish",
    },
    "Yüksek RVOL ve fiyat VWAP altında": {
        "indicator": "RVOL & VWAP (Hacimli Kurumsal Satış)",
        "condition": "Hacim yüksek fakat fiyat hacim ağırlıklı maliyet ortalamasının altında seyrediyor.",
        "meaning": "Büyük oyuncuların ellerindeki pozisyonları piyasaya boşalttığını (dağıtım) gösterir.",
        "impact": "Satış baskısının hacimli ve kararlı olmasına, düşüşün devam etmesine sebep olur.",
        "type": "bearish",
    },
    "CMF net sermaye girişi": {
        "indicator": "CMF (Chaikin Para Akışı)",
        "condition": "CMF göstergesi pozitif bölgede (sıfırın üzerinde).",
        "meaning": "Mumların kapanış fiyatlarının tepeye yakın gerçekleştiğini, piyasaya net para girdiğini gösterir.",
        "impact": "Fiyat düşse bile alttan toplandığını göstererek olası yükseliş hareketlerini destekler.",
        "type": "bullish",
    },
    "CMF net sermaye çıkışı": {
        "indicator": "CMF (Chaikin Para Akışı)",
        "condition": "CMF göstergesi negatif bölgede seyrediyor.",
        "meaning": "Mum kapanışlarının dip seviyelere yakın olduğunu, piyasadan net nakit çıktığını gösterir.",
        "impact": "Tepki alımlarının zayıf kalmasına ve aşağı yönlü hareketlerin hızlanmasına sebep olur.",
        "type": "bearish",
    },
    "OBV EMA20 üzerinde": {
        "indicator": "OBV (Denge İşlem Hacmi)",
        "condition": "OBV hacim çizgisi kendi 20 periyotluk hareketli ortalamasının üzerinde seyrediyor.",
        "meaning": "Hacim birikiminin yükseliş yönlü olduğunu ve alıcıların hacmi artırdığını gösterir.",
        "impact": "Fiyat hareketinin hacimce onaylandığını teyit eder.",
        "type": "bullish",
    },
    "OBV EMA20 altında": {
        "indicator": "OBV (Denge İşlem Hacmi)",
        "condition": "OBV hacim çizgisi ortalamasının altına indi.",
        "meaning": "Satışların daha yüksek hacimle gerçekleştiğini ve hacim tabanının eridiğini gösterir.",
        "impact": "Zayıf hacimli yükselişlerin kalıcı olamamasına ve düşüşün devamına sebep olur.",
        "type": "bearish",
    },
    # Derivatives
    "Negatif fonlama": {
        "indicator": "Vadeli Fonlama Oranı (Funding Rate)",
        "condition": "Fonlama oranı negatif bölgede aşırıya kaçmış durumda (Short pozisyonlar Long'lara prim ödüyor).",
        "meaning": "Vadeli piyasada herkesin düşüşe oynadığını ve Short tarafının aşırı kalabalıklaştığını gösterir.",
        "impact": "Fiyat hafif yükseldiğinde Short pozisyonların stop olmasıyla ani bir yukarı sıçramaya (Short Squeeze) sebep olabilir.",
        "type": "bullish",
    },
    "Aşırı pozitif fonlama": {
        "indicator": "Vadeli Fonlama Oranı (Funding Rate)",
        "condition": "Fonlama oranı +%0.03 eşiğini aşarak aşırı yükseldi (Long pozisyonlar ağır maliyet ödüyor).",
        "meaning": "Piyasada aşırı coşku ve kaldıraçlı alıcı birikmesi (aşırı ısınma) olduğunu gösterir.",
        "impact": "Büyük oyuncuların piyasayı aniden aşağı iterek aşırı kaldıraçlı Long'ları tasfiye etmesine (Long Squeeze) sebep olabilir.",
        "type": "bearish",
    },
    "Fonlama oranı dengeli": {
        "indicator": "Vadeli Fonlama Oranı (Funding Rate)",
        "condition": "Fonlama oranı normal sınırlar içerisinde dengeli seyrediyor.",
        "meaning": "Vadeli piyasada tek taraflı kaldıraç baskısı veya aşırı birikme olmadığını gösterir.",
        "impact": "Piyasanın manipülasyondan uzak, teknik seviyelere daha sadık hareket etmesini sağlar.",
        "type": "neutral",
    },
    "Açık pozisyon hacmi": {
        "indicator": "Açık Pozisyon Hacmi (Open Interest)",
        "condition": "Vadeli piyasada açık olan toplam sözleşme büyüklüğü ölçüldü.",
        "meaning": "Vadeli piyasaya yeni sermaye girdiğini ve işlem likiditesinin derinleştiğini gösterir.",
        "impact": "Fiyat hareketlerinin kayma (slippage) olmadan daha sağlıklı ve likit işlemesine sebep olur.",
        "type": "neutral",
    },
}

WARNING_EXPLANATIONS = {
    "Düşük ADX": {
        "warning": "Düşük ADX (<20): Trend Gücü Zayıf.",
        "why": "Fiyat belirli bir yöne gitmekte zorlanıyor, alıcı ve satıcı dengede.",
        "meaning": "Piyasanın yönlü bir trend yerine yatay bant (konsolidasyon) içinde olduğunu gösterir.",
        "impact": "Trend takip stratejilerinde sahte kırılımlara ve stop avlarına sebep olur.",
        "advice": "Trend kırılımı gerçekleşip hacim teyit edilene kadar beklemek veya dar bantta küçük kârlar hedeflemek uygundur.",
    },
    "Choppiness yüksek": {
        "warning": "Choppiness Yüksek: Konsolidasyon / Yatay Testere.",
        "why": "Fiyat dar bir aralıkta testere hareketi yapıyor.",
        "meaning": "Piyasanın enerji topladığını fakat yönün henüz belirsiz olduğunu ölçer.",
        "impact": "Açılan işlemlerin sürekli kârdan zarara dönmesine ve yön tayin edilememesine sebep olur.",
        "advice": "İşlem sıklığını azaltın; bot sinyali güvenliğiniz için nötr durumdadır.",
    },
    "ADX aşırı yüksek": {
        "warning": "ADX Aşırı Yüksek (>40): Trend Tükenme / Klimaks Riski.",
        "why": "Fiyat hareketi çok dik bir açıyla hızlandı.",
        "meaning": "Mevcut trendin son aşamasına (coşku/panik evresi) gelmiş olabileceğini gösterir.",
        "impact": "Beklenmedik sert düzeltmelere veya kâr satışlarına sebep olabilir.",
        "advice": "Yeni pozisyon açmak yerine mevcut kârları realize etmek veya Stop-Loss'u başabaş seviyesine çekmek önerilir.",
    },
    "Squeeze aktif": {
        "warning": "Bollinger / Keltner Squeeze: Volatilite Sıkışması.",
        "why": "Bollinger bantları Keltner kanallarının içine girdi (fiyat daraldı).",
        "meaning": "Piyasada fırtına öncesi sessizlik yaşandığını, büyük bir patlama hazırlığı olduğunu gösterir.",
        "impact": "Bantlardan birinin kırılmasıyla birlikte yönlü çok sert ve ani bir fiyat hareketine sebep olur.",
        "advice": "Kırılım yönü netleşmeden pozisyon almayın; kırılım anında yöne katılın.",
    },
    "Vadeli Uyarı": {
        "warning": "Vadeli Fonlama Dengesizliği: Tasfiye Riski.",
        "why": "Vadeli tarafta tek yönlü aşırı kaldıraç birikti.",
        "meaning": "Borsadaki açık pozisyonların tasfiye (likidasyon) tehlikesi altında olduğunu gösterir.",
        "impact": "Borsanın hızlı iğneler (kaldıraç avı) atarak stopları patlatmasına sebep olabilir.",
        "advice": "Vadeli işlemlerde kaldıracı 3x-5x seviyesinde tutun ve geniş stop kullanın.",
    },
    "Marjin Uyarısı": {
        "warning": "Marjin Kaldıraç Riski: Teminat Takibi.",
        "why": "Marjin işlemi borçlanma faizi ve kaldıraçlı teminat gerektirir.",
        "meaning": "Piyasa tersine hareket ettiğinde teminatın hızla eriyebileceğini gösterir.",
        "impact": "Marjin çağrısı (Margin Call) veya zorunlu pozisyon kapatılmasına sebep olabilir.",
        "advice": "Teminat oranınızı %200'ün üzerinde tutun ve anlık düşüşlerde likidasyon seviyesini gözleyin.",
    },
}


def _build_reason_detail(reason_str: str) -> dict:
    """Teknik gerekçeyi sade, öğretici ve 4-boyutlu yapıya dönüştürür."""
    sorted_keys = sorted(REASON_EXPLANATIONS.keys(), key=len, reverse=True)
    for key in sorted_keys:
        if key.lower() in reason_str.lower():
            val = REASON_EXPLANATIONS[key]
            cond = val.get("condition") or val.get("why") or reason_str
            mean = val.get("meaning") or val.get("shows") or ""
            imp = val.get("impact") or val.get("causes") or ""
            return {
                "summary": reason_str,
                "indicator": val["indicator"],
                "condition": cond,
                "why": cond,
                "meaning": mean,
                "shows": mean,
                "impact": imp,
                "causes": imp,
                "type": val["type"],
            }
    is_bull = any(w in reason_str.lower() for w in ("bull", "üst", "pozitif", "girişi", "+di"))
    fallback_cond = reason_str
    fallback_shows = "Fiyat ve hacim göstergelerinde belirlenen strateji eşiği tetiklendi."
    fallback_causes = "Bileşik skor motorunda yöne puan katkısı sağlayarak sinyali destekler."
    return {
        "summary": reason_str,
        "indicator": "Teknik Gösterge Kuralı",
        "condition": fallback_cond,
        "why": fallback_cond,
        "meaning": fallback_shows,
        "shows": fallback_shows,
        "impact": fallback_causes,
        "causes": fallback_causes,
        "type": "bullish" if is_bull else "bearish",
    }


def _build_warning_detail(warning_str: str) -> dict:
    """Risk uyarısını sade açıklama ve korunma tavsiyesine dönüştürür."""
    sorted_warn_keys = sorted(WARNING_EXPLANATIONS.keys(), key=len, reverse=True)
    for key in sorted_warn_keys:
        if key.lower() in warning_str.lower():
            val = WARNING_EXPLANATIONS[key]
            return {
                "summary": warning_str,
                "warning": val["warning"],
                "why": val["why"],
                "condition": val["why"],
                "meaning": val["meaning"],
                "shows": val["meaning"],
                "impact": val["impact"],
                "causes": val["impact"],
                "advice": val["advice"],
            }
    return {
        "summary": warning_str,
        "warning": warning_str,
        "why": "Piyasa koşullarında normal dışı bir teknik durum tespit edildi.",
        "meaning": "Fiyat hareketinin belirsizlik veya yüksek oynaklık taşıdığını gösterir.",
        "impact": "İşlemin risk/ödül dengesini olumsuz etkileyebilir.",
        "advice": "İşlem büyüklüğünü küçük tutun ve Stop-Loss seviyesini titizlikle uygulayın.",
    }


def _build_simple_summary(
    signal: str, bull_score: float, bear_score: float, warnings: list, market_type: str
) -> dict:
    """Kullanıcının bir bakışta anlayacağı sade dille piyasa durumu ve eylem tavsiyesi."""
    if signal in ("STRONG_BULLISH", "BULLISH"):
        status = (
            "🟢 Güçlü Yükseliş Eğilimi (Alıcılar Kontrolde)"
            if signal == "STRONG_BULLISH"
            else "🟢 Yükseliş Eğilimi Hakim (Pozitif Görünüm)"
        )
        advice = (
            "Teknik indikatörler ve piyasa yapısı alıcıların üstünlüğünü teyit ediyor. "
            "Destek seviyelerine yakın noktalardan kademeli alım ve kâr hedeflerini (TP1 / TP2) takip etmek uygundur. "
            "Hesaplanan Stop-Loss seviyesine mutlaka sadık kalınız."
        )
    elif signal in ("STRONG_BEARISH", "BEARISH"):
        status = (
            "🔴 Güçlü Düşüş Eğilimi (Satıcılar Baskın)"
            if signal == "STRONG_BEARISH"
            else "🔴 Düşüş Eğilimi Hakim (Temkinli Olun)"
        )
        advice = (
            "Teknik göstergeler piyasada satıcıların baskın olduğunu gösteriyor. "
            "Yeni alım yapmaktan kaçınmak, mevcut pozisyonlarda stop seviyelerini sıkılaştırmak "
            "veya nakitte kalarak dip oluşumunu beklemek daha güvenlidir."
        )
    else:
        status = "🟡 Kararsız / Yatay Piyasa (Net Yön Yok)"
        advice = (
            "Alıcı ve satıcılar dengede; fiyat yatay bir bantta sıkışmış durumda. "
            "Sahte kırılımlardan (testereden) korunmak için net bir trend kırılımı teyit edilene kadar "
            "beklemek veya yalnızca bant sınırlarında düşük riskli küçük işlemler yapmak önerilir."
        )

    if len(warnings) == 0:
        risk_level = "Düşük"
        risk_text = "Piyasa yapısı ve oynaklık dengeli. Göstergeler birbiriyle uyumlu, sahte sinyal riski az."
    elif len(warnings) == 1:
        risk_level = "Orta"
        risk_text = f"1 risk faktörü aktif: {warnings[0]}"
    else:
        risk_level = "Yüksek"
        risk_text = f"Birden fazla risk faktörü aktif ({len(warnings)} uyarı). Yüksek oynaklık veya yatay bant tuzağı riski mevcuttur."

    market_label = (
        "KuCoin Spot"
        if market_type == "spot"
        else ("KuCoin Marjin (5x Kaldıraç)" if market_type == "margin" else "KuCoin Vadeli (USDT-M Perpetual)")
    )

    return {
        "status": status,
        "advice": advice,
        "risk_level": risk_level,
        "risk_text": risk_text,
        "market_label": market_label,
    }


def compute_score(indicators: dict, market_type: str = "spot") -> dict:
    """
    Ağırlıklı boğa/ayı skoru, sinyal durumu, sade özet ve detaylı gerekçeler üretir.
    """
    layers = [
        _score_trend(indicators.get("trend")),
        _score_momentum(indicators.get("momentum")),
        _score_strength(indicators.get("strength")),
        _score_volume(indicators.get("volume")),
        _score_structure(indicators.get("structure")),
    ]
    if market_type == "futures" or indicators.get("derivatives"):
        layers.append(_score_derivatives(indicators.get("derivatives")))

    bull = sum(l[0] for l in layers)
    bear = sum(l[1] for l in layers)
    reasons = [r for l in layers for r in l[2]]
    warnings = _risk_filters(indicators, market_type=market_type)

    max_points = 90.0 if (market_type == "futures" or indicators.get("derivatives")) else 80.0
    bull_score = round(min(bull / max_points * 100, 100), 1)
    bear_score = round(min(bear / max_points * 100, 100), 1)
    net = round(bull_score - bear_score, 1)

    # Choppiness yüksekse sinyali nötrle (spec 4.3).
    chop = (indicators.get("strength") or {}).get("choppiness") or {}
    force_neutral = chop.get("regime") == "CONSOLIDATION"

    if force_neutral:
        signal = "NEUTRAL"
    elif bull_score >= 80 and not warnings:
        signal = "STRONG_BULLISH"
    elif bull_score >= 60:
        signal = "BULLISH"
    elif bear_score >= 80 and not warnings:
        signal = "STRONG_BEARISH"
    elif bear_score >= 60:
        signal = "BEARISH"
    else:
        signal = "NEUTRAL"

    # Sade insan-okunabilir özet & 4-boyutlu gerekçe/uyarı detayları
    simple_summary = _build_simple_summary(signal, bull_score, bear_score, warnings, market_type)
    reasons_detail = [_build_reason_detail(r) for r in reasons]
    warnings_detail = [_build_warning_detail(w) for w in warnings]

    return {
        "bull_score": bull_score,
        "bear_score": bear_score,
        "net_score": net,
        "signal": signal,
        "market_type": market_type,
        "reasons": reasons,
        "reasons_detail": reasons_detail,
        "warnings": warnings,
        "warnings_detail": warnings_detail,
        "simple_summary": simple_summary,
    }


