# Kripto Teknik Analiz İndikatörleri ve Sinyal Sistemi — Coding Agent Teknik Referansı

## 0. Amaç

Bu doküman, kripto para piyasalarında trend, momentum, hacim, volatilite, destek/direnç, market structure ve türev piyasa verilerini kullanarak analiz/sinyal üreten bir coding agent için teknik referanstır.

Amaç **tek bir indikatöre göre AL/SAT kararı vermek değil**, farklı veri kaynaklarını bağımsız feature'lar halinde hesaplayıp birleştirilebilir bir analiz motoru oluşturmaktır.

Önerilen mimari:

```text
OHLCV
 ├── Trend
 ├── Momentum
 ├── Trend Strength
 ├── Volume / Flow
 ├── Volatility
 ├── Support / Resistance
 └── Market Structure

Derivatives / External Data
 ├── Open Interest
 ├── Funding Rate
 ├── Long/Short Ratio
 ├── Liquidations
 ├── CVD
 └── Basis

Higher Timeframes
 ├── 4H regime
 ├── 1H setup
 └── 15m trigger

                         ↓
                  Feature Engine
                         ↓
                Signal / Score Engine
                         ↓
             Explanation + Confidence
```

---

# 1. Ortak veri modeli

## 1.1 OHLCV

Çoğu klasik indikatör için minimum veri:

```text
timestamp
open
high
low
close
volume
```

Tanımlar:

- `O` = Open
- `H` = High
- `L` = Low
- `C` = Close
- `V` = Volume

Bazı indikatörler yalnızca `close` ister. Bazıları `high/low/close`, bazıları `volume` ister.

---

## 1.2 Temel yardımcı fonksiyonlar

### True Range

```text
TR = max(
    High - Low,
    abs(High - PreviousClose),
    abs(Low - PreviousClose)
)
```

### True Range neden gerekir?

ATR, ADX ve bazı volatilite hesaplarında kullanılır.

---

# 2. TREND İNDİKATÖRLERİ

## 2.1 EMA — Exponential Moving Average

### Amaç

Trend yönünü ve dinamik destek/direnç seviyelerini belirlemek.

Yaygın periyotlar:

```text
EMA 20
EMA 50
EMA 100
EMA 200
```

### Veri

Sadece `close` yeterlidir.

### Hesaplama

Önce:

```text
alpha = 2 / (N + 1)
```

Sonra:

```text
EMA_t = alpha * Price_t + (1-alpha) * EMA_(t-1)
```

İlk EMA için SMA seed kullanılabilir:

```text
EMA_initial = SMA(N)
```

### Yorum

```text
price > EMA200 → uzun vadeli bullish bias
price < EMA200 → uzun vadeli bearish bias

EMA50 > EMA200 → bullish trend yapısı
EMA50 < EMA200 → bearish trend yapısı
```

Tek başına AL/SAT sinyali olarak kullanılmamalıdır.

---

## 2.2 SMA — Simple Moving Average

### Amaç

Basit trend filtresi ve ortalama fiyat.

### Veri

`close`

### Hesaplama

```text
SMA_N = sum(Close[i-N+1:i]) / N
```

Örneğin SMA200 son 200 kapanışın aritmetik ortalamasıdır.

### Kullanım

Özellikle:

```text
Price vs SMA200
EMA50 vs SMA200
```

gibi trend filtrelerinde kullanılabilir.

---

## 2.3 Supertrend

### Amaç

Trend yönü ve trailing stop benzeri dinamik seviye üretmek.

### Veri

```text
High
Low
Close
ATR
```

### Temel hesap

```text
HL2 = (High + Low) / 2

BasicUpper = HL2 + multiplier * ATR
BasicLower = HL2 - multiplier * ATR
```

Yaygın parametre:

```text
ATR period = 10
multiplier = 3
```

Final band hesaplamasında önceki band ve önceki close kullanılarak bandın trend yönüne göre taşınması yapılır.

### Çıktı

```text
supertrend_direction = +1 / -1
supertrend_value
```

### Kullanım

```text
direction == +1 → bullish regime
direction == -1 → bearish regime
```

Flip hareketleri giriş/çıkış tetikleyicisi olarak kullanılabilir ancak yatay piyasada false signal üretir.

---

# 3. ICHIMOKU CLOUD

## Amaç

Tek sistem içinde:

- trend
- momentum
- destek/direnç
- breakout
- geleceğe projekte edilen cloud

bilgisi üretmek.

### Veri

```text
High
Low
Close
```

### Standart parametreler

```text
Tenkan = 9
Kijun = 26
Senkou B = 52
Displacement = 26
```

### Tenkan-sen

```text
Tenkan =
(max(high, 9) + min(low, 9)) / 2
```

### Kijun-sen

```text
Kijun =
(max(high, 26) + min(low, 26)) / 2
```

### Senkou Span A

```text
SpanA = (Tenkan + Kijun) / 2
```

26 periyot ileri projekte edilir.

### Senkou Span B

```text
SpanB =
(max(high,52) + min(low,52)) / 2
```

26 periyot ileri projekte edilir.

### Chikou Span

```text
Chikou = Close
```

26 periyot geriye kaydırılır.

### Kullanım

