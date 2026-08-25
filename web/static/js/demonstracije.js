"use strict";(()=>{function t(e){let n=document.getElementById(e);if(!n)throw new Error(`Element #${e} ne postoji u stranici.`);return n}function z(e){return document.getElementById(e)}async function j(e,n={}){let o=await fetch(e,{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify(n)}),r;try{r=await o.json()}catch{throw new Error(`Server je vratio odgovor koji nije JSON (${o.status}).`)}if(!o.ok){let i=r.greska;throw new Error(i??`Gre\u0161ka ${o.status}.`)}return r}function g(e){return e instanceof Error?e.message:String(e)}function u(e){let n=document.createElement("div");return n.textContent=e,n.innerHTML}function a(e,n){return`<div class="par">
        <span class="kljuc">${u(e)}</span>
        <span class="vrijednost">${u(n)}</span>
    </div>`}function c(e,n){return`<div class="poruka ${e}">${n}</div>`}function l(e,n=44){if(e.length<=n)return e;let o=Math.floor(n/2);return`${e.slice(0,o)}\u2026${e.slice(-8)}  (${e.length} cifara)`}function L(){let e=document.querySelectorAll(".tabovi button[data-tab]");e.forEach(n=>{n.addEventListener("click",()=>{e.forEach(r=>r.classList.remove("aktivan")),document.querySelectorAll(".tab-sadrzaj").forEach(r=>r.classList.remove("aktivan")),n.classList.add("aktivan"),document.getElementById(n.dataset.tab??"")?.classList.add("aktivan")})})}function b(e,n="Radim\u2026"){let o=e.innerHTML;return e.disabled=!0,e.innerHTML=`<span class="vrtiljak"></span> ${n}`,()=>{e.disabled=!1,e.innerHTML=o}}L();var f=t("izbor-grupe"),y=t("izbor-scenarija"),S=t("unos-poruke"),T=t("dugme-mitm"),h=t("dugme-mitm-nazad"),$=t("dugme-mitm-dalje"),H=t("dugme-mitm-sve"),d=null,s=0,k=0,p=!1;function x(){let e=window.GRUPE.find(n=>n.id===f.value);if(!e){t("opis-grupe").innerHTML="";return}t("opis-grupe").innerHTML=`
        <div class="objasnjenje-brojevi">
            <span><strong>p</strong> \u2014 prost broj, ${e.bita} bita</span>
            <span><strong>g</strong> \u2014 generator, ${e.g}</span>
        </div>
        <p>${u(e.opis)}</p>
        <p class="prigusen" style="margin:0">
            p i g su javni: \u0161alju se otvoreno i nisu tajna. Tajni su samo
            eksponenti a i b, koje Alice i Bob nikad ne \u0161alju kanalom.
        </p>`}f.addEventListener("change",x);x();function M(e){return`
        <div class="korak ${e.istaknuto?"istaknut":""}">
            <div class="korak-naslov">
                <span class="korak-oznaka">Korak ${e.broj}</span>
                ${u(e.naslov)}
            </div>
            <div class="korak-akter">${u(e.akter)}</div>
            <div class="korak-opis">${u(e.opis)}</div>
            ${e.vrijednosti.map(n=>a(n.kljuc,l(n.vrijednost,60))).join("")}
        </div>`}function v(){if(!d)return;let e=d.koraci.length,n=s>=e;t("koraci-mitm").innerHTML=p?`<div class="pregled-naslov">Cijela razmjena \u2014 svih ${e} koraka</div>`+d.koraci.map(M).join(""):M(d.koraci[s-1]);let o=t("traka-mitm");o.classList.remove("skriven"),o.firstElementChild.style.width=`${(p?e:s)/e*100}%`,t("status-mitm").textContent=p?`Zavr\u0161eno \u2014 svih ${e} koraka`:`Korak ${s} od ${e}`;let r=t("brojevi-mitm");r.classList.remove("skriven"),r.innerHTML=d.koraci.map(i=>`
        <button type="button" class="korak-broj${!p&&i.broj===s?" aktivan":""}"
                data-korak="${i.broj}" ${i.broj<=k?"":"disabled"}
                title="Korak ${i.broj}: ${u(i.naslov)}">${i.broj}</button>`).join(""),h.classList.toggle("skriven",p||s<=1),$.classList.toggle("skriven",p),$.textContent=n?"Prika\u017Ei sve korake \u25A4":"Sljede\u0107i korak \u25B8",H.classList.toggle("skriven",p||n),t("zakljucak-mitm").innerHTML=n?w(d):""}t("brojevi-mitm").addEventListener("click",e=>{let n=e.target.closest(".korak-broj");!n||n.disabled||(s=Number(n.dataset.korak),p=!1,v())});function w(e){return e.scenario==="bez_mallory"?c("uspjeh","Alice i Bob su do\u0161li do <strong>iste</strong> tajne, a ona sama nikad nije pro\u0161la kanalom. Prislu\u0161kiva\u010D je vidio p, g, A i B \u2014 i to mu ne poma\u017Ee, jer bi iz A morao izvu\u0107i a, \u0161to je problem diskretnog logaritma."):c("greska","Mallory je pro\u010Ditala poruku koju je Alice smatrala sigurnom, i mogla ju je izmijeniti prije nego stigne Bobu. Ni Alice ni Bob nemaju ni\u0161ta u protokolu \u010Dime bi to primijetili.<br><br><strong>Ono \u0161to je najlak\u0161e previdjeti:</strong> Mallory nikad nije saznala ni <code>a</code> ni <code>b</code>, niti je razbila diskretni logaritam. Vodila je dvije potpuno regularne DH razmjene. Napad ne ru\u0161i matematiku nego <strong>izostanak autentifikacije</strong> \u2014 zato se DH u praksi nikad ne koristi sam, nego uz potpis ili certifikat (STS, TLS).")}T.addEventListener("click",async()=>{let e=b(T,"Pokre\u0107em\u2026");t("zakljucak-mitm").innerHTML="";try{d=await j("/api/mitm",{grupa:f.value,scenario:y.value,poruka:S.value}),s=1,k=1,p=!1,v()}catch(n){t("koraci-mitm").innerHTML=c("greska",u(g(n)))}finally{e()}});$.addEventListener("click",()=>{d&&(s>=d.koraci.length?p=!0:(s+=1,k=Math.max(k,s)),v())});h.addEventListener("click",()=>{!d||s<=1||(s-=1,v())});H.addEventListener("click",()=>{d&&(s=d.koraci.length,k=d.koraci.length,v())});var E=z("dugme-wiener");function B(e){return e.uspjeh?`
            <div class="korak istaknut">
                <div class="korak-naslov">#${e.broj} \u2014 POGODAK</div>
                ${a("k",l(e.k))}
                ${a("d",l(e.d))}
                ${a("\u03C6(n)",l(e.phi??"\u2014"))}
                ${a("p",l(e.p??"\u2014"))}
                ${a("q",l(e.q??"\u2014"))}
                ${c("uspjeh",u(e.razlog))}
            </div>`:`
        <div class="korak">
            <div class="korak-naslov">#${e.broj} \u2014 odba\u010Deno</div>
            ${a("k",l(e.k,32))}
            ${a("d",l(e.d,32))}
            <div class="prigusen">${u(e.razlog)}</div>
        </div>`}E?.addEventListener("click",async()=>{let e=t("rezultat-wiener"),n=Number(t("izbor-bita").value),o=b(E,"Generi\u0161em klju\u010Deve i napadam\u2026");t("status-wiener").textContent="",e.innerHTML="";try{let r=await j("/api/wiener",{bita:n}),i=r.ranjivi,m=r.normalni;e.innerHTML=`
            <div class="mreza mreza-2">
                <div class="panel">
                    <div class="panel-naslov">Ranjiv klju\u010D</div>
                    <p class="prigusen" style="margin-top:0">
                        d je namjerno izabran malen, radi br\u017Ee dekripcije
                    </p>
                    ${a("n",l(i.n))}
                    ${a("e",l(i.e))}
                    ${a("d (tajni)",l(i.pravi_d))}
                    ${a("d \u2014 broj bita",String(i.d_bita))}
                    ${a("Wienerova granica (bita)",String(i.granica_bita))}
                    ${i.uspjeh?c("greska",`Napad uspio za <strong>${i.trajanje_ms.toFixed(3)} ms</strong> \u2014 pregledano ${i.pregledano} konvergenti.`):c("upozorenje","Napad ovaj put nije uspio \u2014 pokreni ponovo.")}
                </div>
                <div class="panel">
                    <div class="panel-naslov">Normalan klju\u010D</div>
                    <p class="prigusen" style="margin-top:0">
                        e = 65537, d pune du\u017Eine \u2014 kako se radi u praksi
                    </p>
                    ${a("n",l(m.n))}
                    ${a("e",m.e)}
                    ${a("d \u2014 broj bita",String(m.d_bita))}
                    ${a("Ukupno konvergenti",String(m.ukupno_konvergenti))}
                    ${a("Pregledano",String(m.pregledano))}
                    ${m.uspjeh?c("uspjeh",`Napad ne uspijeva, i to za <strong>${m.trajanje_ms.toFixed(3)} ms</strong> \u2014 ostane bez kandidata prije nego i\u0161ta na\u0111e.`):c("greska","Napad je uspio na normalnom klju\u010Du \u2014 to bi bila gre\u0161ka.")}
                </div>
            </div>

            <h2>Kako napad prolazi kroz konvergente</h2>
            <p>
                Iz <code>e\xB7d \u2261 1 (mod \u03C6)</code> slijedi da je <code>k/d</code> jedna od
                konvergenti razvoja <code>e/n</code> u veri\u017Eni razlomak. Napada\u010D ih redom
                isprobava i za svaku provjerava daje li smislen <code>\u03C6</code> \u2014 onaj kod
                kojeg <code>x\xB2 \u2212 (n \u2212 \u03C6 + 1)x + n = 0</code> ima dva cjelobrojna rje\u0161enja.
            </p>
            ${i.koraci.map(B).join("")}

            <h2>Posljedica</h2>
            <div class="panel">
                <p style="margin-top:0">
                    Rekonstruisani <code>d</code> nije samo broj koji se poklapa \u2014 njime se
                    stvarno de\u0161ifruje poruka koju je vlasnik klju\u010Da smatrao sigurnom:
                </p>
                ${a("Poslano",i.poruka)}
                ${a("Napada\u010D pro\u010Ditao",i.procitano??"\u2014")}
                ${a("Rekonstruisani d = pravi d",i.nadjeni_d===i.pravi_d?"da":"ne")}
                ${c("info","<strong>Zaklju\u010Dak (3.3.6):</strong> ranjivost nije u RSA algoritmu nego u izboru parametara. Zato se <code>d</code> uvijek generi\u0161e kao vrijednost uporediva po veli\u010Dini s <code>n</code>, a ubrzanje dekripcije se posti\u017Ee kineskom teoremom o ostacima (CRT), a ne malim eksponentom.")}
            </div>
        `}catch(r){e.innerHTML=c("greska",u(g(r)))}finally{o()}});})();
