/**
 * Oblici podataka koje vraća Python API (web/api.py) i koje Flask ubacuje u
 * stranicu preko `window`.
 *
 * Ovo je glavni razlog zašto frontend uopšte ide u TypeScriptu: polja poput
 * `velicina_bajta` su `null` za redove koji mjere generisanje ključa, a
 * `propusnost_mb_s` za ECDH. Bez tipova se to otkrije tek kao prazan graf.
 */

/** Jedan red iz benchmark/results.csv. */
export interface Mjerenje {
    algoritam: string;
    kategorija: string;
    operacija: string;
    /** null za generisanje_kljuca i razmjena_kljuca */
    velicina_bajta: number | null;
    duzina_kljuca_bita: number | null;
    ponavljanja: number;
    srednje_vrijeme_s: number;
    std_dev_s: number;
    min_vrijeme_s: number;
    /** null kad nema veličine podataka */
    propusnost_mb_s: number | null;
}

/** Metapodaci o algoritmu iz web/algoritmi.py. */
export interface MetaAlgoritma {
    id: string;
    naziv: string;
    vrsta: 'blokovni' | 'tocna' | 'rsa' | 'ecdh';
    grupa: string;
    rucni: boolean;
    kljuc_bita: number;
    blok?: number;
    opis: string;
    napomena: string;
}

export interface Sifrat {
    hex: string;
    base64: string;
    duzina: number;
}

export interface Dopuna {
    prije: number;
    poslije: number;
    blokova: number;
    velicina_bloka: number;
}

export interface OdgovorKljuca {
    kljuc?: string;
    nonce?: string;
    k1?: string;
    k2?: string;
    k3?: string;
    duzina_bita: number;
}

export interface OdgovorSifrovanja {
    sifrat: Sifrat;
    iv: string | null;
    vrijeme_enkripcije_ms: number;
    vrijeme_dekripcije_ms: number;
    vraceno: string;
    ispravno: boolean;
    dopuna: Dopuna | null;
}

export interface OdgovorRsaKljuca {
    /** Veliki brojevi stižu kao stringovi — prelaze 2^53 i number bi ih zaokružio. */
    n: string;
    e: string;
    d: string;
    p: string;
    q: string;
    phi: string;
    bita: number;
    limit_bajtova: number;
    vrijeme_generisanja_ms: number;
}

export interface OdgovorRsaSifrovanja {
    sifrat: Sifrat;
    vrijeme_enkripcije_ms: number;
    vrijeme_dekripcije_ms: number;
    vraceno: string;
    ispravno: boolean;
}

export interface OdgovorEcdh {
    alice_javni: string;
    bob_javni: string;
    tajna_alice: string;
    tajna_bob: string;
    jednake: boolean;
}

export interface OdgovorHibridno {
    izvedeni_kljuc: string;
    sifrat: Sifrat;
    vraceno: string;
    ispravno: boolean;
}

export interface ParVrijednosti {
    kljuc: string;
    vrijednost: string;
}

export interface KorakMitm {
    broj: number;
    naslov: string;
    akter: string;
    opis: string;
    istaknuto: boolean;
    vrijednosti: ParVrijednosti[];
}

export interface OdgovorMitm {
    scenario: 'bez_mallory' | 'sa_mallory';
    grupa: { naziv: string; opis: string };
    uspjeh: boolean;
    koraci: KorakMitm[];
}

export interface KorakWiener {
    broj: number;
    k: string;
    d: string;
    phi: string | null;
    p: string | null;
    q: string | null;
    razlog: string;
    uspjeh: boolean;
}

export interface OdgovorWiener {
    bita: number;
    ranjivi: {
        n: string;
        e: string;
        pravi_d: string;
        d_bita: number;
        granica_bita: number;
        nadjeni_d: string | null;
        pregledano: number;
        ukupno_konvergenti: number;
        trajanje_ms: number;
        uspjeh: boolean;
        poruka: string;
        procitano: string | null;
        koraci: KorakWiener[];
    };
    normalni: {
        n: string;
        e: string;
        d_bita: number;
        pregledano: number;
        ukupno_konvergenti: number;
        trajanje_ms: number;
        uspjeh: boolean;
    };
}

export interface Grupa {
    id: string;
    naziv: string;
    /** Citljiv naziv za padajuci meni. */
    oznaka: string;
    opis: string;
    /** Duzina prostog broja p u bitima. */
    bita: number;
    g: number;
}
