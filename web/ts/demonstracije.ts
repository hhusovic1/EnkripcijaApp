/**
 * Stranica "Sigurnosne demonstracije" — MITM na Diffie-Hellman i Wienerov napad.
 *
 * Oba napada izvršava Python (attacks/), ovdje se samo prikazuju. MITM se
 * otkriva korak po korak jer je poenta napada u redoslijedu poteza, a ne u
 * krajnjem broju.
 */
import type { Grupa, KorakMitm, KorakWiener, OdgovorMitm, OdgovorWiener } from './tipovi';
import {
    el, escapeHtml, mozdaEl, par, posalji, poruka, poveziTabove, skrati,
    tekstGreske, zauzmi,
} from './pomocno';

declare global {
    interface Window {
        GRUPE: Grupa[];
    }
}

poveziTabove();

// =========================================================================
// MITM
// =========================================================================

const izborGrupe = el<HTMLSelectElement>('izbor-grupe');
const izborScenarija = el<HTMLSelectElement>('izbor-scenarija');
const unosPoruke = el<HTMLInputElement>('unos-poruke');

const dugmeMitm = el<HTMLButtonElement>('dugme-mitm');
const dugmeNazad = el<HTMLButtonElement>('dugme-mitm-nazad');
const dugmeDalje = el<HTMLButtonElement>('dugme-mitm-dalje');
const dugmeSve = el<HTMLButtonElement>('dugme-mitm-sve');

let mitm: OdgovorMitm | null = null;
/** Koji se korak trenutno prikazuje (1..n); 0 znaci da razmjena nije pokrenuta. */
let korakBroj = 0;
/** Dokle je korisnik stigao — do tog koraka moze skakati brojevima. */
let dosegnuto = 0;
/** Zavrsni pregled: svi koraci odjednom, tek kad se prodje kroz sve. */
let pregledSvih = false;

function opisGrupe(): void {
    const grupa = window.GRUPE.find((g) => g.id === izborGrupe.value);
    if (!grupa) {
        el('opis-grupe').innerHTML = '';
        return;
    }
    el('opis-grupe').innerHTML = `
        <div class="objasnjenje-brojevi">
            <span><strong>p</strong> — prost broj, ${grupa.bita} bita</span>
            <span><strong>g</strong> — generator, ${grupa.g}</span>
        </div>
        <p>${escapeHtml(grupa.opis)}</p>
        <p class="prigusen" style="margin:0">
            p i g su javni: šalju se otvoreno i nisu tajna. Tajni su samo
            eksponenti a i b, koje Alice i Bob nikad ne šalju kanalom.
        </p>`;
}

izborGrupe.addEventListener('change', opisGrupe);
opisGrupe();

function karticaKoraka(korak: KorakMitm): string {
    // Akter je slobodan tekst iz Pythona ("Mallory -> Bob", "Alice i Bob"...);
    // dovoljno je da se Mallory spominje da korak dobije boju napadaca.
    const napadacev = korak.akter.includes('Mallory');
    return `
        <div class="korak ${korak.istaknuto ? 'istaknut' : ''} ${napadacev ? 'napadac' : ''}">
            <div class="korak-naslov">
                <span class="korak-oznaka">Korak ${korak.broj}</span>
                ${escapeHtml(korak.naslov)}
            </div>
            <div class="korak-akter">${escapeHtml(korak.akter)}</div>
            <div class="korak-opis">${escapeHtml(korak.opis)}</div>
            ${korak.vrijednosti.map((v) => par(v.kljuc, skrati(v.vrijednost, 60))).join('')}
        </div>`;
}

function nacrtajKorake(): void {
    if (!mitm) return;
    const ukupno = mitm.koraci.length;
    const zadnji = korakBroj >= ukupno;

    // Korak po korak se vidi samo tekuci korak — inace se stranica razvuce i
    // ono sto se upravo desilo zavrsi ispod ekrana.
    el('koraci-mitm').innerHTML = pregledSvih
        ? `<div class="pregled-naslov">Cijela razmjena — svih ${ukupno} koraka</div>`
          + `<div class="vremenska-linija">${mitm.koraci.map(karticaKoraka).join('')}</div>`
        : karticaKoraka(mitm.koraci[korakBroj - 1]);

    const traka = el('traka-mitm');
    traka.classList.remove('skriven');
    (traka.firstElementChild as HTMLElement).style.width =
        `${((pregledSvih ? ukupno : korakBroj) / ukupno) * 100}%`;

    el('status-mitm').textContent = pregledSvih
        ? `Završeno — svih ${ukupno} koraka`
        : `Korak ${korakBroj} od ${ukupno}`;

    const brojevi = el('brojevi-mitm');
    brojevi.classList.remove('skriven');
    brojevi.innerHTML = mitm.koraci.map((k) => `
        <button type="button" class="korak-broj${!pregledSvih && k.broj === korakBroj ? ' aktivan' : ''}"
                data-korak="${k.broj}" ${k.broj <= dosegnuto ? '' : 'disabled'}
                title="Korak ${k.broj}: ${escapeHtml(k.naslov)}">${k.broj}</button>`).join('');

    dugmeNazad.classList.toggle('skriven', pregledSvih || korakBroj <= 1);
    dugmeDalje.classList.toggle('skriven', pregledSvih);
    dugmeDalje.textContent = zadnji ? 'Prikaži sve korake ▤' : 'Sljedeći korak ▸';
    dugmeSve.classList.toggle('skriven', pregledSvih || zadnji);

    // Zakljucak ima smisla tek kad se vidjelo sta se u zadnjem koraku desilo.
    el('zakljucak-mitm').innerHTML = zadnji ? zakljucak(mitm) : '';
}

