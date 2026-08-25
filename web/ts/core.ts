/**
 * Stranica "Core algoritmi" — povezuje forme s Python API-jem.
 *
 * Ključevi se drže u memoriji preglednika i šalju nazad uz svaki zahtjev, jer je
 * aplikacija bez stanja na serveru. U stvarnom sistemu tajni ključ nikad ne bi
 * putovao do klijenta; ovdje je to svjesna posljedica toga što je demonstracija
 * i što korisnik treba vidjeti sam ključ.
 */
import type {
    MetaAlgoritma, OdgovorEcdh, OdgovorHibridno, OdgovorKljuca,
    OdgovorRsaKljuca, OdgovorRsaSifrovanja, OdgovorSifrovanja,
} from './tipovi';
import {
    el, escapeHtml, formatirajBajtove, mjera, mozdaEl, par, parovi,
    posalji, poruka, skrati, tekstGreske, zauzmi,
} from './pomocno';

declare global {
    interface Window {
        ALGORITMI: Record<string, MetaAlgoritma>;
    }
}

const ALGORITMI = window.ALGORITMI;

let trenutniKljuc: OdgovorKljuca | null = null;
let trenutniRsa: OdgovorRsaKljuca | null = null;
let trenutnaTajna: string | null = null;
let zadnjiSifrat: OdgovorSifrovanja | null = null;

const izborAlgoritma = el<HTMLSelectElement>('izbor-algoritma');

function meta(): MetaAlgoritma {
    return ALGORITMI[izborAlgoritma.value];
}

// ---------------------------------------------------------------- Izbor algoritma

function prikaziAlgoritam(): void {
    const m = meta();

    const oznakaVrste = m.rucni
        ? '<span class="oznaka rucna">ručna implementacija</span>'
        : '<span class="oznaka biblioteka">biblioteka</span>';
    el('meta-algoritma').innerHTML = oznakaVrste;

    el('opis-algoritma').textContent = m.opis;
    el('napomena-algoritma').innerHTML = `<strong>Na šta paziti.</strong> ${escapeHtml(m.napomena)}`;

    // Prikaži samo sekciju koja odgovara vrsti algoritma
    const sekcije: Record<string, string> = {
        blokovni: 'sekcija-simetricni',
        tocna: 'sekcija-simetricni',
        rsa: 'sekcija-rsa',
        ecdh: 'sekcija-ecdh',
    };
    for (const id of ['sekcija-simetricni', 'sekcija-rsa', 'sekcija-ecdh']) {
        el(id).classList.toggle('skriven', id !== sekcije[m.vrsta]);
    }

    // Ključ jednog algoritma ne vrijedi za drugi
    trenutniKljuc = null;
    zadnjiSifrat = null;
    const prikaz = mozdaEl('prikaz-kljuca');
    if (prikaz) prikaz.innerHTML = '';
    const rezultat = mozdaEl('rezultat-simetricni');
    if (rezultat) rezultat.innerHTML = '';
    const status = mozdaEl('status-kljuca');
    if (status) status.textContent = 'Ključ još nije generisan.';
    const dugme = mozdaEl<HTMLButtonElement>('dugme-sifruj');
    if (dugme) dugme.disabled = true;

    osvjeziInfoDopune();
}

izborAlgoritma.addEventListener('change', prikaziAlgoritam);

// --------------------------------------------------------------- Simetrični

const unosTeksta = el<HTMLTextAreaElement>('unos-teksta');

function osvjeziInfoDopune(): void {
    const info = mozdaEl('info-dopune');
    if (!info) return;

    const m = meta();
    const bajtova = new TextEncoder().encode(unosTeksta.value).length;

    if (m.vrsta === 'tocna') {
        info.textContent = `${bajtova} bajtova — tokovna šifra, šifrat je iste dužine.`;
        return;
    }
    if (m.vrsta !== 'blokovni') return;

    const blok = m.blok ?? 16;
    const dopunjeno = bajtova + (blok - (bajtova % blok));
    info.textContent =
        `${bajtova} bajtova → PKCS#7 dopuna do ${dopunjeno} bajtova ` +
        `(${dopunjeno / blok} blokova po ${blok} B) → CBC režim`;
}

