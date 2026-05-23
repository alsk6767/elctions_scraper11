"""
projekt_3.py: třetí projekt do Engeto Online Python Akademie

author: Petr Svetr
email: petr.svetr@gmail.com
discord: Petr Svetr#4490
"""

import sys
import csv
import requests
from bs4 import BeautifulSoup

# Základní URL
BASE_URL = "https://volby.cz/pls/ps2017nps/"


def zkontroluj_argumenty():
    """Zkontroluje, zda uživatel zadal správný počet argumentů."""
    if len(sys.argv) != 3:
        print("Chyba: Je nutné zadat přesně 2 argumenty!")
        print("Použití: pythonBase projekt_3.py <URL_ODKAZ> <NAZEV_VYSTUPNIHO_SOUBORU>")
        sys.exit(1)
    
    url = sys.argv[1]
    vystupni_soubor = sys.argv[2]
    
    if not url.startswith("https://volby.cz"):
        print("Chyba: První argument musí být validní odkaz z volby.cz!")
        sys.exit(1)
        
    if not vystupni_soubor.endswith(".csv"):
        print("Chyba: Druhý argument musí mít příponu .csv!")
        sys.exit(1)

    return url, vystupni_soubor


def nacti_html(url):
    """Pomocná funkce, která stáhne HTML a vrátí BeautifulSoup objekt."""
    odpoved = requests.get(url)
    if odpoved.status_code != 200:
        print(f"Chyba při stahování stránky: {url}")
        sys.exit(1)
    return BeautifulSoup(odpoved.text, "html.parser")


def ziskej_seznam_obci(hlavni_url):
    """Projde hlavní tabulku územního celku a vytáhne základní info o obcích."""
    soup = nacti_html(hlavni_url)
    obce = []
    
    # Najdeme všechny řádky v tabulkách (může jich být na stránce víc)
    vsechny_tr = soup.find_all("tr")
    
    for tr in vsechny_tr:
        # Hledáme buňku s kódem obce (má class "cislo")
        kod_td = tr.find("td", {"class": "cislo"})
        if kod_td and kod_td.find("a"):
            kod = kod_td.text.strip()
            odkaz_obec = BASE_URL + kod_td.find("a")["href"]
            
            # Název obce bývá obvykle ve stejném řádku, o 1 nebo 2 sloupce vedle
            
td
            nazev_td = tr.find("td", {"class": "overflow_name"})
            if not nazev_td:
                # Pokud nemá class, zkusíme vzít třetí td v pořadí (index 1)
                vsechna_td = tr.find_all("td")
                nazev = vsechna_td[1].text.strip()
            else:
                nazev = nazev_td.text.strip()
                
            obce.append({
                "kod": kod,
                "nazev": nazev,
                "url": odkaz_obec
            })
            
    return obce


def scrapuj_detail_obce(url_obce):
    """Navštíví detail obce a vytáhne voliče, obálky, platné hlasy a hlasy pro strany."""
    soup = nacti_html(url_obce)
    data_obce = {}
    
    # 1. Hlavička s voliči (registrovaní, obálky, platné)
    # Tyto hodnoty najdeme v tabulce s id="ps311_t1"
    vsetky_td = soup.find_all("td")
    
    # Hledáme podle unikátních hlaviček (headers) v HTML kódu
    volici = soup.find("td", {"headers": "sa2"}).text.replace("\xa0", "").strip()
    obalky = soup.find("td", {"headers": "sa3"}).text.replace("\xa0", "").strip()
    platne = soup.find("td", {"headers": "sa6"}).text.replace("\xa0", "").strip()
    
    data_obce["registered"] = int(volici)
    data_obce["envelopes"] = int(obalky)
    data_obce["valid"] = int(platne)
    
    # 2. Hlasy pro politické strany
    # Strany jsou často rozdělené do dvou tabulek (t1 a t2), projdeme proto všechny příslušné řádky
    # Hledáme řádky, kde hlavička odpovídá hlasům pro stranu (t1sb3 nebo t2sb3)
    strany_tr = soup.find_all("tr")
    
    for tr in strany_tr:
        nazev_strany_td = tr.find("td", {"headers": "t1sa1_r1"}) or tr.find("td", {"headers": "t2sa1_r1"}) # zkuste najít název
        # Pokud se hlavičky liší, bezpečnější je hledat td s class "overflow_name" pro název strany
        # a sousední td s class "cislo" pro procenta/počty.
        
        # Pojďme na to univerzálněji přes hlavičky v detailu:
        # V detailu obce jsou názvy stran v td s class "overflow_name"
        nazev_td = tr.find("td", {"class": "overflow_name"})
        if nazev_td:
            nazev_strany = nazev_td.text.strip()
            # Počet hlasů je v tom samém řádku, obvykle v td následujícím (hledáme s patřičnou hlavičkou)
            # Často má header "t1sa2_r1" nebo "t2sa2_r1" (podle tabulky), nebo je to prostě další číslo.
            vsechna_cisla = tr.find_all("td", {"class": "cislo"})
            # První číslo v řádku strany bývá počet hlasů, druhé je procento
            if vsechna_cisla:
                hlasy_strany = vsechna_cisla[0].text.replace("\xa0", "").strip()
                data_obce[nazev_strany] = int(hlasy_strany)
                
    return data_obce


def hlavni_manazer():
    # 1. Kontrola vstupů
    hlavni_url, vystupni_soubor = zkontroluj_argumenty()
    
    print(f"STAHUJI DATA Z VYBRANÉHO URL: {hlavni_url}")
    
    # 2. Získání seznamu obcí
    seznam_obci = ziskej_seznam_obci(hlavni_url)
    if not seznam_obci:
        print("Chyba: Nepodařilo se nalézt žádné obce. Zkontrolujte URL.")
        return
        
    print(f"Nalezeno obcí: {len(seznam_obci)}. Začínám stahovat detaily...")
    
    vysledna_data = []
    
    # 3. Procházení jednotlivých obcí
    for i, obec in enumerate(seznam_obci, 1):
        print(f"Zpracovávám ({i}/{len(seznam_obci)}): {obec['nazev']}")
        
        # Získání detailních dat (voliči + strany)
        detaily = scrapuj_detail_obce(obec["url"])
        
        # Spojení základních dat a detailů do jednoho slovníku
        radek = {
            "code": obec["kod"],
            "location": obec["nazev"],
            **detaily
        }
        vysledna_data.append(radek)
        
    # 4. Zápis do CSV souboru
    print(f"UKLÁDÁM DATA DO SOUBORU: {vystupni_soubor}")
    
    # Hlavičku dynamicky poskládáme z klíčů prvního záznamu
    hlavicka = list(vysledna_data[0].keys())
    
    with open(vystupni_soubor, mode="w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=hlavicka)
        writer.writeheader()
        writer.writerows(vysledna_data)
        
    print("HOTOVO! Projekt byl úspěšně dokončen.")


if __name__ == "__main__":
    hlavni_manazer()