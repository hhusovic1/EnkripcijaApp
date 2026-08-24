# Enkripcijski algoritmi

Demonstraciona aplikacija uz završni rad prvog ciklusa studija — Elektrotehnički
fakultet, Univerzitet u Sarajevu.

Rad analizira enkripcijske algoritme teorijski; ova aplikacija ih pokazuje na
djelu, s **izmjerenim** performansama umjesto brojeva preuzetih iz literature.

**DES, 3DES, AES i RSA su implementirani ručno**, u čistom Pythonu, prema opisu
iz poglavlja 3 rada — bez korištenja kriptografskih biblioteka. ECDH (X25519) i
ChaCha20 idu kroz provjerene biblioteke, jer se eliptičke krive i tokovne šifre ne
implementiraju ručno bez ozbiljnog rizika od suptilnih grešaka (vidi 3.4.5).

## Pokretanje

Potreban je Python 3.11+.

```bash
python -m venv .venv
```

```bash
.venv\Scripts\activate
```

```bash
pip install -r requirements.txt
```

```bash
streamlit run app.py
```

Aplikacija se otvara na `http://localhost:8501`.

Na Linuxu/macOS-u je aktivacija `source .venv/bin/activate`.

## Struktura

| Putanja | Sadržaj |
|---|---|
| `core/` | Implementacije algoritama — jedinstven interfejs `generate_keys()` / `encrypt()` / `decrypt()` |
| `core/modes.py` | PKCS#7 dopuna i CBC režim — sloj iznad blokovnih šifara |
| `attacks/` | MITM na Diffie-Hellman (3.4.4), Wienerov napad na RSA (3.3.6) |
| `benchmark/` | Mjerenje performansi, generisanje grafova, mjerenje nad korisnikovim fajlom |
| `tests/` | Validacija — zvanični test vektori i poređenje s referentnom bibliotekom |
| `pages/` | Stranice Streamlit aplikacije |

## Validacija

```bash
python tests/run_all.py
```

87 testova. Ručne implementacije se provjeravaju na dva nezavisna načina:

- **Zvanični test vektori** — FIPS 46-3 / NBS SP 500-20 za DES, FIPS-197
  (Appendix A, B, C) za AES.
- **Unakrsna provjera** — isti ulaz kroz `pycryptodome`, na stotinama nasumičnih
  ključeva i blokova. Fiksni vektori mogu propustiti grešku koja se javlja samo
  na određenim ulazima.
- **Stranice aplikacije** — svaka grana (svih šest algoritama, oba MITM
  scenarija, Wienerov napad) izvršava se headless kroz Streamlit `AppTest`.

AES S-box se ne prepisuje kao tabela nego **izvodi iz definicije**
(multiplikativni inverz u GF(2⁸) + afina transformacija), a test provjerava da
se izvedena tabela poklapa sa standardom.

## Benchmark

Mjerenje je odvojeno od aplikacije jer je presporo za rad uživo — ručni AES u
čistom Pythonu postiže oko 46 KB/s.

```bash
python benchmark/run_benchmark.py
```

Rezultat je `benchmark/results.csv` (~6 minuta, 104 mjerenja). Grafovi za rad:

```bash
python benchmark/plot_results.py
```

Slike se snimaju u `benchmark/figures/`. Aplikacija crta iste grafove iz istog
CSV-a, pa su brojevi u radu i u aplikaciji garantovano isti.

### Kako čitati rezultate

DES, 3DES, AES i RSA su ručne Python implementacije, pisane radi čitljivosti i
podudaranja s opisom u radu — ne radi brzine. ChaCha20, ECDH i varijante
označene *(biblioteka)* izvršavaju se kroz optimizovani C kod. Razlika među tim
grupama mjeri **implementaciju**, ne samo algoritam; kolona `kategorija` u
CSV-u postoji upravo da se to razdvoji.

Poređenja unutar iste grupe su ono što nosi zaključak — na primjer, izmjereni
odnos 3DES/DES iznosi 2.97×, što potvrđuje tvrdnju iz 3.5.1 da je 3DES
„otprilike tri puta sporiji".

## Demonstracije napada

Obje rade i iz terminala i kroz aplikaciju (stranica *Sigurnosne demonstracije*).

```bash
python attacks/mitm_dh.py
```

MITM na neautentifikovani Diffie-Hellman. Radi na malom prostom broju (čitljivi
brojevi) i na stvarnoj MODP grupi 14 iz RFC 3526. Poruka se stvarno šifruje
ručnim AES-om, pa „Mallory čita poruku" nije tvrdnja nego demonstracija.

```bash
python attacks/wiener_rsa.py
```

Wienerov napad rekonstruiše mali `d` iz javnog ključa preko verižnih razlomaka,
u oko 0.3 ms, i njime dešifruje poruku. Isti napad na normalan ključ
(`e = 65537`, `d` pune dužine) ostane bez kandidata i odmah odustane.

## Mjerenje nad vlastitim fajlom

Stranica *Mjeri svoj fajl* učitava proizvoljan fajl i mjeri algoritme na njemu,
uz provjeru da dekripcija vrati bajt po bajt isti sadržaj. Isto iz terminala:

```bash
python benchmark/measure_file.py neki_fajl.pdf
```

RSA se ne može mjeriti samostalno nad fajlom jer obrađuje samo blok manji od
modula — zato je ponuđen kao **hibridna shema iz 3.5.3**: RSA štiti AES
sesijski ključ, AES štiti sadržaj.

## Ograničenja

- Ručne implementacije su ograničene na 1 MB po mjerenju (na ~46 KB/s veći
  ulazi traju minutama). Bibliotečke idu do 64 MB.
- RSA je udžbenički, **bez OAEP dopune** — deterministički je i ne smije se
  koristiti u praksi. Ovdje služi da se matematika iz 3.3 vidi golim okom.
- Jedan režim rada po algoritmu (CBC za blokovne šifre). Podrška za GCM i
  ostale nije u opsegu.
- Sve je stateless — nema baze, korisničkih naloga ni perzistencije.

## Deploy

Najlakše preko **Streamlit Community Cloud** (besplatno):

1. Push repozitorija na GitHub.
2. Na `share.streamlit.io` povezati repo, glavni fajl je `app.py`.
3. Zavisnosti se čitaju iz `requirements.txt`; ništa drugo ne treba.

Streamlit ima ugrađen produkcijski server, pa **gunicorn nije potreban** — to
vrijedi samo za Flask.

Prije deploya obavezno commitati `benchmark/results.csv`, inače stranica
Benchmark neće imati šta prikazati (mjerenje se ne pokreće na serveru).

Napomena: besplatni resursi su skromni. Stranica *Mjeri svoj fajl* će s ručnim
implementacijama biti osjetno sporija nego lokalno, pa je uputno tamo držati
manje uzorke.
