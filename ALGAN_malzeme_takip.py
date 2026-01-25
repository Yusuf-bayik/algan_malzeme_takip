import tkinter as tk
from tkinter import ttk, messagebox, simpledialog, filedialog
from PIL import Image, ImageTk 
import json
import os
import sys 
import csv
import datetime
import shutil

# --- YOL BULUCU FONKSİYON ---
def dosya_yolunu_bul(dosya_adi):
    if getattr(sys, 'frozen', False):
        uygulama_yolu = os.path.dirname(sys.executable)
    else:
        uygulama_yolu = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(uygulama_yolu, dosya_adi)

# --- 1. VERİ VE AYARLAR ---
kablolarimiz = {}
donanimlarimiz = {}
komponentler = {} 
ekstra_gruplar = [] 

DOSYA_ADI = dosya_yolunu_bul("algan_veri.json")
LOGO_DOSYASI = dosya_yolunu_bul("algan_logo.jpg")
ARKA_PLAN_DOSYASI = dosya_yolunu_bul("teknofest.png")

KULLANICI_ADI = "algan"
SIFRE = "2025"

secilen_tablo = None 
siralama_modu = 0 
aktif_filtre = "TÜMÜ"
root = None 

# Arama çubuğu için global değişken
entry_arama = None 

# --- 2. RENK PALETİ ---
RENKLER = {
    "bg_dark": "#1e1e1e",       
    "sidebar": "#252526",       
    "header": "#007acc",        
    "text": "#d4d4d4",          
    "accent": "#007acc",        
    "row_even": "#2d2d2d",      
    "row_odd": "#333333",       
    "selected": "#264f78",      
    "success": "#4ec9b0",       
    "warning": "#f48771", 
    "info": "#9cdcfe"     
}

# --- 3. DOSYA İŞLEMLERİ ---
def verileri_kaydet():
    veriler = {
        "kablolar": kablolarimiz,
        "donanimlar": donanimlarimiz,
        "komponentler": komponentler,
        "ekstra_gruplar": ekstra_gruplar,
        "ayarlar": { 
            "kullanici_adi": KULLANICI_ADI,
            "sifre": SIFRE
        }
    }
    try:
        with open(DOSYA_ADI, "w", encoding="utf-8") as dosya:
            json.dump(veriler, dosya, ensure_ascii=False, indent=4)
    except Exception as e:
        messagebox.showerror("Kritik Hata", f"Dosya yazılamadı: {e}")

def verileri_yukle():
    global kablolarimiz, donanimlarimiz, komponentler, ekstra_gruplar, KULLANICI_ADI, SIFRE
    if os.path.exists(DOSYA_ADI):
        try:
            with open(DOSYA_ADI, "r", encoding="utf-8") as dosya:
                veriler = json.load(dosya)
                kablolarimiz = veriler.get("kablolar", {})
                donanimlarimiz = veriler.get("donanimlar", {})
                komponentler = veriler.get("komponentler", {}) 
                ekstra_gruplar = veriler.get("ekstra_gruplar", [])
                
                ayarlar = veriler.get("ayarlar", {})
                KULLANICI_ADI = ayarlar.get("kullanici_adi", "admin")
                SIFRE = ayarlar.get("sifre", "1234")
                
                for db in [kablolarimiz, donanimlarimiz, komponentler]:
                    for v in db.values():
                        if "grup" not in v: v["grup"] = "Genel"
                        if "not" not in v: v["not"] = ""
                        if "kritik_esik" not in v: v["kritik_esik"] = 0
        except Exception: pass

# --- 4. YARDIMCI FONKSİYONLAR ---
def gruplari_topla(veri_sozlugu):
    gruplar = set()
    for detay in veri_sozlugu.values():
        gruplar.add(detay.get("grup", "Genel"))
    return list(gruplar)

def tum_gruplari_getir():
    g1 = gruplari_topla(kablolarimiz)
    g2 = gruplari_topla(donanimlarimiz)
    g3 = gruplari_topla(komponentler) 
    toplam = set(g1 + g2 + g3 + ekstra_gruplar)
    liste = sorted(list(toplam))
    if "Genel" in liste:
        liste.remove("Genel")
        liste.insert(0, "Genel")
    elif not liste:
        liste = ["Genel"]
    return liste

def siralamayi_degistir():
    global siralama_modu
    siralama_modu = (siralama_modu + 1) % 3
    
    if siralama_modu == 0:
        text = "🕒 Ekleme Sırası"
    elif siralama_modu == 1:
        text = "🔤 A-Z"
    else:
        text = "📁 Gruplara Göre"
        
    btn_sirala.configure(text=text)
    tabloyu_yenile()

# --- 5. BİLDİRİM SİSTEMİ ---
def bildirim_goster(mesaj, tur="success"):
    renk = RENKLER["success"] if tur == "success" else RENKLER["warning"]
    lbl_sonuc.config(text=mesaj, fg=renk)
    root.after(3000, lambda: lbl_sonuc.config(text=""))

def liste_bildirim(mesaj):
    lbl_stat.config(text=mesaj, fg=RENKLER["success"])
    root.after(3000, lambda: lbl_stat.config(text="Sistem Hazır", fg="#888"))

