/**
 * Stranica "Benchmark" — grafovi i tabela iz benchmark/results.csv.
 *
 * Podaci dolaze već izmjereni (Flask ih ubaci u stranicu); ovdje se ništa ne
 * mjeri. Mjerenje je preskupo za rad uživo — ručni AES postiže oko 46 KB/s.
 */
import {
    Chart, type ChartConfiguration, type ChartDataset, type ChartType, type Plugin,
} from 'chart.js/auto';

import type { Mjerenje } from './tipovi';
import {
    el, escapeHtml, formatirajBajtove, formatirajVrijeme, poveziTabove,
} from './pomocno';

declare global {
    interface Window {
        MJERENJA: Mjerenje[];
        BOJE: Record<string, string>;
        POREDBENA_VELICINA: number;
        NAZIVI_OPERACIJA: Record<string, string>;
    }
}

const MJERENJA = window.MJERENJA;
const BOJE = window.BOJE;
const NAZIVI_OPERACIJA = window.NAZIVI_OPERACIJA;

/** CSV nosi snake_case ("generisanje_kljuca"); u tabeli stoji čitljiv naziv. */
function nazivOperacije(operacija: string): string {
    return NAZIVI_OPERACIJA[operacija] ?? operacija.replace(/_/g, ' ');
}

function boja(algoritam: string): string {
    return BOJE[algoritam] ?? '#888888';
}

/** Vrijednost i njena standardna devijacija — koristi ih plugin za error barove. */
interface TackaSaGreskom {
    x: number;
    y: number;
    greska: number;
}

/**
 * Chart.js nema ugrađene error barove, a bez njih grafovi u aplikaciji ne bi
 * pokazivali isto što i slike u radu. Plugin crta okomitu crticu ±σ oko svake
 * tačke koja ima polje `greska`.
 */
const pluginGresaka: Plugin = {
    id: 'errorBars',
    afterDatasetsDraw(chart) {
        const { ctx } = chart;
        chart.data.datasets.forEach((dataset, indeks) => {
            const meta = chart.getDatasetMeta(indeks);
            if (meta.hidden) return;

            const skalaY = chart.scales[meta.yAxisID ?? 'y'];
            ctx.save();
            ctx.strokeStyle = (dataset.borderColor as string) ?? '#888';
            ctx.lineWidth = 1.2;

            meta.data.forEach((element, i) => {
                const tacka = (dataset.data as unknown as TackaSaGreskom[])[i];
                if (!tacka || !tacka.greska) return;

                const gornja = skalaY.getPixelForValue(tacka.y + tacka.greska);
                // Na logaritamskoj skali nula ne postoji, pa se donja granica ograniči
                const donjaVrijednost = Math.max(tacka.y - tacka.greska, tacka.y / 10);
                const donja = skalaY.getPixelForValue(donjaVrijednost);
                const x = element.x;

                ctx.beginPath();
                ctx.moveTo(x, gornja);
                ctx.lineTo(x, donja);
                ctx.moveTo(x - 3, gornja);
                ctx.lineTo(x + 3, gornja);
                ctx.moveTo(x - 3, donja);
                ctx.lineTo(x + 3, donja);
                ctx.stroke();
            });
            ctx.restore();
        });
    },
};

Chart.register(pluginGresaka);

Chart.defaults.color = '#98a1b3';
Chart.defaults.borderColor = 'rgba(42, 47, 58, .7)';
Chart.defaults.font.family = "-apple-system, 'Segoe UI', Roboto, sans-serif";
Chart.defaults.maintainAspectRatio = false;

// ------------------------------------------------------------------ Izbor

/** Vrijednost filtera koja znaci "sve algoritme", nasuprot praznoj (crtica). */
const SVI = '*';

function sveKvacice(): HTMLInputElement[] {
    return [...document.querySelectorAll<HTMLInputElement>('#lista-algoritama input')];
}

