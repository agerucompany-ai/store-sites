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

// トップのスライド：中央に1枚、左右に前後を少し見せる。自動送り・矢印・ドット・スワイプ
(function(){
  var root=document.getElementById('slider');if(!root)return;
  var slides=[].slice.call(root.querySelectorAll('.slide')),n=slides.length,cur=0,timer=null;
  var dots=root.querySelector('.dots');
  slides.forEach(function(_,i){var b=document.createElement('button');b.setAttribute('aria-label',(/^ja/.test(document.documentElement.lang)?(i+1)+'枚目':'Slide '+(i+1)));b.onclick=function(){go(i);restart()};dots.appendChild(b)});
  function layout(){
    var w=slides[0].offsetWidth,gap=parseFloat(getComputedStyle(root).getPropertyValue('--gap'))||24;
    slides.forEach(function(s,i){
      var d=((i-cur)%n+n)%n;if(d>n/2)d-=n;
      s.style.transform='translateX('+(d*(w+gap))+'px) scale('+(d===0?1:.9)+')';
      s.style.opacity=Math.abs(d)>1?0:(d===0?1:.55);
      s.style.zIndex=d===0?3:(Math.abs(d)===1?2:1);
      s.style.pointerEvents=Math.abs(d)<=1?'auto':'none';
      s.setAttribute('aria-hidden',d===0?'false':'true');
    });
    [].forEach.call(dots.children,function(b,i){b.classList.toggle('on',i===cur)});
  }
  function go(i){cur=(i+n)%n;layout()}
  function restart(){clearInterval(timer);timer=setInterval(function(){go(cur+1)},5500)}
  root.querySelector('.prev').onclick=function(){go(cur-1);restart()};
  root.querySelector('.next').onclick=function(){go(cur+1);restart()};
  // 左右に見えている写真を押したら、リンクには飛ばずその写真を中央へ
  slides.forEach(function(s,i){s.addEventListener('click',function(e){if(i!==cur){e.preventDefault();go(i);restart()}})});
  root.addEventListener('mouseenter',function(){clearInterval(timer)});
  root.addEventListener('mouseleave',restart);
  var x0=null;
  root.addEventListener('touchstart',function(e){x0=e.touches[0].clientX},{passive:true});
  root.addEventListener('touchend',function(e){if(x0===null)return;var dx=e.changedTouches[0].clientX-x0;if(Math.abs(dx)>40){go(cur+(dx<0?1:-1));restart()}x0=null},{passive:true});
  window.addEventListener('resize',layout);
  layout();restart();
})();