unosTeksta.addEventListener('input', osvjeziInfoDopune);

el<HTMLButtonElement>('dugme-kljuc').addEventListener('click', async (dogadjaj) => {
    const dugme = dogadjaj.currentTarget as HTMLButtonElement;
    const oslobodi = zauzmi(dugme, 'Generišem…');
    try {
        trenutniKljuc = await posalji<OdgovorKljuca>('/api/kljuc', { algoritam: meta().id });

        const redovi: Array<[string, string]> = [];
        if (trenutniKljuc.k1) {
            redovi.push(['k1 (hex)', trenutniKljuc.k1]);
            redovi.push(['k2 (hex)', trenutniKljuc.k2!]);
            redovi.push(['k3 (hex)', trenutniKljuc.k3!]);
            redovi.push(['Ukupno', '3 × 56 efektivnih bita']);
        } else {
            redovi.push(['Ključ (hex)', trenutniKljuc.kljuc!]);
            if (trenutniKljuc.nonce) redovi.push(['Nonce (hex)', trenutniKljuc.nonce]);
            redovi.push(['Dužina', `${trenutniKljuc.duzina_bita} bita`]);
        }

        el('prikaz-kljuca').innerHTML = parovi(redovi);
        el('status-kljuca').textContent = '';
        el<HTMLButtonElement>('dugme-sifruj').disabled = false;
    } catch (greska) {
        el('prikaz-kljuca').innerHTML = poruka('greska', escapeHtml(tekstGreske(greska)));
    } finally {
        oslobodi();
    }
});

function prikaziSifrat(): void {
    if (!zadnjiSifrat) return;
    const format = document.querySelector<HTMLInputElement>('input[name="format"]:checked')?.value;
    const tekst = format === 'base64' ? zadnjiSifrat.sifrat.base64 : zadnjiSifrat.sifrat.hex;
    const izlaz = mozdaEl('izlaz-sifrata');
    if (izlaz) izlaz.textContent = tekst;
}

document.querySelectorAll<HTMLInputElement>('input[name="format"]').forEach((radio) => {
    radio.addEventListener('change', prikaziSifrat);
});

el<HTMLButtonElement>('dugme-sifruj').addEventListener('click', async (dogadjaj) => {
    const dugme = dogadjaj.currentTarget as HTMLButtonElement;
    const cilj = el('rezultat-simetricni');
    if (!trenutniKljuc) return;

    const oslobodi = zauzmi(dugme, 'Šifrujem…');
    try {
        const telo: Record<string, unknown> = {
            algoritam: meta().id,
            tekst: unosTeksta.value,
            ...trenutniKljuc,
        };
        const r = await posalji<OdgovorSifrovanja>('/api/sifruj', telo);
        zadnjiSifrat = r;

        cilj.innerHTML = `
            <div class="mjere">
                ${mjera('Enkripcija', `${r.vrijeme_enkripcije_ms.toFixed(2)} ms`)}
                ${mjera('Dekripcija', `${r.vrijeme_dekripcije_ms.toFixed(2)} ms`)}
                ${mjera('Veličina šifrata', formatirajBajtove(r.sifrat.duzina))}
            </div>
            ${r.iv ? `<p class="prigusen">IV (prvih ${r.iv.length / 2} bajtova šifrata): <code>${r.iv}</code></p>` : ''}
            <pre class="izlaz" id="izlaz-sifrata"></pre>
            ${r.ispravno
                ? poruka('uspjeh', 'Dekripcija je vratila <strong>bajt po bajt isti</strong> tekst.')
                : poruka('greska', 'Dekriptovani tekst se NE poklapa s originalom.')}
            <label style="margin-top:.6rem">Dekriptovani tekst</label>
            <pre class="izlaz">${escapeHtml(r.vraceno)}</pre>
        `;
        prikaziSifrat();
    } catch (greska) {
        cilj.innerHTML = poruka('greska', escapeHtml(tekstGreske(greska)));
    } finally {
        oslobodi();
    }
});