el('brojevi-mitm').addEventListener('click', (dogadjaj) => {
    const dugme = (dogadjaj.target as HTMLElement).closest<HTMLButtonElement>('.korak-broj');
    if (!dugme || dugme.disabled) return;
    korakBroj = Number(dugme.dataset.korak);
    pregledSvih = false;
    nacrtajKorake();
});

function zakljucak(rezultat: OdgovorMitm): string {
    if (rezultat.scenario === 'bez_mallory') {
        return poruka('uspjeh',
            'Alice i Bob su došli do <strong>iste</strong> tajne, a ona sama nikad nije ' +
            'prošla kanalom. Prisluškivač je vidio p, g, A i B — i to mu ne pomaže, jer ' +
            'bi iz A morao izvući a, što je problem diskretnog logaritma.');
    }
    return poruka('greska',
        'Mallory je pročitala poruku koju je Alice smatrala sigurnom, i mogla ju je ' +
        'izmijeniti prije nego stigne Bobu. Ni Alice ni Bob nemaju ništa u protokolu ' +
        'čime bi to primijetili.<br><br>' +
        '<strong>Ono što je najlakše previdjeti:</strong> Mallory nikad nije saznala ' +
        'ni <code>a</code> ni <code>b</code>, niti je razbila diskretni logaritam. ' +
        'Vodila je dvije potpuno regularne DH razmjene. Napad ne ruši matematiku nego ' +
        '<strong>izostanak autentifikacije</strong> — zato se DH u praksi nikad ne ' +
        'koristi sam, nego uz potpis ili certifikat (STS, TLS).');
}

dugmeMitm.addEventListener('click', async () => {
    const oslobodi = zauzmi(dugmeMitm, 'Pokrećem…');
    el('zakljucak-mitm').innerHTML = '';
    try {
        mitm = await posalji<OdgovorMitm>('/api/mitm', {
            grupa: izborGrupe.value,
            scenario: izborScenarija.value,
            poruka: unosPoruke.value,
        });
        korakBroj = 1;
        dosegnuto = 1;
        pregledSvih = false;
        nacrtajKorake();
    } catch (greska) {
        el('koraci-mitm').innerHTML = poruka('greska', escapeHtml(tekstGreske(greska)));
    } finally {
        oslobodi();
    }
});

dugmeDalje.addEventListener('click', () => {
    if (!mitm) return;
    if (korakBroj >= mitm.koraci.length) {
        pregledSvih = true;          // zadnji klik otvara pregled cijele razmjene
    } else {
        korakBroj += 1;
        dosegnuto = Math.max(dosegnuto, korakBroj);
    }
    nacrtajKorake();
});

dugmeNazad.addEventListener('click', () => {
    if (!mitm || korakBroj <= 1) return;
    korakBroj -= 1;
    nacrtajKorake();
});

dugmeSve.addEventListener('click', () => {
    if (!mitm) return;
    korakBroj = mitm.koraci.length;
    dosegnuto = mitm.koraci.length;
    nacrtajKorake();
});

// =========================================================================
// Wiener
// =========================================================================

const dugmeWiener = mozdaEl<HTMLButtonElement>('dugme-wiener');

function korakWiener(korak: KorakWiener): string {
    if (korak.uspjeh) {
        return `
            <div class="korak istaknut">
                <div class="korak-naslov">#${korak.broj} — POGODAK</div>
                ${par('k', skrati(korak.k))}
                ${par('d', skrati(korak.d))}
                ${par('φ(n)', skrati(korak.phi ?? '—'))}
                ${par('p', skrati(korak.p ?? '—'))}
                ${par('q', skrati(korak.q ?? '—'))}
                ${poruka('uspjeh', escapeHtml(korak.razlog))}
            </div>`;
    }
    return `
        <div class="korak">
            <div class="korak-naslov">#${korak.broj} — odbačeno</div>
            ${par('k', skrati(korak.k, 32))}
            ${par('d', skrati(korak.d, 32))}
            <div class="prigusen">${escapeHtml(korak.razlog)}</div>
        </div>`;
}