# --- 6. GÖRÜNÜM GÜNCELLEME ---
def sidebar_guncelle():
    liste_sidebar.delete(0, tk.END)
    liste_sidebar.insert(tk.END, "  📂 TÜMÜ") 
    gruplar = tum_gruplari_getir()
    for grp in gruplar:
        liste_sidebar.insert(tk.END, f"  📁 {grp}")

def sidebar_secim(event):
    secim = liste_sidebar.curselection()
    if not secim: return
    deger = liste_sidebar.get(secim[0])
    grup_adi = deger.replace("  📁 ", "").replace("  📂 ", "")
    global aktif_filtre
    aktif_filtre = grup_adi
    lbl_liste_baslik.configure(text=f"Filtre: {aktif_filtre.upper()}")
    
    # Grup değişince arama kutusunu temizleyelim ki kafa karışmasın
    try:
        entry_arama.delete(0, tk.END)
    except: pass
    
    tabloyu_yenile()

def tabloyu_yenile():
    mevcut_tab_id = notebook_liste.index(notebook_liste.select())
    
    if mevcut_tab_id == 0: 
        hedef_tablo = tablo_kablo
        veri_kaynagi = kablolarimiz
    elif mevcut_tab_id == 1: 
        hedef_tablo = tablo_donanim
        veri_kaynagi = donanimlarimiz
    else:
        hedef_tablo = tablo_komponent
        veri_kaynagi = komponentler
        
    for i in hedef_tablo.get_children(): hedef_tablo.delete(i)

    liste_items = list(veri_kaynagi.items())
    
    if siralama_modu == 1: 
        liste_items.sort(key=lambda x: x[0])
    elif siralama_modu == 2: 
        liste_items.sort(key=lambda x: x[1].get("grup", "").lower())

    # --- ARAMA FİLTRESİ ---
    arama_metni = ""
    try:
        if entry_arama:
            arama_metni = entry_arama.get().strip().lower()
    except: pass
    # ----------------------

    count = 0
    for isim, detay in liste_items:
        # 1. GRUP FİLTRESİ
        if aktif_filtre != "TÜMÜ" and detay.get("grup") != aktif_filtre:
            continue
        
        # 2. ARAMA FİLTRESİ (YENİ)
        # Eğer arama kutusunda yazı varsa ve bu yazı ismin içinde geçmiyorsa GÖSTERME
        if arama_metni and arama_metni not in isim:
            continue
            
        ikonlar = []
        try:
            yedek_sayisi = int(detay.get('yedekdeki adet', 0))
            esik_degeri = int(detay.get('kritik_esik', 0))
            if esik_degeri > 0 and yedek_sayisi <= esik_degeri:
                ikonlar.append("⚠️")
        except: pass

        if detay.get("not"):
            ikonlar.append("📝")
            
        durum_ikonu = " ".join(ikonlar)
        
        tag = "even" if count % 2 == 0 else "odd"
        
        hedef_tablo.insert("", "end", iid=isim, values=(
            isim.upper(), 
            detay.get('grup', '-'), 
            detay['kullanimdaki adet'], 
            detay['yedekdeki adet'], 
            durum_ikonu
        ), tags=(tag,))
        count += 1
    
    if lbl_stat.cget("text") == "Sistem Hazır":
        lbl_stat.configure(text=f"Listelenen: {count} adet", fg="#888")

def tab_degisti(event):
    tabloyu_yenile()

# --- 7. İŞLEM FONKSİYONLARI ---
def urun_ekle(event=None):
    tur = tur_secim_ekle.get()
    isim = entry_isim_ekle.get().strip().lower()
    grup = cmb_grup_ekle.get().strip()
    if not grup: grup = "Genel"
    
    if not isim: 
        bildirim_goster("⚠️ Ürün adı boş olamaz!", "error")
        return

    try:
        kullanim = int(entry_kullanim_ekle.get())
        yedek = int(entry_yedek_ekle.get())
        esik_txt = entry_kritik_ekle.get().strip()
        kritik = int(esik_txt) if esik_txt else 0
    except: 
        bildirim_goster("⚠️ Lütfen geçerli sayı giriniz!", "error")
        return

    veri = {
        "kullanimdaki adet": kullanim, 
        "yedekdeki adet": yedek, 
        "grup": grup, 
        "not": "",
        "kritik_esik": kritik
    }
    
    if tur == 1: target = kablolarimiz
    elif tur == 2: target = donanimlarimiz
    else: target = komponentler

    target[isim] = veri

    if grup not in tum_gruplari_getir():
        ekstra_gruplar.append(grup)

    verileri_kaydet()
    
    entry_isim_ekle.delete(0, tk.END)
    entry_kullanim_ekle.delete(0, tk.END)
    entry_yedek_ekle.delete(0, tk.END)
    entry_kritik_ekle.delete(0, tk.END)
    
    sidebar_guncelle() 
    tabloyu_yenile()
    msg = f"✅ {isim.upper()} kaydedildi!"
    if kritik > 0: msg += f" (Limit: {kritik})"
    bildirim_goster(msg)

def yeni_grup_ekle_popup():
    yeni_isim = simpledialog.askstring("Yeni Grup", "Grup Adı Giriniz:")
    if yeni_isim:
        yeni_isim = yeni_isim.strip()
        if yeni_isim not in tum_gruplari_getir():
            ekstra_gruplar.append(yeni_isim)
            verileri_kaydet()
            sidebar_guncelle()
            try: cmb_grup_ekle['values'] = tum_gruplari_getir()
            except: pass
            liste_bildirim(f"Grup oluşturuldu: {yeni_isim}")
        else:
            messagebox.showwarning("Hata", "Bu grup zaten var.")

