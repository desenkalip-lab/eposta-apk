# E-Posta Aracı — Android APK Nasıl Yapılır

Android APK'sı **Linux** ortamında derlenir. Windows'ta doğrudan olmaz.
En kolay yol: **Google Colab** (tarayıcıda açılan ücretsiz Linux). Bilgisayarına
hiçbir şey kurmadan, tarayıcıdan APK üretirsin.

## Gerekli dosyalar (bu klasörde)
- `main.py`
- `eposta_cekirdek.py`
- `buildozer.spec`
- `logo.png`

---

## Adım adım (Google Colab)

### 1) Colab'ı aç
https://colab.research.google.com → **Yeni not defteri**

### 2) İlk hücre — sistem araçlarını kur (çalıştır ▶)
```python
!sudo apt update
!sudo apt install -y git zip unzip openjdk-17-jdk autoconf libtool pkg-config \
    zlib1g-dev libncurses5-dev libncursesw5-dev cmake libffi-dev libssl-dev \
    build-essential ccache
!pip install --upgrade buildozer cython==0.29.36 virtualenv
```

### 3) İkinci hücre — dosyaları yükle
```python
from google.colab import files
print("main.py, eposta_cekirdek.py, buildozer.spec, logo.png dosyalarini sec:")
files.upload()
```
(Açılan pencereden 4 dosyayı birden seç.)

### 4) Üçüncü hücre — APK'yı derle
```python
!buildozer -v android debug
```
⏳ **İlk derleme 20–40 dakika** sürer (Android SDK/NDK indirir). Sabırlı ol,
"BUILD SUCCESSFUL" görene kadar bekle.

### 5) Dördüncü hücre — APK'yı indir
```python
from google.colab import files
import glob
apk = glob.glob('bin/*.apk')[0]
print("Indiriliyor:", apk)
files.download(apk)
```

---

## Telefona kurma
1. İnen `.apk` dosyasını telefona at (kablo, Drive, WhatsApp vb.).
2. Dosyaya dokun → "Bilinmeyen kaynaklardan yüklemeye izin ver" (bir kez).
3. **Yükle** → aç.
4. İlk açılışta **Ayarlar** ekranı gelir → hesabını ekle (Gmail/Hotmail için
   **uygulama şifresi** gerekir, tıpkı masaüstündeki gibi).

---

## Notlar
- Aynı hesaplar, aynı mail mantığı (masaüstüyle `eposta_cekirdek.py` ortak).
- Ayarlar telefonun kendi özel klasöründe saklanır (ayarlar.json).
- Derleme hata verirse: hücrenin çıktısındaki son ~30 satırı bana gönder,
  birlikte çözelim (genelde tek satırlık bir eksik paket olur).
- SSL/sertifika hatası olursa `buildozer.spec` içindeki `requirements`'a
  `certifi` zaten ekli; gerekirse ince ayar yaparız.

## Alternatif
WSL (Windows'ta Linux) veya GitHub Actions ile de derlenebilir. İstersen
GitHub Actions için hazır bir workflow dosyası da hazırlayabilirim (push'layınca
otomatik APK üretir).