function odabrani(): Set<string> {
    const izabrani = new Set<string>();
    document.querySelectorAll<HTMLInputElement>('#lista-algoritama input:checked')
        .forEach((polje) => izabrani.add(polje.value));
    return izabrani;
}

/*
 * Filter u tabeli i kvacice iznad grafova gledaju iste podatke, pa se drze
 * zajedno: izbor u filteru ukljuci kvacicu (inace bi grafovi ostali prazni),
 * a skidanje te kvacice vrati filter na crticu.
 */

function uskladiKvacice(izbor: string): void {
    if (!izbor) return;
    sveKvacice().forEach((polje) => {
        if (izbor === SVI || polje.value === izbor) polje.checked = true;
    });
}

function uskladiFilter(): void {
    const filter = el<HTMLSelectElement>('filter-algoritma');
    const izbor = filter.value;
    if (!izbor) return;

    const nedostaje = izbor === SVI
        ? sveKvacice().some((polje) => !polje.checked)
        : !sveKvacice().some((polje) => polje.value === izbor && polje.checked);
    if (nedostaje) filter.value = '';
}

// ------------------------------------------------------------------ Grafovi

/**
 * Mapa drži i linijske i stupčaste grafove, pa je tip grafa namjerno slobodan.
 * Tip podataka je `unknown` jer serije koriste vlastiti oblik tačke
 * ({x, y, greska}) koji Chart.js generici ne opisuju.
 */
const grafovi = new Map<string, Chart<ChartType, unknown, unknown>>();

/** Crta graf na dato platno, uništavajući prethodni na istom mjestu. */
function nacrtaj<TVrsta extends ChartType>(
    idPlatna: string,
    konfiguracija: ChartConfiguration<TVrsta, unknown, unknown>,
): void {
    grafovi.get(idPlatna)?.destroy();
    const platno = el<HTMLCanvasElement>(idPlatna);

    /*
     * Chart.js na platno upisuje inline width/height. Ako je graf prvi put
     * nacrtan u skrivenom tabu, tu ostane 0px i pri sljedećem crtanju se mjeri
     * platno umjesto kontejnera — pa graf zauvijek ostane nevidljiv. Brisanje
     * inline stila vraća mjerenje na kontejner.
     */
    platno.removeAttribute('style');

    grafovi.set(idPlatna, new Chart(platno, konfiguracija) as Chart<ChartType, unknown, unknown>);
}

const logOsa = (naslov: string, formater: (v: number) => string) => ({
    type: 'logarithmic' as const,
    title: { display: true, text: naslov },
    ticks: {
        callback: (vrijednost: string | number) => {
            const broj = Number(vrijednost);
            // Na log skali Chart.js nudi i međupodioke; označavaju se samo dekade
            const log = Math.log10(broj);
            return Math.abs(log - Math.round(log)) < 1e-9 ? formater(broj) : '';
        },
    },
});

function serijeZaOperaciju(operacija: string, izabrani: Set<string>): ChartDataset<'line'>[] {
    const poAlgoritmu = new Map<string, Mjerenje[]>();

    for (const m of MJERENJA) {
        if (m.operacija !== operacija) continue;
        if (m.velicina_bajta === null) continue;
        if (!izabrani.has(m.algoritam)) continue;
        const lista = poAlgoritmu.get(m.algoritam) ?? [];
        lista.push(m);
        poAlgoritmu.set(m.algoritam, lista);
    }

    return [...poAlgoritmu.entries()]
        .sort(([a], [b]) => a.localeCompare(b))
        .map(([algoritam, redovi]) => {
            redovi.sort((a, b) => (a.velicina_bajta ?? 0) - (b.velicina_bajta ?? 0));
            // RSA ima samo jednu moguću veličinu ulaza, pa nema šta spajati linijom
            const jednaTacka = redovi.length === 1;
            return {
                label: algoritam,
                data: redovi.map((r) => ({
                    x: r.velicina_bajta as number,
                    y: r.srednje_vrijeme_s,
                    greska: r.std_dev_s,
                })),
                borderColor: boja(algoritam),
                backgroundColor: boja(algoritam),
                showLine: !jednaTacka,
                pointStyle: jednaTacka ? 'rectRot' : 'circle',
                pointRadius: jednaTacka ? 7 : 4,
                borderWidth: 2,
                tension: 0,
            } as unknown as ChartDataset<'line'>;
        });
}