def sidebar_sag_tik(event):
    try:
        index = liste_sidebar.nearest(event.y)
        liste_sidebar.selection_clear(0, tk.END)
        liste_sidebar.selection_set(index)
        liste_sidebar.activate(index)
        menu_sidebar.post(event.x_root, event.y_root)
    except: pass

def secili_grubu_sil():
    secim = liste_sidebar.curselection()
    if not secim: return
    grup = liste_sidebar.get(secim[0]).replace("  📁 ", "").replace("  📂 ", "")
    if grup == "Genel" or "TÜMÜ" in grup: return

    if messagebox.askyesno("Sil", f"'{grup}' silinsin mi?\nÜrünler 'Genel' grubuna atılacak."):
        for db in [kablolarimiz, donanimlarimiz, komponentler]: 
            for v in db.values():
                if v.get("grup") == grup: v["grup"] = "Genel"
        if grup in ekstra_gruplar: ekstra_gruplar.remove(grup)
        verileri_kaydet()
        sidebar_guncelle()
        tabloyu_yenile()
        liste_bildirim("Grup silindi.")

def secili_grubu_adlandir():
    secim = liste_sidebar.curselection()
    if not secim: return
    eski = liste_sidebar.get(secim[0]).replace("  📁 ", "").replace("  📂 ", "")
    if "TÜMÜ" in eski: return

    yeni = simpledialog.askstring("Adlandır", "Yeni isim:", initialvalue=eski)
    if yeni and yeni != eski:
        for db in [kablolarimiz, donanimlarimiz, komponentler]: 
            for v in db.values():
                if v.get("grup") == eski: v["grup"] = yeni
        if eski in ekstra_gruplar:
            ekstra_gruplar.remove(eski); ekstra_gruplar.append(yeni)
        verileri_kaydet()
        sidebar_guncelle()
        tabloyu_yenile()
        liste_bildirim("Grup adı güncellendi.")

# --- YENİ EKLENEN FONKSİYONLAR (VERİ GÜVENLİĞİ) ---
def yedek_olustur():
    zaman_damgasi = datetime.datetime.now().strftime("%Y-%m-%d_%H-%M")
    yedek_klasoru = os.path.dirname(DOSYA_ADI) 
    yedek_adi = f"YEDEK_algan_veri_{zaman_damgasi}.json"
    hedef_yol = os.path.join(yedek_klasoru, yedek_adi)
    
    try:
        shutil.copy2(DOSYA_ADI, hedef_yol)
        messagebox.showinfo("Başarılı", f"Yedek oluşturuldu:\n\n{yedek_adi}")
    except Exception as e:
        messagebox.showerror("Hata", f"Yedekleme başarısız: {e}")

def excele_aktar():
    try:
        dosya_yolu = filedialog.asksaveasfilename(
            defaultextension=".csv",
            filetypes=[("CSV Dosyası (Excel)", "*.csv"), ("Tüm Dosyalar", "*.*")],
            initialfile="algan_stok_listesi.csv",
            title="Excel Listesini Nereye Kaydetmek İstersiniz?"
        )
        
        if dosya_yolu:
            with open(dosya_yolu, mode='w', newline='', encoding='utf-8-sig') as file:
                writer = csv.writer(file, delimiter=';') 
                writer.writerow(["TÜR", "ÜRÜN ADI", "GRUP", "KULLANIM", "YEDEK", "NOT"])
                
                for ad, veri in kablolarimiz.items():
                    writer.writerow(["Kablo", ad.upper(), veri.get("grup"), veri.get("kullanimdaki adet"), veri.get("yedekdeki adet"), veri.get("not", "")])
                
                for ad, veri in donanimlarimiz.items():
                    writer.writerow(["Donanım", ad.upper(), veri.get("grup"), veri.get("kullanimdaki adet"), veri.get("yedekdeki adet"), veri.get("not", "")])
                    
                for ad, veri in komponentler.items():
                    writer.writerow(["Komponent", ad.upper(), veri.get("grup"), veri.get("kullanimdaki adet"), veri.get("yedekdeki adet"), veri.get("not", "")])
                    
            messagebox.showinfo("Başarılı", f"Dosya başarıyla kaydedildi:\n{dosya_yolu}")
            
    except Exception as e:
        messagebox.showerror("Hata", f"Dışa aktarma hatası: {e}")

def yedekten_don():
    dosya_yolu = filedialog.askopenfilename(
        initialdir=os.path.dirname(DOSYA_ADI),
        title="Yedek Dosyası Seç (JSON)",
        filetypes=(("JSON Dosyaları", "*.json"), ("Tüm Dosyalar", "*.*"))
    )
    if dosya_yolu:
        cevap = messagebox.askyesno("DİKKAT!", "Eski bir yedeğe dönmek üzeresiniz.\nŞu anki veriler silinip, seçtiğiniz yedeğin verileri yüklenecek.\n\nEmin misiniz?")
        if cevap:
            try:
                shutil.copy2(dosya_yolu, DOSYA_ADI)
                verileri_yukle()
                sidebar_guncelle()
                tabloyu_yenile()
                messagebox.showinfo("Başarılı", "Sistem seçilen yedeğe geri döndürüldü!")
            except Exception as e:
                messagebox.showerror("Hata", f"Geri yükleme başarısız: {e}")