dugmeWiener?.addEventListener('click', async () => {
    const cilj = el('rezultat-wiener');
    const bita = Number(el<HTMLSelectElement>('izbor-bita').value);
    const oslobodi = zauzmi(dugmeWiener, 'Generišem ključeve i napadam…');
    el('status-wiener').textContent = '';
    cilj.innerHTML = '';

    try {
        const r = await posalji<OdgovorWiener>('/api/wiener', { bita });
        const ranjivi = r.ranjivi;
        const normalni = r.normalni;

        cilj.innerHTML = `
            <div class="mreza mreza-2">
                <div class="panel">
                    <div class="panel-naslov">Ranjiv ključ</div>
                    <p class="prigusen" style="margin-top:0">
                        d je namjerno izabran malen, radi brže dekripcije
                    </p>
                    ${par('n', skrati(ranjivi.n))}
                    ${par('e', skrati(ranjivi.e))}
                    ${par('d (tajni)', skrati(ranjivi.pravi_d))}
                    ${par('d — broj bita', String(ranjivi.d_bita))}
                    ${par('Wienerova granica (bita)', String(ranjivi.granica_bita))}
                    ${ranjivi.uspjeh
                        ? poruka('greska',
                            `Napad uspio za <strong>${ranjivi.trajanje_ms.toFixed(3)} ms</strong> — ` +
                            `pregledano ${ranjivi.pregledano} konvergenti.`)
                        : poruka('upozorenje', 'Napad ovaj put nije uspio — pokreni ponovo.')}
                </div>
                <div class="panel">
                    <div class="panel-naslov">Normalan ključ</div>
                    <p class="prigusen" style="margin-top:0">
                        e = 65537, d pune dužine — kako se radi u praksi
                    </p>
                    ${par('n', skrati(normalni.n))}
                    ${par('e', normalni.e)}
                    ${par('d — broj bita', String(normalni.d_bita))}
                    ${par('Ukupno konvergenti', String(normalni.ukupno_konvergenti))}
                    ${par('Pregledano', String(normalni.pregledano))}
                    ${normalni.uspjeh
                        ? poruka('uspjeh',
                            `Napad ne uspijeva, i to za <strong>${normalni.trajanje_ms.toFixed(3)} ms</strong> ` +
                            '— ostane bez kandidata prije nego išta nađe.')
                        : poruka('greska', 'Napad je uspio na normalnom ključu — to bi bila greška.')}
                </div>
            </div>

            <h2>Kako napad prolazi kroz konvergente</h2>
            <p>
                Iz <code>e·d ≡ 1 (mod φ)</code> slijedi da je <code>k/d</code> jedna od
                konvergenti razvoja <code>e/n</code> u verižni razlomak. Napadač ih redom
                isprobava i za svaku provjerava daje li smislen <code>φ</code> — onaj kod
                kojeg <code>x² − (n − φ + 1)x + n = 0</code> ima dva cjelobrojna rješenja.
            </p>
            <div class="vremenska-linija">
                ${ranjivi.koraci.map(korakWiener).join('')}
            </div>

            <h2>Posljedica</h2>
            <div class="panel">
                <p style="margin-top:0">
                    Rekonstruisani <code>d</code> nije samo broj koji se poklapa — njime se
                    stvarno dešifruje poruka koju je vlasnik ključa smatrao sigurnom:
                </p>
                ${par('Poslano', ranjivi.poruka)}
                ${par('Napadač pročitao', ranjivi.procitano ?? '—')}
                ${par('Rekonstruisani d = pravi d',
                    ranjivi.nadjeni_d === ranjivi.pravi_d ? 'da' : 'ne')}
                ${poruka('info',
                    '<strong>Zaključak:</strong> ranjivost nije u RSA algoritmu nego ' +
                    'u izboru parametara. Zato se <code>d</code> uvijek generiše kao vrijednost ' +
                    'uporediva po veličini s <code>n</code>, a ubrzanje dekripcije se postiže ' +
                    'kineskom teoremom o ostacima (CRT), a ne malim eksponentom.')}
            </div>
        `;
    } catch (greska) {
        cilj.innerHTML = poruka('greska', escapeHtml(tekstGreske(greska)));
    } finally {
        oslobodi();
    }
});