```text
Close > Cloud → bullish
Close < Cloud → bearish
Close inside Cloud → neutral / transition

Tenkan > Kijun → bullish momentum
Tenkan < Kijun → bearish momentum
```

Cloud kalınlığı destek/direnç gücü için feature olabilir.

---

# 4. PARABOLIC SAR

## Amaç

Trend yönü ve trailing stop noktası.

### Veri

```text
High
Low
```

### Temel parametreler

```text
Step = 0.02
Maximum AF = 0.20
```

### Formül

Bull trend için:

```text
SAR_next = SAR_current + AF * (EP - SAR_current)
```

- `AF` = acceleration factor
- `EP` = extreme point

Yeni high oluştuğunda EP ve AF güncellenir.

Bear trend için extreme point low tarafıdır.

### Kullanım

```text
price > SAR → bullish
price < SAR → bearish
```

Yatay piyasada çok sayıda false reversal üretir.

---

# 5. MOMENTUM

# 5.1 RSI — Relative Strength Index

## Amaç

Momentum ve aşırı alım/aşırı satım bölgelerini ölçmek.

### Veri

`close`

### Standart

```text
period = 14
```

### Hesap

Fiyat değişimi:

```text
Delta = Close_t - Close_(t-1)
```

Pozitif ve negatif değişimler ayrılır.

Wilder smoothing ile:

```text
AvgGain
AvgLoss
```

hesaplanır.

Sonra:

```text
RS = AvgGain / AvgLoss

RSI = 100 - (100 / (1 + RS))
```

### Kullanım

Klasik:

```text
RSI > 70 → overbought
RSI < 30 → oversold
```

Ancak trend piyasasında bu tek başına AL/SAT değildir.

Trend filtresi olarak:

```text
RSI > 50 → bullish momentum
RSI < 50 → bearish momentum
```

daha kullanışlı olabilir.

### Ek feature'lar

```text
RSI slope
RSI crossing 50
RSI crossing 30/70
RSI divergence
```

---

# 5.2 Stochastic RSI

## Amaç

RSI'ın kendi son dönem aralığı içindeki konumunu ölçer.

### Veri

Önce RSI gerekir.

### Formül

```text
StochRSI =
(RSI - LowestRSI_N) /
(HighestRSI_N - LowestRSI_N)
```

Sonuç 0–1 aralığındadır.

Yüzde formatında 0–100 yapılabilir.

Yaygın:

```text
RSI period = 14
Stoch period = 14
K = 3
D = 3
```

### Kullanım

```text
> 80 → high momentum / overbought region
< 20 → low momentum / oversold region
```

Özellikle kısa vadeli dönüşlerde kullanılır.

---

# 5.3 MACD

## Amaç

Trend + momentum değişimini ölçmek.

### Veri

`close`

### Standart

```text
Fast = 12
Slow = 26
Signal = 9
```

### Formül

```text
MACD = EMA12 - EMA26

Signal = EMA9(MACD)

Histogram = MACD - Signal
```

### Kullanım

```text
MACD > Signal → bullish momentum
MACD < Signal → bearish momentum

Histogram > 0 → bullish momentum
Histogram < 0 → bearish momentum
```

Feature'lar:

```text
MACD crossover
Signal crossover
Histogram slope
Histogram zero-cross
```

---

# 5.4 CCI — Commodity Channel Index

## Amaç

Fiyatın ortalamasından ne kadar saptığını ölçmek.

### Veri

```text
High
Low
Close
```

### Typical Price

```text
TP = (H + L + C) / 3
```

### Formül

```text
CCI =
(TP - SMA(TP,N)) /
(0.015 * MeanDeviation)
```

Yaygın:

```text
N = 20
```

### Kullanım

```text
CCI > +100 → güçlü bullish momentum
CCI < -100 → güçlü bearish momentum
```

---

# 5.5 Williams %R

## Amaç

Kapanışın son N periyottaki high-low aralığındaki konumunu ölçer.

### Veri

```text
High
Low
Close
```

### Formül

```text
%R =
(HighestHigh_N - Close) /
(HighestHigh_N - LowestLow_N) * -100
```

Sonuç:

```text
0 ile -100
```

### Kullanım

```text
>-20 → overbought
<-80 → oversold
```

---

# 5.6 ROC — Rate of Change

### Amaç

Fiyat değişim hızını ölçmek.

### Formül

```text
ROC_N =
((Close_t - Close_(t-N)) / Close_(t-N)) * 100
```

### Kullanım

```text
ROC > 0 → fiyat N dönem öncesinden yüksek
ROC < 0 → düşük
```

Momentum feature'ı olarak kullanılabilir.

---

# 5.7 Momentum

Basit:

```text
Momentum_N = Close_t - Close_(t-N)
```

Alternatif yüzde:

```text
MomentumPct =
(Close_t / Close_(t-N) - 1) * 100
```

ROC ile büyük ölçüde benzer bilgi taşır.

---

# 6. TREND STRENGTH

# 6.1 ADX

## Amaç

Trendin yönünü değil, **gücünü** ölçmek.

### Veri

```text
High
Low
Close
```

### Temel bileşenler

Directional Movement:

