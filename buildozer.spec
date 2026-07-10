[app]

# Uygulama bilgileri
title = E-Posta Araci
package.name = epostaaraci
package.domain = com.favoriteknik

# Kaynak
source.dir = .
source.include_exts = py,png,jpg,kv,atlas,ico
version = 1.0

# Bagimliliklar: mail mantigi saf stdlib; SSL icin openssl, Android icin pyjnius
requirements = python3,kivy==2.3.1,pyjnius,plyer,openssl,certifi

# Ikon
icon.filename = %(source.dir)s/logo.png

# Ekran
orientation = portrait
fullscreen = 0

# Android izinleri: internet SART (mail icin)
android.permissions = INTERNET,ACCESS_NETWORK_STATE

# API seviyeleri
android.api = 33
android.minapi = 24
android.archs = arm64-v8a,armeabi-v7a

# Ekleri baska uygulamalarla acmak icin FileProvider (opsiyonel)
android.add_src =

# Log
log_level = 2

[buildozer]
log_level = 2
warn_on_root = 1
