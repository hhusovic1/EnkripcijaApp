"use strict";(()=>{function t(e){let i=document.getElementById(e);if(!i)throw new Error(`Element #${e} ne postoji u stranici.`);return i}function $(e){return document.getElementById(e)}async function m(e,i={}){let a=await fetch(e,{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify(i)}),o;try{o=await a.json()}catch{throw new Error(`Server je vratio odgovor koji nije JSON (${a.status}).`)}if(!a.ok){let r=o.greska;throw new Error(r??`Gre\u0161ka ${a.status}.`)}return o}function v(e){return e instanceof Error?e.message:String(e)}function c(e){let i=document.createElement("div");return i.textContent=e,i.innerHTML}function n(e,i){return`<div class="par">
        <span class="kljuc">${c(e)}</span>
        <span class="vrijednost">${c(i)}</span>
    </div>`}function l(e,i){return`<div class="poruka ${e}">${i}</div>`}function s(e,i=44){if(e.length<=i)return e;let a=Math.floor(i/2);return`${e.slice(0,a)}\u2026${e.slice(-8)}  (${e.length} cifara)`}function b(){let e=document.querySelectorAll(".tabovi button[data-tab]");e.forEach(i=>{i.addEventListener("click",()=>{e.forEach(o=>o.classList.remove("aktivan")),document.querySelectorAll(".tab-sadrzaj").forEach(o=>o.classList.remove("aktivan")),i.classList.add("aktivan"),document.getElementById(i.dataset.tab??"")?.classList.add("aktivan")})})}function g(e,i="Radim\u2026"){let a=e.innerHTML;return e.disabled=!0,e.innerHTML=`<span class="vrtiljak"></span> ${i}`,()=>{e.disabled=!1,e.innerHTML=a}}b();var j=t("izbor-grupe"),E=t("izbor-scenarija"),M=t("unos-poruke"),f=t("dugme-mitm"),T=t("dugme-mitm-dalje"),L=t("dugme-mitm-sve"),d=null,u=0;function h(){let e=window.GRUPE.find(i=>i.id===j.value);t("opis-grupe").textContent=e?.opis??""}j.addEventListener("change",h);h();function k(){if(!d)return;t("koraci-mitm").innerHTML=d.koraci.slice(0,u).map(a=>`
        <div class="korak ${a.istaknuto?"istaknut":""}">
            <div class="korak-naslov">${a.broj}. ${c(a.naslov)}</div>
            <div class="korak-akter">${c(a.akter)}</div>
            <div class="korak-opis">${c(a.opis)}</div>
            ${a.vrijednosti.map(o=>n(o.kljuc,s(o.vrijednost,60))).join("")}
        </div>
    `).join("");let e=t("traka-mitm");e.classList.remove("skriven"),e.firstElementChild.style.width=`${u/d.koraci.length*100}%`,t("status-mitm").textContent=`Korak ${u} od ${d.koraci.length}`;let i=u>=d.koraci.length;T.classList.toggle("skriven",i),L.classList.toggle("skriven",i),t("zakljucak-mitm").innerHTML=i?H(d):""}function H(e){return e.scenario==="bez_mallory"?l("uspjeh","Alice i Bob su do\u0161li do <strong>iste</strong> tajne, a ona sama nikad nije pro\u0161la kanalom. Prislu\u0161kiva\u010D je vidio p, g, A i B \u2014 i to mu ne poma\u017Ee, jer bi iz A morao izvu\u0107i a, \u0161to je problem diskretnog logaritma."):l("greska","Mallory je pro\u010Ditala poruku koju je Alice smatrala sigurnom, i mogla ju je izmijeniti prije nego stigne Bobu. Ni Alice ni Bob nemaju ni\u0161ta u protokolu \u010Dime bi to primijetili.<br><br><strong>Ono \u0161to je najlak\u0161e previdjeti:</strong> Mallory nikad nije saznala ni <code>a</code> ni <code>b</code>, niti je razbila diskretni logaritam. Vodila je dvije potpuno regularne DH razmjene. Napad ne ru\u0161i matematiku nego <strong>izostanak autentifikacije</strong> \u2014 zato se DH u praksi nikad ne koristi sam, nego uz potpis ili certifikat (STS, TLS).")}f.addEventListener("click",async()=>{let e=g(f,"Pokre\u0107em\u2026");t("zakljucak-mitm").innerHTML="";try{d=await m("/api/mitm",{grupa:j.value,scenario:E.value,poruka:M.value}),u=1,k()}catch(i){t("koraci-mitm").innerHTML=l("greska",c(v(i)))}finally{e()}});T.addEventListener("click",()=>{d&&(u=Math.min(u+1,d.koraci.length),k())});L.addEventListener("click",()=>{d&&(u=d.koraci.length,k())});var z=$("dugme-wiener");function x(e){return e.uspjeh?`
            <div class="korak istaknut">
                <div class="korak-naslov">#${e.broj} \u2014 POGODAK</div>
                ${n("k",s(e.k))}
                ${n("d",s(e.d))}
                ${n("\u03C6(n)",s(e.phi??"\u2014"))}
                ${n("p",s(e.p??"\u2014"))}
                ${n("q",s(e.q??"\u2014"))}
                ${l("uspjeh",c(e.razlog))}
            </div>`:`
        <div class="korak">
            <div class="korak-naslov">#${e.broj} \u2014 odba\u010Deno</div>
            ${n("k",s(e.k,32))}
            ${n("d",s(e.d,32))}
            <div class="prigusen">${c(e.razlog)}</div>
        </div>`}z?.addEventListener("click",async()=>{let e=t("rezultat-wiener"),i=Number(t("izbor-bita").value),a=g(z,"Generi\u0161em klju\u010Deve i napadam\u2026");t("status-wiener").textContent="",e.innerHTML="";try{let o=await m("/api/wiener",{bita:i}),r=o.ranjivi,p=o.normalni;e.innerHTML=`
            <div class="mreza mreza-2">
                <div class="panel">
                    <div class="panel-naslov">Ranjiv klju\u010D</div>
                    <p class="prigusen" style="margin-top:0">
                        d je namjerno izabran malen, radi br\u017Ee dekripcije
                    </p>
                    ${n("n",s(r.n))}
                    ${n("e",s(r.e))}
                    ${n("d (tajni)",s(r.pravi_d))}
                    ${n("d \u2014 broj bita",String(r.d_bita))}
                    ${n("Wienerova granica (bita)",String(r.granica_bita))}
                    ${r.uspjeh?l("greska",`Napad uspio za <strong>${r.trajanje_ms.toFixed(3)} ms</strong> \u2014 pregledano ${r.pregledano} konvergenti.`):l("upozorenje","Napad ovaj put nije uspio \u2014 pokreni ponovo.")}
                </div>
                <div class="panel">
                    <div class="panel-naslov">Normalan klju\u010D</div>
                    <p class="prigusen" style="margin-top:0">
                        e = 65537, d pune du\u017Eine \u2014 kako se radi u praksi
                    </p>
                    ${n("n",s(p.n))}
                    ${n("e",p.e)}
                    ${n("d \u2014 broj bita",String(p.d_bita))}
                    ${n("Ukupno konvergenti",String(p.ukupno_konvergenti))}
                    ${n("Pregledano",String(p.pregledano))}
                    ${p.uspjeh?l("uspjeh",`Napad ne uspijeva, i to za <strong>${p.trajanje_ms.toFixed(3)} ms</strong> \u2014 ostane bez kandidata prije nego i\u0161ta na\u0111e.`):l("greska","Napad je uspio na normalnom klju\u010Du \u2014 to bi bila gre\u0161ka.")}
                </div>
            </div>

            <h2>Kako napad prolazi kroz konvergente</h2>
            <p>
                Iz <code>e\xB7d \u2261 1 (mod \u03C6)</code> slijedi da je <code>k/d</code> jedna od
                konvergenti razvoja <code>e/n</code> u veri\u017Eni razlomak. Napada\u010D ih redom
                isprobava i za svaku provjerava daje li smislen <code>\u03C6</code> \u2014 onaj kod
                kojeg <code>x\xB2 \u2212 (n \u2212 \u03C6 + 1)x + n = 0</code> ima dva cjelobrojna rje\u0161enja.
            </p>
            ${r.koraci.map(x).join("")}

            <h2>Posljedica</h2>
            <div class="panel">
                <p style="margin-top:0">
                    Rekonstruisani <code>d</code> nije samo broj koji se poklapa \u2014 njime se
                    stvarno de\u0161ifruje poruka koju je vlasnik klju\u010Da smatrao sigurnom:
                </p>
                ${n("Poslano",r.poruka)}
                ${n("Napada\u010D pro\u010Ditao",r.procitano??"\u2014")}
                ${n("Rekonstruisani d = pravi d",r.nadjeni_d===r.pravi_d?"da":"ne")}
                ${l("info","<strong>Zaklju\u010Dak (3.3.6):</strong> ranjivost nije u RSA algoritmu nego u izboru parametara. Zato se <code>d</code> uvijek generi\u0161e kao vrijednost uporediva po veli\u010Dini s <code>n</code>, a ubrzanje dekripcije se posti\u017Ee kineskom teoremom o ostacima (CRT), a ne malim eksponentom.")}
            </div>
        `}catch(o){e.innerHTML=l("greska",c(v(o)))}finally{a()}});})();
