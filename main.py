# -*- coding: utf-8 -*-
"""
E-Posta Aracı — çökme-GÜVENLİ giriş noktası.

Asıl uygulama app_gui.py'de. Burada tek amaç: açılışta (import dahil) NE olursa
olsun uygulama sessizce kapanmasın; tam hatayı EKRANDA göstersin (telefonda
logcat okumak zor) ve mümkünse bir dosyaya yazsın. Böylece kullanıcı ekranın
fotoğrafını çekip bize gönderebilir.
"""
import traceback


def _dosyaya_yaz(iz):
    import os
    yerler = []
    try:
        from jnius import autoclass                      # Android
        Env = autoclass("android.os.Environment")
        try:
            kok = Env.getExternalStorageDirectory().getAbsolutePath()
            yerler.append(os.path.join(kok, "eposta_hata.txt"))
        except Exception:
            pass
        try:
            ind = Env.getExternalStoragePublicDirectory(
                Env.DIRECTORY_DOWNLOADS).getAbsolutePath()
            yerler.append(os.path.join(ind, "eposta_hata.txt"))
        except Exception:
            pass
    except Exception:
        pass
    yerler.append(os.path.join(os.path.expanduser("~"), "eposta_hata.txt"))
    for y in yerler:
        try:
            with open(y, "w", encoding="utf-8") as f:
                f.write(iz)
        except Exception:
            pass


def _hatayi_goster(iz):
    """Kivy ile minimal bir ekranda hatayı gösterir (uygulama açık kalır)."""
    from kivy.app import App
    from kivy.uix.scrollview import ScrollView
    from kivy.uix.label import Label
    from kivy.metrics import dp
    from kivy.core.window import Window

    Window.clearcolor = (1, 1, 1, 1)

    class _HataApp(App):
        def build(self):
            self.title = "E-Posta Aracı — Hata"
            sv = ScrollView()
            l = Label(text="AÇILIŞ HATASI (fotoğrafını çek):\n\n" + iz,
                      color=(0.85, 0.1, 0.1, 1), font_size="12sp",
                      halign="left", valign="top", size_hint_y=None,
                      padding=(dp(12), dp(12)))
            l.bind(width=lambda w, v: setattr(l, "text_size", (l.width - dp(20), None)),
                   texture_size=lambda w, v: setattr(l, "height", l.texture_size[1]))
            sv.add_widget(l)
            return sv
    _HataApp().run()


try:
    import app_gui
    app_gui.EpostaApp().run()
except Exception:
    _iz = traceback.format_exc()
    try:
        _dosyaya_yaz(_iz)
    except Exception:
        pass
    try:
        _hatayi_goster(_iz)
    except Exception:
        # Kivi ile bile gösterilemiyorsa en azından logcat'e bas.
        print("EPOSTA ACILIS HATASI:\n" + _iz)