```text
UpMove = High_t - High_(t-1)
DownMove = Low_(t-1) - Low_t
```

Kurallar:

```text
+DM = UpMove if UpMove > DownMove and UpMove > 0
-DM = DownMove if DownMove > UpMove and DownMove > 0
```

TR hesaplanır.

Wilder smoothing ile:

```text
+DI = 100 * Smoothed(+DM) / ATR
-DI = 100 * Smoothed(-DM) / ATR
```

Directional Index:

```text
DX = 100 * abs(+DI - -DI) / (+DI + -DI)
```

ADX:

```text
ADX = WilderAverage(DX, N)
```

Yaygın:

```text
N = 14
```

### Kullanım

Kabaca:

```text
ADX < 15-20 → zayıf / range
ADX 20-25 → trend oluşuyor olabilir
ADX > 25 → belirgin trend
ADX > 40 → güçlü trend
```

Eşikler piyasaya göre optimize edilmelidir.

Yön için:

```text
+DI > -DI → bullish directional bias
-DI > +DI → bearish directional bias
```

---

# 6.2 Aroon

## Amaç

Yeni high/low oluşma sıklığı üzerinden trend yönünü ölçmek.

### Veri

`High`, `Low`

### Formül

```text
AroonUp =
(N - periods_since_highest_high) / N * 100

AroonDown =
(N - periods_since_lowest_low) / N * 100
```

### Kullanım

```text
AroonUp > AroonDown → bullish
AroonDown > AroonUp → bearish
```

---

# 6.3 Choppiness Index

## Amaç

Piyasanın trend mi yoksa yatay/range mi olduğunu ayırmak.

### Veri

```text
High
Low
Close
TR
```

### Formül

```text
CI =
100 * log10(
SUM(TR,N) /
(HighestHigh_N - LowestLow_N)
) /
log10(N)
```

Yüksek değer:

```text
choppy / range
```

Düşük değer:

```text
trending
```

Yaygın yorum:

```text
CI > ~61.8 → choppy
CI < ~38.2 → trending
```

Bunlar kesin kurallar değildir.

---

# 7. HACİM

# 7.1 Volume Moving Average

### Amaç

Mevcut hacmin normalden yüksek/düşük olup olmadığını belirlemek.

```text
VolumeMA = SMA(Volume,N)
```

Örneğin:

```text
RelativeVolume = Volume / VolumeMA20
```

### Kullanım

```text
RelativeVolume > 1 → ortalamanın üstü
RelativeVolume > 1.5 → belirgin hacim artışı
```

---

# 7.2 OBV — On Balance Volume

## Amaç

Hacmin fiyat yönüyle birlikte birikimini ölçmek.

### Veri

```text
Close
Volume
```

### Formül

```text
if Close_t > Close_(t-1):
    OBV_t = OBV_(t-1) + Volume_t

if Close_t < Close_(t-1):
    OBV_t = OBV_(t-1) - Volume_t

else:
    OBV_t = OBV_(t-1)
```

### Kullanım

OBV'nin yönü ve fiyatla divergence'ı önemlidir.

```text
price ↑ + OBV ↑ → volume confirmation
price ↑ + OBV ↓ → warning
```

---

# 7.3 VWAP

## Amaç

İşlem hacmiyle ağırlıklandırılmış ortalama fiyat.

### Veri

```text
High
Low
Close
Volume
```

### Typical price

Basit yaklaşım:

```text
TP = (H + L + C) / 3
```

### Formül

```text
VWAP =
SUM(TP * Volume) /
SUM(Volume)
```

Intraday VWAP genellikle her seans başında resetlenir.

### Kullanım

```text
price > VWAP → bullish intraday bias
price < VWAP → bearish intraday bias
```

Kriptoda 24/7 piyasa olduğu için session tanımı açıkça belirtilmelidir.

---

# 7.4 Anchored VWAP

## Amaç

VWAP'ı belirli bir olaydan itibaren başlatmak.

Anchor örnekleri:

- önemli swing low
- swing high
- breakout candle
- haftalık başlangıç
- aylık başlangıç
- büyük haber
- cycle low

### Formül

Anchor'dan itibaren:

```text
AVWAP =
SUM(TP * Volume) /
SUM(Volume)
```

### Kullanım

Özellikle büyük hareketlerin ortalama maliyetini takip etmek için kullanılır.

---

# 7.5 Money Flow Index — MFI

## Amaç

Fiyat + hacim kullanarak para akışını ölçmek.

### Veri

```text
High
Low
Close
Volume
```

### Typical Price

```text
TP = (H + L + C) / 3
```

### Raw Money Flow

```text
RMF = TP * Volume
```

Pozitif/negatif akış, TP'nin önceki TP ile karşılaştırılmasına göre ayrılır.

```text
MoneyRatio =
PositiveMoneyFlow /
NegativeMoneyFlow
```

Sonra:

```text
MFI =
100 - 100/(1 + MoneyRatio)
```

Yaygın:

```text
N = 14
```

---

# 7.6 Chaikin Money Flow — CMF

## Amaç

Fiyatın candle içindeki konumu ve hacmi kullanarak accumulation/distribution ölçmek.

### Veri

```text
High
Low
Close
Volume
```

### Money Flow Multiplier

