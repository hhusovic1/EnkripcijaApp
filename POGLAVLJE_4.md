# 4. IMPLEMENTACIJA I EKSPERIMENTALNA ANALIZA ENKRIPCIJSKIH ALGORITAMA

## 4.1 Tehnologije i alati

Aplikacija je razvijena u programskom jeziku **Python** (verzija 3.11+, razvijano na 3.14). Python je odabran jer njegova sintaksa omogućava da implementacija algoritma ostane bliska matematičkom opisu iz prethodnih poglavlja — petlja koja izvodi šesnaest Feistelovih rundi u kodu izgleda gotovo isto kao u pseudokodu. Čitljivost je ovdje bila važnija od brzine izvršavanja, jer kod prvenstveno služi kao ilustracija teorije.

Korisnički interfejs izveden je kao web aplikacija zasnovana na mikroframeworku **Flask**, koji kriptografske funkcije izlaže kroz JSON API. Kod koji se izvršava u pregledniku pisan je u **TypeScriptu** i kompajlira se alatom esbuild u JavaScript; statička provjera tipova pokazala se korisnom pri radu s ključevima i bajtovnim nizovima, gdje je greška u tipu podatka lako previdiva. Grafovi se crtaju bibliotekom Chart.js, koja je ubundlana u izlaznu datoteku, pa aplikacija radi i bez pristupa internetu. Za izvoz rezultata u PDF korištena je biblioteka `reportlab`, za crtanje grafova za potrebe rada `matplotlib`, a za mjerenje vremena modul `timeit` iz standardne biblioteke.

Kod je organizovan u slojeve. Direktorij `core/` sadrži isključivo kriptografske implementacije i ne zna ništa o korisničkom interfejsu; `web/` ih izlaže kroz HTTP i ne implementira nijednu kriptografsku operaciju sam; `attacks/` i `benchmark/` koriste isti `core/` kao i aplikacija. Svaki modul u `core/` izlaže isti interfejs — `generate_keys()`, `encrypt()` i `decrypt()` — zahvaljujući čemu se algoritmi mogu porediti i mjeriti jedinstvenim kodom, bez posebnih slučajeva po algoritmu. Zbog te podjele svaka demonstracija u aplikaciji pokreće tačno isti kod koji je i izmjeren i testiran.

## 4.2 Cilj aplikacije

Prethodna poglavlja algoritme opisuju teorijski. Aplikacija je razvijena s tri konkretna cilja.

**Prvi cilj je pokazati algoritme na djelu.** Opis Feistelove mreže ili proširenja ključa ostaje apstraktan sve dok se ne vidi kako se konkretan ulazni tekst pretvara u šifrat i vraća nazad. Aplikacija omogućava da se svaki od šest obrađenih algoritama primijeni na proizvoljan tekst i da se rezultat odmah provjeri.

**Drugi cilj je da performanse budu izmjerene, a ne preuzete iz literature.** Podaci o brzini algoritama koji se navode u literaturi odnose se na različit hardver, različite implementacije i često se ne mogu provjeriti. Sva mjerenja u ovom radu potiču iz vlastitog eksperimenta, izvedenog na poznatom hardveru i poznatom kodu, i mogu se ponoviti pokretanjem jedne skripte.

**Treći cilj je da se pokaže i ono što se u teoriji navodi kao slabost.** Tvrdnja da neautentifikovana razmjena ključeva nije sigurna, ili da premali privatni eksponent kompromituje RSA, ostaje puka tvrdnja dok se napad ne izvede. Aplikacija oba napada stvarno izvršava, nad stvarno šifrovanim porukama.

Uz to, ručna implementacija DES-a, 3DES-a, AES-a i RSA — u čistom Pythonu, prema opisu iz poglavlja 3, bez upotrebe kriptografskih biblioteka — služi kao dokaz razumijevanja algoritma. Poziv gotove funkcije ne pokazuje da je algoritam shvaćen; implementacija koja prolazi zvanične test vektore to pokazuje.

Iz istog razloga svjesno je povučena i granica. ECDH nad krivom Curve25519 i tokovna šifra ChaCha20 koriste provjerene biblioteke, jer se aritmetika eliptičkih krivih i generisanje toka ključa ne implementiraju ručno bez ozbiljnog rizika od suptilnih grešaka koje testovi teško otkrivaju. To je odluka u skladu s preporukom iznesenom u poglavlju 3.4.5, a ne propust u realizaciji.

## 4.3 Implementirani algoritmi

Ručno su implementirani sljedeći algoritmi:

