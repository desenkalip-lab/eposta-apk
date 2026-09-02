# -*- coding: utf-8 -*-
"""
E-Posta Aracı — ÇEKİRDEK (platformdan bağımsız mail mantığı)

Masaüstü sürümüyle AYNI: SMTP gönder, IMAP oku, HTML->metin, hesap yönetimi.
Arayüz (tkinter/Kivy) burayı çağırır. Android'de de aynen çalışır.
Yalnız Python standart kütüphanesi kullanılır.
"""

import os
import re
import json
import time
import base64
import smtplib
import imaplib
import email
import urllib.request
import urllib.parse
import urllib.error
from email.header import decode_header, make_header
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email.mime.image import MIMEImage
from email.utils import formatdate, parseaddr, parsedate_to_datetime
from email import encoders
from html import escape as html_escape
from html.parser import HTMLParser

# Ayar dosyası yolu — arayüz (main.py) başlangıçta ayarlar.
# Android'de App.user_data_dir, masaüstünde ~/.eposta_araci
AYAR_DOSYASI = os.path.join(os.path.expanduser("~"), ".eposta_araci", "ayarlar.json")


def ayar_yolu_ayarla(klasor):
    global AYAR_DOSYASI
    os.makedirs(klasor, exist_ok=True)
    AYAR_DOSYASI = os.path.join(klasor, "ayarlar.json")


SAGLAYICILAR = {
    "Gmail": {"smtp_host": "smtp.gmail.com", "smtp_port": 465,
              "imap_host": "imap.gmail.com", "imap_port": 993},
    "Outlook / Hotmail": {"smtp_host": "smtp-mail.outlook.com", "smtp_port": 587,
                          "imap_host": "imap-mail.outlook.com", "imap_port": 993},
    "Yandex": {"smtp_host": "smtp.yandex.com", "smtp_port": 465,
               "imap_host": "imap.yandex.com", "imap_port": 993},
    "Özel (info@ / kurumsal)": {"smtp_host": "", "smtp_port": 465,
                                "imap_host": "", "imap_port": 993},
}

HESAP_SABLON = {
    "saglayici": "Gmail", "ad": "", "eposta": "", "sifre": "",
    "smtp_host": "smtp.gmail.com", "smtp_port": 465,
    "imap_host": "imap.gmail.com", "imap_port": 993,
}

URL_RE = re.compile(r'((?:https?://|www\.)[^\s<>()\[\]"\']+)', re.I)


# ---------------------------------------------------------------------------
# Ayar (config)
# ---------------------------------------------------------------------------

def _hesap_normalize(h):
    hesap = dict(HESAP_SABLON)
    hesap.update(h or {})
    if hesap.get("saglayici") not in SAGLAYICILAR:
        hesap["saglayici"] = "Özel (info@ / kurumsal)"
    try:
        hesap["smtp_port"] = int(hesap.get("smtp_port") or 0)
        hesap["imap_port"] = int(hesap.get("imap_port") or 0)
    except (TypeError, ValueError):
        hesap["smtp_port"], hesap["imap_port"] = 465, 993
    return hesap


def _sifre_coz(b64):
    if not b64:
        return ""
    try:
        return base64.b64decode(b64.encode("utf-8")).decode("utf-8")
    except Exception:
        return ""


