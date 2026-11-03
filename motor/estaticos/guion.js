(function(){
/* Candado: si por lo que sea el guion se carga dos veces, la segunda no hace
   nada. Dos copias corriendo a la vez peleaban por el audio y lo arrancaban
   dos veces. */
if (window.__crsinmob) return;
window.__crsinmob = true;

var RM = matchMedia("(prefers-reduced-motion: reduce)").matches;
var $ = function(s,c){ return (c||document).querySelector(s); };
var $$ = function(s,c){ return [].slice.call((c||document).querySelectorAll(s)); };

/* ---- titular letra por letra ---- */
var chIdx = 0;
$$("[data-split]").forEach(function(el){
  var nodes = [].slice.call(el.childNodes);
  el.innerHTML = "";
  function put(text, host){
    text.split(/(\s+)/).forEach(function(tok){
      if (!tok) return;
      if (/^\s+$/.test(tok)){ host.appendChild(document.createTextNode(" ")); return; }
      var w = document.createElement("span"); w.className = "w";
      tok.split("").forEach(function(c){
        var sp = document.createElement("span");
        sp.className = "ch"; sp.style.transitionDelay = (chIdx*0.018)+"s";
        sp.textContent = c; chIdx++; w.appendChild(sp);
      });
      host.appendChild(w);
    });
  }
  nodes.forEach(function(n){
    if (n.nodeType === 3) put(n.textContent, el);
    else { var em = document.createElement("em"); el.appendChild(em); put(n.textContent, em); }
  });
});

/* ---- párrafo editorial: palabra por palabra ---- */
$$("[data-words]").forEach(function(el){
  var nodes = [].slice.call(el.childNodes), i = 0;
  el.innerHTML = "";
  function put(text, italic){
    text.split(/(\s+)/).forEach(function(tok){
      if (!tok || /^\s+$/.test(tok)) { if (tok) el.appendChild(document.createTextNode(" ")); return; }
      var w = document.createElement("span");
      w.className = "wd"; w.style.transitionDelay = (i*0.055)+"s"; i++;
      if (italic){ var em = document.createElement("em"); em.textContent = tok; w.appendChild(em); }
      else w.textContent = tok;
      el.appendChild(w);
    });
  }
  nodes.forEach(function(n){ put(n.textContent, n.nodeType !== 3); });
});

/* ---- precarga ---- */
var pre = $("#pre"), pct = $("#pct"), pbar = $("#pbar"), hero = $("#hero"), vid = $("#vid");
var aIntro = $("#aIntro"), flash = $("#flash");

/* Reproduce con sonido e insiste: el primer intento suele rechazarse unos
   milisegundos antes de que el navegador lo permita. Si de plano lo bloquea,
   arranca en silencio (eso sí se permite) y se le quita el silencio en cuanto
   el visitante toca, hace clic o escribe: no hay ningún botón que apretar. */
function play(a, vol, insistir){
  var t0 = Date.now(), ventana = insistir || 2600;
  (function go(){
    if (!a.paused && !a.muted) return;
    a.muted = false;
    if (vol != null) a.volume = vol;
    var pr = a.play();
    if (!pr || !pr.catch) return;
    pr.catch(function(){
      if (Date.now() - t0 < ventana) return setTimeout(go, 220);
      a.muted = true; a.play().catch(function(){}); armar();
    });
  })();
}
var armado = false;
function armar(){
  if (armado) return; armado = true;
  var ev = ["pointerdown","touchstart","touchend","keydown","click","wheel","scroll"];
  var abrir = function(){
    if (aIntro) aIntro.muted = false;
    aud.muted = false;
    if (aud.paused && pre.classList.contains("go")) amb(true);
    if (!aud.muted && !aud.paused) ev.forEach(function(e){ removeEventListener(e, abrir); });
  };
  ev.forEach(function(e){ addEventListener(e, abrir, {passive:true}); });
}
armar();
try { aud.load(); } catch (err) {}

/* La pantalla de carga solo sale mientras el sitio carga de verdad, y una
   sola vez por visita: si el visitante va a una propiedad y regresa, ya no
   vuelve a aparecer. */
var YA_VISTA = false;
try { YA_VISTA = sessionStorage.getItem("crs-intro") === "1"; } catch (err) {}

var MIN = 900, MAX = 6500, arranque = Date.now(), cargado = false, tick = null;

/* Si el navegador deja sonar la intro, le damos aire para que se escuche;
   si la bloquea, no tiene caso esperar y entramos en cuanto cargue. */
function minimoReal(){
  var sonando = aIntro && !aIntro.paused && !aIntro.muted && aIntro.currentTime > 0.15;
  return sonando ? 2600 : MIN;
}

function marcar(){ try { sessionStorage.setItem("crs-intro", "1"); } catch (err) {} }

function entrar(){
  pre.classList.add("go"); hero.classList.add("go");
  setTimeout(function(){ pre.style.display = "none"; }, 1900);
  marcar();
  if (aIntro && !aIntro.paused){
    var fo = setInterval(function(){
      aIntro.volume = Math.max(0, aIntro.volume - .05);
      if (aIntro.volume <= 0){ clearInterval(fo); aIntro.pause(); } }, 110);
  }
  arrancaHero();
  setTimeout(function(){ if (typeof amb === "function") amb(true); }, 250);
}
function done(){ entrar(); }

function arrancaHero(){
  if (vid && !RM){
    vid.classList.add("in2");
    try { vid.playbackRate = .62; } catch (err) {}
    vid.play().catch(function(){});
  }
}

function saltar(){
  if (tick) clearInterval(tick);
  pre.style.display = "none";
  hero.classList.add("go");
  marcar();
  arrancaHero();
  setTimeout(function(){ if (typeof amb === "function") amb(true); }, 300);
}

if (RM || YA_VISTA){
  saltar();
} else {
  if (document.readyState === "complete") cargado = true;
  else addEventListener("load", function(){ cargado = true; });

  if (aIntro) play(aIntro, 0.65, 2600);

  tick = setInterval(function(){
    var t = Date.now() - arranque;
    var p = cargado ? 100 : Math.min(94, (t / MAX) * 100 + 6);
    pct.textContent = Math.round(p);
    pbar.style.setProperty("--p", p / 100);
    if ((cargado && t >= minimoReal()) || t >= MAX){
      clearInterval(tick); tick = null;
      pct.textContent = 100; pbar.style.setProperty("--p", 1);
      setTimeout(done, 280);
    }
  }, 60);
}

/* ---- el video se disuelve y vuelve a empezar ---- */
if (vid && !RM){
  vid.addEventListener("ended", function(){
    vid.classList.add("rew");
    if (flash){ flash.classList.remove("on"); void flash.offsetWidth; flash.classList.add("on"); }
    setTimeout(function(){
      try { vid.currentTime = 0; } catch(e){}
      vid.play().catch(function(){});
      vid.classList.remove("rew");
    }, 820);
  });
}

/* ---- marquesinas ---- */
$$("[data-marq]").forEach(function(m){
  var items = m.dataset.marq.split("|"), h = "";
  for (var r=0; r<2; r++) items.forEach(function(x){ h += "<span>"+x+"</span>"; });
  m.innerHTML = h;
});

/* ---- scroll ---- */
var prog = $("#prog"), hdr = $("#hdr"), last = 0;
var pars = $$(".par"), hin = $("#hin"), hbg = $("#hbg");
function onScroll(){
  var y = scrollY, h = document.body.scrollHeight - innerHeight;
  prog.style.transform = "scaleX(" + (h>0 ? y/h : 0) + ")";
  hdr.classList.toggle("solid", y > innerHeight*0.72);
  hdr.classList.toggle("up", y > last && y > innerHeight);
  last = y;
  if (RM) return;
  /* hero: el texto sube y se desvanece */
  if (y < innerHeight*1.2){
    var k = Math.min(1, y/innerHeight);
    hin.style.transform = "translate3d(0," + (k*-90) + "px,0)";
    hin.style.opacity = String(1 - k*1.25);
    hbg.style.transform = "scale(" + (1 + k*0.14) + ")";
  }
  pars.forEach(function(el){
    var b = el.getBoundingClientRect();
    if (b.bottom < -250 || b.top > innerHeight + 250) return;
    var q2 = (b.top + b.height/2 - innerHeight/2)/innerHeight;
    el.style.transform = "translate3d(0," + (q2*(+el.dataset.speed||10)) + "px,0)";
  });
}
addEventListener("scroll", onScroll, {passive:true});
addEventListener("resize", onScroll);
addEventListener("load", onScroll);
onScroll();

/* ---- apariciones ---- */
var io = new IntersectionObserver(function(es){
  es.forEach(function(e){ if (e.isIntersecting){ e.target.classList.add("in"); io.unobserve(e.target); } });
}, {threshold:.15, rootMargin:"0px 0px -6% 0px"});
$$(".rv,.mask,.edi").forEach(function(el){ io.observe(el); });

/* ---- contadores ---- */
var cio = new IntersectionObserver(function(es){
  es.forEach(function(e){
    if (!e.isIntersecting) return; cio.unobserve(e.target);
    if (RM) return;
    var el = e.target, to = parseFloat(el.dataset.to), dec = +(el.dataset.dec||0);
    var pre2 = el.dataset.pre||"", suf = el.dataset.suf||"", raw = "raw" in el.dataset, t0 = null;
    requestAnimationFrame(function f(t){
      t0 = t0 || t; var k = Math.min(1,(t-t0)/1500), v = to*(1-Math.pow(1-k,3));
      el.textContent = pre2 + (raw ? Math.round(v) : v.toLocaleString("en-US",{minimumFractionDigits:dec,maximumFractionDigits:dec})) + suf;
      if (k < 1) requestAnimationFrame(f);
    });
  });
}, {threshold:.5});
$$("[data-to]").forEach(function(el){ cio.observe(el); });

/* ---- carrusel ---- */
var car = $("#car"), bar = $("#cbar"), cnt = $("#ccnt");
if (car && bar && cnt){
function stepW(){ var c = car.querySelector(".prop"); return c ? c.offsetWidth + 24 : 400; }
var NPROP = Math.max(1, car.querySelectorAll(".prop").length);
bar.style.width = (100/NPROP) + "%";
function sync(){
  var max = car.scrollWidth - car.clientWidth, q = max>0 ? car.scrollLeft/max : 0;
  bar.style.transform = "translateX(" + (q*(NPROP-1)*100) + "%)";
  cnt.textContent = ("0"+(Math.round(q*(NPROP-1))+1)).slice(-2) + " / " + ("0"+NPROP).slice(-2);
}
car.addEventListener("scroll", sync, {passive:true}); sync();
$("#next").addEventListener("click", function(){ car.scrollBy({left:stepW(), behavior:"smooth"}); });
$("#prev").addEventListener("click", function(){ car.scrollBy({left:-stepW(), behavior:"smooth"}); });
var dn=false, sx=0, sl=0, mv=0;
car.addEventListener("pointerdown", function(e){ dn=true; mv=0; sx=e.clientX; sl=car.scrollLeft; car.classList.add("drag"); });
addEventListener("pointerup", function(){ if(dn){ dn=false; car.classList.remove("drag"); } });
car.addEventListener("pointermove", function(e){ if(!dn) return; var d=e.clientX-sx; mv+=Math.abs(d); car.scrollLeft=sl-d; });
car.addEventListener("click", function(e){ if (mv>24) e.preventDefault(); }, true);
}

/* ---- música de fondo: automática, sin controles ---- */
var aud = $("#aud"), fade = null, MAXV = .42;
function amb(on){
  if (!on || RM) return;
  clearInterval(fade);
  if (aud.paused || aud.muted){ aud.volume = 0; play(aud, 0, 6000); }
  fade = setInterval(function(){
    aud.volume = Math.min(MAXV, aud.volume + .015);
    if (aud.volume >= MAXV) clearInterval(fade); }, 90);
}

/* ---- cursor, inclinación y botones magnéticos ---- */
if (matchMedia("(hover:hover)").matches && !RM){
  var cu = $("#cur"), cx=0, cy=0, tx=0, ty=0;
  addEventListener("pointermove", function(e){ tx=e.clientX; ty=e.clientY; });
  (function raf(){ cx+=(tx-cx)*.18; cy+=(ty-cy)*.18; cu.style.transform="translate("+cx+"px,"+cy+"px) translate(-50%,-50%)"; requestAnimationFrame(raf); })();
  $$("a,button").forEach(function(el){
    el.addEventListener("pointerenter", function(){ cu.classList.add("big"); });
    el.addEventListener("pointerleave", function(){ cu.classList.remove("big"); });
  });
  $$(".mag").forEach(function(el){
    el.addEventListener("pointermove", function(e){
      var r = el.getBoundingClientRect();
      el.style.transform = "translate(" + (e.clientX-r.left-r.width/2)*.3 + "px," + (e.clientY-r.top-r.height/2)*.45 + "px)";
    });
    el.addEventListener("pointerleave", function(){ el.style.transform = ""; });
  });
  $$(".tilt").forEach(function(el){
    el.addEventListener("pointermove", function(e){
      var r = el.getBoundingClientRect();
      var rx = ((e.clientY-r.top)/r.height - .5) * -7, ry = ((e.clientX-r.left)/r.width - .5) * 7;
      el.style.transform = "perspective(800px) rotateX("+rx+"deg) rotateY("+ry+"deg) translateY(-5px)";
    });
    el.addEventListener("pointerleave", function(){ el.style.transform = ""; });
  });
}
})();
