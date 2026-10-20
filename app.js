'use strict';
const solutions={growth:{title:'Стратегический консалтинг',description:'Анализ текущей ситуации, оценка альтернатив и формирование обоснованного плана действий.',format:'Стратегическая диагностика и консультационная сессия',service:'strategy'},process:{title:'Бизнес-аналитика и продуктовые решения',description:'Структурирование задачи, исследование процессов, данных и продуктовых гипотез.',format:'Аналитическая диагностика и рекомендации',service:'analytics'},leadership:{title:'Бизнес-психоаналитическое консультирование',description:'Исследование управленческих трудностей, организационных отношений и индивидуальных паттернов.',format:'Индивидуальная консультация или работа с управленческой командой',service:'human'},risk:{title:'Корпоративное право',description:'Выявление правовых вопросов, оценка рисков и определение вариантов правовой поддержки.',format:'Первичный правовой разбор запроса',service:'legal'},market:{title:'Маркетинг и коммуникации',description:'Анализ рынка, позиционирования и возможных направлений маркетингового развития.',format:'Маркетинговая диагностика и стратегическая сессия',service:'marketing'}};
const services={strategy:{title:'Стратегия и управление',intro:'Консультационная работа по стратегическим и управленческим задачам компаний и руководителей.',items:['Разработка и актуализация стратегии','Оценка рыночных сценариев и альтернатив','Стратегические сессии и дорожные карты','Поддержка организационных изменений'],problem:'growth'},analytics:{title:'Продукты и бизнес-аналитика',intro:'Аналитическая поддержка бизнес- и продуктовых решений на основе данных, процессов и гипотез.',items:['Бизнес-анализ и моделирование процессов','Продуктовая стратегия и развитие продукта','Система показателей и аналитика данных','Приоритизация инициатив и оценка гипотез'],problem:'process'},human:{title:'Бизнес-психоаналитическое консультирование',intro:'Индивидуальная и организационная работа с человеческими аспектами управления. Терапевтические услуги рассматриваются отдельно, в рамках квалификации специалиста.',items:['Психодинамика организаций и команд','Лидерство, конфликты и сложные решения','Индивидуальные консультационные запросы','Психоаналитическая работа при наличии соответствующей квалификации'],problem:'leadership'},legal:{title:'Корпоративное право',intro:'Правовое консультирование по вопросам функционирования и развития бизнеса.',items:['Корпоративные вопросы и управление','Договорная работа','Оценка юридических рисков','Правовая поддержка деловых решений'],problem:'risk'},marketing:{title:'Маркетинг и коммуникации',intro:'Исследование рыночного контекста и разработка направлений продвижения и позиционирования.',items:['Маркетинговая стратегия','Анализ рынка и целевой аудитории','Позиционирование и бренд','Цифровые коммуникации и каналы привлечения'],problem:'market'}};
const $=s=>document.querySelector(s);const nav=$('#nav');const toggle=$('#menuToggle');toggle.addEventListener('click',()=>{const open=nav.classList.toggle('open');toggle.setAttribute('aria-expanded',String(open));toggle.setAttribute('aria-label',open?'Закрыть меню':'Открыть меню')});nav.querySelectorAll('a').forEach(a=>a.addEventListener('click',()=>{nav.classList.remove('open');toggle.setAttribute('aria-expanded','false')}));
function currentProblem(){return document.querySelector('input[name="problem"]:checked')?.value||'growth'}function updateResult(){const d=solutions[currentProblem()];$('#resultTitle').textContent=d.title;$('#resultDescription').textContent=d.description;$('#resultFormat').textContent=d.format}document.querySelectorAll('input[name="problem"]').forEach(x=>x.addEventListener('change',updateResult));updateResult();
$('#downloadBrief').addEventListener('click',()=>{const d=solutions[currentProblem()];$('#contactService').value=d.service;const outcome=$('#outcome').value.trim();if(outcome)$('#contactMessage').value=outcome;$('#contact').scrollIntoView({behavior:window.matchMedia('(prefers-reduced-motion: reduce)').matches?'auto':'smooth'});setTimeout(()=>$('#contactMessage').focus({preventScroll:true}),400)});
const dialog=$('#serviceDialog');let selected='strategy';document.querySelectorAll('.service-trigger').forEach(btn=>btn.addEventListener('click',()=>{selected=btn.dataset.service;const d=services[selected];$('#dialogTitle').textContent=d.title;$('#dialogIntro').textContent=d.intro;$('#dialogItems').replaceChildren(...d.items.map(t=>{const li=document.createElement('li');li.textContent=t;return li}));dialog.showModal()}));$('#dialogClose').addEventListener('click',()=>dialog.close());dialog.addEventListener('click',e=>{if(e.target===dialog)dialog.close()});$('#dialogChoose').addEventListener('click',()=>{const input=document.querySelector(`input[name="problem"][value="${services[selected].problem}"]`);input.checked=true;updateResult();dialog.close();$('#navigator').scrollIntoView({behavior:'smooth'})});$('#year').textContent=new Date().getFullYear();


// Application form: submissions require an explicitly configured Formspree endpoint.
// Never claim that a request was sent unless the service returns success.
const contactForm=$('#contactForm'), formStatus=$('#formStatus'), submitBtn=$('#contactSubmit');
contactForm.addEventListener('submit',async(event)=>{
 event.preventDefault();
 formStatus.className='form-status'; formStatus.textContent='';
 if(!contactForm.reportValidity())return;
 const endpoint=(window.SHCHERBININY_CONFIG?.formEndpoint||'').trim();
 if(!/^https:\/\/formspree\.io\/f\/[a-zA-Z0-9]+$/.test(endpoint)){
   formStatus.textContent='Приём обращений пока настраивается. Форма заполнена, но данные не отправлены. Пожалуйста, не закрывайте страницу до подключения канала связи.';
   formStatus.classList.add('is-warning');return;
 }
 submitBtn.disabled=true;submitBtn.setAttribute('aria-busy','true');
 const payload=new FormData(contactForm);
 payload.append('_subject','Новая заявка — Щербинины');
 try{
   const response=await fetch(endpoint,{method:'POST',body:payload,headers:{Accept:'application/json'}});
   if(!response.ok)throw new Error('HTTP '+response.status);
   contactForm.reset();
   formStatus.textContent='Спасибо. Обращение отправлено. Мы свяжемся с вами по указанному адресу.';
   formStatus.classList.add('is-success');
 }catch(error){
   formStatus.textContent='Не удалось отправить обращение. Проверьте соединение и повторите попытку. Введённые данные сохранены в форме.';
   formStatus.classList.add('is-warning');
 }finally{submitBtn.disabled=false;submitBtn.removeAttribute('aria-busy')}
});
const revealTargets=document.querySelectorAll('.section-heading,.service-card,.editorial-content,.about-grid,.contact-grid');
if('IntersectionObserver'in window && !window.matchMedia('(prefers-reduced-motion: reduce)').matches){
 const observer=new IntersectionObserver(entries=>{entries.forEach(e=>{if(e.isIntersecting){e.target.classList.add('is-visible');observer.unobserve(e.target)}})},{threshold:.1});
 revealTargets.forEach(el=>{el.classList.add('reveal');observer.observe(el)});
}