# --- AYARLAR ---
def ayarlari_ac():
    win = tk.Toplevel(root)
    win.title("Ayarlar ve Veri Yönetimi")
    win.geometry("400x500") 
    win.configure(bg=RENKLER["bg_dark"])
    
    # -- GÜVENLİK AYARLARI --
    tk.Label(win, text="⚙️ GÜVENLİK AYARLARI", bg=RENKLER["bg_dark"], fg="white", font=("Segoe UI", 12, "bold")).pack(pady=(20, 10))
    
    def lbl(t): tk.Label(win, text=t, bg=RENKLER["bg_dark"], fg=RENKLER["text"], anchor="w").pack(fill="x", padx=40, pady=(5,0))
    
    lbl("Mevcut Şifre:")
    e_eski = tk.Entry(win, show="*")
    e_eski.pack(padx=40, fill="x")
    e_eski.focus_set() 
    
    lbl("Yeni Kullanıcı Adı:")
    e_yeni_kul = tk.Entry(win)
    e_yeni_kul.pack(padx=40, fill="x")
    e_yeni_kul.insert(0, KULLANICI_ADI)
    
    lbl("Yeni Şifre:")
    e_yeni_sif = tk.Entry(win, show="*")
    e_yeni_sif.pack(padx=40, fill="x")
    e_yeni_sif.insert(0, SIFRE)
    
    def kaydet(event=None):
        global KULLANICI_ADI, SIFRE
        eski = e_eski.get()
        yeni_k = e_yeni_kul.get().strip()
        yeni_s = e_yeni_sif.get().strip()
        
        if eski != SIFRE:
            messagebox.showerror("Hata", "Mevcut şifre yanlış!")
            return
        
        if not yeni_k or not yeni_s:
            messagebox.showerror("Hata", "Alanlar boş bırakılamaz.")
            return
            
        KULLANICI_ADI = yeni_k
        SIFRE = yeni_s
        verileri_kaydet() 
        messagebox.showinfo("Başarılı", "Giriş bilgileri güncellendi.")
        
    tk.Button(win, text="ŞİFREYİ GÜNCELLE", command=kaydet, bg=RENKLER["success"], fg="black", font=("Segoe UI", 9, "bold")).pack(pady=15, fill="x", padx=40)
    
    # -- VERİ YÖNETİMİ --
    tk.Frame(win, height=2, bg="#3c3c3c").pack(fill="x", padx=20, pady=10) 
    tk.Label(win, text="💾 VERİ YÖNETİMİ & YEDEKLEME", bg=RENKLER["bg_dark"], fg=RENKLER["info"], font=("Segoe UI", 12, "bold")).pack(pady=10)

    btn_yedekle = tk.Button(win, text="📂 YEDEK OLUŞTUR (Güvenli)", command=yedek_olustur, bg="#3c3c3c", fg="white", relief="flat", pady=5)
    btn_yedekle.pack(fill="x", padx=40, pady=5)

    btn_excel = tk.Button(win, text="📊 EXCEL OLARAK İNDİR (Rapor)", command=excele_aktar, bg="#2d6a4f", fg="white", relief="flat", pady=5)
    btn_excel.pack(fill="x", padx=40, pady=5)

    btn_geri_yukle = tk.Button(win, text="⚠️ YEDEKTEN GERİ YÜKLE", command=yedekten_don, bg="#bc4749", fg="white", relief="flat", pady=5)
    btn_geri_yukle.pack(fill="x", padx=40, pady=5)

    win.bind('<Return>', kaydet)

# --- SAĞ TIK DÜZENLEME ---
def secilen_ogeyi_getir():
    aktif_tab_id = notebook_liste.index(notebook_liste.select())
    if aktif_tab_id == 0: 
        tablo = tablo_kablo
        tur = "Kablo"
    elif aktif_tab_id == 1:
        tablo = tablo_donanim
        tur = "Donanim"
    else:
        tablo = tablo_komponent
        tur = "Komponent"
        
    sel = tablo.selection()
    if not sel: return None, None, None
    isim = sel[0] 
    return sel, tur, isim

def sag_tik_duzenle():
    _, tur, isim = secilen_ogeyi_getir()
    if not isim: return
    if tur == "Kablo": hedef = kablolarimiz
    elif tur == "Donanim": hedef = donanimlarimiz
    else: hedef = komponentler
    
    if isim not in hedef: return

    veri = hedef[isim]
    
    win = tk.Toplevel(root)
    win.title(f"Düzenle: {isim}")
    win.geometry("300x400") 
    win.configure(bg=RENKLER["bg_dark"])
    
    def lbl(txt): tk.Label(win, text=txt, bg=RENKLER["bg_dark"], fg="white").pack(pady=2)
    
    lbl("Kullanım:"); e1 = tk.Entry(win); e1.pack(); e1.insert(0, veri["kullanimdaki adet"])
    lbl("Yedek:"); e2 = tk.Entry(win); e2.pack(); e2.insert(0, veri["yedekdeki adet"])
    
    lbl("Kritik Stok Limiti (0=Yok):")
    e3 = tk.Entry(win)
    e3.pack()
    e3.insert(0, veri.get("kritik_esik", 0))

    lbl("Grup:"); c1 = ttk.Combobox(win, values=tum_gruplari_getir()); c1.pack(); c1.set(veri["grup"])
    
    def kaydet(event=None):
        try:
            veri["kullanimdaki adet"] = int(e1.get())
            veri["yedekdeki adet"] = int(e2.get())
            veri["kritik_esik"] = int(e3.get()) 
            veri["grup"] = c1.get()
            
            if c1.get() not in tum_gruplari_getir(): ekstra_gruplar.append(c1.get())
            verileri_kaydet(); sidebar_guncelle(); tabloyu_yenile(); win.destroy()
            liste_bildirim("Ürün güncellendi.")
        except: messagebox.showerror("Hata", "Sayı girin")
    
    tk.Button(win, text="KAYDET", command=kaydet, bg=RENKLER["success"], fg="black", font="bold").pack(pady=20)
    win.bind('<Return>', kaydet)