// -------------------------------------------------------------------- RSA

const unosRsa = mozdaEl<HTMLTextAreaElement>('unos-rsa');

function osvjeziRsaLimit(): void {
    const info = mozdaEl('info-rsa-limit');
    if (!info || !unosRsa) return;
    const bajtova = new TextEncoder().encode(unosRsa.value).length;
    if (!trenutniRsa) {
        info.textContent = `${bajtova} bajtova — generiši ključ da vidiš granicu.`;
        return;
    }
    const limit = trenutniRsa.limit_bajtova;
    info.textContent = `${bajtova} od ${limit} dopuštenih bajtova`;
    info.style.color = bajtova > limit ? 'var(--greska)' : '';
}

unosRsa?.addEventListener('input', osvjeziRsaLimit);

mozdaEl<HTMLButtonElement>('dugme-rsa-kljuc')?.addEventListener('click', async (dogadjaj) => {
    const dugme = dogadjaj.currentTarget as HTMLButtonElement;
    const oslobodi = zauzmi(dugme, 'Tražim proste brojeve…');
    try {
        trenutniRsa = await posalji<OdgovorRsaKljuca>('/api/rsa/kljuc', {
            bita: meta().kljuc_bita,
        });

        el('prikaz-rsa-kljuca').innerHTML = `
            <div class="mreza mreza-2">
                <div>
                    <h3 style="margin-top:0">Javni ključ (n, e)</h3>
                    <p class="prigusen" style="margin:.2rem 0 .6rem">smije se slobodno dijeliti</p>
                    ${par('n', skrati(trenutniRsa.n))}
                    ${par('e', trenutniRsa.e)}
                </div>
                <div>
                    <h3 style="margin-top:0">Privatni ključ (n, d)</h3>
                    <p class="prigusen" style="margin:.2rem 0 .6rem">nikad se ne dijeli</p>
                    ${par('d', skrati(trenutniRsa.d))}
                    ${poruka('upozorenje',
                        'Privatni eksponent se u praksi <strong>nikad ne prikazuje niti prenosi</strong>. ' +
                        'Vidljiv je samo zato što je ovo demonstracija. Isto vrijedi za p, q i φ(n) — ' +
                        'oni se nakon generisanja ključa uništavaju.')}
                    <details>
                        <summary style="cursor:pointer" class="prigusen">Prikaži p, q i φ(n)</summary>
                        <div style="margin-top:.5rem">
                            ${par('p', skrati(trenutniRsa.p))}
                            ${par('q', skrati(trenutniRsa.q))}
                            ${par('φ(n)', skrati(trenutniRsa.phi))}
                        </div>
                    </details>
                </div>
            </div>
            <p class="prigusen">Generisano za ${(trenutniRsa.vrijeme_generisanja_ms / 1000).toFixed(2)} s</p>
        `;
        el('status-rsa').textContent = '';
        el<HTMLButtonElement>('dugme-rsa-sifruj').disabled = false;
        osvjeziRsaLimit();
    } catch (greska) {
        el('prikaz-rsa-kljuca').innerHTML = poruka('greska', escapeHtml(tekstGreske(greska)));
    } finally {
        oslobodi();
    }
});