```text
MFM =
((Close - Low) - (High - Close)) /
(High - Low)
```

### Money Flow Volume

```text
MFV = MFM * Volume
```

### CMF

```text
CMF_N =
SUM(MFV,N) /
SUM(Volume,N)
```

### Kullanım

```text
CMF > 0 → buying pressure
CMF < 0 → selling pressure
```

`High == Low` durumunda bölme hatası engellenmelidir.

---

# 7.7 Volume Profile

## Amaç

Belirli bir fiyat aralığında hangi fiyat seviyelerinde ne kadar hacim işlendiğini görmek.

### İhtiyaç

İdeal olarak:

```text
price-level volume
```

Sadece OHLCV candle verisi varsa gerçek trade-level volume profile elde edilemez; candle hacmini fiyat aralığına dağıtan yaklaşık yöntem kullanılabilir.

### Temel kavramlar

```text
POC = Point of Control
VAH = Value Area High
VAL = Value Area Low
```

POC en yüksek hacimli fiyat seviyesidir.

Value Area, seçilen hacim yüzdesini kapsayan bölgedir. Yaygın oran `%70`.

### Kullanım

- POC → önemli kabul/maliyet seviyesi
- VAH → value area üst sınırı
- VAL → alt sınır
- düşük hacimli bölgeler → hızlı geçiş/reaksiyon bölgeleri

---

# 8. VOLATİLİTE

# 8.1 ATR — Average True Range

## Amaç

Trend yönünü değil, fiyat hareketinin büyüklüğünü ölçmek.

### Veri

```text
High
Low
Close
```

### TR

```text
TR = max(
H-L,
abs(H-PreviousClose),
abs(L-PreviousClose)
)
```

### ATR

Wilder smoothing ile:

```text
ATR_N = WilderAverage(TR,N)
```

Yaygın:

```text
N = 14
```

### Kullanım

Stop mesafesi:

```text
LongStop = Entry - ATR * multiplier
ShortStop = Entry + ATR * multiplier
```

Örneğin 1.5–3 ATR arası değerler kullanılabilir; optimum değer asset/timeframe'e bağlıdır.

Normalized ATR:

```text
ATRPercent = ATR / Close * 100
```

Farklı coinleri karşılaştırmada daha kullanışlıdır.

---

# 8.2 Bollinger Bands

## Amaç

Volatilite ve fiyatın ortalamaya göre konumunu ölçmek.

### Veri

`close`

### Standart

```text
N = 20
K = 2
```

### Formül

```text
Middle = SMA(Close,N)
Std = StandardDeviation(Close,N)

Upper = Middle + K * Std
Lower = Middle - K * Std
```

### Bollinger %B

```text
%B =
(Close - Lower) /
(Upper - Lower)
```

### Band Width

```text
BBWidth =
(Upper - Lower) / Middle
```

### Kullanım

Band width düşükse volatilite sıkışması olabilir.

Breakout teyidinde volume ve trend strength ile birlikte kullanılabilir.

---

# 8.3 Keltner Channels

## Amaç

ATR tabanlı volatilite kanalı.

### Veri

```text
High
Low
Close
```

### Tipik formül

```text
Middle = EMA(Close,20)

Upper = Middle + multiplier * ATR(10)
Lower = Middle - multiplier * ATR(10)
```

Yaygın multiplier:

```text
2
```

### Kullanım

Bollinger Bands ile birlikte squeeze tespiti yapılabilir.

---

# 8.4 Historical Volatility

Log return:

```text
r_t = ln(C_t / C_(t-1))
```

N dönem standart sapması:

```text
HV = StdDev(r,N)
```

Yıllıklandırılmış:

```text
HV_annualized = StdDev(r,N) * sqrt(periods_per_year)
```

Kriptoda `periods_per_year`, timeframe'e göre hesaplanmalıdır.

Örneğin 1H:

```text
24 * 365
```

---

# 9. DESTEK / DİRENÇ

# 9.1 Pivot Points

Klasik günlük pivot için önceki gün:

```text
P = (H + L + C) / 3
```

Sonra:

```text
R1 = 2P - L
S1 = 2P - H

R2 = P + (H-L)
S2 = P - (H-L)

R3 = H + 2(P-L)
S3 = L - 2(H-P)
```

### Veri

Önceki period OHLC.

Günlük, haftalık veya aylık pivot üretilebilir.

---

# 9.2 Previous High / Low

Önceki:

- day high/low
- week high/low
- month high/low

seviyeleri.

Kriptoda liquidity ve breakout analizinde önemlidir.

### Veri

OHLC + timeframe aggregation.

---

# 9.3 Fibonacci Retracement

### Amaç

Bir swing hareketindeki olası geri çekilme bölgelerini hesaplamak.

Yaygın seviyeler:

```text
23.6%
38.2%
50%
61.8%
78.6%
```

Swing low → swing high hareketinde:

```text
Level = High - Ratio * (High-Low)
```

Ters yönde formül yön değiştirilir.

### Kritik nokta

Fibonacci'nin sonucu swing high/low seçimine bağlıdır.

Bu nedenle otomatik sistemde swing algoritması açıkça tanımlanmalıdır.

---

# 9.4 Donchian Channels