def sag_tik_sil():
    _, tur, isim = secilen_ogeyi_getir()
    if not isim: return
    if messagebox.askyesno("Sil", "Bu ürün silinsin mi?"):
        if tur == "Kablo": kablolarimiz.pop(isim)
        elif tur == "Donanim": donanimlarimiz.pop(isim)
        else: komponentler.pop(isim)
        
        verileri_kaydet(); tabloyu_yenile()
        liste_bildirim("Ürün silindi.")

def sag_tik_not(event=None): 
    _, tur, isim = secilen_ogeyi_getir()
    if not isim: return
    if tur == "Kablo": hedef = kablolarimiz
    elif tur == "Donanim": hedef = donanimlarimiz
    else: hedef = komponentler
    
    win = tk.Toplevel(root)
    win.title("Not Düzenle")
    win.geometry("400x350") 
    win.configure(bg=RENKLER["bg_dark"])
    
    tk.Label(win, text=f"{isim.upper()} Notları:", bg=RENKLER["bg_dark"], fg="white").pack(pady=10)

    t = tk.Text(win, height=10, width=40)
    t.pack(padx=10, pady=5)
    t.insert("1.0", hedef[isim].get("not", ""))
    t.focus_set()
    
    def kaydet(event=None):
        hedef[isim]["not"] = t.get("1.0", tk.END).strip()
        verileri_kaydet(); tabloyu_yenile(); win.destroy()
        liste_bildirim("Not kaydedildi.")
        return "break"
    
    tk.Button(win, text="NOTU KAYDET (Enter)", command=kaydet, bg=RENKLER["accent"], fg="white", font=("Segoe UI", 10, "bold")).pack(side="bottom", fill="x", pady=10, padx=10)
    t.bind('<Return>', kaydet) 
    t.bind('<Shift-Return>', lambda e: None) 

def item_menu_ac(event):
    item = event.widget.identify_row(event.y)
    if item:
        event.widget.selection_set(item)
        menu_item.post(event.x_root, event.y_root)