- **DES** — kompletna Feistelova struktura sa šesnaest rundi, početnom i završnom permutacijom, permutacijama ključa PC-1 i PC-2 te svih osam S-boxeva.
- **3DES** — izveden nad istim kodom u EDE konfiguraciji, s podrškom za sve tri opcije ključa.
- **AES** — sve tri dužine ključa (128, 192 i 256 bita), s transformacijama SubBytes, ShiftRows, MixColumns i AddRoundKey te pripadajućim proširenjem ključa. S-box se pritom ne prepisuje kao gotova tabela nego se izvodi iz definicije, kao multiplikativni inverz u polju GF(2⁸) praćen afinom transformacijom.
- **RSA** — generisanje prostih brojeva Miller-Rabinovim testom, izračun modula, Ojlerove funkcije i para eksponenata te modularno stepenovanje, za dužine ključa 1024, 2048, 3072 i 4096 bita.

Blokovne šifre nadograđene su zasebnim slojem koji implementira dopunu po standardu PKCS#7 i režim ulančavanja blokova (CBC), čime rade nad ulazom proizvoljne dužine. Režim ECB namjerno nije ponuđen. Preko provjerenih biblioteka realizovani su ECDH razmjena ključeva nad krivom Curve25519 i tokovna šifra ChaCha20, uključujući hibridnu shemu opisanu u poglavlju 3.5.3, u kojoj se zajednička tajna dobijena razmjenom koristi kao ključ simetrične šifre.

## 4.4 Korisnički interfejs

Aplikacija se sastoji od četiri stranice.

**Početna** ukratko predstavlja obrađene algoritme i njihove osnovne parametre.

**Core algoritmi** omogućava šifrovanje i dešifrovanje proizvoljnog teksta bilo kojim od šest algoritama. Simetrični rade nad tekstom proizvoljne dužine, RSA nad jednim blokom, a ECDH prikazuje razmjenu ključeva i hibridnu shemu. Nakon svake operacije prikazuje se utrošeno vrijeme i automatski se provjerava da dešifrovanje vraća bajt po bajt isti sadržaj — korisnik dakle vidi i rezultat i dokaz njegove ispravnosti.

**Benchmark** prikazuje izmjerene performanse kroz veličine podataka i dužine ključeva, s prikazanim standardnim devijacijama. Podaci se učitavaju iz unaprijed izračunate datoteke, jer bi mjerenje uživo bilo presporo. Rezultati se mogu preuzeti u dva oblika: kao sirova CSV datoteka, radi dalje obrade, i kao formatiran **PDF izvještaj** s tabelom grupisanom po algoritmu, pripremljen za štampu.

**Sigurnosne demonstracije** pokreću oba napada opisana u nastavku. Napad posrednika prikazuje se korak po korak, jer je njegova poenta upravo u redoslijedu poteza.

Uz web aplikaciju razvijena je i funkcija **mjerenja nad korisnikovom datotekom**, koja algoritme pokreće uživo nad učitanim sadržajem umjesto nad nasumičnim podacima. Prije pokretanja procjenjuje se trajanje operacije na osnovu propusnosti izmjerene u ranijem eksperimentu, pa se korisnik upozorava ako bi mjerenje trajalo predugo — što je posljedica toga što ručne implementacije rade reda veličine desetak kilobajta u sekundi.

## 4.5 Validacija implementacija

Ispravnost implementacija provjerava se sa **105 automatizovanih testova** raspoređenih u devet modula, čije izvršavanje traje oko trideset sekundi. Provjera se izvodi na dva nezavisna načina.

Prvi su **zvanični test vektori** — FIPS 46-3 i NBS SP 500-20 za DES te FIPS-197 (dodaci A, B i C) za AES. Drugi je **unakrsna provjera**, u kojoj se isti ulaz propušta kroz vlastitu implementaciju i kroz biblioteku `pycryptodome`, na stotinama nasumično generisanih ključeva i blokova. Oba načina su potrebna jer fiksni skup vektora može propustiti grešku koja se javlja samo na određenim ulazima.

Testovima su obuhvaćeni i rubni slučajevi, poput slabih i polu-slabih DES ključeva, podudaranja izvedenog AES S-boxa sa standardom, te ponašanje svake rute API-ja uključujući obradu neispravnog ulaza.

## 4.6 Analiza sigurnosti kroz demonstracije napada

Uz same algoritme implementirana su i dva napada opisana u teorijskom dijelu. Oba se izvršavaju stvarno, u trenutku pokretanja, i dostupna su i iz terminala i kroz aplikaciju.

### 4.6.1 Napad posrednika na Diffie-Hellmanovu razmjenu

Napad je implementiran kao potpuna simulacija protokola, s tri učesnika i dva odvojena komunikaciona kanala. Izvodi se u dvije varijante: nad malim sigurnim prostim brojem od 65 bita, gdje se sve međuvrijednosti mogu pročitati na ekranu, i nad stvarnom MODP grupom 14 od 2048 bita iz standarda RFC 3526 — dakle nad parametrima koji se koriste u praksi.

