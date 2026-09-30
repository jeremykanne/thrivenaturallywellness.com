(function(){
var d=document,w=window,cfg=w.TNW||{};
function load(src,cb){var s=d.createElement("script");s.src=src;s.async=true;if(cb)s.onload=cb;d.head.appendChild(s);return s}

/* mobile menu */
var mb=d.querySelector(".menu-btn"),nav=d.getElementById("nav");
if(mb&&nav)mb.addEventListener("click",function(){var o=nav.classList.toggle("open");mb.setAttribute("aria-expanded",o)});

/* testimonial sliders: scroll-snap + dots + gentle autoplay */
d.querySelectorAll("[data-slider]").forEach(function(sl){
  var track=sl.querySelector(".slides"),slides=track.children,dots=sl.querySelectorAll(".dots button"),i=0,timer;
  function go(n){i=(n+slides.length)%slides.length;track.scrollTo({left:slides[i].offsetLeft-track.offsetLeft,behavior:"smooth"})}
  function mark(){dots.forEach(function(b,k){b.setAttribute("aria-current",k===i)})}
  dots.forEach(function(b,k){b.addEventListener("click",function(){go(k);stop()})});
  track.addEventListener("scroll",function(){var n=Math.round(track.scrollLeft/track.clientWidth);if(n!==i){i=n;mark()}},{passive:true});
  function start(){if(!w.matchMedia("(prefers-reduced-motion: reduce)").matches&&slides.length>1)timer=setInterval(function(){go(i+1)},7000)}
  function stop(){clearInterval(timer)}
  sl.addEventListener("pointerenter",stop);sl.addEventListener("focusin",stop);
  mark();start();
});

/* Calendly: load only when needed */
var calReady;
function calendly(){
  if(!calReady)calReady=new Promise(function(res){
    var l=d.createElement("link");l.rel="stylesheet";l.href="https://assets.calendly.com/assets/external/widget.css";d.head.appendChild(l);
    load("https://assets.calendly.com/assets/external/widget.js",res);
  });
  return calReady;
}
var embeds=d.querySelectorAll("[data-calendly]");
if(embeds.length&&"IntersectionObserver" in w){
  var io=new IntersectionObserver(function(es){es.forEach(function(e){
    if(!e.isIntersecting)return;io.unobserve(e.target);var el=e.target;
    calendly().then(function(){el.innerHTML="";el.classList.add("loaded");w.Calendly.initInlineWidget({url:el.dataset.calendly,parentElement:el})});
  })},{rootMargin:"400px"});
  embeds.forEach(function(el){io.observe(el)});
}
d.querySelectorAll("[data-calendly-popup]").forEach(function(b){
  b.addEventListener("click",function(){calendly().then(function(){w.Calendly.initPopupWidget({url:b.dataset.calendlyPopup})})});
});

/* analytics: Google tag, Meta pixel, Hotjar — loaded after first interaction or 4s after load */
var started=false;
function track(){
  if(started)return;started=true;
  w.dataLayer=w.dataLayer||[];w.gtag=function(){w.dataLayer.push(arguments)};
  w.gtag("js",new Date());w.gtag("set","linker",{domains:["www.thrivenaturallywellness.com"]});w.gtag("config",cfg.gtag);
  load("https://www.googletagmanager.com/gtag/js?id="+cfg.gtag);
  if(!w.fbq){var n=w.fbq=function(){n.callMethod?n.callMethod.apply(n,arguments):n.queue.push(arguments)};if(!w._fbq)w._fbq=n;n.push=n;n.loaded=true;n.version="2.0";n.queue=[];
    load("https://connect.facebook.net/en_US/fbevents.js");w.fbq("init",cfg.fb);w.fbq("track","PageView")}
  w.hj=w.hj||function(){(w.hj.q=w.hj.q||[]).push(arguments)};w._hjSettings={hjid:cfg.hj,hjsv:6};
  load("https://static.hotjar.com/c/hotjar-"+cfg.hj+".js?sv=6");
}
["pointerdown","keydown","touchstart","scroll"].forEach(function(ev){w.addEventListener(ev,track,{once:true,passive:true})});
w.addEventListener("load",function(){setTimeout(track,4000)});
})();