## Amaç

Son N periyottaki en yüksek ve en düşük fiyatı takip etmek.

```text
Upper = HighestHigh(N)
Lower = LowestLow(N)
Middle = (Upper + Lower) / 2
```

### Kullanım

```text
Close > Upper(previous) → breakout
Close < Lower(previous) → breakdown
```

Breakout sistemlerinde kullanılabilir.

---

# 10. MARKET STRUCTURE

Bu bölüm klasik indikatörlerden daha önemlidir.

# 10.1 Swing High / Swing Low

Örneğin pivot strength = `L`.

Swing high:

```text
High[t] > High[t-L:t]
High[t] > High[t+1:t+L]
```

Swing low bunun tersidir.

### Parametre

```text
left_bars = L
right_bars = L
```

### Kritik nokta

Sağdaki candle'lar görülmeden swing kesinleşmez.

Bu nedenle canlı sistemde lookahead/repainting engellenmelidir.

---

# 10.2 Higher High / Higher Low

Bullish structure:

```text
HH
HL
HH
HL
```

Bearish:

```text
LH
LL
LH
LL
```

Feature:

```text
market_structure = BULLISH / BEARISH / RANGE
```

---

# 10.3 BOS — Break of Structure

Bullish BOS:

```text
Close > previous confirmed swing high
```

Bearish BOS:

```text
Close < previous confirmed swing low
```

Sadece wick kırılmasını BOS kabul edip etmediğin açıkça tanımlanmalıdır.

Öneri:

```text
body_close_confirmation = true
```

---

# 10.4 CHoCH — Change of Character

Mevcut trend yapısının ilk anlamlı şekilde bozulması.

Örneğin bearish structure:

```text
LH → LL → LH
```

sonrasında fiyat son LH'yi kırarsa:

```text
potential bullish CHoCH
```

CHoCH ile BOS terminolojisi platformlara göre farklı kullanılabildiği için kod içinde kesin tanım yapılmalıdır.

---

# 10.5 Liquidity Sweep

Örnek:

```text
Previous High = 100

Price → 101
Price → 99
Close → 99
```

High sweep oluşmuştur.

Bullish liquidity sweep:

- önceki low altına wick
- sonra seviyenin üzerine kapanış

Bearish liquidity sweep:

- önceki high üzerine wick
- sonra seviyenin altına kapanış

Bu yapı özellikle false breakout tespitinde kullanılabilir.

---

# 10.6 Fair Value Gap — FVG

Üç candle yapısı.

Bullish FVG:

```text
Candle 1 High < Candle 3 Low
```

Candle 2 güçlü yukarı hareket yaratır.

Gap:

```text
Candle1 High → Candle3 Low
```

Bearish FVG:

```text
Candle1 Low > Candle3 High
```

### Feature'lar

```text
FVG size
FVG percentage
age
filled/unfilled
direction
distance from current price
```

---

# 10.7 Order Block

Order Block otomatik olarak tek ve evrensel biçimde tanımlanmış bir indikatör değildir.

Kodlama için kural tanımlanmalıdır.

Örnek bullish OB:

1. güçlü bullish displacement oluşur
2. displacement öncesindeki son bearish candle seçilir
3. candle range zone olarak kaydedilir
4. zone invalidation için tanım yapılır

Örneğin:

```text
bullish OB = last bearish candle before bullish BOS
```

Invalidation:

```text
close < OB_low
```

Bu sadece örnek algoritmadır; farklı OB tanımları mümkündür.

---

# 11. DERIVATIVES DATA

Klasik OHLCV'den ayrı veri kaynağı gerekir.

# 11.1 Open Interest

## Amaç

Vadeli işlemlerde açık pozisyonların toplam nominal büyüklüğünü takip etmek.

### Veri

Exchange API'den:

```text
timestamp
open_interest
```

Mümkünse kontrat türü ve quote currency de tutulmalıdır.

### Kullanım

Örnek kombinasyon:

```text
Price ↑ + OI ↑
→ yeni pozisyonlarla desteklenen hareket

Price ↑ + OI ↓
→ short covering olasılığı

Price ↓ + OI ↑
→ yeni short exposure olasılığı

Price ↓ + OI ↓
→ long liquidation / position closing olasılığı
```

Bunlar tek başına kesin yön sinyali değildir.

### Kritik

Open interest'in coin cinsinden mi USD cinsinden mi olduğu kaydedilmelidir.

---

# 11.2 Funding Rate

## Amaç

Perpetual futures long/short tarafındaki funding mekanizmasını takip etmek.

### Veri

Exchange:

```text
funding_rate
funding_timestamp
```

### Kullanım

Pozitif funding:

```text
longs shortlara ödeme yapıyor
```

Negatif:

```text
shorts longs'a ödeme yapıyor
```

Aşırı funding kalabalık positioning göstergesi olabilir.

Normal/orta funding ise tek başına sinyal değildir.

---

# 11.3 Long/Short Ratio

### Veri

Exchange veya veri sağlayıcısı.

```text
long_accounts
short_accounts
```

veya doğrudan:

```text
long_short_ratio
```

### Kullanım

Kalabalık positioning'i izlemek.

### Kritik