Aplikacija najprije prikazuje **urednu razmjenu**, u kojoj Alice i Bob dolaze do iste zajedničke tajne, a zatim istu razmjenu s napadačem u sredini. Napadač bira dva tajna eksponenta, jedan prema svakoj strani, presreće javnu vrijednost jedne strane i drugoj podmeće vlastitu. Umjesto jedne razmjene uspostavljaju se dvije, pa Alice i Bob završe s **različitim** zajedničkim tajnama — što nijedno od njih dvoje nikada ne provjeri, jer protokol to od njih ne traži.

Poruka se potom stvarno šifruje ručno implementiranim AES-om u CBC režimu, ključem izvedenim iz zajedničke tajne. Napadač je dešifruje, pročita, ponovo šifruje drugim ključem i proslijedi dalje; primalac dobije očekivanu poruku i ništa ne posumnja. Demonstracija ide i korak dalje i pokazuje da napadač, budući da posjeduje ključ prema primaocu, nije ograničen na čitanje — može poslati proizvoljan sadržaj koji će primaocu izgledati kao da dolazi od pošiljaoca.

Ključna poenta koju demonstracija čuva jeste da napadač **nikada ne saznaje tajne eksponente** niti rješava problem diskretnog logaritma. On vodi dvije potpuno uredne Diffie-Hellmanove razmjene. Napad ne ruši matematiku protokola nego izostanak autentifikacije učesnika.

### 4.6.2 Wienerov napad na RSA

Wienerov napad rekonstruiše mali privatni eksponent iz javnog ključa postupkom verižnih razlomaka. Implementacija razvija razlomak `e/n` u niz konvergenti i za svaku provjerava da li dobijeni kandidat zadovoljava uslove ispravnog ključa, bilježeći pritom svaki pregledani kandidat i razlog njegovog odbacivanja — pa se u aplikaciji vidi ne samo rezultat nego i tok pretrage.

Nad namjerno ranjivim ključem napad pronađe privatni eksponent za oko 0,3 milisekunde i njime dešifruje poruku. Primijenjen na uredno generisan ključ, s javnim eksponentom 65537 i privatnim eksponentom pune dužine, isti postupak ostaje bez ijednog valjanog kandidata i odmah odustaje. Kontrast između ta dva slučaja pokazuje da napad cilja na loš izbor parametara, a ne na sam algoritam.

## 4.7 Analiza performansi

Mjerenje je izvedeno zasebnom skriptom, odvojeno od aplikacije, jer je za rad uživo presporo. Obuhvata **104 mjerenja** nad ulazima veličine od 64 bajta do 10 megabajta i nad četiri dužine RSA ključa, uz pedeset ponavljanja po tački. Za svaku tačku bilježe se srednje vrijeme, standardna devijacija, najkraće izmjereno vrijeme i propusnost. Rezultati se snimaju u datoteku `results.csv`, iz koje se crtaju i grafovi u ovom radu i grafovi u aplikaciji, čime je osigurano da su prikazani brojevi identični.

Pri tumačenju rezultata nužno je razdvojiti dvije grupe. Ručne implementacije pisane su radi čitljivosti i podudaranja s opisom u radu, a bibliotečke se izvršavaju kroz optimizovan C kod. Poređenje između tih grupa mjeri kvalitet implementacije, a ne svojstva algoritma, pa se zaključci izvode iz poređenja unutar iste grupe.

**Tabela 4.1 — Izmjerene performanse odabranih algoritama**

| Mjerenje | Rezultat |
|---|---|
| 3DES naspram DES-a | 2,97× sporiji |
| AES-128 naspram DES-a (64 KB) | 1,354 s naspram 1,878 s |
| AES-128 naspram AES-256 (64 KB) | 1,354 s naspram 2,075 s |
| RSA generisanje ključa, 1024 bita | 0,048 s |
| RSA generisanje ključa, 4096 bita | 7,604 s (σ = 5,49 s) |
| ECDH generisanje ključa i razmjena | ≈ 0,03 ms po operaciji |
| Ručni AES naspram bibliotečkog | 0,046 MB/s naspram 503 MB/s |
| Wienerov napad na ranjiv ključ | ≈ 0,3 ms |

Mjerenja potvrđuju očekivanja iznesena u teorijskom dijelu. Trostruki DES je gotovo tačno tri puta sporiji od DES-a, što odgovara trostrukom izvršavanju iste šifre. AES je uprkos većem bloku brži od DES-a, jer je njegova runda jednostavnija za izvršavanje na modernim procesorima. Povećanje dužine AES ključa sa 128 na 256 bita poskupljuje operaciju za oko 53 posto, što je cijena četiri dodatne runde.