function grafVrijemeVsVelicina(izabrani: Set<string>): void {
    for (const [idPlatna, operacija] of [
        ['graf-enkripcija', 'enkripcija'],
        ['graf-dekripcija', 'dekripcija'],
    ] as const) {
        nacrtaj(idPlatna, {
            type: 'line',
            data: { datasets: serijeZaOperaciju(operacija, izabrani) },
            options: {
                parsing: false,
                interaction: { mode: 'nearest', intersect: false },
                scales: {
                    x: logOsa('Veličina podataka', formatirajBajtove),
                    y: logOsa('Vrijeme', formatirajVrijeme),
                },
                plugins: {
                    legend: { labels: { boxWidth: 12, usePointStyle: true } },
                    tooltip: {
                        callbacks: {
                            label: (kontekst) => {
                                const t = kontekst.raw as TackaSaGreskom;
                                return `${kontekst.dataset.label}: ${formatirajVrijeme(t.y)}` +
                                    ` ± ${formatirajVrijeme(t.greska)}  (${formatirajBajtove(t.x)})`;
                            },
                        },
                    },
                },
            },
        });
    }
}

function grafGenerisanjaKljuca(izabrani: Set<string>): void {
    const keygen = MJERENJA.filter(
        (m) => m.operacija === 'generisanje_kljuca' && izabrani.has(m.algoritam),
    );

    const rsa = keygen
        .filter((m) => m.algoritam.startsWith('RSA'))
        .sort((a, b) => (a.duzina_kljuca_bita ?? 0) - (b.duzina_kljuca_bita ?? 0));

    nacrtaj('graf-rsa-keygen', {
        type: 'line',
        data: {
            labels: rsa.map((m) => `${m.duzina_kljuca_bita} bita`),
            datasets: [{
                label: 'RSA',
                /*
                 * Tačke nose i `x` (oznaku kategorije). S parsing-om koji navodi
                 * samo yAxisKey Chart.js traži podrazumijevano polje `x`, ne
                 * nađe ga, i graf ostane prazan uz uredno iscrtane ose.
                 */
                data: rsa.map((m) => ({
                    x: `${m.duzina_kljuca_bita} bita`,
                    y: m.srednje_vrijeme_s,
                    greska: m.std_dev_s,
                })) as never,
                parsing: { xAxisKey: 'x', yAxisKey: 'y' },
                borderColor: boja('RSA-2048'),
                backgroundColor: boja('RSA-2048'),
                borderWidth: 2,
                pointRadius: 6,
            }],
        },
        options: {
            scales: { y: logOsa('Vrijeme', formatirajVrijeme) },
            plugins: {
                legend: { display: false },
                tooltip: {
                    callbacks: {
                        label: (kontekst) => {
                            const t = kontekst.raw as TackaSaGreskom;
                            return `${formatirajVrijeme(t.y)} ± ${formatirajVrijeme(t.greska)}`;
                        },
                    },
                },
            },
        },
    });

    const ostali = keygen
        .filter((m) => !m.algoritam.startsWith('RSA'))
        .sort((a, b) => a.srednje_vrijeme_s - b.srednje_vrijeme_s);

    nacrtaj('graf-ostali-keygen', {
        type: 'bar',
        data: {
            labels: ostali.map((m) => m.algoritam),
            datasets: [{
                label: 'Generisanje ključa',
                data: ostali.map((m) => m.srednje_vrijeme_s),
                backgroundColor: ostali.map((m) => boja(m.algoritam)),
            }],
        },
        options: {
            indexAxis: 'y',
            scales: { x: logOsa('Vrijeme', formatirajVrijeme) },
            plugins: {
                legend: { display: false },
                tooltip: {
                    callbacks: {
                        label: (kontekst) => formatirajVrijeme(kontekst.parsed.x ?? 0),
                    },
                },
            },
        },
    });
}

