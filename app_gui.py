# -*- coding: utf-8 -*-
"""
E-Posta Aracı — Android (Kivy) arayüzü.
Mail mantığı eposta_cekirdek.py'de (masaüstüyle aynı). Bu dosya sadece arayüz.
"""

import os
import threading
import webbrowser

try:
    from plyer import notification as _plyer_notif
except Exception:
    _plyer_notif = None
try:
    from plyer import filechooser as _plyer_files
except Exception:
    _plyer_files = None

from kivy.app import App
from kivy.clock import Clock
from kivy.metrics import dp
from kivy.core.window import Window
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.gridlayout import GridLayout
from kivy.uix.scrollview import ScrollView
from kivy.uix.label import Label
from kivy.uix.button import Button
from kivy.uix.textinput import TextInput
from kivy.uix.spinner import Spinner
from kivy.uix.screenmanager import ScreenManager, Screen, SlideTransition
from kivy.uix.popup import Popup
from kivy.uix.switch import Switch
from kivy.base import ExceptionHandler, ExceptionManager
try:
    from kivy.core.clipboard import Clipboard   # Android'de sağlayıcı patlarsa uygulama açılmasın diye korumalı
except Exception:
    Clipboard = None

import eposta_cekirdek as c


def _hata_dosyaya_yaz(iz):
    """Hata izini bulunabilecek yerlere yazmayı dener (Android + ev dizini)."""
    yerler = []
    try:
        from jnius import autoclass
        Env = autoclass("android.os.Environment")
        try:
            yerler.append(os.path.join(
                Env.getExternalStorageDirectory().getAbsolutePath(), "eposta_hata.txt"))
        except Exception:
            pass
        try:
            yerler.append(os.path.join(Env.getExternalStoragePublicDirectory(
                Env.DIRECTORY_DOWNLOADS).getAbsolutePath(), "eposta_hata.txt"))
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


class _CalismaHatasiYakala(ExceptionHandler):
    """Açılış/olay-döngüsü hatalarını yakalar: uygulamayı KAPATMAZ, hatayı
    canlı pencerede gösterir. Telefonda logcat okumak zor olduğu için şart."""
    def handle_exception(self, inst):
        import traceback
        iz = traceback.format_exc()
        _hata_dosyaya_yaz(iz)
        try:
            app = App.get_running_app()
            if app is not None:
                app._hatayi_ekranda_goster(iz)
        except Exception:
            pass
        return ExceptionManager.PASS

PRIMARY = (0.31, 0.275, 0.898, 1)      # #4f46e5
PRIMARY_D = (0.263, 0.22, 0.792, 1)    # #4338ca
BG = (0.933, 0.945, 0.972, 1)          # #eef1f8
CARD = (1, 1, 1, 1)
TEXT = (0.067, 0.094, 0.153, 1)        # #111827
MUTED = (0.42, 0.447, 0.5, 1)          # #6b7280
LINK = (0.114, 0.306, 0.847, 1)        # #1d4ed8
LINE = (0.898, 0.906, 0.922, 1)

ROL_AD = {"inbox": "Gelen Kutusu", "sent": "Gönderilmiş",
          "self": "Kendime", "trash": "Silinmiş"}


def duz_dugme(metin, renk=PRIMARY, yazi=(1, 1, 1, 1), boy=48, **kw):
    kw.setdefault("font_size", "15sp")
    b = Button(text=metin, size_hint_y=None, height=dp(boy),
               background_normal="", background_color=renk, color=yazi, **kw)
    return b


class Kart(BoxLayout):
    """Beyaz zeminli, dolgulu kutu."""
    def __init__(self, **kw):
        super().__init__(**kw)
        self.orientation = "vertical"
        from kivy.graphics import Color, Rectangle
        with self.canvas.before:
            Color(*CARD)
            self._r = Rectangle(pos=self.pos, size=self.size)
        self.bind(pos=self._g, size=self._g)

    def _g(self, *a):
        self._r.pos = self.pos
        self._r.size = self.size