"Account ratio", "position ratio" ve "notional ratio" birbirinden farklı olabilir.

Dataset'e:

```text
ratio_type
```

alanı eklenmelidir.

---

# 11.4 Liquidations

### Veri

Mümkünse trade/event düzeyinde:

```text
timestamp
side
price
quantity
notional
exchange
symbol
```

### Feature'lar

```text
long_liquidation_volume
short_liquidation_volume
total_liquidation_volume
liquidation_zscore
```

Ani liquidation cluster'ları volatilite ve reversal analizinde kullanılabilir.

---

# 11.5 CVD — Cumulative Volume Delta

## Amaç

Aggressive buying/selling imbalance ölçmek.

### İdeal veri

Trade-level:

```text
timestamp
price
quantity
aggressor_side
```

Delta:

```text
Delta =
BuyAggressiveVolume - SellAggressiveVolume
```

CVD:

```text
CVD_t = CVD_(t-1) + Delta_t
```

### Kritik

Sadece OHLCV varsa gerçek CVD hesaplanamaz.

Bazı sistemler candle yönüne göre yaklaşık delta üretir; bu **gerçek order-flow CVD değildir**.

---

# 11.6 Basis

Futures fiyatı ile spot fiyatı arasındaki fark.

Basit:

```text
Basis = FuturesPrice - SpotPrice
```

Yüzde:

```text
BasisPct =
(Futures - Spot) / Spot * 100
```

Annualized basis:

```text
BasisAnnualized =
BasisPct * 365 / DaysToExpiry
```

Perpetual futures için farklı yorum gerekir.

---

# 12. BTC DOMINANCE VE MARKET-WIDE DATA

## BTC Dominance

```text
BTC Dominance =
BTC Market Cap /
Total Crypto Market Cap * 100
```

### Kullanım

Altcoin risk regime'i için kullanılabilir.

Örneğin:

```text
BTC güçlü + dominance yükseliyor
```

altcoinlerin BTC'ye göre relatif zayıf kalabileceği bir regime olabilir.

Ancak bu doğrudan altcoin AL/SAT sinyali değildir.

---

# 13. TOTAL MARKET CAP

Toplam crypto market capitalization.

Feature'lar:

```text
Total Market Cap trend
EMA20/50/200
ROC
RSI
breakout
```

Altcoin piyasası için market regime filtresi olarak kullanılabilir.

---

# 14. STABLECOIN DOMINANCE

Örneğin USDT/USDC gibi stablecoin market cap veya dominance verileri kullanılabilir.

Stablecoin dominance:

```text
Stablecoin Market Cap /
Total Crypto Market Cap
```

Yükseliş genellikle risk-off davranışını incelemek için kullanılan bir feature olabilir.

Tek başına piyasa yönü olarak yorumlanmamalıdır.

---

# 15. MULTI-TIMEFRAME ANALYSIS

Önerilen yapı:

```text
4H = regime
1H = setup
15m = trigger
```

Örneğin:

## 4H

```text
Close > EMA200
EMA50 > EMA200
ADX > 20
```

→ bullish regime.

## 1H

```text
price > VWAP
RSI > 50
MACD histogram rising
```

→ bullish setup.

## 15m

```text
bullish BOS
volume spike
price reclaim VWAP
```

→ trigger.

### Önemli

Higher timeframe verisi lower timeframe'e taşınırken gelecekteki candle bilgisi kullanılmamalıdır.

TradingView/Pine tarafında özellikle:

```text
lookahead_off
```

mantığı korunmalıdır.

---

# 16. FEATURE ENGINE TASARIMI

Her indikatör yalnızca görsel çizgi üretmek yerine normalize edilmiş feature'lar üretmelidir.

Örneğin:

```json
{
  "ema": {
    "ema20": 102.4,
    "ema50": 100.2,
    "ema200": 94.8,
    "price_above_ema200": true,
    "ema50_above_ema200": true
  },
  "rsi": {
    "value": 61.4,
    "above_50": true,
    "slope": 2.3
  },
  "adx": {
    "value": 28.2,
    "plus_di": 31.1,
    "minus_di": 16.7
  }
}
```

Bu yapı daha sonra scoring engine tarafından kullanılabilir.

---

# 17. SİNYAL SCORE SİSTEMİ

İndikatörleri doğrudan "BUY" olarak yorumlamak yerine puanlama kullanılabilir.

Örnek:

```text
TREND
price > EMA200             +2
EMA50 > EMA200             +2
Supertrend bullish         +1

MOMENTUM
RSI > 50                   +1
MACD > Signal              +1

TREND STRENGTH
ADX > 25                   +1

VOLUME
RelativeVolume > 1.5       +1

STRUCTURE
Bullish BOS                +2

DERIVATIVES
OI confirmation             +1
Funding extreme             -1
```

Sonra:

```text
bull_score
bear_score
```

ayrı hesaplanabilir.

Önemli:

**Score = olasılık veya garanti değildir.**

Score sadece feature'ların önceden belirlenmiş ağırlıklı kombinasyonudur.

---

# 18. ÖNERİLEN SIGNAL STATES

Binary:

```text
BUY
SELL
```

yerine:

```text
STRONG_BULLISH
BULLISH
NEUTRAL
BEARISH
STRONG_BEARISH
```

