/** Zajedničke pomoćne funkcije za sve stranice. */

/** Traži element i baca grešku ako ga nema — bolje nego tihi `null` kasnije. */
export function el<T extends HTMLElement>(id: string): T {
    const cvor = document.getElementById(id);
    if (!cvor) {
        throw new Error(`Element #${id} ne postoji u stranici.`);
    }
    return cvor as T;
}

/** Kao `el`, ali vraća null bez greške — za elemente kojih na nekim stranicama nema. */
export function mozdaEl<T extends HTMLElement>(id: string): T | null {
    return document.getElementById(id) as T | null;
}

/**
 * POST na Python API. Greške koje backend vrati kao {"greska": "..."} podižu se
 * kao Error s tom porukom, da pozivalac ima jedno mjesto za obradu.
 */
export async function posalji<T>(putanja: string, telo: unknown = {}): Promise<T> {
    const odgovor = await fetch(putanja, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(telo),
    });

    let podaci: unknown;
    try {
        podaci = await odgovor.json();
    } catch {
        throw new Error(`Server je vratio odgovor koji nije JSON (${odgovor.status}).`);
    }

    if (!odgovor.ok) {
        const poruka = (podaci as { greska?: string }).greska;
        throw new Error(poruka ?? `Greška ${odgovor.status}.`);
    }
    return podaci as T;
}

/** Poruka iz greške bez "Error: " prefiksa — korisniku to ništa ne znači. */
export function tekstGreske(greska: unknown): string {
    return greska instanceof Error ? greska.message : String(greska);
}

export function escapeHtml(tekst: string): string {
    const div = document.createElement('div');
    div.textContent = tekst;
    return div.innerHTML;
}

/** Red "ključ → vrijednost" u istom stilu kao drugdje u aplikaciji. */
export function par(kljuc: string, vrijednost: string): string {
    return `<div class="par">
        <span class="kljuc">${escapeHtml(kljuc)}</span>
        <span class="vrijednost">${escapeHtml(vrijednost)}</span>
    </div>`;
}

export function parovi(stavke: Array<[string, string]>): string {
    return stavke.map(([k, v]) => par(k, v)).join('');
}

export function poruka(vrsta: 'info' | 'uspjeh' | 'upozorenje' | 'greska', tekst: string): string {
    return `<div class="poruka ${vrsta}">${tekst}</div>`;
}

export function mjera(oznaka: string, vrijednost: string): string {
    return `<div class="mjera">
        <div class="broj">${escapeHtml(vrijednost)}</div>
        <div class="oznaka-mjere">${escapeHtml(oznaka)}</div>
    </div>`;
}

/** Skraćuje jako duge brojeve (RSA modul ima 300+ cifara). */
export function skrati(vrijednost: string, maks = 44): string {
    if (vrijednost.length <= maks) return vrijednost;
    const pola = Math.floor(maks / 2);
    return `${vrijednost.slice(0, pola)}…${vrijednost.slice(-8)}  (${vrijednost.length} cifara)`;
}

export function formatirajVrijeme(sekunde: number): string {
    if (sekunde >= 1) return `${sekunde.toFixed(2)} s`;
    if (sekunde >= 1e-3) return `${(sekunde * 1e3).toFixed(2)} ms`;
    return `${(sekunde * 1e6).toFixed(0)} µs`;
}

export function formatirajBajtove(bajtova: number): string {
    if (bajtova >= 1e6) return `${(bajtova / 1e6).toPrecision(3).replace(/\.?0+$/, '')} MB`;
    if (bajtova >= 1e3) return `${(bajtova / 1e3).toPrecision(3).replace(/\.?0+$/, '')} KB`;
    return `${bajtova} B`;
}

/** Prebacivanje tabova — isti obrazac na Benchmark i Demonstracije stranici. */
export function poveziTabove(): void {
    const dugmad = document.querySelectorAll<HTMLButtonElement>('.tabovi button[data-tab]');
    dugmad.forEach((dugme) => {
        dugme.addEventListener('click', () => {
            dugmad.forEach((d) => d.classList.remove('aktivan'));
            document.querySelectorAll('.tab-sadrzaj').forEach((s) => s.classList.remove('aktivan'));

            dugme.classList.add('aktivan');
            const cilj = document.getElementById(dugme.dataset.tab ?? '');
            cilj?.classList.add('aktivan');
        });
    });
}

/** Postavlja dugme u stanje "radi se" i vraća funkciju koja ga vraća nazad. */
export function zauzmi(dugme: HTMLButtonElement, tekst = 'Radim…'): () => void {
    const original = dugme.innerHTML;
    dugme.disabled = true;
    dugme.innerHTML = `<span class="vrtiljak"></span> ${tekst}`;
    return () => {
        dugme.disabled = false;
        dugme.innerHTML = original;
    };
}