function grafPoredjenja(izabrani: Set<string>, velicina: number): void {
    const enkripcija = MJERENJA.filter(
        (m) => m.operacija === 'enkripcija' && m.velicina_bajta !== null
            && izabrani.has(m.algoritam),
    );

    // Za svaki algoritam se uzima mjerenje najbliže traženoj veličini; kod RSA
    // to je njegov jedini blok, pa se stvarna veličina ispisuje uz naziv.
    const najblize = new Map<string, Mjerenje>();
    for (const m of enkripcija) {
        const postojece = najblize.get(m.algoritam);
        const razlika = Math.abs((m.velicina_bajta as number) - velicina);
        if (!postojece
            || razlika < Math.abs((postojece.velicina_bajta as number) - velicina)) {
            najblize.set(m.algoritam, m);
        }
    }

    const redovi = [...najblize.values()].sort(
        (a, b) => a.srednje_vrijeme_s - b.srednje_vrijeme_s,
    );

    nacrtaj('graf-poredjenje', {
        type: 'bar',
        data: {
            labels: redovi.map((m) => (
                m.velicina_bajta === velicina
                    ? m.algoritam
                    : `${m.algoritam} (${formatirajBajtove(m.velicina_bajta as number)})`
            )),
            datasets: [{
                label: `Vrijeme enkripcije pri ${formatirajBajtove(velicina)}`,
                data: redovi.map((m) => m.srednje_vrijeme_s),
                backgroundColor: redovi.map((m) => boja(m.algoritam)),
            }],
        },
        options: {
            scales: { y: logOsa('Vrijeme enkripcije', formatirajVrijeme) },
            plugins: {
                legend: { display: false },
                tooltip: {
                    callbacks: {
                        label: (kontekst) => {
                            const m = redovi[kontekst.dataIndex];
                            return `${formatirajVrijeme(m.srednje_vrijeme_s)}` +
                                ` ± ${formatirajVrijeme(m.std_dev_s)}  (n=${m.ponavljanja})`;
                        },
                    },
                },
            },
        },
    });
}

// ------------------------------------------------------------------ Tabela

function popuniTabelu(izabrani: Set<string>): void {
    const operacija = el<HTMLSelectElement>('filter-operacije').value;
    const izborAlgoritma = el<HTMLSelectElement>('filter-algoritma').value;
    // "Svi algoritmi" nije filter nego prikaz svega oznacenog u panelu iznad
    const algoritam = izborAlgoritma === SVI ? '' : izborAlgoritma;
    const tijelo = el<HTMLTableSectionElement>('tabela-rezultata').querySelector('tbody');
    if (!tijelo) return;

    // Izbor algoritma u filteru je jaci od kvacica iznad grafova — kad je
    // postavljen, tabela pokazuje samo taj algoritam.
    const redovi = MJERENJA
        .filter((m) => (algoritam ? m.algoritam === algoritam : izabrani.has(m.algoritam)))
        .filter((m) => !operacija || m.operacija === operacija)
        .sort((a, b) => a.algoritam.localeCompare(b.algoritam)
            || a.operacija.localeCompare(b.operacija)
            || (a.velicina_bajta ?? 0) - (b.velicina_bajta ?? 0));

    el('dugme-ponisti').classList.toggle('skriven', !izborAlgoritma && !operacija);

    tijelo.innerHTML = redovi.map((m) => `
        <tr>
            <td>${escapeHtml(m.algoritam)}</td>
            <td><span class="oznaka-operacije">${escapeHtml(nazivOperacije(m.operacija))}</span></td>
            <td class="broj">${m.velicina_bajta === null ? '—' : formatirajBajtove(m.velicina_bajta)}</td>
            <td class="broj">${m.duzina_kljuca_bita ?? '—'}</td>
            <td class="broj">${formatirajVrijeme(m.srednje_vrijeme_s)}</td>
            <td class="broj">${formatirajVrijeme(m.std_dev_s)}</td>
            <td class="broj">${m.ponavljanja}</td>
            <td class="broj">${m.propusnost_mb_s === null ? '—' : m.propusnost_mb_s.toFixed(3)}</td>
        </tr>
    `).join('');

    if (redovi.length === 0) {
        const tekst = (!algoritam && izabrani.size === 0)
            ? 'Nijedan algoritam nije označen — izaberi ih u panelu iznad.'
            : 'Nema mjerenja za izabranu kombinaciju filtera.';
        tijelo.innerHTML = `<tr><td colspan="8" class="prazna-tabela">
            ${escapeHtml(tekst)}
        </td></tr>`;
    }

    const opis = [
        izborAlgoritma === SVI ? 'svi algoritmi' : algoritam || null,
        operacija ? nazivOperacije(operacija).toLowerCase() : null,
    ].filter(Boolean).join(', ');

    el('sazetak-tabele').textContent = opis
        ? `Prikazano ${redovi.length} od ukupno ${MJERENJA.length} mjerenja (${opis}).`
        : `Prikazano ${redovi.length} od ukupno ${MJERENJA.length} mjerenja.`;
}

