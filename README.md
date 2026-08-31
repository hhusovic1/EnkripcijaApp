# Enkripcijski algoritmi

Demonstraciona aplikacija uz završni rad prvog ciklusa studija — Elektrotehnički
fakultet, Univerzitet u Sarajevu.

Rad analizira enkripcijske algoritme teorijski; ova aplikacija ih pokazuje na
djelu, s **izmjerenim** performansama umjesto brojeva preuzetih iz literature.

**DES, 3DES, AES i RSA implementirani su ručno**, u čistom Pythonu, prema opisu
iz poglavlja 3 rada — bez kriptografskih biblioteka, i validirani protiv
zvaničnih test vektora. ECDH (X25519) i ChaCha20 idu kroz provjerene biblioteke,
jer se eliptičke krive i tokovne šifre ne implementiraju ručno bez ozbiljnog
rizika od suptilnih grešaka (vidi 3.4.5).

---

## Sadržaj

- [Pokretanje](#pokretanje)
- [Šta aplikacija radi](#šta-aplikacija-radi)
- [Struktura](#struktura)
- [Validacija](#validacija)
- [Benchmark](#benchmark)
- [Demonstracije napada](#demonstracije-napada)
- [Frontend](#frontend)
- [Deploy](#deploy)
- [Ograničenja](#ograničenja)

---

## Pokretanje

Potreban je **samo Python 3.11+** (razvijano na 3.14). Node je potreban
isključivo ako mijenjaš frontend — kompajlirani JavaScript je u repozitoriju.

```bash
python -m venv .venv
```

Aktivacija na Windowsu:

```bash
.venv\Scripts\activate
```



Zatim:

```bash
pip install -r requirements.txt
```

```bash
python server.py
```

Aplikacija se otvara na `http://localhost:5000`.

---

## Šta aplikacija radi

**Core algoritmi** — šifruj i dešifruj tekst bilo kojim od šest algoritama.
Simetrični rade nad tekstom proizvoljne dužine (PKCS#7 dopuna + CBC), RSA nad
jednim blokom, a ECDH demonstrira razmjenu ključeva i hibridnu shemu iz 3.5.3.
Nakon svake operacije prikazuje se vrijeme i provjerava da dekripcija vrati
bajt po bajt isti sadržaj.

**Benchmark** — izmjerene performanse kroz veličine podataka i dužine ključeva,
s error barovima. Podaci su unaprijed izmjereni; mjerenje uživo bilo bi
presporo, jer ručni AES postiže oko 46 KB/s.

**Sigurnosne demonstracije** — MITM napad na Diffie-Hellman i Wienerov napad na
RSA. Oba se izvršavaju stvarno, u trenutku klika; MITM se otkriva korak po
korak, jer je poenta napada u redoslijedu poteza.

---

## Struktura

| Putanja | Sadržaj |
|---|---|
| `core/` | Implementacije algoritama — jedinstven interfejs `generate_keys()` / `encrypt()` / `decrypt()` |
| `core/modes.py` | PKCS#7 dopuna i CBC režim — sloj iznad blokovnih šifara |
| `attacks/` | MITM na Diffie-Hellman (3.4.4), Wienerov napad na RSA (3.3.6) |
| `benchmark/` | Mjerenje performansi i generisanje grafova za rad |
| `web/` | Flask aplikacija — rute, JSON API, Jinja šabloni, CSS |
| `web/ts/` | TypeScript izvor za frontend (kompajlira se u `web/static/js/`) |
| `tests/` | Validacija |
| `server.py`, `wsgi.py` | Ulazne tačke — razvojni server i WSGI za produkciju |

Sav kriptografski kod je UI-agnostičan. `web/` ga samo izlaže kroz HTTP i ne
implementira ništa svoje.

---

## Validacija

```bash
python tests/run_all.py
```

**105 testova**, oko 30 sekundi.

| Modul | Testova | Šta pokriva |
|---|---|---|
| `test_des.py` | 13 | FIPS 46-3 / NBS SP 500-20 vektori, slabi i polu-slabi ključevi, 3DES opcije |
| `test_aes.py` | 13 | FIPS-197 Appendix A, B i C — sve tri dužine ključa |
| `test_rsa.py` | 13 | Struktura ključa, verižni razlomci, Wiener, sve četiri dužine |
| `test_modes.py` | 14 | PKCS#7, CBC, ECDH, ChaCha20 |
| `test_mitm.py` | 13 | Uredna DH razmjena i napad posrednika |
| `test_api.py` | 17 | Svaka Flask ruta, uključujući obradu grešaka |
| `test_wiener.py` | 9 | Rekonstrukcija malog `d`, kontrast s normalnim ključem |
| `test_stranice.py` | 9 | Streamlit stranice kroz `AppTest` |
| `test_plot.py` | 4 | Grafovi, uključujući crtanje iz više niti |

Ručne implementacije provjeravaju se na **dva nezavisna načina**:

1. **Zvanični test vektori** — FIPS 46-3 za DES, FIPS-197 za AES.
2. **Unakrsna provjera** — isti ulaz kroz `pycryptodome`, na stotinama
   nasumičnih ključeva i blokova. Fiksni vektori mogu propustiti grešku koja se
   javlja samo na određenim ulazima.

AES S-box se ne prepisuje kao tabela nego **izvodi iz definicije**
(multiplikativni inverz u GF(2⁸) + afina transformacija), a test provjerava da
se izvedena tabela poklapa sa standardom.

---

## Benchmark

Mjerenje je odvojeno od aplikacije jer je presporo za rad uživo.

```bash
python benchmark/run_benchmark.py
```

Rezultat je `benchmark/results.csv` — 104 mjerenja, oko 6 minuta. Slike za rad:

```bash
python benchmark/plot_results.py
```

Snimaju se u `benchmark/figures/`. Aplikacija crta iste grafove iz istog CSV-a,
pa su brojevi u radu i u aplikaciji garantovano isti.

### Kako čitati rezultate

DES, 3DES, AES i RSA su ručne Python implementacije, pisane radi čitljivosti i
podudaranja s opisom u radu — **ne radi brzine**. ChaCha20, ECDH i varijante
označene *(biblioteka)* izvršavaju se kroz optimizovani C kod. Razlika među tim
grupama mjeri **implementaciju**, ne samo algoritam; kolona `kategorija` u
CSV-u postoji upravo da se to razdvoji.

Poređenja **unutar iste grupe** su ono što nosi zaključak:

| Nalaz | Izmjereno |
|---|---|
| 3DES naspram DES-a | **2.97×** sporiji — potvrđuje tvrdnju iz 3.5.1 |
| AES-128 naspram DES-a | 85 ms naspram 117 ms — AES je brži |
| RSA keygen, 1024 → 4096 bita | 0.048 s → 7.60 s, uz σ = 5.49 s |
| Ručni AES naspram biblioteke | ~6600× — mjeri implementaciju, ne algoritam |

Velika devijacija kod RSA keygena nije greška mjerenja: traženje prostog broja
je probabilističko.

### Zašto RSA na grafu ima samo jednu tačku

Ostali algoritmi obrađuju ulaz proizvoljne dužine u petlji, pa se mogu izmjeriti
na više veličina. RSA je jedna operacija nad jednim brojem manjim od modula, pa
dužina ključa određuje **jedinu moguću** veličinu ulaza (126–510 B). Tačke leže
nisko jer je obrađeno malo podataka, a ne zato što je RSA brz — po bajtu je
RSA-4096 dekripcija 3.8 KB/s naspram 24.3 KB/s ručnog AES-a.

---

## Demonstracije napada

Rade i iz terminala i kroz aplikaciju.

```bash
python attacks/mitm_dh.py
```

MITM na neautentifikovani Diffie-Hellman. Radi na malom prostom broju (čitljivi
brojevi) i na stvarnoj MODP grupi 14 iz RFC 3526. Poruka se stvarno šifruje
ručnim AES-om, pa „Mallory čita poruku" nije tvrdnja nego demonstracija.

Ključna poenta koju testovi čuvaju: **Mallory nikad ne sazna tajne eksponente**
niti razbija diskretni logaritam. Vodi dvije regularne DH razmjene — napad ruši
izostanak autentifikacije, ne matematiku.

```bash
python attacks/wiener_rsa.py
```

Wienerov napad rekonstruiše mali `d` iz javnog ključa preko verižnih razlomaka,
u oko 0.3 ms, i njime dešifruje poruku. Isti napad na normalan ključ
(`e = 65537`, `d` pune dužine) ostane bez kandidata i odmah odustane.

---

## Frontend

Kod koji radi u pregledniku pisan je u **TypeScriptu** (`web/ts/`) i kompajlira
se esbuildom u `web/static/js/`. Backend je i dalje potpuno Python — TypeScript
postoji samo u pregledniku.

Potrebno **samo pri izmjeni frontenda**:

```bash
npm install
```

```bash
npm run build
```

| Komanda | Šta radi |
|---|---|
| `npm run build` | Kompajlira i minifikuje u `web/static/js/` |
| `npm run watch` | Prati izmjene i kompajlira automatski |
| `npm run typecheck` | Provjerava tipove bez kompajliranja |

Kompajlirani JavaScript **se commita**, pa pokretanje aplikacije nikad ne traži
Node. Chart.js je ubundlan u izlaz, bez CDN-a — grafovi rade i offline.

---

## Deploy

Flask treba WSGI server:

```bash
gunicorn wsgi:app
```

Na Renderu ili Railwayu: build komanda `pip install -r requirements.txt`, start
komanda `gunicorn wsgi:app`. Node se na serveru ne koristi.

Prije deploya obavezno commitati `benchmark/results.csv` — mjerenje se ne
pokreće na serveru, pa bi Benchmark stranica ostala prazna.

Besplatni resursi su skromni, pa će ručne implementacije biti osjetno sporije
nego lokalno.

---

## Ograničenja

- **RSA je udžbenički, bez OAEP dopune** — deterministički je i ne smije se
  koristiti u praksi. Ovdje služi da se matematika iz 3.3 vidi golim okom.
- Ključevi putuju do preglednika i nazad, jer aplikacija nema stanje na serveru.
  U stvarnom sistemu tajni ključ nikad ne bi napustio server; ovdje je to
  svjesna posljedica toga što korisnik treba vidjeti sam ključ.
- Ručne implementacije ograničene su na 64 KB po operaciji u aplikaciji — na
  ~46 KB/s veći ulazi blokiraju stranicu.
- Jedan režim rada po algoritmu (CBC za blokovne šifre). GCM i ostali nisu u
  opsegu.
- Sve je stateless — nema baze, korisničkih naloga ni perzistencije.

---

## Napomena o Streamlit verziji

Ranija verzija aplikacije u Streamlitu (`app.py`, `app_ui.py`, `pages/`)
zadržana je paralelno dok se prelazak na Flask ne potvrdi:

```bash
streamlit run app.py
```

Radi na portu 8501 i koristi isti `core/`. Kad više ne bude potrebna, brišu se
ti fajlovi, `tests/test_stranice.py` i `streamlit` iz `requirements.txt`.
