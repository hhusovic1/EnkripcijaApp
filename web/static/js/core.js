"use strict";(()=>{function r(e){let t=document.getElementById(e);if(!t)throw new Error(`Element #${e} ne postoji u stranici.`);return t}function d(e){return document.getElementById(e)}async function m(e,t={}){let n=await fetch(e,{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify(t)}),a;try{a=await n.json()}catch{throw new Error(`Server je vratio odgovor koji nije JSON (${n.status}).`)}if(!n.ok){let i=a.greska;throw new Error(i??`Gre\u0161ka ${n.status}.`)}return a}function p(e){return e instanceof Error?e.message:String(e)}function l(e){let t=document.createElement("div");return t.textContent=e,t.innerHTML}function c(e,t){return`<div class="par">
        <span class="kljuc">${l(e)}</span>
        <span class="vrijednost">${l(t)}</span>
    </div>`}function E(e){return e.map(([t,n])=>c(t,n)).join("")}function s(e,t){return`<div class="poruka ${e}">${t}</div>`}function v(e,t){return`<div class="mjera">
        <div class="broj">${l(t)}</div>
        <div class="oznaka-mjere">${l(e)}</div>
    </div>`}function k(e,t=44){if(e.length<=t)return e;let n=Math.floor(t/2);return`${e.slice(0,n)}\u2026${e.slice(-8)}  (${e.length} cifara)`}function M(e){return e>=1e6?`${(e/1e6).toPrecision(3).replace(/\.?0+$/,"")} MB`:e>=1e3?`${(e/1e3).toPrecision(3).replace(/\.?0+$/,"")} KB`:`${e} B`}function g(e,t="Radim\u2026"){let n=e.innerHTML;return e.disabled=!0,e.innerHTML=`<span class="vrtiljak"></span> ${t}`,()=>{e.disabled=!1,e.innerHTML=n}}var w=window.ALGORITMI,j=null,u=null,$=null,f=null,x=r("izbor-algoritma");function T(){return w[x.value]}function H(){let e=T(),t=e.rucni?'<span class="oznaka rucna">ru\u010Dna implementacija</span>':'<span class="oznaka biblioteka">biblioteka</span>';r("meta-algoritma").innerHTML=`${t} &nbsp; rad, sekcija <strong>${l(e.sekcija)}</strong>`,r("opis-algoritma").textContent=e.opis,r("napomena-algoritma").innerHTML=`<strong>Na \u0161ta paziti.</strong> ${l(e.napomena)}`;let n={blokovni:"sekcija-simetricni",tocna:"sekcija-simetricni",rsa:"sekcija-rsa",ecdh:"sekcija-ecdh"};for(let L of["sekcija-simetricni","sekcija-rsa","sekcija-ecdh"])r(L).classList.toggle("skriven",L!==n[e.vrsta]);j=null,f=null;let a=d("prikaz-kljuca");a&&(a.innerHTML="");let i=d("rezultat-simetricni");i&&(i.innerHTML="");let o=d("status-kljuca");o&&(o.textContent="Klju\u010D jo\u0161 nije generisan.");let z=d("dugme-sifruj");z&&(z.disabled=!0),y()}x.addEventListener("change",H);var b=r("unos-teksta");function y(){let e=d("info-dopune");if(!e)return;let t=T(),n=new TextEncoder().encode(b.value).length;if(t.vrsta==="tocna"){e.textContent=`${n} bajtova \u2014 tokovna \u0161ifra, \u0161ifrat je iste du\u017Eine.`;return}if(t.vrsta!=="blokovni")return;let a=t.blok??16,i=n+(a-n%a);e.textContent=`${n} bajtova \u2192 PKCS#7 dopuna do ${i} bajtova (${i/a} blokova po ${a} B) \u2192 CBC re\u017Eim`}b.addEventListener("input",y);r("dugme-kljuc").addEventListener("click",async e=>{let t=e.currentTarget,n=g(t,"Generi\u0161em\u2026");try{j=await m("/api/kljuc",{algoritam:T().id});let a=[];j.k1?(a.push(["k1 (hex)",j.k1]),a.push(["k2 (hex)",j.k2]),a.push(["k3 (hex)",j.k3]),a.push(["Ukupno","3 \xD7 56 efektivnih bita"])):(a.push(["Klju\u010D (hex)",j.kljuc]),j.nonce&&a.push(["Nonce (hex)",j.nonce]),a.push(["Du\u017Eina",`${j.duzina_bita} bita`])),r("prikaz-kljuca").innerHTML=E(a),r("status-kljuca").textContent="",r("dugme-sifruj").disabled=!1}catch(a){r("prikaz-kljuca").innerHTML=s("greska",l(p(a)))}finally{n()}});function B(){if(!f)return;let t=document.querySelector('input[name="format"]:checked')?.value==="base64"?f.sifrat.base64:f.sifrat.hex,n=d("izlaz-sifrata");n&&(n.textContent=t)}document.querySelectorAll('input[name="format"]').forEach(e=>{e.addEventListener("change",B)});r("dugme-sifruj").addEventListener("click",async e=>{let t=e.currentTarget,n=r("rezultat-simetricni");if(!j)return;let a=g(t,"\u0160ifrujem\u2026");try{let i={algoritam:T().id,tekst:b.value,...j},o=await m("/api/sifruj",i);f=o,n.innerHTML=`
            <div class="mjere">
                ${v("Enkripcija",`${o.vrijeme_enkripcije_ms.toFixed(2)} ms`)}
                ${v("Dekripcija",`${o.vrijeme_dekripcije_ms.toFixed(2)} ms`)}
                ${v("Veli\u010Dina \u0161ifrata",M(o.sifrat.duzina))}
            </div>
            ${o.iv?`<p class="prigusen">IV (prvih ${o.iv.length/2} bajtova \u0161ifrata): <code>${o.iv}</code></p>`:""}
            <pre class="izlaz" id="izlaz-sifrata"></pre>
            ${o.ispravno?s("uspjeh","Dekripcija je vratila <strong>bajt po bajt isti</strong> tekst."):s("greska","Dekriptovani tekst se NE poklapa s originalom.")}
            <label style="margin-top:.6rem">Dekriptovani tekst</label>
            <pre class="izlaz">${l(o.vraceno)}</pre>
        `,B()}catch(i){n.innerHTML=s("greska",l(p(i)))}finally{a()}});var h=d("unos-rsa");function _(){let e=d("info-rsa-limit");if(!e||!h)return;let t=new TextEncoder().encode(h.value).length;if(!u){e.textContent=`${t} bajtova \u2014 generi\u0161i klju\u010D da vidi\u0161 granicu.`;return}let n=u.limit_bajtova;e.textContent=`${t} od ${n} dopu\u0161tenih bajtova`,e.style.color=t>n?"var(--greska)":""}h?.addEventListener("input",_);d("dugme-rsa-kljuc")?.addEventListener("click",async e=>{let t=e.currentTarget,n=g(t,"Tra\u017Eim proste brojeve\u2026");try{u=await m("/api/rsa/kljuc",{bita:T().kljuc_bita}),r("prikaz-rsa-kljuca").innerHTML=`
            <div class="mreza mreza-2">
                <div>
                    <h3 style="margin-top:0">Javni klju\u010D (n, e)</h3>
                    <p class="prigusen" style="margin:.2rem 0 .6rem">smije se slobodno dijeliti</p>
                    ${c("n",k(u.n))}
                    ${c("e",u.e)}
                </div>
                <div>
                    <h3 style="margin-top:0">Privatni klju\u010D (n, d)</h3>
                    <p class="prigusen" style="margin:.2rem 0 .6rem">nikad se ne dijeli</p>
                    ${c("d",k(u.d))}
                    ${s("upozorenje","Privatni eksponent se u praksi <strong>nikad ne prikazuje niti prenosi</strong>. Vidljiv je samo zato \u0161to je ovo demonstracija. Isto vrijedi za p, q i \u03C6(n) \u2014 oni se nakon generisanja klju\u010Da uni\u0161tavaju (3.3.3).")}
                    <details>
                        <summary style="cursor:pointer" class="prigusen">Prika\u017Ei p, q i \u03C6(n)</summary>
                        <div style="margin-top:.5rem">
                            ${c("p",k(u.p))}
                            ${c("q",k(u.q))}
                            ${c("\u03C6(n)",k(u.phi))}
                        </div>
                    </details>
                </div>
            </div>
            <p class="prigusen">Generisano za ${(u.vrijeme_generisanja_ms/1e3).toFixed(2)} s</p>
        `,r("status-rsa").textContent="",r("dugme-rsa-sifruj").disabled=!1,_()}catch(a){r("prikaz-rsa-kljuca").innerHTML=s("greska",l(p(a)))}finally{n()}});d("dugme-rsa-sifruj")?.addEventListener("click",async e=>{let t=e.currentTarget,n=r("rezultat-rsa");if(!u||!h)return;let a=g(t,"\u0160ifrujem\u2026");try{let i=await m("/api/rsa/sifruj",{n:u.n,e:u.e,d:u.d,tekst:h.value}),o=i.vrijeme_enkripcije_ms>0?`${Math.round(i.vrijeme_dekripcije_ms/i.vrijeme_enkripcije_ms)}\xD7`:"\u2014";n.innerHTML=`
            <div class="mjere">
                ${v("Enkripcija (javnim)",`${i.vrijeme_enkripcije_ms.toFixed(2)} ms`)}
                ${v("Dekripcija (privatnim)",`${i.vrijeme_dekripcije_ms.toFixed(2)} ms`)}
                ${v("Odnos",o)}
            </div>
            <p class="prigusen">
                Dekripcija je znatno sporija jer je e = 65537 broj sa samo dva
                postavljena bita, dok je d pune du\u017Eine modula (3.3.3).
            </p>
            <pre class="izlaz">${i.sifrat.hex}</pre>
            ${i.ispravno?s("uspjeh","Dekripcija privatnim klju\u010Dem vratila je originalnu poruku."):s("greska","Poruka se ne poklapa.")}
            <pre class="izlaz">${l(i.vraceno)}</pre>
        `}catch(i){n.innerHTML=s("greska",l(p(i)))}finally{a()}});d("dugme-ecdh")?.addEventListener("click",async e=>{let t=e.currentTarget,n=r("rezultat-ecdh"),a=g(t,"Razmjenjujem\u2026");try{let i=await m("/api/ecdh/razmjena");$=i.tajna_alice,n.innerHTML=`
            <div class="mreza mreza-2">
                <div>
                    <h3 style="margin-top:0">Alice</h3>
                    ${c("Javni klju\u010D (hex)",i.alice_javni)}
                </div>
                <div>
                    <h3 style="margin-top:0">Bob</h3>
                    ${c("Javni klju\u010D (hex)",i.bob_javni)}
                </div>
            </div>
            <h3>Zajedni\u010Dka tajna</h3>
            ${c("Alice izra\u010Dunala",i.tajna_alice)}
            ${c("Bob izra\u010Dunao",i.tajna_bob)}
            ${i.jednake?s("uspjeh","Obje strane su do\u0161le do <strong>iste</strong> tajne, a ona sama nikad nije pro\u0161la kanalom \u2014 prenijeti su samo javni klju\u010Devi."):s("greska","Tajne se ne poklapaju.")}
        `,r("dugme-ecdh-sifruj").disabled=!1}catch(i){n.innerHTML=s("greska",l(p(i)))}finally{a()}});d("dugme-ecdh-sifruj")?.addEventListener("click",async e=>{let t=e.currentTarget,n=r("rezultat-hibridni"),a=r("unos-ecdh");if(!$)return;let i=g(t,"\u0160ifrujem\u2026");try{let o=await m("/api/ecdh/hibridno",{tajna:$,tekst:a.value});n.innerHTML=`
            ${c("Izvedeni AES-128 klju\u010D (hex)",o.izvedeni_kljuc)}
            ${c("\u0160ifrat (hex)",k(o.sifrat.hex,96))}
            ${o.ispravno?s("uspjeh","Bob je istim izvedenim klju\u010Dem de\u0161ifrovao poruku \u2014 nijedna strana nije morala unaprijed dijeliti tajnu."):s("greska","De\u0161ifrovanje nije uspjelo.")}
        `}catch(o){n.innerHTML=s("greska",l(p(o)))}finally{i()}});H();})();