# --- ANA UYGULAMA BAŞLATICI ---
def ana_uygulamayi_baslat():
    global root, notebook_liste, tablo_kablo, tablo_donanim, tablo_komponent, lbl_stat
    global tur_secim_ekle, entry_isim_ekle, cmb_grup_ekle, entry_kullanim_ekle, entry_yedek_ekle, lbl_sonuc
    global liste_sidebar, lbl_liste_baslik, btn_sirala, menu_sidebar, menu_item
    global entry_kritik_ekle, entry_arama # GLOBAL EKLENDİ

    root = tk.Tk()
    root.title("ALGAN STOCK MANAGER - ULTIMATE ")
    root.geometry("1100x750") 

    try:
        icon_img = Image.open(LOGO_DOSYASI)
        photo_icon = ImageTk.PhotoImage(icon_img)
        root.iconphoto(False, photo_icon)
    except Exception: pass

    style = ttk.Style()
    style.theme_use('clam')

    style.configure("Treeview", 
                    background=RENKLER["bg_dark"], 
                    foreground=RENKLER["text"], 
                    fieldbackground=RENKLER["bg_dark"],
                    rowheight=35,
                    font=("Segoe UI", 10))

    style.configure("Treeview.Heading", 
                    background=RENKLER["sidebar"], 
                    foreground="white", 
                    font=("Segoe UI", 10, "bold"),
                    relief="flat")

    style.map("Treeview", background=[('selected', RENKLER["selected"])])
    style.map("Treeview.Heading", background=[('active', RENKLER["header"])])

    style.configure("TNotebook", background=RENKLER["bg_dark"], borderwidth=0)
    style.configure("TNotebook.Tab", background=RENKLER["sidebar"], foreground="white", padding=[20, 8])
    style.map("TNotebook.Tab", background=[('selected', RENKLER["accent"])])

    root.configure(bg=RENKLER["bg_dark"])

    # BAŞLIK (Header)
    frame_header = tk.Frame(root, bg=RENKLER["header"], height=60)
    frame_header.pack(fill="x")

    header_container = tk.Frame(frame_header, bg=RENKLER["header"])
    header_container.pack(side="left", padx=20, pady=5)

    try:
        pil_img = Image.open(LOGO_DOSYASI)
        pil_img.thumbnail((50, 50)) 
        logo_img = ImageTk.PhotoImage(pil_img)
        lbl_logo = tk.Label(header_container, image=logo_img, bg=RENKLER["header"])
        lbl_logo.image = logo_img 
        lbl_logo.pack(side="left", padx=(0, 10))
    except Exception: pass

    tk.Label(header_container, text="ALGAN STOK TAKİP SİSTEMİ", bg=RENKLER["header"], fg="white", font=("Segoe UI", 18, "bold")).pack(side="left")

    # ANA TABLAR
    main_tabs = ttk.Notebook(root)
    main_tabs.pack(fill="both", expand=True, padx=10, pady=10)

    tab_liste = ttk.Frame(main_tabs)
    tab_ekle = ttk.Frame(main_tabs)
    main_tabs.add(tab_liste, text=" 📊 STOK LİSTESİ ")
    main_tabs.add(tab_ekle, text=" ➕ YENİ EKLE ")

    # --- SEKME 1: LİSTE VE SIDEBAR ---
    paned = tk.PanedWindow(tab_liste, orient=tk.HORIZONTAL, bg=RENKLER["bg_dark"], sashwidth=4, sashrelief="flat")
    paned.pack(fill="both", expand=True)

    sidebar = tk.Frame(paned, bg=RENKLER["sidebar"], width=230)
    paned.add(sidebar)

    tk.Label(sidebar, text="GRUPLAR", bg=RENKLER["sidebar"], fg="#888", font=("Segoe UI", 9, "bold")).pack(anchor="w", padx=15, pady=(20,5))

    liste_sidebar = tk.Listbox(sidebar, bg=RENKLER["sidebar"], fg=RENKLER["text"], 
                                selectbackground=RENKLER["selected"], 
                                activestyle="none", borderwidth=0, highlightthickness=0, 
                                font=("Segoe UI", 11))
    liste_sidebar.pack(fill="both", expand=True, padx=5, pady=5)
    liste_sidebar.bind("<<ListboxSelect>>", sidebar_secim)
    liste_sidebar.bind("<Button-3>", sidebar_sag_tik)

    btn_yeni_grup = tk.Button(sidebar, text="+ YENİ GRUP OLUŞTUR", bg=RENKLER["selected"], fg="white", relief="flat", command=yeni_grup_ekle_popup, pady=8)
    btn_yeni_grup.pack(fill="x", side="bottom", padx=15, pady=5)

    btn_ayarlar = tk.Button(sidebar, text="⚙️ AYARLAR", bg="#3c3c3c", fg="white", relief="flat", command=ayarlari_ac, pady=8)
    btn_ayarlar.pack(fill="x", side="bottom", padx=15, pady=(0, 15))

    content = tk.Frame(paned, bg=RENKLER["bg_dark"])
    paned.add(content)

    top_bar = tk.Frame(content, bg=RENKLER["bg_dark"])
    top_bar.pack(fill="x", padx=15, pady=15)
    lbl_liste_baslik = tk.Label(top_bar, text="Filtre: TÜMÜ", bg=RENKLER["bg_dark"], fg="white", font=("Segoe UI", 16))
    lbl_liste_baslik.pack(side="left")

    # --- ARAMA ÇUBUĞU (YENİ) ---
    btn_sirala = ttk.Button(top_bar, text="🕒 Ekleme Sırası", command=siralamayi_degistir)
    btn_sirala.pack(side="right")

    tk.Label(top_bar, text="🔍 Ara:", bg=RENKLER["bg_dark"], fg="#888", font=("Segoe UI", 10)).pack(side="right", padx=(15, 5))
    entry_arama = tk.Entry(top_bar, bg="#333", fg="white", insertbackground="white", relief="flat", font=("Segoe UI", 10))
    entry_arama.pack(side="right", ipady=3, padx=(0, 5))
    
    # Her tuşa basıldığında tabloyu yenile
    entry_arama.bind("<KeyRelease>", lambda event: tabloyu_yenile())
    # ---------------------------

    notebook_liste = ttk.Notebook(content)
    notebook_liste.pack(fill="both", expand=True, padx=10, pady=5)
    notebook_liste.bind("<<NotebookTabChanged>>", tab_degisti)

    sub_kablo = ttk.Frame(notebook_liste)
    sub_donanim = ttk.Frame(notebook_liste)
    sub_komponent = ttk.Frame(notebook_liste) 

    notebook_liste.add(sub_kablo, text=" KABLOLAR ")
    notebook_liste.add(sub_donanim, text=" DONANIMLAR ")
    notebook_liste.add(sub_komponent, text=" KOMPONENTLER ") 

    cols = ("Isim", "Grup", "Kul.", "Yedek", "Durum")

    def tablo_kur(parent):
        tv = ttk.Treeview(parent, columns=cols, show="headings")
        tv.heading("Isim", text="ÜRÜN ADI", anchor="w")
        tv.heading("Grup", text="GRUP", anchor="center")
        tv.heading("Kul.", text="KULLANIMDA", anchor="center")
        tv.heading("Yedek", text="YEDEKTE", anchor="center")
        tv.heading("Durum", text="DURUM", anchor="center") 
        
        tv.column("Isim", width=250, anchor="w")
        tv.column("Grup", width=120, anchor="center")
        tv.column("Kul.", width=100, anchor="center") 
        tv.column("Yedek", width=100, anchor="center")
        tv.column("Durum", width=80, anchor="center")
        
        tv.tag_configure("odd", background=RENKLER["row_odd"])
        tv.tag_configure("even", background=RENKLER["row_even"])
        
        tv.pack(fill="both", expand=True)
        tv.bind("<Button-3>", item_menu_ac)
        tv.bind("<Double-1>", sag_tik_not) 
        return tv

    tablo_kablo = tablo_kur(sub_kablo)
    tablo_donanim = tablo_kur(sub_donanim)
    tablo_komponent = tablo_kur(sub_komponent) 

    footer = tk.Frame(content, bg=RENKLER["sidebar"], height=30)
    footer.pack(fill="x")
    lbl_stat = tk.Label(footer, text="Sistem Hazır", bg=RENKLER["sidebar"], fg="#888", font=("Segoe UI", 9))
    lbl_stat.pack(side="right", padx=10)


    # --- SEKME 2: MODERN EKLEME KARTI ---
    bg_frame = tk.Frame(tab_ekle, bg=RENKLER["bg_dark"])
    bg_frame.pack(fill="both", expand=True)

    card_frame = tk.Frame(bg_frame, bg=RENKLER["sidebar"], padx=25, pady=25)
    card_frame.place(relx=0.5, rely=0.5, anchor="center", width=500) 

    tk.Label(card_frame, text="YENİ ÜRÜN KARTI", bg=RENKLER["sidebar"], fg=RENKLER["accent"], font=("Segoe UI", 14, "bold")).pack(pady=(0, 20))

    fr_radio = tk.Frame(card_frame, bg=RENKLER["sidebar"])
    fr_radio.pack(fill="x", pady=5)
    tur_secim_ekle = tk.IntVar(value=1)
    style.configure("TRadiobutton", background=RENKLER["sidebar"], foreground="white", font=("Segoe UI", 10))
    
    ttk.Radiobutton(fr_radio, text="🔌 Kablo", variable=tur_secim_ekle, value=1).pack(side="left", padx=(40, 10))
    ttk.Radiobutton(fr_radio, text="🖥️ Donanım", variable=tur_secim_ekle, value=2).pack(side="left", padx=10)
    ttk.Radiobutton(fr_radio, text="⚙️ Komponent", variable=tur_secim_ekle, value=3).pack(side="left", padx=10)

    tk.Label(card_frame, text="ÜRÜN ADI", bg=RENKLER["sidebar"], fg="#888", font=("Segoe UI", 9, "bold"), anchor="w").pack(fill="x", pady=(20, 5))
    entry_isim_ekle = tk.Entry(card_frame, bg=RENKLER["bg_dark"], fg="white", insertbackground="white", relief="flat", font=("Segoe UI", 11))
    entry_isim_ekle.pack(fill="x", ipady=8, padx=1)

    tk.Label(card_frame, text="GRUP / KATEGORİ", bg=RENKLER["sidebar"], fg="#888", font=("Segoe UI", 9, "bold"), anchor="w").pack(fill="x", pady=(15, 5))
    cmb_grup_ekle = ttk.Combobox(card_frame, font=("Segoe UI", 11))
    cmb_grup_ekle.pack(fill="x", ipady=5)

    fr_adetler = tk.Frame(card_frame, bg=RENKLER["sidebar"])
    fr_adetler.pack(fill="x", pady=(20, 5))

    fr_sol = tk.Frame(fr_adetler, bg=RENKLER["sidebar"])
    fr_sol.pack(side="left", fill="x", expand=True, padx=(0, 10))
    tk.Label(fr_sol, text="KULLANIM ADEDİ", bg=RENKLER["sidebar"], fg="#888", font=("Segoe UI", 8, "bold"), anchor="w").pack(fill="x")
    entry_kullanim_ekle = tk.Entry(fr_sol, bg=RENKLER["bg_dark"], fg="white", insertbackground="white", relief="flat", font=("Segoe UI", 11), justify="center")
    entry_kullanim_ekle.pack(fill="x", ipady=8, pady=5)

    fr_sag = tk.Frame(fr_adetler, bg=RENKLER["sidebar"])
    fr_sag.pack(side="right", fill="x", expand=True, padx=(10, 0))
    tk.Label(fr_sag, text="YEDEK ADEDİ", bg=RENKLER["sidebar"], fg="#888", font=("Segoe UI", 8, "bold"), anchor="w").pack(fill="x")
    entry_yedek_ekle = tk.Entry(fr_sag, bg=RENKLER["bg_dark"], fg="white", insertbackground="white", relief="flat", font=("Segoe UI", 11), justify="center")
    entry_yedek_ekle.pack(fill="x", ipady=8, pady=5)

    tk.Label(card_frame, text="KRİTİK STOK UYARISI LİMİTİ (Opsiyonel)", bg=RENKLER["sidebar"], fg="#888", font=("Segoe UI", 8, "bold"), anchor="w").pack(fill="x", pady=(15, 5))
    entry_kritik_ekle = tk.Entry(card_frame, bg=RENKLER["bg_dark"], fg="white", insertbackground="white", relief="flat", font=("Segoe UI", 11), justify="center")
    entry_kritik_ekle.pack(fill="x", ipady=8, padx=1)
    entry_kritik_ekle.bind('<Return>', urun_ekle)

    btn_kaydet = tk.Button(card_frame, text="SİSTEME KAYDET", command=urun_ekle, bg=RENKLER["success"], fg="#1e1e1e", font=("Segoe UI", 11, "bold"), relief="flat", cursor="hand2")
    btn_kaydet.pack(fill="x", pady=(20, 0), ipady=6)

    lbl_sonuc = tk.Label(card_frame, text="", bg=RENKLER["sidebar"], font=("Segoe UI", 10, "bold"))
    lbl_sonuc.pack(pady=(10, 0))

    # --- MENÜLER ---
    menu_sidebar = tk.Menu(root, tearoff=0, bg=RENKLER["sidebar"], fg="white")
    menu_sidebar.add_command(label="✏️ Adlandır", command=secili_grubu_adlandir)
    menu_sidebar.add_command(label="🗑️ Sil", command=secili_grubu_sil)

    menu_item = tk.Menu(root, tearoff=0, bg=RENKLER["sidebar"], fg="white")
    menu_item.add_command(label="📝 Durum/Not", command=sag_tik_not)
    menu_item.add_command(label="✏️ Düzenle", command=sag_tik_duzenle)
    menu_item.add_separator()
    menu_item.add_command(label="🗑️ Sil", command=sag_tik_sil)

    sidebar_guncelle()
    tabloyu_yenile()
    try: cmb_grup_ekle['values'] = tum_gruplari_getir()
    except: pass

    root.mainloop()

