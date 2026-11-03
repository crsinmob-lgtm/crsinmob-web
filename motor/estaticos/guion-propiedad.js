(function(){
var RM = matchMedia("(prefers-reduced-motion: reduce)").matches;
var $  = function(s,c){ return (c||document).querySelector(s); };
var $$ = function(s,c){ return [].slice.call((c||document).querySelectorAll(s)); };

/* barra de progreso, encabezado y parallax */
var prog = $("#prog"), hdr = $("#hdr"), last = 0, pars = $$(".par");
function onScroll(){
  var y = scrollY, h = document.body.scrollHeight - innerHeight;
  if (prog) prog.style.transform = "scaleX(" + (h>0 ? y/h : 0) + ")";
  if (hdr){
    hdr.classList.toggle("solid", y > innerHeight*0.6);
    hdr.classList.toggle("up", y > last && y > innerHeight);
  }
  last = y;
  if (RM) return;
  pars.forEach(function(el){
    var b = el.getBoundingClientRect();
    if (b.bottom < -250 || b.top > innerHeight + 250) return;
    var q = (b.top + b.height/2 - innerHeight/2)/innerHeight;
    el.style.transform = "translate3d(0," + (q*(+el.dataset.speed||10)) + "px,0)";
  });
}
addEventListener("scroll", onScroll, {passive:true});
addEventListener("resize", onScroll);
onScroll();

/* apariciones */
var io = new IntersectionObserver(function(es){
  es.forEach(function(e){ if (e.isIntersecting){ e.target.classList.add("in"); io.unobserve(e.target); } });
}, {threshold:.12, rootMargin:"0px 0px -5% 0px"});
$$(".rv,.mask").forEach(function(el){ io.observe(el); });

/* visor de fotos */
var fotos = $$("[data-lb]"), lb = $("#lb"), lbi = $("#lbi"), lbn = $("#lbn"), at = 0;
if (fotos.length && lb){
  var abrir = function(i){
    at = (i + fotos.length) % fotos.length;
    lbi.src = fotos[at].dataset.lb;
    lbn.textContent = ("0"+(at+1)).slice(-2) + " / " + ("0"+fotos.length).slice(-2);
    lb.classList.add("on"); document.body.classList.add("lock");
  };
  var cerrar = function(){ lb.classList.remove("on"); document.body.classList.remove("lock"); };
  fotos.forEach(function(el,i){ el.addEventListener("click", function(e){ e.preventDefault(); abrir(i); }); });
  $(".x", lb).addEventListener("click", cerrar);
  $(".p", lb).addEventListener("click", function(){ abrir(at-1); });
  $(".s", lb).addEventListener("click", function(){ abrir(at+1); });
  lb.addEventListener("click", function(e){ if (e.target === lb) cerrar(); });
  addEventListener("keydown", function(e){
    if (!lb.classList.contains("on")) return;
    if (e.key === "Escape") cerrar();
    if (e.key === "ArrowRight") abrir(at+1);
    if (e.key === "ArrowLeft")  abrir(at-1);
  });
}

/* cursor y botones magnéticos */
if (matchMedia("(hover:hover)").matches && !RM){
  var cu = $("#cur");
  if (cu){
    var cx=0, cy=0, tx=0, ty=0;
    addEventListener("pointermove", function(e){ tx=e.clientX; ty=e.clientY; });
    (function raf(){ cx+=(tx-cx)*.18; cy+=(ty-cy)*.18;
      cu.style.transform="translate("+cx+"px,"+cy+"px) translate(-50%,-50%)"; requestAnimationFrame(raf); })();
    $$("a,button").forEach(function(el){
      el.addEventListener("pointerenter", function(){ cu.classList.add("big"); });
      el.addEventListener("pointerleave", function(){ cu.classList.remove("big"); });
    });
  }
  $$(".mag").forEach(function(el){
    el.addEventListener("pointermove", function(e){
      var r = el.getBoundingClientRect();
      el.style.transform = "translate(" + (e.clientX-r.left-r.width/2)*.3 + "px," + (e.clientY-r.top-r.height/2)*.45 + "px)";
    });
    el.addEventListener("pointerleave", function(){ el.style.transform = ""; });
  });
}

/* videos de YouTube: se cargan al tocarlos */
$$("[data-yt]").forEach(function(el){
  el.addEventListener("click", function(){
    var f = document.createElement("iframe");
    f.src = "https://www.youtube-nocookie.com/embed/" + el.dataset.yt + "?autoplay=1&rel=0";
    f.allow = "accelerometer; autoplay; encrypted-media; gyroscope; picture-in-picture";
    f.allowFullscreen = true;
    el.replaceChildren(f);
  }, {once:true});
});
})();