ve ayrıca:

```text
TRENDING
RANGING
TRANSITION
```

kullanılabilir.

Örneğin:

```json
{
  "regime": "TRENDING",
  "direction": "BULLISH",
  "trend_score": 78,
  "momentum_score": 71,
  "volume_score": 82,
  "structure_score": 88,
  "derivatives_score": 63,
  "overall_score": 77
}
```

---

# 19. SIGNAL EXPLANATION

Her sinyal neden üretildiğini açıklamalıdır.

Örnek:

```text
BULLISH SETUP

+ Price above EMA200
+ EMA50 above EMA200
+ ADX 28
+ RSI 61
+ Bullish BOS
+ Volume 1.7x 20-period average
+ OI increasing

Warnings:
- Funding elevated
- Price 1.8 ATR above EMA50
```

Bu, yalnızca:

```text
BUY
```

çıktısından çok daha değerlidir.

---

# 20. FALSE SIGNAL FİLTRELERİ

## 20.1 Low volume

Breakout + düşük volume:

```text
potential weak breakout
```

## 20.2 Low ADX

ADX düşükse trend-following sinyallerinin güvenilirliği azalabilir.

## 20.3 Price too extended

Örneğin:

```text
distance_from_EMA50 / ATR > threshold
```

ise yeni giriş riski artabilir.

## 20.4 Conflicting timeframes

```text
4H bearish
1H bullish
15m bullish
```

→ counter-trend setup olarak işaretlenmeli.

## 20.5 Funding extreme

Aşırı funding crowding riskini artırabilir.

## 20.6 OI divergence

Fiyat ve OI hareketi beklenen yapıyla uyuşmuyorsa warning üretilebilir.

---

# 21. DIVERGENCE ENGINE

RSI, MACD, OBV, CVD gibi göstergeler için divergence hesaplanabilir.

## Bullish divergence

```text
Price: lower low
Indicator: higher low
```

## Bearish divergence

```text
Price: higher high
Indicator: lower high
```

Swing noktaları aynı algoritmayla belirlenmelidir.

Divergence tek başına giriş sinyali olmamalıdır.

---

# 22. DATA QUALITY

Her veri noktasında mümkünse:

```text
timestamp
exchange
symbol
timeframe
source
```

saklanmalıdır.

Türev verilerde:

```text
contract_type
quote_currency
ratio_type
```

gibi metadata önemlidir.

### Eksik veri

Kod:

```text
NaN
null
missing
```

durumlarını açıkça yönetmelidir.

Eksik veri varsa:

```text
signal = unavailable
```

ile:

```text
signal = bearish
```

aynı şey olmamalıdır.

---

# 23. WARM-UP PERIOD

İndikatörler ilk candle'larda güvenilir değildir.

Örneğin EMA200 için en az 200 candle gerekir.

Birden fazla indikatör varsa başlangıçta en uzun lookback + smoothing süresi kadar veri alınmalıdır.

Örneğin:

```text
max_period = 200
```

ise minimum 200+ candle.

Pratikte daha fazla geçmiş alınması tercih edilir.

---

# 24. REPAINTING VE LOOKAHEAD

Coding agent aşağıdaki kurallara uymalıdır:

1. Gelecekteki candle bilgisi kullanılmayacak.
2. Henüz kapanmamış candle sinyali kesinleşmiş kabul edilmeyecek.
3. Swing high/low ancak gerekli sağ taraf candle'ları oluştuktan sonra confirmed kabul edilecek.
4. Higher timeframe data future leakage yapmayacak.
5. Backtest ile live calculation aynı mantığı kullanacak.

Özellikle:

```text
confirmed candle
```

ile:

```text
intrabar provisional signal
```

ayrılmalıdır.

---

# 25. BACKTEST TASARIMI

Sistem değerlendirilirken yalnızca win rate kullanılmamalıdır.

Ölçümler:

```text
Total Trades
Win Rate
Loss Rate
Profit Factor
Expectancy
Average Win
Average Loss
Max Drawdown
Sharpe Ratio
Sortino Ratio
Average Holding Time
Maximum Consecutive Losses
```

Ayrıca:

```text
fees
slippage
funding
spread
```

mümkünse dahil edilmelidir.

Kripto sistemlerinde bunları yok saymak backtest sonucunu yapay biçimde iyileştirebilir.

---

# 26. OVERFITTING

İndikatör sayısını artırmak otomatik olarak sistemi iyileştirmez.

Özellikle kaçınılması gereken:

```text
100 feature
→ historical data
→ optimize thresholds
→ perfect backtest
```

Bu yapı gelecekte çalışmayabilir.

Tercih:

```text
Train period
Validation period
Out-of-sample test
Walk-forward test
```

ve mümkünse farklı coin/timeframe dönemleri.

---

# 27. ÖNERİLEN İLK SÜRÜM

Coding agent ilk sürümde şu feature set ile başlayabilir:

### Trend

```text
EMA20
EMA50
EMA200
Supertrend
Ichimoku
```

### Momentum

```text
RSI14
MACD
StochRSI
```

### Trend strength

```text
ADX14
Aroon
Choppiness
```

### Volume