# --- GİRİŞ EKRANI (CANVAS İLE MODERN TASARIM) ---
def giris_ekrani():
    giris_root = tk.Tk()
    giris_root.title("Giriş Yap")
    
    W, H = 400, 550
    giris_root.geometry(f"{W}x{H}")
    giris_root.resizable(False, False)

    canvas = tk.Canvas(giris_root, width=W, height=H, highlightthickness=0)
    canvas.pack(fill="both", expand=True)

    try:
        bg_pil = Image.open(ARKA_PLAN_DOSYASI)
        bg_pil = bg_pil.resize((W, H), Image.LANCZOS)
        bg_img = ImageTk.PhotoImage(bg_pil)
        canvas.create_image(0, 0, image=bg_img, anchor="nw")
    except:
        canvas.configure(bg="#1e1e1e")

    try:
        logo_pil = Image.open(LOGO_DOSYASI).convert("RGBA")
        basewidth = 160
        wpercent = (basewidth / float(logo_pil.size[0]))
        hsize = int((float(logo_pil.size[1]) * float(wpercent)))
        logo_pil = logo_pil.resize((basewidth, hsize), Image.LANCZOS)
        
        data = logo_pil.getdata()
        new_data = []
        for item in data:
            if item[0] > 230 and item[1] > 230 and item[2] > 230:
                new_data.append((255, 255, 255, 0)) 
            else:
                new_data.append(item)
        logo_pil.putdata(new_data)
        
        logo_img = ImageTk.PhotoImage(logo_pil)
        canvas.create_image(W/2, 100, image=logo_img)
        giris_root.logo_img_ref = logo_img 
    except Exception as e:
        print(f"Logo hatası: {e}")

    canvas.create_text(W/2 + 2, 242, text="HOŞ GELDİNİZ", fill="black", font=("Segoe UI", 18, "bold"))
    canvas.create_text(W/2, 240, text="HOŞ GELDİNİZ", fill="#FFD700", font=("Segoe UI", 18, "bold"))

    canvas.create_text(W/2 - 149, 291, text="Kullanıcı Adı", fill="black", font=("Segoe UI", 10, "bold"), anchor="w")
    canvas.create_text(W/2 - 150, 290, text="Kullanıcı Adı", fill="#FFD700", font=("Segoe UI", 10, "bold"), anchor="w")
    
    ent_kul = tk.Entry(giris_root, bg="#2d2d2d", fg="white", font=("Segoe UI", 11), relief="flat", insertbackground="white")
    canvas.create_window(W/2, 320, window=ent_kul, width=300, height=35)

    canvas.create_text(W/2 - 149, 361, text="Şifre", fill="black", font=("Segoe UI", 10, "bold"), anchor="w")
    canvas.create_text(W/2 - 150, 360, text="Şifre", fill="#FFD700", font=("Segoe UI", 10, "bold"), anchor="w")
    
    ent_sif = tk.Entry(giris_root, bg="#2d2d2d", fg="white", font=("Segoe UI", 11), relief="flat", show="*", insertbackground="white")
    canvas.create_window(W/2, 390, window=ent_sif, width=300, height=35)

    lbl_hata = tk.Label(giris_root, text="", bg="#1e1e1e", fg="#f48771", font=("Segoe UI", 9)) 
    canvas.create_window(W/2, 430, window=lbl_hata, width=300)

    def kontrol_et(event=None):
        k = ent_kul.get()
        s = ent_sif.get()
        if k == KULLANICI_ADI and s == SIFRE:
            giris_root.destroy()
            ana_uygulamayi_baslat()
        else:
            lbl_hata.config(text="Hatalı kullanıcı adı veya şifre!", bg="#2d2d2d")

    btn_giris = tk.Button(giris_root, text="GİRİŞ YAP", command=kontrol_et, 
                          bg="#007acc", fg="white", font=("Segoe UI", 12, "bold"), 
                          relief="flat", cursor="hand2", activebackground="#005f9e", activeforeground="white")
    
    canvas.create_window(W/2, 480, window=btn_giris, width=300, height=45)
    giris_root.bind('<Return>', kontrol_et)

    giris_root.mainloop()

# --- BAŞLATMA ---
verileri_yukle()
giris_ekrani()