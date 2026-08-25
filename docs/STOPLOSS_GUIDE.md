# Panduan Stop Loss untuk Pemula di POEMS

> Cara pasang stop loss otomatis di POEMS (Phillip Securities Indonesia)
> untuk melindungi modal Anda.

---

## Apa itu Stop Loss?

**Stop Loss** adalah order otomatis yang **menjual saham Anda** kalau harga turun ke level tertentu. Fungsinya: **batas kerugian**.

Contoh:
- Anda beli BBRI di Rp 4.500
- Engine kasih SL di Rp 4.300
- Kalau harga turun ke 4.300, sistem otomatis jual → Anda rugi Rp 200/saham
- Tanpa SL, harga bisa turun ke 4.000 → Anda rugi Rp 500/saham

**Kenapa wajib?** Karena manusia cenderung "harap" harga balik naik. SL memaksa Anda keluar sesuai plan.

---

## Cara Pasang Stop Loss di POEMS

### Step 1: Login POEMS
1. Buka https://www.poems.co.id
2. Login dengan username dan password Anda

### Step 2: Buka Order Entry
1. Klik menu **Order** atau **Trade**
2. Pilih **Sell** (karena SL adalah order jual)

### Step 3: Isi Order Stop Loss
| Field | Isi | Contoh |
|---|---|---|
| Stock | Ticker saham | BBRI |
| Order Type | **Stop Loss** atau **Stop Limit** | Stop Limit |
| Quantity | Jumlah lot Anda | 10 lots (1000 saham) |
| Stop Price | Harga SL dari engine | 4300 |
| Limit Price | Harga minimal jual | 4290 (sedikit di bawah stop) |

**Kenapa Stop Limit (bukan Stop Market)?**
- Stop Limit = jual di harga spesifik, tidak lebih buruk dari limit price
- Stop Market = jual di harga apa pun (bisa di harga sangat rendah saat gap down)
- Untuk pemula, **Stop Limit lebih aman** karena tahu pasti harga jual minimal

### Step 4: Submit
1. Klik **Submit** atau **Place Order**
2. Cek status order → harus **Active** atau **Queued**
3. Order akan otomatis eksekusi kalau harga tembus stop price

---

## Cara Baca Trade Plan dari Engine

Engine kasih output seperti ini:
```
Entry: Rp 2.610 | SL: Rp 2.600 | TP1: Rp 2.780 | TP2: Rp 3.205 | R/R: 17.41
```

Artinya:

| Field | Nilai | Tindakan di POEMS |
|---|---|---|
| **Entry** | Rp 2.610 | Beli di harga ini (Limit Buy) |
| **SL** | Rp 2.600 | Pasang Stop Loss Sell di sini |
| **TP1** | Rp 2.780 | Pasang Limit Sell (ambil profit 1) |
| **TP2** | Rp 3.205 | Pasang Limit Sell (ambil profit 2) |
| **R/R** | 17.41 | Risk/reward ratio (harus >= 1.5) |

### Urutan Pasang Order

```
1. BELI: Limit Buy di Entry price
2. SL: Stop Limit Sell di SL price (setelah beli terisi)
3. TP1: Limit Sell di TP1 price (50-70% dari posisi)
4. TP2: Limit Sell di TP2 price (sisanya)
```

---

## Contoh Praktis

**Modal:** Rp 10.000.000
**RISK:** 2% = Rp 200.000 (max kerugian per trade)
**Saham:** BBRI, Entry Rp 4.500, SL Rp 4.300

Engine hitung:
- Risk per share = 4.500 - 4.300 = Rp 200
- Max shares = 200.000 / 200 = 1.000 saham = 10 lots
- Position size: 10 lots

Di POEMS:
1. **Beli** 10 lots BBRI di harga 4.500 (Limit Buy)
2. Setelah beli terisi, pasang:
   - **Stop Loss Sell** 10 lots di stop 4.300, limit 4.290
   - **Limit Sell** 5-7 lots di TP1 (misal 4.800)
   - **Limit Sell** 3-5 lots di TP2 (misal 5.000)

---

## Tips Penting untuk Pemula

### 1. Selalu Pasang SL Setelah Beli
**Jangan menunda.** Begitu order beli terisi, langsung pasang SL. Kalau tidak, Anda tidak ada proteksi.

### 2. Jangan Pindah SL Lebih Jauh
Kalau harga turun ke dekat SL, **jangan pindah SL ke bawah** dengan harapan harga balik. Itu = menambah resiko.

Boleh: pindah SL ke atas (trailing stop) kalau harga sudah naik.
Tidak boleh: pindah SL ke bawah kalau harga turun.

### 3. Auto-Reject (ARA/ARB)
BEI punya batas harga harian:
- **ARA** (Auto Reject Atas): harga naik maksimal → beli tidak bisa
- **ARB** (Auto Reject Bawah): harga turun maksimal → jual tidak bisa

Kalau ARB aktif, order SL Anda **tidak bisa dieksekusi** hari itu. Harga lanjut turun besoknya. Ini resiko BEI yang tidak bisa dihindari 100%.

**Tips:** Pilih saham likuid (BBCA, BBRI, TLKM) dimana ARA/ARB jarang terjadi.

### 4. Jangan Liquidate Semua di TP1
Ambil 50-70% di TP1, sisanya biarkan ke TP2. Kalau trend kuat, TP2 bisa jauh lebih untung.

### 5. Catat Setiap Trade
Buat spreadsheet sederhana:
| Date | Ticker | Entry | SL | TP1 | TP2 | Lots | Result | Reason |
|---|---|---|---|---|---|---|---|---|
| 2026-01-15 | BBRI | 4500 | 4300 | 4800 | 5000 | 10 | ? | Breakout |

Engine punya backtest feature untuk evaluasi performance secara historis.

---

## Yang Engine Lakukan vs Yang Anda Lakukan

| Engine | Anda di POEMS |
|---|---|
| Analisis saham, deteksi setup | Buka POEMS |
| Hitung Entry, SL, TP, position sizing | Input order beli di Entry |
| Kirim email sinyal BUY/SELL | Pasang SL setelah beli terisi |
| Monitor thesis dan setup status | Pasang TP1 dan TP2 |
| Decision SELL → exit signal | Jual manual atau SL kena |

---

## FAQ Stop Loss

**Q: Kalau harga gap down di atas SL saya, apa yang terjadi?**
A: Untuk Stop Limit: order tidak dieksekusi (limit price tidak tercapai). Anda harus jual manual.
Untuk Stop Market: order dieksekusi di harga apa pun (bisa jauh di bawah SL).

**Q: Berapa lama SL order berlaku di POEMS?**
A: Biasanya 1 hari trading (Good Till Day). Kalau mau lebih lama, pilih **GTC** (Good Till Cancelled).

**Q: Bisa pasang SL sebelum beli?**
A: Tidak. Pasang SL setelah order beli terisi (position sudah ada).

**Q: Kalau engine bilang SELL, tapi harga di atas Entry saya, harus jual?**
A: Engine kasih sinyal SELL berarti ada alasan (structural invalidation atau opposing setup). Tapi kalau masih untung, Anda boleh: (1) jual semua, (2) jual sebagian, (3) rapat SL. Keputusan tetap di tangan Anda.

---

*Disclaimer: Panduan ini bersifat edukatif. Setiap keputusan investasi dan risiko tanggung jawab pengguna.*