Kod RSA je porast troška generisanja ključa izrazito nelinearan: prelazak sa 1024 na 4096 bita produžava postupak približno sto šezdeset puta. Velika standardna devijacija pritom nije greška mjerenja, nego posljedica toga što je traženje prostog broja probabilističan postupak čije trajanje ovisi o sreći pri izboru kandidata. Nasuprot tome, ECDH nad Curve25519 postiže uporediv nivo sigurnosti uz vrijeme reda mikrosekundi.

Prilikom čitanja grafa vremena u odnosu na veličinu ulaza treba imati u vidu da RSA ima samo jednu mjernu tačku po dužini ključa. Za razliku od ostalih algoritama, koji ulaz obrađuju u petlji, RSA izvodi jednu operaciju nad brojem manjim od modula, pa dužina ključa određuje jedinu moguću veličinu ulaza, od 126 do 510 bajtova. Niska pozicija tih tačaka na grafu posljedica je male količine obrađenih podataka, a ne brzine algoritma — po bajtu, dešifrovanje RSA-4096 postiže 3,8 KB/s naspram 24,3 KB/s ručno implementiranog AES-a.

## 4.8 Ograničenja implementacije

Aplikacija je razvijena u obrazovne svrhe i njena ograničenja proizlaze upravo iz te namjene.

Implementacija RSA je **udžbenička, bez dopune po standardu OAEP**. Takav RSA je deterministički i ne smije se koristiti u praksi; ovdje je zadržan u tom obliku da bi matematika iz poglavlja 3.3 bila vidljiva bez posrednog sloja. Ključevi u web aplikaciji putuju do preglednika i nazad, jer aplikacija ne čuva stanje na serveru — u stvarnom sistemu privatni ključ nikada ne bi napustio server, ali ovdje korisnik treba vidjeti sam ključ. Zbog brzine ručnih implementacija ulaz je u aplikaciji ograničen na 64 kilobajta po operaciji. Podržan je po jedan režim rada za blokovne šifre (CBC), dok autentifikovani režimi poput GCM-a nisu u opsegu rada.

Nijedno od ovih ograničenja ne utiče na izmjerene rezultate niti na demonstracije napada, jer se svi mjere nad istim kodom koji je i validiran.

## 4.9 Zaključak

Realizacija aplikacije potvrdila je nekoliko zaključaka iznesenih u teorijskom dijelu rada, ali ih je i konkretizovala brojevima.

**Simetrični i asimetrični algoritmi ne takmiče se za isti posao.** Razlika u brzini nije stvar optimizacije nego reda veličine, i objašnjava zašto se u praksi ne koristi ni jedan ni drugi pristup samostalno, nego hibridna shema u kojoj asimetrični algoritam prenosi ključ, a simetrični šifruje podatke. To je zaključak koji se u aplikaciji nije morao tvrditi — proizašao je iz mjerenja.

**Napredak u dizajnu algoritama vrijedi više od povećanja parametara.** Prelazak s DES-a na 3DES sigurnost je kupio trostrukim usporenjem, dok AES istovremeno nudi i veću sigurnost i bolje performanse. Isto vrijedi u asimetričnoj kriptografiji: ECDH nad eliptičkom krivom postiže nivo sigurnosti uporediv s RSA-om od 3072 bita, uz nekoliko redova veličine manji trošak. Rješenje nije u produžavanju ključa nego u boljem algoritmu.

**Sigurnost sistema ne počiva samo na algoritmu.** Obje demonstracije napada uspijevaju, a nijedna ne razbija matematiku na kojoj algoritam počiva. Napad posrednika uspijeva jer razmjena ključeva nije autentifikovana, a Wienerov napad jer je privatni eksponent izabran premalen. Ispravan algoritam pogrešno upotrijebljen ne pruža nikakvu zaštitu, što je zapažanje s najvećom praktičnom težinom u cijelom radu — jer se u stvarnim sistemima propusti gotovo uvijek javljaju na nivou protokola i izbora parametara, a ne u samoj šifri.

**Razlika između specifikacije i implementacije je mjerljiva.** Ista specifikacija AES-a, implementirana čitljivo u Pythonu i optimizovano u C-u, daje razliku u propusnosti od približno četiri reda veličine. Zbog toga se u proizvodnim sistemima koriste provjerene i optimizovane biblioteke, dok ručne implementacije poput ovdje razvijenih imaju obrazovnu, a ne primjensku vrijednost.

Konačno, aplikacija pokazuje da se svi obrađeni algoritmi mogu implementirati na osnovu javno dostupnih specifikacija i uspješno validirati zvaničnim test vektorima. Sigurnost tih algoritama ne počiva na tajnosti njihovog opisa, čime je u praksi potvrđen Kerckhoffsov princip naveden u uvodnom dijelu rada.
