"use strict";(()=>{function r(e){let t=document.getElementById(e);if(!t)throw new Error(`Element #${e} ne postoji u stranici.`);return t}function c(e){return document.getElementById(e)}async function k(e,t={}){let n=await fetch(e,{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify(t)}),i;try{i=await n.json()}catch{throw new Error(`Server je vratio odgovor koji nije JSON (${n.status}).`)}if(!n.ok){let a=i.greska;throw new Error(a??`Gre\u0161ka ${n.status}.`)}return i}function p(e){return e instanceof Error?e.message:String(e)}function l(e){let t=document.createElement("div");return t.textContent=e,t.innerHTML}function u(e,t){return`<div class="par">
        <span class="kljuc">${l(e)}</span>
        <span class="vrijednost">${l(t)}</span>
    </div>`}function x(e){return e.map(([t,n])=>u(t,n)).join("")}function s(e,t){return`<div class="poruka ${e}">${t}</div>`}function v(e,t){return`<div class="mjera">
        <div class="broj">${l(t)}</div>
        <div class="oznaka-mjere">${l(e)}</div>
    </div>`}function g(e,t=44){if(e.length<=t)return e;let n=Math.floor(t/2);return`${e.slice(0,n)}\u2026${e.slice(-8)}  (${e.length} cifara)`}function M(e){return e.toPrecision(3).replace(/(\.\d*?)0+$/,"$1").replace(/\.$/,"")}function H(e){return e>=1e6?`${M(e/1e6)} MB`:e>=1e3?`${M(e/1e3)} KB`:`${e} B`}function f(e,t="Radim\u2026"){let n=e.innerHTML;return e.disabled=!0,e.innerHTML=`<span class="vrtiljak"></span> ${t}`,()=>{e.disabled=!1,e.innerHTML=n}}var S=window.ALGORITMI,m=null,d=null,L=null,h=null,y=r("izbor-algoritma");function b(){return S[y.value]}function j(e,t=!0){c(e)?.classList.toggle("gotov",t)}var A=["korak-sim-1","korak-sim-2","korak-sim-3","korak-rsa-1","korak-rsa-2","korak-rsa-3","korak-ecdh-1","korak-ecdh-2"];function B(){let e=b(),t=e.rucni?'<span class="oznaka rucna">ru\u010Dna implementacija</span>':'<span class="oznaka biblioteka">biblioteka</span>';r("meta-algoritma").innerHTML=t,r("opis-algoritma").textContent=e.opis,r("napomena-algoritma").innerHTML=`<strong>Na \u0161ta paziti.</strong> ${l(e.napomena)}`;let n={blokovni:"sekcija-simetricni",tocna:"sekcija-simetricni",rsa:"sekcija-rsa",ecdh:"sekcija-ecdh"};for(let z of["sekcija-simetricni","sekcija-rsa","sekcija-ecdh"])r(z).classList.toggle("skriven",z!==n[e.vrsta]);m=null,h=null;let i=c("prikaz-kljuca");i&&(i.innerHTML="");let a=c("rezultat-simetricni");a&&(a.innerHTML="");let o=c("status-kljuca");o&&(o.textContent="Klju\u010D jo\u0161 nije generisan.");let E=c("dugme-sifruj");E&&(E.disabled=!0),A.forEach(z=>j(z,!1)),_()}y.addEventListener("change",B);var $=r("unos-teksta");function _(){let e=c("info-dopune");if(!e)return;let t=b(),n=new TextEncoder().encode($.value).length;if(t.vrsta==="tocna"){e.textContent=`${n} bajtova \u2014 tokovna \u0161ifra, \u0161ifrat je iste du\u017Eine.`;return}if(t.vrsta!=="blokovni")return;let i=t.blok??16,a=n+(i-n%i);e.textContent=`${n} bajtova \u2192 PKCS#7 dopuna do ${a} bajtova (${a/i} blokova po ${i} B) \u2192 CBC re\u017Eim`}$.addEventListener("input",_);r("dugme-kljuc").addEventListener("click",async e=>{let t=e.currentTarget,n=f(t,"Generi\u0161em\u2026");try{m=await k("/api/kljuc",{algoritam:b().id});let i=[];m.k1?(i.push(["k1 (hex)",m.k1]),i.push(["k2 (hex)",m.k2]),i.push(["k3 (hex)",m.k3]),i.push(["Ukupno","3 \xD7 56 efektivnih bita"])):(i.push(["Klju\u010D (hex)",m.kljuc]),m.nonce&&i.push(["Nonce (hex)",m.nonce]),i.push(["Du\u017Eina",`${m.duzina_bita} bita`])),r("prikaz-kljuca").innerHTML=x(i),r("status-kljuca").textContent="",r("dugme-sifruj").disabled=!1,j("korak-sim-1")}catch(i){r("prikaz-kljuca").innerHTML=s("greska",l(p(i)))}finally{n()}});function O(){if(!h)return;let t=document.querySelector('input[name="format"]:checked')?.value==="base64"?h.sifrat.base64:h.sifrat.hex,n=c("izlaz-sifrata");n&&(n.textContent=t)}document.querySelectorAll('input[name="format"]').forEach(e=>{e.addEventListener("change",O)});r("dugme-sifruj").addEventListener("click",async e=>{let t=e.currentTarget,n=r("rezultat-simetricni");if(!m)return;let i=f(t,"\u0160ifrujem\u2026");try{let a={algoritam:b().id,tekst:$.value,...m},o=await k("/api/sifruj",a);h=o,n.innerHTML=`
            <div class="mjere">
                ${v("Enkripcija",`${o.vrijeme_enkripcije_ms.toFixed(2)} ms`)}
                ${v("Dekripcija",`${o.vrijeme_dekripcije_ms.toFixed(2)} ms`)}
                ${v("Veli\u010Dina \u0161ifrata",H(o.sifrat.duzina))}
            </div>
            ${o.iv?`<p class="prigusen">IV (prvih ${o.iv.length/2} bajtova \u0161ifrata): <code>${o.iv}</code></p>`:""}
            <pre class="izlaz" id="izlaz-sifrata"></pre>
            ${o.ispravno?s("uspjeh","Dekripcija je vratila <strong>bajt po bajt isti</strong> tekst."):s("greska","Dekriptovani tekst se NE poklapa s originalom.")}
            <label style="margin-top:.6rem">Dekriptovani tekst</label>
            <pre class="izlaz">${l(o.vraceno)}</pre>
        `,O(),j("korak-sim-2"),j("korak-sim-3")}catch(a){n.innerHTML=s("greska",l(p(a)))}finally{i()}});var T=c("unos-rsa");function w(){let e=c("info-rsa-limit");if(!e||!T)return;let t=new TextEncoder().encode(T.value).length;if(!d){e.textContent=`${t} bajtova \u2014 generi\u0161i klju\u010D da vidi\u0161 granicu.`;return}let n=d.limit_bajtova;e.textContent=`${t} od ${n} dopu\u0161tenih bajtova`,e.style.color=t>n?"var(--greska)":""}T?.addEventListener("input",w);c("dugme-rsa-kljuc")?.addEventListener("click",async e=>{let t=e.currentTarget,n=f(t,"Tra\u017Eim proste brojeve\u2026");try{d=await k("/api/rsa/kljuc",{bita:b().kljuc_bita}),r("prikaz-rsa-kljuca").innerHTML=`
            <div class="mreza mreza-2">
                <div>
                    <h3 style="margin-top:0">Javni klju\u010D (n, e)</h3>
                    <p class="prigusen" style="margin:.2rem 0 .6rem">smije se slobodno dijeliti</p>
                    ${u("n",g(d.n))}
                    ${u("e",d.e)}
                </div>
                <div>
                    <h3 style="margin-top:0">Privatni klju\u010D (n, d)</h3>
                    <p class="prigusen" style="margin:.2rem 0 .6rem">nikad se ne dijeli</p>
                    ${u("d",g(d.d))}
                    ${s("upozorenje","Privatni eksponent se u praksi <strong>nikad ne prikazuje niti prenosi</strong>. Vidljiv je samo zato \u0161to je ovo demonstracija. Isto vrijedi za p, q i \u03C6(n) \u2014 oni se nakon generisanja klju\u010Da uni\u0161tavaju.")}
                    <details>
                        <summary style="cursor:pointer" class="prigusen">Prika\u017Ei p, q i \u03C6(n)</summary>
                        <div style="margin-top:.5rem">
                            ${u("p",g(d.p))}
                            ${u("q",g(d.q))}
                            ${u("\u03C6(n)",g(d.phi))}
                        </div>
                    </details>
                </div>
            </div>
            <p class="prigusen">Generisano za ${(d.vrijeme_generisanja_ms/1e3).toFixed(2)} s</p>
        `,r("status-rsa").textContent="",r("dugme-rsa-sifruj").disabled=!1,j("korak-rsa-1"),w()}catch(i){r("prikaz-rsa-kljuca").innerHTML=s("greska",l(p(i)))}finally{n()}});c("dugme-rsa-sifruj")?.addEventListener("click",async e=>{let t=e.currentTarget,n=r("rezultat-rsa");if(!d||!T)return;let i=f(t,"\u0160ifrujem\u2026");try{let a=await k("/api/rsa/sifruj",{n:d.n,e:d.e,d:d.d,tekst:T.value}),o=a.vrijeme_enkripcije_ms>0?`${Math.round(a.vrijeme_dekripcije_ms/a.vrijeme_enkripcije_ms)}\xD7`:"\u2014";n.innerHTML=`
            <div class="mjere">
                ${v("Enkripcija (javnim)",`${a.vrijeme_enkripcije_ms.toFixed(2)} ms`)}
                ${v("Dekripcija (privatnim)",`${a.vrijeme_dekripcije_ms.toFixed(2)} ms`)}
                ${v("Odnos",o)}
            </div>
            <p class="prigusen">
                Dekripcija je znatno sporija jer je e = 65537 broj sa samo dva
                postavljena bita, dok je d pune du\u017Eine modula.
            </p>
            <pre class="izlaz">${a.sifrat.hex}</pre>
            ${a.ispravno?s("uspjeh","Dekripcija privatnim klju\u010Dem vratila je originalnu poruku."):s("greska","Poruka se ne poklapa.")}
            <pre class="izlaz">${l(a.vraceno)}</pre>
        `,j("korak-rsa-2"),j("korak-rsa-3")}catch(a){n.innerHTML=s("greska",l(p(a)))}finally{i()}});c("dugme-ecdh")?.addEventListener("click",async e=>{let t=e.currentTarget,n=r("rezultat-ecdh"),i=f(t,"Razmjenjujem\u2026");try{let a=await k("/api/ecdh/razmjena");L=a.tajna_alice,n.innerHTML=`
            <div class="mreza mreza-2">
                <div>
                    <h3 style="margin-top:0">Alice</h3>
                    ${u("Javni klju\u010D (hex)",a.alice_javni)}
                </div>
                <div>
                    <h3 style="margin-top:0">Bob</h3>
                    ${u("Javni klju\u010D (hex)",a.bob_javni)}
                </div>
            </div>
            <h3>Zajedni\u010Dka tajna</h3>
            ${u("Alice izra\u010Dunala",a.tajna_alice)}
            ${u("Bob izra\u010Dunao",a.tajna_bob)}
            ${a.jednake?s("uspjeh","Obje strane su do\u0161le do <strong>iste</strong> tajne, a ona sama nikad nije pro\u0161la kanalom \u2014 prenijeti su samo javni klju\u010Devi."):s("greska","Tajne se ne poklapaju.")}
        `,r("dugme-ecdh-sifruj").disabled=!1,j("korak-ecdh-1")}catch(a){n.innerHTML=s("greska",l(p(a)))}finally{i()}});c("dugme-ecdh-sifruj")?.addEventListener("click",async e=>{let t=e.currentTarget,n=r("rezultat-hibridni"),i=r("unos-ecdh");if(!L)return;let a=f(t,"\u0160ifrujem\u2026");try{let o=await k("/api/ecdh/hibridno",{tajna:L,tekst:i.value});n.innerHTML=`
            ${u("Izvedeni AES-128 klju\u010D (hex)",o.izvedeni_kljuc)}
            ${u("\u0160ifrat (hex)",g(o.sifrat.hex,96))}
            ${o.ispravno?s("uspjeh","Bob je istim izvedenim klju\u010Dem de\u0161ifrovao poruku \u2014 nijedna strana nije morala unaprijed dijeliti tajnu."):s("greska","De\u0161ifrovanje nije uspjelo.")}
        `,j("korak-ecdh-2")}catch(o){n.innerHTML=s("greska",l(p(o)))}finally{a()}});B();})();
