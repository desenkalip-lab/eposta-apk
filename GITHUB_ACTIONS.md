# Otomatik APK — GitHub Actions

Bu klasörü bir GitHub deposuna yükleyince, **her push'ta APK otomatik derlenir**
ve indirebileceğin bir dosya olarak yayınlanır. Bilgisayarına hiçbir şey kurmana
gerek yok; derlemeyi GitHub'ın sunucuları (ücretsiz) yapar.

## Bir kerelik kurulum

### 1) GitHub hesabı
Yoksa: https://github.com → ücretsiz hesap aç.

### 2) Yeni depo (repository) oluştur
- Sağ üst **+** → **New repository**
- İsim: `eposta-android`  ·  **Private** (özel) seçebilirsin
- **Create repository**

### 3) Dosyaları yükle
**Kolay yol (tarayıcıdan):**
- Depo sayfasında **"uploading an existing file"** bağlantısına tıkla
- Şu dosyaları sürükle-bırak: `main.py`, `eposta_cekirdek.py`, `buildozer.spec`,
  `logo.png`, `.gitignore`
- **Commit changes**
- Sonra `.github/workflows/build-apk.yml` için: **Add file → Create new file**,
  dosya adına aynen `.github/workflows/build-apk.yml` yaz, içeriğini yapıştır, commit.

**Ya da git ile (bilgisayardan):**
```bash
cd "D:\MASA ÜSTÜ\E-Posta Android"
git init
git add .
git commit -m "E-Posta Android ilk sürüm"
git branch -M main
git remote add origin https://github.com/KULLANICI_ADIN/eposta-android.git
git push -u origin main
```

### 4) Derleme otomatik başlar
- Depoda üstteki **Actions** sekmesine gir.
- "APK Derle" işini göreceksin (⏳ ilk sefer ~25-40 dk).
- Yeşil ✓ olunca biter.

## APK'yı indirme
İki yerden alabilirsin:
- **Releases** (depo sağ tarafı) → en son "E-Posta Aracı APK" → `.apk` dosyasını indir.
- Ya da **Actions** → ilgili çalışma → aşağıda **Artifacts → eposta-apk**.

## Telefona kurma
1. `.apk`'yı telefona at (Drive/WhatsApp/kablo).
2. Dokun → "Bilinmeyen kaynaklara izin ver" (bir kez).
3. Yükle → aç → Ayarlar'dan hesabını ekle.

## Güncelleme
Kodda değişiklik olunca dosyayı depoya tekrar yükle (veya `git push`) →
**yeni APK otomatik üretilir**. Bu yüzden "push'layınca otomatik APK".

---
İstersen bu depoyu senin için ben de oluşturup ilk push'u yapabilirim —
GitHub hesabının bu bilgisayarda `gh` (GitHub CLI) ile bağlı olması yeterli.