```text
Relative Volume
OBV
VWAP
MFI
CMF
```

### Volatility

```text
ATR14
ATR%
Bollinger Bands
BB Width
Keltner Channels
```

### Levels

```text
Pivot
Previous Day High/Low
Previous Week High/Low
Donchian
Fibonacci
Volume Profile
```

### Structure

```text
Swing High/Low
HH/HL/LH/LL
BOS
CHoCH
Liquidity Sweep
FVG
Order Block
```

### Derivatives

```text
Open Interest
Funding Rate
Long/Short Ratio
Liquidations
CVD
Basis
```

### Market-wide

```text
BTC Dominance
Total Market Cap
Stablecoin Dominance
```

---

# 28. VERİ KAYNAĞI MATRİSİ

| Feature | OHLC | Volume | Trade | Derivatives | Market Data |
|---|---:|---:|---:|---:|---:|
| EMA | ✓ | | | | |
| SMA | ✓ | | | | |
| Supertrend | ✓ | | | | |
| Ichimoku | ✓ | | | | |
| SAR | ✓ | | | | |
| RSI | ✓ | | | | |
| Stoch RSI | ✓ | | | | |
| MACD | ✓ | | | | |
| CCI | ✓ | | | | |
| Williams %R | ✓ | | | | |
| ROC | ✓ | | | | |
| ADX | ✓ | | | | |
| Aroon | ✓ | | | | |
| Choppiness | ✓ | | | | |
| Relative Volume | | ✓ | | | |
| OBV | ✓ | ✓ | | | |
| VWAP | ✓ | ✓ | | | |
| MFI | ✓ | ✓ | | | |
| CMF | ✓ | ✓ | | | |
| Volume Profile | ✓* | ✓* | | | |
| ATR | ✓ | | | | |
| Bollinger | ✓ | | | | |
| Keltner | ✓ | | | | |
| Historical Volatility | ✓ | | | | |
| Pivot | ✓ | | | | |
| Fibonacci | ✓ | | | | |
| Donchian | ✓ | | | | |
| Market Structure | ✓ | | | | |
| FVG | ✓ | | | | |
| Order Block | ✓ | | | | |
| Open Interest | | | | ✓ | |
| Funding | | | | ✓ | |
| Long/Short | | | | ✓ | |
| Liquidations | | | ✓ | ✓ | |
| CVD | | | ✓ | | |
| Basis | | | | ✓ | ✓ |
| BTC Dominance | | | | | ✓ |
| Total Market Cap | | | | | ✓ |
| Stablecoin Dominance | | | | | ✓ |

`*` Gerçek volume profile için daha ayrıntılı volume/trade dağılımı tercih edilir.

---

# 29. CODING AGENT İÇİN ZORUNLU TASARIM KURALLARI

Coding agent şu prensiplere uymalıdır:

### 1. Her indikatör ayrı fonksiyon/modül

Örnek:

```text
calculate_ema()
calculate_rsi()
calculate_macd()
calculate_adx()
calculate_atr()
calculate_obv()
calculate_vwap()
calculate_market_structure()
calculate_bos()
calculate_fvg()
```

### 2. Ham veri değiştirilmemeli

```text
raw_ohlcv
```

immutable/read-only kabul edilmeli.

### 3. Feature layer

```text
raw data
    ↓
indicator calculations
    ↓
normalized features
    ↓
signal engine
```

### 4. Parametreler hard-code edilmemeli

Örneğin:

```yaml
ema:
  fast: 20
  medium: 50
  slow: 200

rsi:
  period: 14

adx:
  period: 14
  strong_threshold: 25

atr:
  period: 14
```

### 5. Her feature'ın metadata'sı

Örneğin:

```json
{
  "name": "rsi",
  "value": 61.3,
  "timeframe": "1h",
  "timestamp": "...",
  "period": 14,
  "source": "binance"
}
```

### 6. Sinyal ve gösterge birbirinden ayrılmalı

```text
indicator:
    RSI = 61

interpretation:
    bullish_momentum = true

signal:
    BUY = false
```

RSI'nin 61 olması otomatik olarak BUY değildir.

---

# 30. SONUÇ

Bu sistemde en önemli ayrım:

```text
INDICATOR
```

ile

```text
SIGNAL
```

arasındadır.

Örneğin:

```text
RSI = 68
```

bir **ölçümdür**.

```text
RSI > 50
```

bir **feature** olabilir.

```text
RSI > 50 + EMA50 > EMA200 + ADX > 25 + bullish BOS
```

bir **setup** olabilir.

Bunların üzerine:

```text
volume confirmation
OI confirmation
funding filter
risk/volatility filter
```

eklendiğinde daha gelişmiş bir **signal model** oluşur.

Son katman:

```text
Market Regime
      ↓
Trend
      ↓
Momentum
      ↓
Volume
      ↓
Structure
      ↓
Derivatives
      ↓
Volatility
      ↓
Signal Score
      ↓
Risk Management
      ↓
Final Signal
```

olmalıdır.

**Önemli tasarım kararı:** Sistem "kesin AL/SAT" üretmek yerine her sinyalin dayanaklarını, kullanılan timeframe'i, veri kalitesini ve karşıt sinyalleri de döndürmelidir.