// ------------------------------------------------------------------ Osvježavanje

function osvjezi(): void {
    const izabrani = odabrani();
    const velicina = Number(el<HTMLSelectElement>('izbor-velicine').value);

    grafVrijemeVsVelicina(izabrani);
    grafGenerisanjaKljuca(izabrani);
    grafPoredjenja(izabrani, velicina);
    popuniTabelu(izabrani);
}

sveKvacice().forEach((polje) => polje.addEventListener('change', () => {
    uskladiFilter();
    osvjezi();
}));

el<HTMLSelectElement>('izbor-velicine').addEventListener('change', osvjezi);
el<HTMLSelectElement>('filter-operacije').addEventListener('change', osvjezi);
el<HTMLSelectElement>('filter-algoritma').addEventListener('change', (dogadjaj) => {
    uskladiKvacice((dogadjaj.target as HTMLSelectElement).value);
    osvjezi();
});

el<HTMLButtonElement>('dugme-ponisti').addEventListener('click', () => {
    el<HTMLSelectElement>('filter-operacije').value = '';
    el<HTMLSelectElement>('filter-algoritma').value = '';
    osvjezi();
});

el<HTMLButtonElement>('dugme-svi').addEventListener('click', () => {
    sveKvacice().forEach((polje) => { polje.checked = true; });
    osvjezi();
});

el<HTMLButtonElement>('dugme-nijedan').addEventListener('click', () => {
    sveKvacice().forEach((polje) => { polje.checked = false; });
    uskladiFilter();
    osvjezi();
});

poveziTabove();

/*
 * Graf nacrtan dok mu je tab skriven izmjeri kontejner kao 0x0 i takav ostane
 * kad se tab otvori — ni Chart.js-ov resize() ni ResizeObserver to ne poprave,
 * jer element pri display:none uopšte nema okvir. Zato se grafovi jednostavno
 * ponovo iscrtaju nakon promjene taba, kad je novi raspored već primijenjen.
 *
 * setTimeout umjesto requestAnimationFrame: rAF se ne izvršava dok stranica nije
 * vidljiva, pa bi graf ostao neiscrtan ako korisnik promijeni tab u pozadinskoj
 * kartici i tek se poslije vrati na nju.
 */
document.querySelectorAll<HTMLButtonElement>('.tabovi button[data-tab]').forEach((dugme) => {
    dugme.addEventListener('click', () => setTimeout(osvjezi, 0));
});

osvjezi();