def yapilandirma_yukle():
    cfg = {"aktif": 0, "hesaplar": [], "engelli": [], "onemli": [], "anahtarlar": [],
           "defter": [], "kendine_kopya": False, "imza": "", "imza_logo": "",
           "haber_gorulen": {}}
    try:
        with open(AYAR_DOSYASI, "r", encoding="utf-8") as f:
            veri = json.load(f)
    except FileNotFoundError:
        return cfg
    except Exception as e:
        print("Ayar okunamadı:", e)
        return cfg

    if "hesaplar" in veri:
        for h in veri.get("hesaplar", []):
            h = dict(h)
            h["sifre"] = _sifre_coz(h.get("sifre", ""))
            cfg["hesaplar"].append(_hesap_normalize(h))
        cfg["aktif"] = veri.get("aktif", 0)
    else:
        h = dict(veri)
        h["sifre"] = _sifre_coz(h.get("sifre", ""))
        if h.get("eposta"):
            cfg["hesaplar"].append(_hesap_normalize(h))
    cfg["engelli"] = veri.get("engelli", []) or []
    cfg["onemli"] = veri.get("onemli", []) or []
    cfg["anahtarlar"] = veri.get("anahtarlar", []) or []
    cfg["defter"] = veri.get("defter", []) or []
    cfg["kendine_kopya"] = bool(veri.get("kendine_kopya", False))
    cfg["imza"] = veri.get("imza", "") or ""
    cfg["imza_logo"] = veri.get("imza_logo", "") or ""
    hg = veri.get("haber_gorulen", {})
    cfg["haber_gorulen"] = hg if isinstance(hg, dict) else {}

    if not (0 <= cfg["aktif"] < len(cfg["hesaplar"])):
        cfg["aktif"] = 0 if cfg["hesaplar"] else -1
    for k in ("engelli", "onemli", "anahtarlar", "defter"):
        if not isinstance(cfg.get(k), list):
            cfg[k] = []
    return cfg


