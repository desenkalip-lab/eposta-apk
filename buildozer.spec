[app]

# Uygulama bilgileri
title = E-Posta Araci
package.name = epostaaraci
package.domain = com.favoriteknik

# Kaynak
source.dir = .
source.include_exts = py,png,jpg,kv,atlas,ico
source.exclude_dirs = .github, __pycache__, .buildozer, bin, dist
version = 1.0
android.numeric_version = 1

# Bagimliliklar (Favori Mesaj'in CALISAN tarifiyle ayni)
requirements = python3,kivy==2.3.1,pyjnius,plyer,android,openssl,certifi

# Ikon
icon.filename = %(source.dir)s/logo.png
presplash.filename = %(source.dir)s/logo.png

# Ekran
orientation = portrait
fullscreen = 0

# Android izinleri: internet SART (mail icin)
android.permissions = INTERNET,ACCESS_NETWORK_STATE

# SDK lisansini otomatik kabul et (CI'da elle onay yok)
android.accept_sdk_license = True

# API seviyeleri
android.api = 33
android.minapi = 24
android.archs = arm64-v8a,armeabi-v7a
android.debug_artifact = apk

# Log
log_level = 2

[buildozer]
log_level = 2
warn_on_root = 1