mozdaEl<HTMLButtonElement>('dugme-rsa-sifruj')?.addEventListener('click', async (dogadjaj) => {
    const dugme = dogadjaj.currentTarget as HTMLButtonElement;
    const cilj = el('rezultat-rsa');
    if (!trenutniRsa || !unosRsa) return;

    const oslobodi = zauzmi(dugme, 'Šifrujem…');
    try {
        const r = await posalji<OdgovorRsaSifrovanja>('/api/rsa/sifruj', {
            n: trenutniRsa.n, e: trenutniRsa.e, d: trenutniRsa.d,
            tekst: unosRsa.value,
        });

        const odnos = r.vrijeme_enkripcije_ms > 0
            ? `${Math.round(r.vrijeme_dekripcije_ms / r.vrijeme_enkripcije_ms)}×`
            : '—';

        cilj.innerHTML = `
            <div class="mjere">
                ${mjera('Enkripcija (javnim)', `${r.vrijeme_enkripcije_ms.toFixed(2)} ms`)}
                ${mjera('Dekripcija (privatnim)', `${r.vrijeme_dekripcije_ms.toFixed(2)} ms`)}
                ${mjera('Odnos', odnos)}
            </div>
            <p class="prigusen">
                Dekripcija je znatno sporija jer je e = 65537 broj sa samo dva
                postavljena bita, dok je d pune dužine modula.
            </p>
            <pre class="izlaz">${r.sifrat.hex}</pre>
            ${r.ispravno
                ? poruka('uspjeh', 'Dekripcija privatnim ključem vratila je originalnu poruku.')
                : poruka('greska', 'Poruka se ne poklapa.')}
            <pre class="izlaz">${escapeHtml(r.vraceno)}</pre>
        `;
    } catch (greska) {
        cilj.innerHTML = poruka('greska', escapeHtml(tekstGreske(greska)));
    } finally {
        oslobodi();
    }
});

// ------------------------------------------------------------------- ECDH

mozdaEl<HTMLButtonElement>('dugme-ecdh')?.addEventListener('click', async (dogadjaj) => {
    const dugme = dogadjaj.currentTarget as HTMLButtonElement;
    const cilj = el('rezultat-ecdh');
    const oslobodi = zauzmi(dugme, 'Razmjenjujem…');
    try {
        const r = await posalji<OdgovorEcdh>('/api/ecdh/razmjena');
        trenutnaTajna = r.tajna_alice;

        cilj.innerHTML = `
            <div class="mreza mreza-2">
                <div>
                    <h3 style="margin-top:0">Alice</h3>
                    ${par('Javni ključ (hex)', r.alice_javni)}
                </div>
                <div>
                    <h3 style="margin-top:0">Bob</h3>
                    ${par('Javni ključ (hex)', r.bob_javni)}
                </div>
            </div>
            <h3>Zajednička tajna</h3>
            ${par('Alice izračunala', r.tajna_alice)}
            ${par('Bob izračunao', r.tajna_bob)}
            ${r.jednake
                ? poruka('uspjeh',
                    'Obje strane su došle do <strong>iste</strong> tajne, a ona sama nikad ' +
                    'nije prošla kanalom — prenijeti su samo javni ključevi.')
                : poruka('greska', 'Tajne se ne poklapaju.')}
        `;
        el<HTMLButtonElement>('dugme-ecdh-sifruj').disabled = false;
    } catch (greska) {
        cilj.innerHTML = poruka('greska', escapeHtml(tekstGreske(greska)));
    } finally {
        oslobodi();
    }
});

mozdaEl<HTMLButtonElement>('dugme-ecdh-sifruj')?.addEventListener('click', async (dogadjaj) => {
    const dugme = dogadjaj.currentTarget as HTMLButtonElement;
    const cilj = el('rezultat-hibridni');
    const unos = el<HTMLTextAreaElement>('unos-ecdh');
    if (!trenutnaTajna) return;

    const oslobodi = zauzmi(dugme, 'Šifrujem…');
    try {
        const r = await posalji<OdgovorHibridno>('/api/ecdh/hibridno', {
            tajna: trenutnaTajna,
            tekst: unos.value,
        });

        cilj.innerHTML = `
            ${par('Izvedeni AES-128 ključ (hex)', r.izvedeni_kljuc)}
            ${par('Šifrat (hex)', skrati(r.sifrat.hex, 96))}
            ${r.ispravno
                ? poruka('uspjeh',
                    'Bob je istim izvedenim ključem dešifrovao poruku — nijedna strana ' +
                    'nije morala unaprijed dijeliti tajnu.')
                : poruka('greska', 'Dešifrovanje nije uspjelo.')}
        `;
    } catch (greska) {
        cilj.innerHTML = poruka('greska', escapeHtml(tekstGreske(greska)));
    } finally {
        oslobodi();
    }
});

prikaziAlgoritam();
