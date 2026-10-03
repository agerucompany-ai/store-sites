// ヘッダー（スクロールで色付き）・スマホメニュー・フェードイン
(function(){
  var h=document.querySelector('.site-header'),nav=h.querySelector('nav'),btn=h.querySelector('.menu-btn');
  function onScroll(){h.classList.toggle('solid',window.scrollY>40)}
  window.addEventListener('scroll',onScroll,{passive:true});onScroll();
  btn.addEventListener('click',function(){nav.classList.toggle('open')});
  nav.querySelectorAll('a').forEach(function(a){a.addEventListener('click',function(){nav.classList.remove('open')})});
  if('IntersectionObserver' in window){
    var io=new IntersectionObserver(function(es){es.forEach(function(e){if(e.isIntersecting){e.target.classList.add('in');io.unobserve(e.target)}})},{threshold:.12});
    document.querySelectorAll('.fade').forEach(function(el){io.observe(el)});
  }else{document.querySelectorAll('.fade').forEach(function(el){el.classList.add('in')})}
})();