class EpostaApp(App):
    def build(self):
        # Açılışta herhangi bir şey patlarsa uygulama sessizce kapanmasın;
        # hatayı EKRANDA göster (telefonda logcat okumak zor).
        # Olay-döngüsü (Clock, dokunma) hatalarını da yakala:
        try:
            ExceptionManager.add_handler(_CalismaHatasiYakala())
        except Exception:
            pass
        try:
            return self._build_ic()
        except Exception:
            import traceback
            iz = traceback.format_exc()
            try:
                with open(os.path.join(self.user_data_dir, "acilis_hatasi.txt"),
                          "w", encoding="utf-8") as f:
                    f.write(iz)
            except Exception:
                pass
            sv = ScrollView()
            lbl = Label(text="AÇILIŞ HATASI:\n\n" + iz, color=(0.85, 0.1, 0.1, 1),
                        font_size="12sp", halign="left", valign="top", size_hint_y=None,
                        padding=(dp(10), dp(10)))
            lbl.bind(width=lambda w, v: setattr(lbl, "text_size", (lbl.width, None)),
                     texture_size=lambda w, v: setattr(lbl, "height", lbl.texture_size[1]))
            sv.add_widget(lbl)
            return sv

    def _hatayi_ekranda_goster(self, iz):
        """Olay-döngüsü hatasını canlı pencerede, kapanmadan gösterir (bir kez)."""
        if getattr(self, "_hata_pop_acik", False):
            return
        self._hata_pop_acik = True
        try:
            icerik = BoxLayout(orientation="vertical", padding=dp(8), spacing=dp(6))
            sv = ScrollView()
            lbl = Label(text="ÇALIŞMA HATASI (fotoğrafını çek):\n\n" + iz,
                        color=(0.85, 0.1, 0.1, 1), font_size="12sp",
                        halign="left", valign="top", size_hint_y=None)
            lbl.bind(width=lambda w, v: setattr(lbl, "text_size", (lbl.width - dp(16), None)),
                     texture_size=lambda w, v: setattr(lbl, "height", lbl.texture_size[1]))
            sv.add_widget(lbl)
            icerik.add_widget(sv)
            pop = Popup(title="Hata", content=icerik, size_hint=(0.97, 0.95),
                        auto_dismiss=False)
            kapat = duz_dugme("Kapat", PRIMARY, boy=46)

            def _kapat(*a):
                self._hata_pop_acik = False
                pop.dismiss()
            kapat.bind(on_release=_kapat)
            icerik.add_widget(kapat)
            pop.open()
        except Exception:
            self._hata_pop_acik = False

    def _build_ic(self):
        self.title = "E-Posta Aracı"
        Window.clearcolor = BG
        # Ayar dosyası: uygulamanın özel klasörü
        c.ayar_yolu_ayarla(self.user_data_dir)
        self.cfg = c.yapilandirma_yukle()
        self.aktif_rol = "inbox"
        self.liste_cache = {}         # rol -> (folder, [mesaj])
        self.acik_mesaj = None
        self._sec_uid = None
        self._compose_ekler = []      # gönderilecek dosya yolları
        self._haber_yukle()

        kok = BoxLayout(orientation="vertical")
        kok.add_widget(self._ust_bar())
        self.sm = ScreenManager(transition=SlideTransition(duration=0.15))
        self.sm.add_widget(self._ekran_liste())
        self.sm.add_widget(self._ekran_mesaj())
        self.sm.add_widget(self._ekran_gonder())
        self.sm.add_widget(self._ekran_ayarlar())
        kok.add_widget(self.sm)
        kok.add_widget(self._alt_bar())

        self._hesap_spinner_guncelle()
        Clock.schedule_once(lambda dt: self._acilis(), 0.3)
        return kok

    # ---- durum ----
    @property
    def ayar(self):
        h = self.cfg["hesaplar"]
        a = self.cfg["aktif"]
        return h[a] if 0 <= a < len(h) else {}

    def _acilis(self):
        if c.kimlik_var(self.ayar):
            self.git("liste")
            self.yenile()
        else:
            self.git("ayarlar")

    def git(self, ekran):
        self.sm.current = ekran

    def _durum(self, metin):
        self.lbl_durum.text = metin

    # ---- arka plan iş ----
    def arka(self, fn, tamam, hata=None):
        def isi():
            try:
                sonuc = fn()
                Clock.schedule_once(lambda dt: tamam(sonuc), 0)
            except Exception as e:
                msg = f"{type(e).__name__}: {e}"
                Clock.schedule_once(lambda dt: (hata or self._genel_hata)(msg), 0)
        threading.Thread(target=isi, daemon=True).start()

    def _genel_hata(self, msg):
        self._durum("Hata.")
        self.uyari("Hata", msg + c.auth_ipucu(msg))

    # ---- bildirim (önemli/anahtar) ----
    def _haber_yukle(self):
        email = c.eposta_adresi(self.ayar.get("eposta", ""))
        self._haber_gorulen = set(self.cfg.get("haber_gorulen", {}).get(email, []))

    def _haber_kaydet(self):
        email = c.eposta_adresi(self.ayar.get("eposta", ""))
        if not email:
            return
        self.cfg.setdefault("haber_gorulen", {})[email] = list(self._haber_gorulen)[-3000:]
        try:
            c.yapilandirma_kaydet(self.cfg)
        except Exception:
            pass

    def _bildir(self, yeni):
        # yeni: [(m, mhim, mkey), ...]
        if not yeni:
            return
        baslik = f"🔔 {len(yeni)} önemli mesaj"
        satir = []
        for m, mhim, mkey in yeni[:4]:
            satir.append(f"{'⭐' if mhim else ''}{'🔔' if mkey else ''} {m.get('from','')[:30]} — {m.get('subject','')[:30]}")
        mesaj = "\n".join(satir)
        if _plyer_notif is not None:
            try:
                _plyer_notif.notify(title=baslik, message=mesaj, app_name="E-Posta Aracı", timeout=8)
                return
            except Exception:
                pass
        # yedek: uygulama içi kısa uyarı
        self.uyari(baslik, mesaj)

    # ---- üst bar ----
    def _ust_bar(self):
        from kivy.graphics import Color, Rectangle
        bar = BoxLayout(size_hint_y=None, height=dp(54), padding=(dp(10), dp(6)), spacing=dp(6))
        with bar.canvas.before:
            Color(*PRIMARY)
            r = Rectangle(pos=bar.pos, size=bar.size)
        bar.bind(pos=lambda *a: setattr(r, "pos", bar.pos),
                 size=lambda *a: setattr(r, "size", bar.size))
        bar.add_widget(Label(text="✉", font_size="22sp", size_hint_x=None, width=dp(30)))
        self.sp_hesap = Spinner(text="hesap", values=[], size_hint_x=1,
                                background_normal="", background_color=PRIMARY_D,
                                color=(1, 1, 1, 1), font_size="14sp")
        self.sp_hesap.bind(text=self._hesap_secildi)
        bar.add_widget(self.sp_hesap)
        yb = duz_dugme("⟳", PRIMARY_D, boy=42, size_hint_x=None, width=dp(46), font_size="20sp")
        yb.bind(on_release=lambda *a: self.yenile())
        bar.add_widget(yb)
        return bar

    def _alt_bar(self):
        bar = BoxLayout(size_hint_y=None, height=dp(52), spacing=dp(2))
        for etiket, ekran in (("📥 Gelen", "liste"), ("✉ Gönder", "gonder"), ("⚙ Ayarlar", "ayarlar")):
            b = duz_dugme(etiket, (0.12, 0.16, 0.22, 1), boy=52)
            b.bind(on_release=lambda w, e=ekran: self._alt_git(e))
            bar.add_widget(b)
        return bar

    def _alt_git(self, ekran):
        if ekran == "liste":
            self.aktif_rol = "inbox"
            self._rol_spinner_ayar()
        self.git(ekran)
        if ekran == "gonder":
            self._gonder_temizle()

    # ---- hesap spinner ----
    def _hesap_etiket(self, h):
        return h.get("eposta") or "(adsız)"

    def _hesap_spinner_guncelle(self):
        etiketler = [self._hesap_etiket(h) for h in self.cfg["hesaplar"]]
        self.sp_hesap.values = etiketler
        a = self.cfg["aktif"]
        self.sp_hesap.text = etiketler[a] if 0 <= a < len(etiketler) else "hesap yok"

    def _hesap_secildi(self, spinner, deger):
        for i, h in enumerate(self.cfg["hesaplar"]):
            if self._hesap_etiket(h) == deger and i != self.cfg["aktif"]:
                self.cfg["aktif"] = i
                c.yapilandirma_kaydet(self.cfg)
                self.liste_cache.clear()
                self._haber_yukle()
                if self.sm.current == "liste":
                    self.yenile()
                break

    # ================= EKRAN: LİSTE =================
    def _ekran_liste(self):
        ek = Screen(name="liste")
        dis = BoxLayout(orientation="vertical")
        # klasör seçici
        ust = BoxLayout(size_hint_y=None, height=dp(44), padding=(dp(8), dp(4)), spacing=dp(6))
        self.sp_rol = Spinner(text="Gelen Kutusu",
                              values=[ROL_AD[r] for r in ("inbox", "sent", "self", "trash")],
                              background_normal="", background_color=(0.9, 0.91, 0.95, 1),
                              color=TEXT, font_size="14sp")
        self.sp_rol.bind(text=self._rol_secildi)
        ust.add_widget(self.sp_rol)
        self.btn_cop = duz_dugme("🧹 Çöpü Boşalt", (0.882, 0.114, 0.282, 1), boy=40,
                                 size_hint_x=None, width=dp(130), font_size="12sp", opacity=0)
        self.btn_cop.bind(on_release=lambda *a: self._cop_bosalt())
        self.btn_cop.disabled = True
        ust.add_widget(self.btn_cop)
        dis.add_widget(ust)
        # liste
        sv = ScrollView()
        self.liste_grid = GridLayout(cols=1, size_hint_y=None, spacing=dp(1), padding=(0, 0))
        self.liste_grid.bind(minimum_height=self.liste_grid.setter("height"))
        sv.add_widget(self.liste_grid)
        dis.add_widget(sv)
        self.lbl_durum = Label(text="Hazır.", size_hint_y=None, height=dp(26),
                               color=MUTED, font_size="12sp")
        dis.add_widget(self.lbl_durum)
        ek.add_widget(dis)
        return ek

    def _rol_ad_ters(self, ad):
        for r, a in ROL_AD.items():
            if a == ad:
                return r
        return "inbox"

    def _rol_secildi(self, spinner, ad):
        self.aktif_rol = self._rol_ad_ters(ad)
        self._cop_ui()
        self.yenile()

    def _rol_spinner_ayar(self):
        self.sp_rol.text = ROL_AD.get(self.aktif_rol, "Gelen Kutusu")
        self._cop_ui()

    def _cop_ui(self):
        cop = (self.aktif_rol == "trash")
        self.btn_cop.opacity = 1 if cop else 0
        self.btn_cop.disabled = not cop

    def _cop_bosalt(self):
        ayar = dict(self.ayar)

        def onayla(evet):
            if not evet:
                return
            self._durum("Çöp boşaltılıyor…")
            self.arka(lambda: c.cop_bosalt(ayar),
                      lambda n: (self._durum(f"{n} mesaj kalıcı silindi."), self.yenile()))
        self.onay("Çöpü Boşalt", "Silinmiş kutusundaki TÜM mesajlar kalıcı silinsin mi?", onayla)

    def yenile(self):
        if not c.kimlik_var(self.ayar):
            self.uyari("Eksik", "Önce Ayarlar'dan hesap ekle.")
            self.git("ayarlar")
            return
        rol = self.aktif_rol
        self._durum(f"{ROL_AD[rol]} yükleniyor…")
        self.liste_grid.clear_widgets()
        ayar = dict(self.ayar)
        self.arka(lambda: c.klasor_listele(ayar, rol, 30),
                  lambda sonuc: self._liste_doldur(rol, sonuc))

    def _liste_doldur(self, rol, sonuc):
        folder, liste = sonuc
        if folder is None:
            self._durum(f"{ROL_AD[rol]} klasörü bulunamadı.")
            return
        self.liste_cache[rol] = (folder, liste)
        engelli = set(self.cfg.get("engelli", []))
        onemli = set(self.cfg.get("onemli", []))
        gosterilen = 0
        haber_yeni = []
        for m in liste:
            kisi_ham = m["to"] if rol in ("sent", "self") else m["from"]
            adr = c.eposta_adresi(kisi_ham)
            if rol == "inbox" and adr in engelli:
                continue
            if rol == "self":
                ben = c.eposta_adresi(self.ayar.get("eposta", ""))
                if ben and ben not in (m.get("to", "").lower()):
                    continue
            mhim = adr in onemli
            mkey = c.anahtar_eslesme(m, self.cfg.get("anahtarlar", []))
            im = ("⭐" if mhim else "") + ("🔔" if mkey else "")
            self.liste_grid.add_widget(self._mesaj_satir(rol, m, kisi_ham, im))
            gosterilen += 1
            if rol == "inbox" and (mhim or mkey) and m["uid"] not in self._haber_gorulen:
                haber_yeni.append((m, mhim, mkey))
                self._haber_gorulen.add(m["uid"])
        self._durum(f"{gosterilen} mesaj." if gosterilen else "Mesaj yok.")
        if haber_yeni:
            self._haber_kaydet()
            self._bildir(haber_yeni)

    def _mesaj_satir(self, rol, m, kisi, im):
        from kivy.uix.floatlayout import FloatLayout
        from kivy.graphics import Color, Rectangle
        fl = FloatLayout(size_hint_y=None, height=dp(66))
        satir = BoxLayout(orientation="vertical", padding=(dp(10), dp(6)),
                          size_hint=(1, 1), pos_hint={"x": 0, "y": 0})
        with satir.canvas.before:
            Color(*CARD)
            r = Rectangle(pos=satir.pos, size=satir.size)
        satir.bind(pos=lambda *a: setattr(r, "pos", satir.pos),
                   size=lambda *a: setattr(r, "size", satir.size))
        ust = f"{im} {kisi}".strip()
        l1 = Label(text=self._kisalt(ust, 40), color=TEXT, font_size="14sp", bold=True,
                   halign="left", valign="middle", size_hint_y=None, height=dp(22))
        l1.bind(size=lambda w, s: setattr(l1, "text_size", (l1.width, None)))
        l2 = Label(text=self._kisalt(m["subject"], 46) + "   ·   " + c.tarih_bicim(m["date"]),
                   color=MUTED, font_size="12sp", halign="left", valign="middle",
                   size_hint_y=None, height=dp(20))
        l2.bind(size=lambda w, s: setattr(l2, "text_size", (l2.width, None)))
        satir.add_widget(l1)
        satir.add_widget(l2)
        fl.add_widget(satir)
        btn = Button(background_normal="", background_color=(0, 0, 0, 0),
                     size_hint=(1, 1), pos_hint={"x": 0, "y": 0})
        btn.bind(on_release=lambda *a: self._mesaj_ac(rol, m))
        fl.add_widget(btn)
        return fl

    def _kisalt(self, s, n):
        s = (s or "").replace("\n", " ")
        return s if len(s) <= n else s[:n - 1] + "…"

    # ================= EKRAN: MESAJ =================
    def _ekran_mesaj(self):
        ek = Screen(name="mesaj")
        dis = BoxLayout(orientation="vertical")
        ub = BoxLayout(size_hint_y=None, height=dp(44), spacing=dp(4), padding=(dp(6), dp(4)))
        gb = duz_dugme("‹ Geri", (0.9, 0.91, 0.95, 1), TEXT, boy=40, size_hint_x=None, width=dp(80))
        gb.bind(on_release=lambda *a: self.git("liste"))
        ub.add_widget(gb)
        yb = duz_dugme("↩ Yanıtla", PRIMARY, boy=40)
        yb.bind(on_release=lambda *a: self._yanitla(False))
        ub.add_widget(yb)
        mb = duz_dugme("⋮", (0.9, 0.91, 0.95, 1), TEXT, boy=40, size_hint_x=None, width=dp(48),
                       font_size="20sp")
        mb.bind(on_release=lambda *a: self._mesaj_islemler())
        ub.add_widget(mb)
        sb = duz_dugme("🗑", (0.882, 0.114, 0.282, 1), boy=40, size_hint_x=None, width=dp(56),
                       font_size="18sp")
        sb.bind(on_release=lambda *a: self._mesaj_sil())
        ub.add_widget(sb)
        dis.add_widget(ub)

        sv = ScrollView()
        self.mesaj_grid = GridLayout(cols=1, size_hint_y=None, padding=dp(12), spacing=dp(8))
        self.mesaj_grid.bind(minimum_height=self.mesaj_grid.setter("height"))
        sv.add_widget(self.mesaj_grid)
        dis.add_widget(sv)
        ek.add_widget(dis)
        return ek

    def _mesaj_ac(self, rol, m):
        self._sec_rol = rol
        self._sec_uid = m["uid"]
        self._sec_folder = self.liste_cache.get(rol, (None, None))[0]
        self.git("mesaj")
        self.mesaj_grid.clear_widgets()
        self.mesaj_grid.add_widget(self._etiket("Açılıyor…", MUTED, "13sp"))
        ayar = dict(self.ayar)
        folder = self._sec_folder
        uid = m["uid"]
        self.arka(lambda: c.mesaj_getir(ayar, folder, uid), self._mesaj_goster)

    def _mesaj_goster(self, m):
        self.acik_mesaj = m
        self.mesaj_grid.clear_widgets()
        self.mesaj_grid.add_widget(self._etiket(m["subject"] or "(konu yok)", TEXT, "18sp", bold=True))
        meta = f"Gönderen: {m['from']}\nTarih: {c.tarih_bicim(m['date'])}"
        if m.get("to"):
            meta += f"\nKime: {m['to']}"
        self.mesaj_grid.add_widget(self._etiket(meta, MUTED, "12sp"))
        # ekler
        if m["ekler"]:
            self.mesaj_grid.add_widget(self._etiket("📎 Ekler:", MUTED, "13sp", bold=True))
            for ad, veri in m["ekler"]:
                b = duz_dugme("📄 " + self._kisalt(ad, 40), (0.93, 0.95, 1, 1), LINK, boy=42)
                b.bind(on_release=lambda w, a=ad, v=veri: self._ek_ac(a, v))
                self.mesaj_grid.add_widget(b)
        # gövde (linkler tıklanabilir)
        govde = m["body"] or "(boş)"
        lbl = Label(text=self._link_markup(govde), markup=True, color=TEXT, font_size="14sp",
                    halign="left", valign="top", size_hint_y=None)
        lbl.bind(width=lambda w, val: setattr(lbl, "text_size", (lbl.width, None)),
                 texture_size=lambda w, val: setattr(lbl, "height", lbl.texture_size[1]))
        lbl.bind(on_ref_press=lambda inst, ref: self.url_ac(ref))
        self.mesaj_grid.add_widget(lbl)

    def _link_markup(self, metin):
        # URL'leri [ref] ile tıklanabilir + mavi yap
        def rep(mo):
            u = mo.group(1)
            son = ""
            while u and u[-1] in '.,;:!?)]}>"\'':
                son = u[-1] + son
                u = u[:-1]
            hedef = u if u.lower().startswith("http") else "http://" + u
            return f"[ref={hedef}][color=1d4ed8][u]{u}[/u][/color][/ref]{son}"
        # markup kaçışı
        metin = metin.replace("&", "&amp;").replace("[", "&bl;").replace("]", "&br;")
        metin = c.URL_RE.sub(rep, metin)
        return metin

    def url_ac(self, url):
        try:
            webbrowser.open(url)
        except Exception:
            try:
                from jnius import autoclass
                Intent = autoclass('android.content.Intent')
                Uri = autoclass('android.net.Uri')
                PythonActivity = autoclass('org.kivy.android.PythonActivity')
                intent = Intent(Intent.ACTION_VIEW, Uri.parse(url))
                PythonActivity.mActivity.startActivity(intent)
            except Exception as e:
                self.uyari("Bağlantı", f"Açılamadı: {e}")

    def _ek_ac(self, ad, veri):
        guvenli = "".join(ch if ch not in '<>:"/\\|?*\n\r\t' else "_" for ch in ad).strip(" .") or "ek"
        try:
            klasor = os.path.join(self.user_data_dir, "ekler")
            os.makedirs(klasor, exist_ok=True)
            yol = os.path.join(klasor, guvenli)
            with open(yol, "wb") as f:
                f.write(veri)
        except Exception as e:
            self.uyari("Ek", f"Kaydedilemedi: {e}")
            return
        # açmayı dene
        try:
            if hasattr(os, "startfile"):
                os.startfile(yol)          # Windows (test)
                return
        except Exception:
            pass
        try:
            from jnius import autoclass, cast
            Intent = autoclass('android.content.Intent')
            Uri = autoclass('android.net.Uri')
            File = autoclass('java.io.File')
            PythonActivity = autoclass('org.kivy.android.PythonActivity')
            FileProvider = autoclass('androidx.core.content.FileProvider')
            ctx = PythonActivity.mActivity
            f = File(yol)
            uri = FileProvider.getUriForFile(ctx, ctx.getPackageName() + ".fileprovider", f)
            intent = Intent(Intent.ACTION_VIEW)
            intent.setData(uri)
            intent.addFlags(Intent.FLAG_GRANT_READ_URI_PERMISSION)
            ctx.startActivity(intent)
        except Exception as e:
            self.uyari("Ek", f"Kaydedildi:\n{yol}\n\n(Otomatik açılamadı: {e})")

    def _mesaj_sil(self):
        if not self._sec_uid:
            return
        rol = self._sec_rol
        folder = self._sec_folder
        uid = self._sec_uid
        ayar = dict(self.ayar)
        kalici = (rol == "trash")

        def onayla(evet):
            if not evet:
                return
            self._durum("Siliniyor…")
            self.arka(lambda: c.mail_sil_coklu(ayar, folder, [uid], kalici=kalici),
                      lambda s: (self.git("liste"), self.yenile()))
        self.onay("Sil", "Bu mesaj silinsin mi?" + (" (kalıcı)" if kalici else ""), onayla)

    def _yanitla(self, tumu=False):
        m = self.acik_mesaj
        if not m:
            return
        self._gonder_temizle()
        gonderen = c.eposta_adresi(m["from"])
        ben = c.eposta_adresi(self.ayar.get("eposta", ""))
        self.ti_kime.text = gonderen
        if tumu:
            cc = []
            for parca in (m.get("to", "") + ", " + m.get("cc", "")).replace(";", ",").split(","):
                a = c.eposta_adresi(parca)
                if a and a != ben and a != gonderen and a not in cc:
                    cc.append(a)
            self.ti_cc.text = ", ".join(cc)
        konu = m.get("subject", "")
        self.ti_konu.text = konu if konu.lower().startswith("re:") else "Re: " + konu
        alinti = "\n\n----- Özgün mesaj -----\n" + "\n".join("> " + s for s in (m.get("body", "") or "").splitlines())
        self.ti_govde.text = alinti
        self.git("gonder")

    def _mesaj_islemler(self):
        m = self.acik_mesaj
        if not m:
            return
        adr = c.eposta_adresi(m["from"])
        onemli = adr in self.cfg.get("onemli", [])
        engelli = adr in self.cfg.get("engelli", [])
        secenekler = [
            ("↩↩ Tümünü Yanıtla", lambda: self._yanitla(True)),
            ("☆ Önemliden çıkar" if onemli else "⭐ Önemli kişi yap", lambda: self._onemli_toggle(adr)),
            ("✅ Engeli kaldır" if engelli else "🚫 Engelle", lambda: self._engel_toggle(adr)),
            ("📇 Deftere Kaydet", lambda: self._deftere_kaydet(m)),
        ]
        self.secim_popup("İşlemler", secenekler)

    def _onemli_toggle(self, adr):
        lst = self.cfg.setdefault("onemli", [])
        if adr in lst:
            lst.remove(adr)
            self._durum(f"Önemliden çıkarıldı: {adr}")
        else:
            lst.append(adr)
            self._durum(f"Önemli: {adr}")
        c.yapilandirma_kaydet(self.cfg)

    def _engel_toggle(self, adr):
        lst = self.cfg.setdefault("engelli", [])
        if adr in lst:
            lst.remove(adr)
            self._durum(f"Engel kaldırıldı: {adr}")
        else:
            lst.append(adr)
            self._durum(f"Engellendi: {adr}")
        c.yapilandirma_kaydet(self.cfg)

    def _deftere_kaydet(self, m):
        from email.utils import parseaddr
        ad, adr = parseaddr(m.get("from", ""))
        adr = (adr or "").strip().lower()
        if not adr:
            return
        if any(k.get("eposta", "").lower() == adr for k in self.cfg.get("defter", [])):
            self.uyari("Defter", "Zaten defterde.")
            return
        self.cfg.setdefault("defter", []).append({"ad": (ad or "").strip(), "eposta": adr})
        c.yapilandirma_kaydet(self.cfg)
        self.uyari("Defter", f"Eklendi: {adr}")

    # ================= EKRAN: GÖNDER =================
    def _ekran_gonder(self):
        ek = Screen(name="gonder")
        sv = ScrollView()
        g = GridLayout(cols=1, size_hint_y=None, padding=dp(12), spacing=dp(8))
        g.bind(minimum_height=g.setter("height"))
        g.add_widget(self._etiket("Yeni E-Posta", TEXT, "18sp", bold=True))
        self.ti_kime = self._giris("Kime (virgülle çoklu)")
        g.add_widget(self.ti_kime)
        self.ti_cc = self._giris("Cc (isteğe bağlı)")
        g.add_widget(self.ti_cc)
        self.ti_konu = self._giris("Konu")
        g.add_widget(self.ti_konu)
        self.ti_govde = self._giris("Mesaj…", cok=True, boy=200)
        g.add_widget(self.ti_govde)

        arac = BoxLayout(size_hint_y=None, height=dp(46), spacing=dp(6))
        eb = duz_dugme("📎 Ek Ekle", (0.9, 0.91, 0.95, 1), TEXT, boy=46)
        eb.bind(on_release=lambda *a: self._ek_dosya_ekle())
        arac.add_widget(eb)
        db = duz_dugme("📇 Defter", (0.9, 0.91, 0.95, 1), TEXT, boy=46)
        db.bind(on_release=lambda *a: self._defter_sec_compose())
        arac.add_widget(db)
        g.add_widget(arac)
        self.lbl_ekler = self._etiket("", MUTED, "12sp")
        g.add_widget(self.lbl_ekler)

        knd = BoxLayout(size_hint_y=None, height=dp(40), spacing=dp(8))
        self.sw_kendine = Switch(active=bool(self.cfg.get("kendine_kopya")), size_hint_x=None, width=dp(70))
        self.sw_kendine.bind(active=self._kendine_degisti)
        knd.add_widget(self.sw_kendine)
        knd.add_widget(self._etiket("Bir kopya bana da gönder", TEXT, "13sp"))
        g.add_widget(knd)

        self.btn_gonder = duz_dugme("📨 Gönder", PRIMARY, boy=52)
        self.btn_gonder.bind(on_release=lambda *a: self._gonder())
        g.add_widget(self.btn_gonder)
        self.lbl_gonder_durum = self._etiket("", MUTED, "12sp")
        g.add_widget(self.lbl_gonder_durum)
        sv.add_widget(g)
        ek.add_widget(sv)
        return ek

    def _gonder_temizle(self):
        for ti in (getattr(self, "ti_kime", None), getattr(self, "ti_cc", None),
                   getattr(self, "ti_konu", None), getattr(self, "ti_govde", None)):
            if ti:
                ti.text = ""
        self._compose_ekler = []
        if hasattr(self, "lbl_ekler"):
            self.lbl_ekler.text = ""

    def _kendine_degisti(self, sw, deger):
        self.cfg["kendine_kopya"] = bool(deger)
        c.yapilandirma_kaydet(self.cfg)

    def _ekler_guncelle(self):
        if not self._compose_ekler:
            self.lbl_ekler.text = ""
        else:
            adlar = ", ".join(os.path.basename(y) for y in self._compose_ekler)
            self.lbl_ekler.text = "📎 " + adlar

    def _ek_dosya_ekle(self):
        if _plyer_files is None:
            self.uyari("Ek", "Dosya seçici bu ortamda yok (Android'de çalışır).")
            return
        try:
            secilen = _plyer_files.open_file(multiple=True)
        except Exception as e:
            self.uyari("Ek", f"Dosya seçilemedi: {e}")
            return
        if secilen:
            for y in secilen:
                if y and y not in self._compose_ekler:
                    self._compose_ekler.append(y)
            self._ekler_guncelle()

    def _defter_sec_compose(self):
        defter = self.cfg.get("defter", [])
        if not defter:
            self.uyari("Defter", "Adres defteri boş. Ayarlar'dan kişi ekle.")
            return
        secenekler = []
        for k in defter:
            ep = k.get("eposta", "")
            ad = k.get("ad", "") or ep
            secenekler.append((f"{ad} <{ep}>", lambda e=ep: self._kime_ekle(e)))
        self.secim_popup("Defterden ekle", secenekler)

    def _kime_ekle(self, ep):
        mevcut = [a.strip() for a in self.ti_kime.text.replace(";", ",").split(",") if a.strip()]
        if ep not in mevcut:
            mevcut.append(ep)
        self.ti_kime.text = ", ".join(mevcut)

    def _gonder(self):
        ayar = dict(self.ayar)
        if not c.kimlik_var(ayar):
            self.uyari("Eksik", "Önce hesap ekle.")
            self.git("ayarlar")
            return
        kime = self.ti_kime.text.strip()
        if not kime:
            self.uyari("Eksik", "Kime alanı boş.")
            return
        konu = self.ti_konu.text
        govde = self.ti_govde.text
        cc = self.ti_cc.text.strip()
        bcc = ""
        if self.sw_kendine.active:
            bcc = ayar["eposta"]
        imza = self.cfg.get("imza", "")
        logo = self.cfg.get("imza_logo", "")
        ekler = list(self._compose_ekler)
        self.btn_gonder.disabled = True
        self.lbl_gonder_durum.text = "Gönderiliyor…"
        self.arka(lambda: c.eposta_gonder(ayar, kime, cc, bcc, konu, govde, ekler,
                                          imza_metin=imza, imza_logo=logo),
                  lambda s: self._gonder_ok(), self._gonder_hata)

    def _gonder_ok(self):
        self.btn_gonder.disabled = False
        self.lbl_gonder_durum.text = "Gönderildi ✓"
        self._gonder_temizle()
        self.uyari("Tamam", "E-posta gönderildi.")

    def _gonder_hata(self, msg):
        self.btn_gonder.disabled = False
        self.lbl_gonder_durum.text = "Hata."
        self.uyari("Gönderilemedi", msg + c.auth_ipucu(msg))

    # ================= EKRAN: AYARLAR =================
    def _ekran_ayarlar(self):
        ek = Screen(name="ayarlar")
        sv = ScrollView()
        g = GridLayout(cols=1, size_hint_y=None, padding=dp(12), spacing=dp(8))
        g.bind(minimum_height=g.setter("height"))
        g.add_widget(self._etiket("Hesap Ekle / Düzenle", TEXT, "18sp", bold=True))

        self.sp_saglayici = Spinner(text="Gmail", values=list(c.SAGLAYICILAR.keys()),
                                    size_hint_y=None, height=dp(46), background_normal="",
                                    background_color=(0.9, 0.91, 0.95, 1), color=TEXT)
        self.sp_saglayici.bind(text=self._saglayici_degisti)
        g.add_widget(self.sp_saglayici)
        self.ti_eposta = self._giris("E-posta adresi")
        g.add_widget(self.ti_eposta)
        self.ti_sifre = self._giris("Şifre / Uygulama Şifresi", parola=True)
        g.add_widget(self.ti_sifre)
        yardim = duz_dugme("🔑 Uygulama Şifresi Al", (0.93, 0.95, 1, 1), LINK, boy=44)
        yardim.bind(on_release=lambda *a: self._uyg_sifre())
        g.add_widget(yardim)
        g.add_widget(self._etiket("Gmail/Hotmail'de NORMAL şifre çalışmaz; uygulama şifresi gerekir.",
                                  MUTED, "11sp"))
        # Hotmail/Outlook: Microsoft basic auth'u kapattı → şifresiz OAuth girişi.
        msb = duz_dugme("🔐 Microsoft ile Giriş (Hotmail)", PRIMARY_D, boy=46)
        msb.bind(on_release=lambda *a: self._ms_giris())
        g.add_widget(msb)
        g.add_widget(self._etiket("Hotmail/Outlook için şifre yerine bunu kullan: "
                                  "üstteki kutuya adresini yaz, düğmeye bas, çıkan kodu "
                                  "microsoft.com/device'de gir.", MUTED, "11sp"))

        satir = BoxLayout(size_hint_y=None, height=dp(50), spacing=dp(6))
        kb = duz_dugme("💾 Kaydet", PRIMARY)
        kb.bind(on_release=lambda *a: self._hesap_kaydet())
        satir.add_widget(kb)
        tb = duz_dugme("🔌 Test", (0.9, 0.91, 0.95, 1), TEXT)
        tb.bind(on_release=lambda *a: self._baglanti_test())
        satir.add_widget(tb)
        g.add_widget(satir)

        # Hesap listesi
        g.add_widget(self._etiket("Hesaplar", MUTED, "13sp", bold=True))
        self.hesap_liste = GridLayout(cols=1, size_hint_y=None, spacing=dp(4))
        self.hesap_liste.bind(minimum_height=self.hesap_liste.setter("height"))
        g.add_widget(self.hesap_liste)

        # İmza
        g.add_widget(self._etiket("İmza (mesaj sonuna eklenir)", MUTED, "13sp", bold=True))
        self.ti_imza = self._giris("İmza metni…", cok=True, boy=90)
        self.ti_imza.text = self.cfg.get("imza", "")
        g.add_widget(self.ti_imza)
        ib = duz_dugme("İmzayı Kaydet", (0.9, 0.91, 0.95, 1), TEXT, boy=44)
        ib.bind(on_release=lambda *a: self._imza_kaydet())
        g.add_widget(ib)

        # Listeler (engelli / önemli / anahtar) + adres defteri
        self.liste_kutulari = {}
        for anahtar, baslik in (("onemli", "⭐ Önemli Kişiler"),
                                ("engelli", "🚫 Engelli Kişiler"),
                                ("anahtarlar", "🔔 Anahtar Kelimeler"),
                                ("defter", "📇 Adres Defteri")):
            g.add_widget(self._etiket(baslik, MUTED, "13sp", bold=True))
            eb = duz_dugme("+ Ekle", (0.9, 0.91, 0.95, 1), TEXT, boy=40)
            eb.bind(on_release=lambda w, a=anahtar: self._genel_ekle(a))
            g.add_widget(eb)
            kutu = GridLayout(cols=1, size_hint_y=None, spacing=dp(3))
            kutu.bind(minimum_height=kutu.setter("height"))
            self.liste_kutulari[anahtar] = kutu
            g.add_widget(kutu)

        sv.add_widget(g)
        ek.add_widget(sv)
        Clock.schedule_once(lambda dt: (self._hesap_liste_doldur(), self._listeleri_doldur()), 0.1)
        return ek

    def _listeleri_doldur(self):
        for anahtar, kutu in self.liste_kutulari.items():
            kutu.clear_widgets()
            for oge in self.cfg.get(anahtar, []):
                if anahtar == "defter":
                    metin = (oge.get("ad") or "") + "  <" + oge.get("eposta", "") + ">"
                    deger = oge
                else:
                    metin = oge
                    deger = oge
                satir = BoxLayout(size_hint_y=None, height=dp(40), spacing=dp(4))
                satir.add_widget(self._etiket(metin, TEXT, "12sp"))
                sb = duz_dugme("✕", (0.882, 0.114, 0.282, 1), boy=40, size_hint_x=None,
                               width=dp(44))
                sb.bind(on_release=lambda w, a=anahtar, d=deger: self._genel_sil(a, d))
                satir.add_widget(sb)
                kutu.add_widget(satir)

    def _genel_ekle(self, anahtar):
        if anahtar == "defter":
            def geri(ad, ep):
                ep = (ep or "").strip().lower()
                if ep:
                    self.cfg.setdefault("defter", []).append({"ad": ad.strip(), "eposta": ep})
                    c.yapilandirma_kaydet(self.cfg)
                    self._listeleri_doldur()
            self.metin_giris("Kişi Ekle", "Ad (isteğe bağlı)", geri, ipucu2="E-posta")
        else:
            ipucu = "Kelime / ifade" if anahtar == "anahtarlar" else "E-posta adresi"
            def geri(deger):
                deger = deger.strip()
                if anahtar != "anahtarlar":
                    deger = deger.lower()
                if deger and deger not in self.cfg.setdefault(anahtar, []):
                    self.cfg[anahtar].append(deger)
                    c.yapilandirma_kaydet(self.cfg)
                    self._listeleri_doldur()
            self.metin_giris("Ekle", ipucu, geri)

    def _genel_sil(self, anahtar, deger):
        try:
            self.cfg.get(anahtar, []).remove(deger)
            c.yapilandirma_kaydet(self.cfg)
            self._listeleri_doldur()
        except ValueError:
            pass

    def _saglayici_degisti(self, sp, ad):
        bilgi = c.SAGLAYICILAR.get(ad)
        if bilgi and not self.ti_eposta.text:
            pass  # sunucular kaydederken uygulanır

    def _hesap_kaydet(self):
        eposta = self.ti_eposta.text.strip()
        sifre = self.ti_sifre.text
        if not eposta or not sifre:
            self.uyari("Eksik", "E-posta ve şifre gerekli.")
            return
        bilgi = c.SAGLAYICILAR.get(self.sp_saglayici.text, c.SAGLAYICILAR["Gmail"])
        # var olan mı?
        idx = None
        for i, h in enumerate(self.cfg["hesaplar"]):
            if h.get("eposta", "").lower() == eposta.lower():
                idx = i
                break
        hesap = c._hesap_normalize({
            "saglayici": self.sp_saglayici.text, "eposta": eposta, "sifre": sifre,
            "smtp_host": bilgi["smtp_host"], "smtp_port": bilgi["smtp_port"],
            "imap_host": bilgi["imap_host"], "imap_port": bilgi["imap_port"]})
        if idx is None:
            self.cfg["hesaplar"].append(hesap)
            self.cfg["aktif"] = len(self.cfg["hesaplar"]) - 1
        else:
            self.cfg["hesaplar"][idx] = hesap
            self.cfg["aktif"] = idx
        c.yapilandirma_kaydet(self.cfg)
        self._hesap_spinner_guncelle()
        self._hesap_liste_doldur()
        self.ti_eposta.text = ""
        self.ti_sifre.text = ""
        self._durum("Hesap kaydedildi.")
        self.uyari("Tamam", "Hesap kaydedildi. Test etmek için 🔌 Test'e bas.")

    # ---- Microsoft (Hotmail/Outlook) şifresiz giriş: cihaz kodu akışı ----
    def _panoya(self, metin):
        try:
            Clipboard.copy(metin)
            self._durum("Kod kopyalandı.")
        except Exception:
            pass

    def _ms_giris(self):
        eposta = self.ti_eposta.text.strip()
        if not eposta:
            self.uyari("E-posta gerekli",
                       "Önce üstteki kutuya Hotmail/Outlook adresini yaz, "
                       "sonra bu düğmeye bas.")
            return
        self._durum("Microsoft kodu alınıyor…")
        self.arka(lambda: c.ms_cihaz_kodu(),
                  lambda v: self._ms_kod_goster(eposta, v))

    def _ms_kod_goster(self, eposta, v):
        self._durum("Microsoft girişi bekleniyor…")
        self._ms_iptal = False
        kod = v.get("user_code", "")
        uri = v.get("verification_uri", "https://microsoft.com/device")
        icerik = BoxLayout(orientation="vertical", padding=dp(14), spacing=dp(8))
        icerik.add_widget(self._etiket(
            "1) Aşağıdaki adresi aç\n2) Bu kodu gir\n3) Hotmail hesabınla giriş yap",
            TEXT, "14sp"))
        icerik.add_widget(self._etiket(uri, LINK, "15sp", bold=True))
        icerik.add_widget(self._etiket(kod, PRIMARY, "30sp", bold=True))
        pop = Popup(title="Microsoft ile Giriş", content=icerik,
                    size_hint=(0.92, 0.6), auto_dismiss=False)
        self._ms_pop = pop
        satir = BoxLayout(size_hint_y=None, height=dp(48), spacing=dp(8))
        ab = duz_dugme("🌐 Aç", PRIMARY)
        ab.bind(on_release=lambda *a: self.url_ac(uri))
        satir.add_widget(ab)
        cb = duz_dugme("📋 Kodu Kopyala", (0.9, 0.91, 0.95, 1), TEXT)
        cb.bind(on_release=lambda *a: self._panoya(kod))
        satir.add_widget(cb)
        icerik.add_widget(satir)
        ib = duz_dugme("İptal", (0.882, 0.114, 0.282, 1), boy=44)

        def iptal(*a):
            self._ms_iptal = True
            pop.dismiss()
            self._durum("İptal edildi.")
        ib.bind(on_release=iptal)
        icerik.add_widget(ib)
        pop.open()
        dc = v.get("device_code")
        interval = v.get("interval", 5)
        expires = v.get("expires_in", 900)
        self.arka(lambda: c.ms_token_bekle(dc, interval, expires,
                                           lambda: getattr(self, "_ms_iptal", False)),
                  lambda tok: self._ms_tamam(eposta, tok),
                  lambda msg: self._ms_hata(msg))

    def _ms_tamam(self, eposta, tok):
        try:
            self._ms_pop.dismiss()
        except Exception:
            pass
        bilgi = c.SAGLAYICILAR["Outlook / Hotmail"]
        hesap = c._hesap_normalize({
            "saglayici": "Outlook / Hotmail", "eposta": eposta, "sifre": "",
            "smtp_host": bilgi["smtp_host"], "smtp_port": bilgi["smtp_port"],
            "imap_host": bilgi["imap_host"], "imap_port": bilgi["imap_port"],
            "refresh_token": tok.get("refresh_token", "")})
        idx = None
        for i, h in enumerate(self.cfg["hesaplar"]):
            if h.get("eposta", "").lower() == eposta.lower():
                idx = i
                break
        if idx is None:
            self.cfg["hesaplar"].append(hesap)
            self.cfg["aktif"] = len(self.cfg["hesaplar"]) - 1
        else:
            self.cfg["hesaplar"][idx] = hesap
            self.cfg["aktif"] = idx
        c.yapilandirma_kaydet(self.cfg)
        self._hesap_spinner_guncelle()
        self._hesap_liste_doldur()
        self.ti_eposta.text = ""
        self.ti_sifre.text = ""
        self._durum("Microsoft girişi tamam.")
        self.uyari("Tamam", "Hotmail hesabın eklendi. 📥 Gelen'e geçip Yenile'ye bas.")

    def _ms_hata(self, msg):
        try:
            self._ms_pop.dismiss()
        except Exception:
            pass
        self._genel_hata(msg)

    def _hesap_liste_doldur(self):
        self.hesap_liste.clear_widgets()
        for i, h in enumerate(self.cfg["hesaplar"]):
            satir = BoxLayout(size_hint_y=None, height=dp(44), spacing=dp(4))
            et = self._hesap_etiket(h) + ("  ✓" if i == self.cfg["aktif"] else "")
            l = duz_dugme(et, (0.96, 0.97, 0.99, 1), TEXT, boy=44)
            l.bind(on_release=lambda w, ix=i: self._hesap_aktif_yap(ix))
            satir.add_widget(l)
            sil = duz_dugme("Sil", (0.882, 0.114, 0.282, 1), boy=44, size_hint_x=None, width=dp(60))
            sil.bind(on_release=lambda w, ix=i: self._hesap_sil(ix))
            satir.add_widget(sil)
            self.hesap_liste.add_widget(satir)

    def _hesap_aktif_yap(self, ix):
        self.cfg["aktif"] = ix
        c.yapilandirma_kaydet(self.cfg)
        self._hesap_spinner_guncelle()
        self._hesap_liste_doldur()
        self.liste_cache.clear()
        self._haber_yukle()

    def _hesap_sil(self, ix):
        def onayla(evet):
            if not evet:
                return
            del self.cfg["hesaplar"][ix]
            self.cfg["aktif"] = 0 if self.cfg["hesaplar"] else -1
            c.yapilandirma_kaydet(self.cfg)
            self._hesap_spinner_guncelle()
            self._hesap_liste_doldur()
        self.onay("Hesabı Sil", "Bu hesap kaldırılsın mı?", onayla)

    def _imza_kaydet(self):
        self.cfg["imza"] = self.ti_imza.text
        c.yapilandirma_kaydet(self.cfg)
        self.uyari("İmza", "İmza kaydedildi.")

    def _baglanti_test(self):
        eposta = self.ti_eposta.text.strip() or self.ayar.get("eposta", "")
        sifre = self.ti_sifre.text or self.ayar.get("sifre", "")
        aktif = self.ayar
        # Microsoft (şifresiz) hesabı: aktif hesabın refresh_token'ıyla test et.
        if aktif.get("refresh_token") and (not self.ti_eposta.text.strip()
                or eposta.lower() == aktif.get("eposta", "").lower()):
            ayar = dict(aktif)
        else:
            if not eposta or not sifre:
                self.uyari("Eksik", "E-posta ve şifre gerekli.")
                return
            bilgi = c.SAGLAYICILAR.get(self.sp_saglayici.text, c.SAGLAYICILAR["Gmail"])
            ayar = c._hesap_normalize({"eposta": eposta, "sifre": sifre,
                                       "smtp_host": bilgi["smtp_host"], "smtp_port": bilgi["smtp_port"],
                                       "imap_host": bilgi["imap_host"], "imap_port": bilgi["imap_port"]})
        self._durum("Test ediliyor…")

        def test():
            sonuc = []
            try:
                M = c.imap_baglan(ayar); M.select("INBOX", readonly=True); M.logout()
                sonuc.append("IMAP: ✓")
            except Exception as e:
                sonuc.append(f"IMAP: ✗ {e}")
            return "\n".join(sonuc)
        self.arka(test, lambda s: self.uyari("Bağlantı Testi", s + c.auth_ipucu(s)))

    def _uyg_sifre(self):
        sag = self.sp_saglayici.text
        if "Gmail" in sag:
            url = "https://myaccount.google.com/apppasswords"
        elif "Outlook" in sag or "Hotmail" in sag:
            url = "https://account.microsoft.com/security"
        elif "Yandex" in sag:
            url = "https://id.yandex.com/security/app-passwords"
        else:
            url = "https://account.microsoft.com/security"
        self.url_ac(url)

    # ---- ortak widget'lar ----
    def _etiket(self, metin, renk, boy, bold=False):
        l = Label(text=metin, color=renk, font_size=boy, bold=bold, halign="left",
                  valign="top", size_hint_y=None, markup=False)
        l.bind(width=lambda w, v: setattr(l, "text_size", (l.width, None)),
               texture_size=lambda w, v: setattr(l, "height", max(l.texture_size[1], dp(18))))
        return l

    def _giris(self, ipucu, cok=False, parola=False, boy=46):
        ti = TextInput(hint_text=ipucu, multiline=cok, password=parola,
                       size_hint_y=None, height=dp(boy), font_size="15sp",
                       padding=(dp(8), dp(10)), background_color=(0.97, 0.98, 0.99, 1),
                       foreground_color=TEXT)
        return ti

    def uyari(self, baslik, metin):
        icerik = BoxLayout(orientation="vertical", padding=dp(12), spacing=dp(8))
        sv = ScrollView()
        l = Label(text=metin, color=TEXT, font_size="14sp", halign="left", valign="top",
                  size_hint_y=None)
        l.bind(width=lambda w, v: setattr(l, "text_size", (l.width, None)),
               texture_size=lambda w, v: setattr(l, "height", l.texture_size[1]))
        sv.add_widget(l)
        icerik.add_widget(sv)
        pop = Popup(title=baslik, content=icerik, size_hint=(0.9, 0.6))
        kb = duz_dugme("Tamam", PRIMARY, boy=46)
        kb.bind(on_release=pop.dismiss)
        icerik.add_widget(kb)
        pop.open()

    def onay(self, baslik, metin, geri):
        icerik = BoxLayout(orientation="vertical", padding=dp(12), spacing=dp(8))
        icerik.add_widget(self._etiket(metin, TEXT, "14sp"))
        satir = BoxLayout(size_hint_y=None, height=dp(48), spacing=dp(8))
        pop = Popup(title=baslik, content=icerik, size_hint=(0.85, 0.4))
        eb = duz_dugme("Evet", (0.882, 0.114, 0.282, 1))
        eb.bind(on_release=lambda *a: (pop.dismiss(), geri(True)))
        hb = duz_dugme("Hayır", (0.9, 0.91, 0.95, 1), TEXT)
        hb.bind(on_release=lambda *a: (pop.dismiss(), geri(False)))
        satir.add_widget(hb)
        satir.add_widget(eb)
        icerik.add_widget(satir)
        pop.open()

    def secim_popup(self, baslik, secenekler):
        icerik = BoxLayout(orientation="vertical", padding=dp(8), spacing=dp(6))
        pop = Popup(title=baslik, content=icerik,
                    size_hint=(0.9, min(0.9, 0.2 + 0.11 * len(secenekler))))
        for etiket, cb in secenekler:
            b = duz_dugme(etiket, (0.95, 0.96, 0.99, 1), TEXT, boy=48)
            b.bind(on_release=lambda w, f=cb: (pop.dismiss(), f()))
            icerik.add_widget(b)
        k = duz_dugme("Kapat", (0.9, 0.91, 0.95, 1), TEXT, boy=44)
        k.bind(on_release=pop.dismiss)
        icerik.add_widget(k)
        pop.open()

    def metin_giris(self, baslik, ipucu, geri, ipucu2=None):
        icerik = BoxLayout(orientation="vertical", padding=dp(12), spacing=dp(8))
        ti1 = self._giris(ipucu)
        icerik.add_widget(ti1)
        ti2 = None
        if ipucu2:
            ti2 = self._giris(ipucu2)
            icerik.add_widget(ti2)
        satir = BoxLayout(size_hint_y=None, height=dp(48), spacing=dp(8))
        pop = Popup(title=baslik, content=icerik, size_hint=(0.9, 0.45))

        def tamam(*a):
            pop.dismiss()
            if ti2 is not None:
                geri(ti1.text.strip(), ti2.text.strip())
            else:
                geri(ti1.text.strip())
        eb = duz_dugme("Tamam", PRIMARY)
        eb.bind(on_release=tamam)
        hb = duz_dugme("İptal", (0.9, 0.91, 0.95, 1), TEXT)
        hb.bind(on_release=pop.dismiss)
        satir.add_widget(hb)
        satir.add_widget(eb)
        icerik.add_widget(satir)
        pop.open()


if __name__ == "__main__":
    EpostaApp().run()
