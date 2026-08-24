/**
 * Stranica "Sigurnosne demonstracije" — MITM na Diffie-Hellman i Wienerov napad.
 *
 * Oba napada izvršava Python (attacks/), ovdje se samo prikazuju. MITM se
 * otkriva korak po korak jer je poenta napada u redoslijedu poteza, a ne u
 * krajnjem broju.
 */
import type { Grupa, KorakWiener, OdgovorMitm, OdgovorWiener } from './tipovi';
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
const dugmeDalje = el<HTMLButtonElement>('dugme-mitm-dalje');
const dugmeSve = el<HTMLButtonElement>('dugme-mitm-sve');

let mitm: OdgovorMitm | null = null;
let vidljivo = 0;

function opisGrupe(): void {
    const grupa = window.GRUPE.find((g) => g.id === izborGrupe.value);
    el('opis-grupe').textContent = grupa?.opis ?? '';
}

izborGrupe.addEventListener('change', opisGrupe);
opisGrupe();

function nacrtajKorake(): void {
    if (!mitm) return;

    el('koraci-mitm').innerHTML = mitm.koraci.slice(0, vidljivo).map((korak) => `
        <div class="korak ${korak.istaknuto ? 'istaknut' : ''}">
            <div class="korak-naslov">${korak.broj}. ${escapeHtml(korak.naslov)}</div>
            <div class="korak-akter">${escapeHtml(korak.akter)}</div>
            <div class="korak-opis">${escapeHtml(korak.opis)}</div>
            ${korak.vrijednosti.map((v) => par(v.kljuc, skrati(v.vrijednost, 60))).join('')}
        </div>
    `).join('');

    const traka = el('traka-mitm');
    traka.classList.remove('skriven');
    (traka.firstElementChild as HTMLElement).style.width =
        `${(vidljivo / mitm.koraci.length) * 100}%`;
    el('status-mitm').textContent = `Korak ${vidljivo} od ${mitm.koraci.length}`;

    const gotovo = vidljivo >= mitm.koraci.length;
    dugmeDalje.classList.toggle('skriven', gotovo);
    dugmeSve.classList.toggle('skriven', gotovo);

    el('zakljucak-mitm').innerHTML = gotovo ? zakljucak(mitm) : '';
}

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
        vidljivo = 1;
        nacrtajKorake();
    } catch (greska) {
        el('koraci-mitm').innerHTML = poruka('greska', escapeHtml(tekstGreske(greska)));
    } finally {
        oslobodi();
    }
});

dugmeDalje.addEventListener('click', () => {
    if (!mitm) return;
    vidljivo = Math.min(vidljivo + 1, mitm.koraci.length);
    nacrtajKorake();
});

dugmeSve.addEventListener('click', () => {
    if (!mitm) return;
    vidljivo = mitm.koraci.length;
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
            ${ranjivi.koraci.map(korakWiener).join('')}

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
                    '<strong>Zaključak (3.3.6):</strong> ranjivost nije u RSA algoritmu nego ' +
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