def yapilandirma_kaydet(cfg):
    klasor = os.path.dirname(AYAR_DOSYASI)
    if klasor:
        os.makedirs(klasor, exist_ok=True)
    out = {"aktif": cfg.get("aktif", 0), "hesaplar": [],
           "engelli": cfg.get("engelli", []), "onemli": cfg.get("onemli", []),
           "anahtarlar": cfg.get("anahtarlar", []), "defter": cfg.get("defter", []),
           "kendine_kopya": cfg.get("kendine_kopya", False),
           "imza": cfg.get("imza", ""), "imza_logo": cfg.get("imza_logo", ""),
           "haber_gorulen": cfg.get("haber_gorulen", {})}
    for h in cfg.get("hesaplar", []):
        # Geçici token önbelleğini (_at/_at_bitis) yazma; refresh_token kalır.
        hh = {k: v for k, v in h.items() if not k.startswith("_")}
        hh["sifre"] = base64.b64encode((h.get("sifre") or "").encode("utf-8")).decode("utf-8")
        out["hesaplar"].append(hh)
    with open(AYAR_DOSYASI, "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=2)


# ---------------------------------------------------------------------------
# Yardımcılar
# ---------------------------------------------------------------------------

def _coz(metin):
    if not metin:
        return ""
    try:
        return str(make_header(decode_header(metin)))
    except Exception:
        return metin


def eposta_adresi(metin):
    return (parseaddr(metin or "")[1] or "").strip().lower()


def kimlik_var(ayar):
    """Hesap bağlanmaya hazır mı: e-posta + (şifre YA DA Microsoft anahtarı)."""
    return bool(ayar.get("eposta") and (ayar.get("sifre") or ayar.get("refresh_token")))


def tarih_bicim(s):
    if not s:
        return ""
    try:
        return parsedate_to_datetime(s).strftime("%d/%m/%Y")
    except Exception:
        return s[:16]


def auth_ipucu(metin):
    m = (metin or "").lower()
    isaretler = ("badcredentials", "authenticationfailed", "5.7.8",
                 "username and password not accepted", "invalid credentials",
                 "535", "auth")
    if any(x in m for x in isaretler):
        return ("\n\n⚠️ Kimlik doğrulanamadı. Gmail/Hotmail'de NORMAL şifre çalışmaz; "
                "'Uygulama Şifresi' gerekir (2 Adımlı Doğrulama açıkken üretilir).")
    return ""


class _HTMLMetin(HTMLParser):
    ATLA = {"script", "style", "head", "title"}
    BLOK = {"p", "div", "tr", "table", "li", "ul", "ol", "blockquote",
            "section", "header", "footer", "h1", "h2", "h3", "h4", "h5", "h6"}

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.parcalar = []
        self._atla = 0
        self._a_href = None

    def handle_starttag(self, tag, attrs):
        tag = tag.lower()
        if tag in self.ATLA:
            self._atla += 1
        elif tag == "br":
            self.parcalar.append("\n")
        elif tag == "a":
            self._a_href = dict(attrs).get("href")
        elif tag in self.BLOK:
            self.parcalar.append("\n")

    def handle_startendtag(self, tag, attrs):
        if tag.lower() == "br":
            self.parcalar.append("\n")

    def handle_endtag(self, tag):
        tag = tag.lower()
        if tag in self.ATLA and self._atla > 0:
            self._atla -= 1
        elif tag == "a":
            href = self._a_href
            self._a_href = None
            if href and href.lower().startswith(("http", "www")):
                if href not in "".join(self.parcalar[-4:]):
                    self.parcalar.append(f" ({href})")
        elif tag in ("td", "th"):
            self.parcalar.append("  ")
        elif tag in self.BLOK:
            self.parcalar.append("\n")

    def handle_data(self, data):
        if not self._atla:
            self.parcalar.append(data)

    def metin(self):
        s = "".join(self.parcalar)
        s = re.sub(r"[ \t\r\f\v]+", " ", s)
        s = re.sub(r" *\n *", "\n", s)
        s = re.sub(r"\n{3,}", "\n\n", s)
        return s.strip()


def html_temizle(html):
    try:
        p = _HTMLMetin()
        p.feed(html or "")
        p.close()
        s = p.metin()
        if s:
            return s
    except Exception:
        pass
    import html as _h
    m = re.sub(r"(?is)<(script|style|head).*?</\1>", "", html or "")
    m = re.sub(r"(?s)<!--.*?-->", "", m)
    m = re.sub(r"(?i)<\s*br\s*/?>", "\n", m)
    m = re.sub(r"(?i)</\s*(p|div|tr|table)\s*>", "\n", m)
    m = re.sub(r"<[^>]+>", "", m)
    return _h.unescape(m).strip()


def _govde_coz(parca):
    try:
        ham = parca.get_payload(decode=True)
        if ham is None:
            return ""
        return ham.decode(parca.get_content_charset() or "utf-8", errors="replace")
    except Exception:
        return ""


# ---------------------------------------------------------------------------
# Microsoft OAuth2 (Outlook/Hotmail: basic auth kapalı, şifre çalışmaz)
# Telefonda CİHAZ KODU akışı: kullanıcı microsoft.com/device adresine kodu
# girip giriş yapar; uygulama token gelene kadar bekler. Loopback/redirect YOK.
# ---------------------------------------------------------------------------
MS_CLIENT_ID = "9e5f94bc-e8a4-4e73-b8be-63364c29d753"   # Thunderbird (kamuya açık public client)
MS_AUTORITE = "https://login.microsoftonline.com/common/oauth2/v2.0"
MS_SCOPE = ("offline_access https://outlook.office.com/IMAP.AccessAsUser.All "
            "https://outlook.office.com/SMTP.Send")


def _http_post(url, veri):
    data = urllib.parse.urlencode(veri).encode()
    req = urllib.request.Request(url, data=data,
                                 headers={"Content-Type": "application/x-www-form-urlencoded"})
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            return r.status, json.loads(r.read().decode())
    except urllib.error.HTTPError as e:
        try:
            return e.code, json.loads(e.read().decode())
        except Exception:
            return e.code, {}


def ms_cihaz_kodu():
    """Cihaz kodu akışını başlatır → {user_code, verification_uri, device_code, interval}."""
    _, veri = _http_post(MS_AUTORITE + "/devicecode",
                         {"client_id": MS_CLIENT_ID, "scope": MS_SCOPE})
    if "device_code" not in veri:
        raise RuntimeError(veri.get("error_description", "Microsoft giriş kodu alınamadı."))
    return veri


def ms_token_bekle(device_code, interval=5, expires_in=900, iptal=None):
    """Kullanıcı microsoft.com/device'de onaylayana kadar bekler; token sözlüğü döndürür."""
    son = time.time() + int(expires_in or 900)
    bekle = max(2, int(interval or 5))
    while time.time() < son:
        if iptal is not None and iptal():
            raise RuntimeError("İptal edildi.")
        time.sleep(bekle)
        _, veri = _http_post(MS_AUTORITE + "/token",
                             {"client_id": MS_CLIENT_ID, "grant_type": "device_code",
                              "device_code": device_code})
        if "access_token" in veri:
            return veri
        hata = veri.get("error", "")
        if hata == "authorization_pending":
            continue
        if hata == "slow_down":
            bekle += 5
            continue
        raise RuntimeError(veri.get("error_description", hata or "Giriş başarısız."))
    raise RuntimeError("Süre doldu, tekrar dene.")


def ms_token_yenile(refresh_token):
    _, veri = _http_post(MS_AUTORITE + "/token",
                         {"client_id": MS_CLIENT_ID, "grant_type": "refresh_token",
                          "scope": MS_SCOPE, "refresh_token": refresh_token})
    if "access_token" not in veri:
        raise RuntimeError(veri.get("error_description",
                                    "Microsoft oturumu yenilenemedi (tekrar giriş gerek)."))
    return veri


def ms_erisim_tokeni(ayar):
    """Hesabın refresh_token'ından taze access_token üretir (kısa süre önbellek)."""
    simdi = time.time()
    if ayar.get("_at") and ayar.get("_at_bitis", 0) > simdi + 60:
        return ayar["_at"]
    veri = ms_token_yenile(ayar["refresh_token"])
    ayar["_at"] = veri["access_token"]
    ayar["_at_bitis"] = simdi + int(veri.get("expires_in", 3600))
    if veri.get("refresh_token"):
        ayar["refresh_token"] = veri["refresh_token"]
    return ayar["_at"]


def _xoauth2(eposta, token):
    return "user=%s\1auth=Bearer %s\1\1" % (eposta, token)


# ---------------------------------------------------------------------------
# Gönderme
# ---------------------------------------------------------------------------

def _logo_alt_tip(yol):
    ext = os.path.splitext(yol)[1].lower().lstrip(".")
    return {"jpg": "jpeg", "jpeg": "jpeg", "png": "png", "gif": "gif", "bmp": "bmp"}.get(ext, "png")


def eposta_gonder(ayar, kime, cc, bcc, konu, govde, ekler, imza_metin="", imza_logo=""):
    gonderen_ad = ayar.get("ad") or ""
    gonderen = ayar["eposta"]
    tam_metin = govde
    if imza_metin:
        tam_metin = (govde or "") + "\n\n--\n" + imza_metin

    logo_var = bool(imza_logo) and os.path.exists(imza_logo)
    msg = MIMEMultipart("mixed")
    if logo_var:
        ilgili = MIMEMultipart("related")
        alt = MIMEMultipart("alternative")
        alt.attach(MIMEText(tam_metin, "plain", "utf-8"))
        html_govde = html_escape(govde or "").replace("\n", "<br>")
        html = ("<html><body><div style=\"font-family:Arial,sans-serif;font-size:14px;\">"
                + html_govde)
        if imza_metin:
            html += "<br><br>--<br>" + html_escape(imza_metin).replace("\n", "<br>")
        html += "<br><br><img src=\"cid:imzalogo\" style=\"max-width:320px;\"></div></body></html>"
        alt.attach(MIMEText(html, "html", "utf-8"))
        ilgili.attach(alt)
        with open(imza_logo, "rb") as f:
            img = MIMEImage(f.read(), _subtype=_logo_alt_tip(imza_logo))
        img.add_header("Content-ID", "<imzalogo>")
        img.add_header("Content-Disposition", "inline",
                       filename=("utf-8", "", os.path.basename(imza_logo)))
        ilgili.attach(img)
        msg.attach(ilgili)
    else:
        msg.attach(MIMEText(tam_metin, "plain", "utf-8"))

    msg["From"] = f"{gonderen_ad} <{gonderen}>" if gonderen_ad else gonderen
    msg["To"] = kime
    if cc:
        msg["Cc"] = cc
    msg["Subject"] = konu
    msg["Date"] = formatdate(localtime=True)

    for yol in ekler:
        with open(yol, "rb") as f:
            veri = f.read()
        parca = MIMEBase("application", "octet-stream")
        parca.set_payload(veri)
        encoders.encode_base64(parca)
        parca.add_header("Content-Disposition", "attachment",
                         filename=("utf-8", "", os.path.basename(yol)))
        msg.attach(parca)

    def _ayikla(s):
        return [a.strip() for a in (s or "").replace(";", ",").split(",") if a.strip()]
    alicilar = _ayikla(kime) + _ayikla(cc) + _ayikla(bcc)
    if not alicilar:
        raise ValueError("En az bir alıcı gerekli.")

    host, port = ayar["smtp_host"], int(ayar["smtp_port"])
    if port == 465:
        sunucu = smtplib.SMTP_SSL(host, port, timeout=30)
    else:
        sunucu = smtplib.SMTP(host, port, timeout=30)
        sunucu.ehlo(); sunucu.starttls(); sunucu.ehlo()
    try:
        if ayar.get("refresh_token"):                   # Microsoft OAuth
            token = ms_erisim_tokeni(ayar)
            sunucu.ehlo()
            kod = base64.b64encode(_xoauth2(ayar["eposta"], token).encode()).decode()
            typ, resp = sunucu.docmd("AUTH", "XOAUTH2 " + kod)
            if typ == 334:
                typ, resp = sunucu.docmd("")            # hata challenge'ını bitir
            if typ != 235:
                raise smtplib.SMTPAuthenticationError(typ, resp)
        else:
            sunucu.login(ayar["eposta"], ayar["sifre"])
        sunucu.sendmail(gonderen, alicilar, msg.as_string())
    finally:
        try:
            sunucu.quit()
        except Exception:
            pass


# ---------------------------------------------------------------------------
# IMAP okuma
# ---------------------------------------------------------------------------

def imap_baglan(ayar):
    M = imaplib.IMAP4_SSL(ayar["imap_host"], int(ayar["imap_port"]))
    if ayar.get("refresh_token"):                       # Microsoft OAuth
        token = ms_erisim_tokeni(ayar)
        M.authenticate("XOAUTH2", lambda _: _xoauth2(ayar["eposta"], token).encode())
    else:
        M.login(ayar["eposta"], ayar["sifre"])
    return M


def _list_satir_coz(satir):
    if isinstance(satir, bytes):
        satir = satir.decode("utf-8", "replace")
    m = re.match(r'\((?P<bayrak>[^)]*)\)\s+(?:"[^"]*"|NIL)\s+(?P<ad>.+)$', satir)
    if not m:
        return None, []
    ad = m.group("ad").strip()
    if ad.startswith('"') and ad.endswith('"'):
        ad = ad[1:-1]
    return ad, m.group("bayrak").split()


def _klasor_coz(M, rol):
    if rol == "inbox":
        return "INBOX"
    if rol == "self":
        rol = "sent"
    ozel = {"sent": "\\sent", "trash": "\\trash"}[rol]
    anahtar = {"sent": ["sent", "gönder", "giden", "sent mail", "sent items"],
               "trash": ["trash", "deleted", "çöp", "silin", "deleted items"]}[rol]
    try:
        typ, veri = M.list()
    except Exception:
        return None
    if typ != "OK" or not veri:
        return None
    aday = None
    for satir in veri:
        ad, bayraklar = _list_satir_coz(satir)
        if not ad:
            continue
        if any(b.lower() == ozel for b in bayraklar):
            return ad
        dusuk = ad.lower()
        if aday is None and any(k in dusuk for k in anahtar):
            aday = ad
    return aday


def klasor_listele(ayar, rol, adet=25):
    M = imap_baglan(ayar)
    try:
        folder = _klasor_coz(M, rol)
        if not folder:
            return None, []
        M.select(folder, readonly=True)
        typ, veri = M.uid("SEARCH", None, "ALL")
        if typ != "OK" or not veri or not veri[0]:
            return folder, []
        uidler = veri[0].split()
        if adet and adet > 0 and len(uidler) > adet:
            son = uidler[-adet:]
        else:
            son = uidler
        son = list(reversed(son))
        sonuc = []
        for u in son:
            typ, d = M.uid("FETCH", u, "(BODY.PEEK[HEADER.FIELDS (FROM TO CC SUBJECT DATE)])")
            if typ != "OK" or not d or not d[0]:
                continue
            msg = email.message_from_bytes(d[0][1])
            sonuc.append({
                "uid": u.decode() if isinstance(u, bytes) else str(u),
                "from": _coz(msg.get("From", "")), "to": _coz(msg.get("To", "")),
                "cc": _coz(msg.get("Cc", "")),
                "subject": _coz(msg.get("Subject", "(konu yok)")),
                "date": msg.get("Date", "")})
        return folder, sonuc
    finally:
        try:
            M.logout()
        except Exception:
            pass


def mesaj_getir(ayar, folder, uid):
    M = imap_baglan(ayar)
    try:
        M.select(folder, readonly=True)
        typ, veri = M.uid("FETCH", uid.encode(), "(RFC822)")
        if typ != "OK" or not veri or not veri[0]:
            raise RuntimeError("Mesaj getirilemedi.")
        msg = email.message_from_bytes(veri[0][1])
        govde, ekler = "", []
        if msg.is_multipart():
            duz, html = "", ""
            for parca in msg.walk():
                if parca.is_multipart():
                    continue
                ctype = parca.get_content_type()
                cdisp = str(parca.get("Content-Disposition") or "").lower()
                if "attachment" in cdisp or parca.get_filename():
                    ad = _coz(parca.get_filename() or "ek")
                    try:
                        ekler.append((ad, parca.get_payload(decode=True) or b""))
                    except Exception:
                        pass
                elif ctype == "text/plain" and not duz:
                    duz = _govde_coz(parca)
                elif ctype == "text/html" and not html:
                    html = _govde_coz(parca)
            if duz.strip():
                govde = duz
            elif html.strip():
                govde = html_temizle(html)
            else:
                govde = duz or ""
        else:
            ham = _govde_coz(msg)
            govde = html_temizle(ham) if msg.get_content_type() == "text/html" else ham
        return {"from": _coz(msg.get("From", "")), "to": _coz(msg.get("To", "")),
                "cc": _coz(msg.get("Cc", "")),
                "subject": _coz(msg.get("Subject", "(konu yok)")),
                "date": msg.get("Date", ""), "body": govde, "ekler": ekler}
    finally:
        try:
            M.logout()
        except Exception:
            pass


def mail_sil_coklu(ayar, folder, uidler, kalici=False):
    if not uidler:
        return
    M = imap_baglan(ayar)
    try:
        M.select(folder)
        trash = None if kalici else _klasor_coz(M, "trash")
        for u in uidler:
            ub = u.encode() if isinstance(u, str) else u
            if not kalici and trash and trash != folder:
                M.uid("COPY", ub, trash)
            M.uid("STORE", ub, "+FLAGS", "(\\Deleted)")
        M.expunge()
    finally:
        try:
            M.logout()
        except Exception:
            pass


def cop_bosalt(ayar):
    M = imap_baglan(ayar)
    try:
        trash = _klasor_coz(M, "trash")
        if not trash:
            return 0
        M.select(trash)
        typ, veri = M.uid("SEARCH", None, "ALL")
        uidler = veri[0].split() if (typ == "OK" and veri and veri[0]) else []
        if not uidler:
            return 0
        for u in uidler:
            M.uid("STORE", u, "+FLAGS", "(\\Deleted)")
        M.expunge()
        return len(uidler)
    finally:
        try:
            M.logout()
        except Exception:
            pass


def anahtar_eslesme(m, anahtarlar):
    if not anahtarlar:
        return False
    metin = (m.get("subject", "") + " " + m.get("from", "")).lower()
    return any(k.lower() in metin for k in anahtarlar if k.strip())
