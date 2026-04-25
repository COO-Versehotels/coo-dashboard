# Verse Hotels — Review Performance Dashboard

Dashboard untuk monitoring rating & review 4 unit Verse Hotels Group di 5 OTA platform (Agoda, Booking.com, Traveloka, Trip.com, Tiket.com).

🌐 **Live Dashboard:** https://coo-versehotels.github.io/coo-dashboard/

## 🏨 Unit yang Dimonitor

| Hotel | Lokasi |
|---|---|
| Verse Lite Gajah Mada | Central Jakarta |
| Verse Luxe Wahid Hasyim | Central Jakarta |
| Verse Cirebon | Cirebon |
| Oak Tree Mahakam Blok M | South Jakarta |

## 🤖 Automation

Scraping berjalan **otomatis tiap 2 jam** via GitHub Actions di cloud server (gratis untuk public repo). Tidak perlu laptop nyala.

**Schedule:** Setiap 2 jam pada menit ke-15 (WIB)
- 06:15, 08:15, 10:15, 12:15, 14:15, 16:15, 18:15, 20:15, 22:15, 00:15, 02:15, 04:15

Setiap run akan:
1. Scrape 5 platform untuk 4 hotel
2. Update `data.json` (snapshot hari ini) + `history.json` (akumulasi histori)
3. Auto-commit ke repo
4. Trigger rebuild GitHub Pages (dashboard refresh otomatis)

## 📁 File Structure

```
coo-dashboard/
├── agoda_collector.py        # Python scraper utama
├── data.json                 # Output: data hari ini (di-update tiap 2 jam)
├── history.json              # Output: histori per tanggal
├── error_log.txt             # Output: log error
├── index.html                # Dashboard frontend
├── .gitignore
├── README.md
└── .github/
    └── workflows/
        └── scrape.yml        # GitHub Actions config
```

## 🛠️ Manual Run (Untuk Testing)

Jalankan scraper langsung dari GitHub:

1. Buka tab **Actions** di repo
2. Pilih workflow **"Auto Scrape Reviews"**
3. Klik **"Run workflow"** → **"Run workflow"**
4. Tunggu ~3-5 menit, cek hasilnya

## 🔧 Troubleshooting

### Workflow gagal dengan error "Resource not accessible by integration"
→ Buka **Settings** → **Actions** → **General** → scroll ke "Workflow permissions" → pilih **"Read and write permissions"** → Save

### Banyak data N/A di dashboard
→ Cek tab **Actions** untuk lihat run terakhir. Kalau ada error, download artifact `error-log` untuk debug.

### Dashboard tidak update setelah scraping sukses
→ Cek tab **Settings** → **Pages**. Pastikan source = "Deploy from a branch", branch = "main", folder = "/ (root)".

## 📊 v2 Improvements (Apr 2026)

- ✅ Exponential backoff retry (5s → 15s → 45s)
- ✅ Network-aware retry (extra delay untuk `NETWORK_IO_SUSPENDED`)
- ✅ Hotel-level cooldown (jeda 30s setelah 3 platform berturut error)
- ✅ Inter-hotel delay (3 detik antar hotel)
- ✅ GitHub Actions automation (tidak perlu laptop nyala)

## 📝 License

Internal use only — Verse Hotels Group.
