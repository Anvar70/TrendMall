import {root,el,button,link,badge,empty,busy,load,all,pagination,table,field,makeForm,editDialog,mutate,orderTable,api,t,money,date,toast,lang,params,poll,admin,prefix} from '../components/ui.js';

export async function ordersPage(){
  const filters=el('form',{class:'filters'},field('search'),field({name:'status',type:'select',options:[['',t('all')],...['NEW','CONFIRMED','PACKING','SHIPPED','DELIVERED','CANCELLED']]}),field({name:'date_from',type:'date'}),field({name:'date_to',type:'date'}),field({name:'payment_status',type:'select',options:[['',t('all')],'PAID','UNPAID']}));
  const results=el('div');root.replaceChildren(...(admin?[filters]:[]),el('div',{class:'toolbar'},button('refresh',()=>refresh())),results);
  let current=prefix+'orders/'+location.search;
  const refresh=async(url)=>{if(url)current=url;const data=await api(current);results.replaceChildren(orderTable(data.results),pagination(data,next=>refresh(next)));};
  filters.addEventListener('submit',e=>{e.preventDefault();const q=new URLSearchParams(new FormData(filters));refresh(prefix+'orders/?'+q);});
  filters.addEventListener('change',()=>filters.requestSubmit());
  await refresh();if(admin)poll(()=>refresh(),12000);
}
export async function orderDetail(){
  const number=params.public_number;
  const order=await api(prefix+'orders/'+number+'/');
  const address=order.address_snapshot;
  const actions=el('div',{class:'action-row'});
  const change=(status)=>editDialog('status',[{name:'reason',type:'textarea'}],{},async data=>{await mutate(prefix+'orders/'+number+'/'+(admin?'status/':'cancel/'),admin?{...data,status}:data);await orderDetail();});
  if(admin){const transitions={NEW:['CONFIRMED','CANCELLED'],CONFIRMED:['PACKING','CANCELLED'],PACKING:['SHIPPED','CANCELLED'],SHIPPED:['DELIVERED']};for(const status of transitions[order.status]||[])actions.append(button(status,()=>change(status),status==='CANCELLED'?'quiet':''));}
  else{if(order.status==='NEW')actions.append(button('cancel',()=>change('CANCELLED')));actions.append(link('support','/shop/messages/?order='+encodeURIComponent(number),'button quiet'));}
  root.replaceChildren(...(new URLSearchParams(location.search).has('created')?[el('p',{class:'success',role:'status'},t('order_success'))]:[]),
    el('div',{class:'section-heading'},el('h2',{},number),badge(order.status),badge(order.payment_status)),actions,
    el('div',{class:'panel'},table(order.items,[['product',i=>i.product_name_snapshot[lang]||i.product_name_snapshot.uz],['sku',i=>i.sku_snapshot],['variant',i=>Object.values(i.attributes_snapshot).join(' / ')],['price',i=>money(i.unit_price)],['quantity'],['total',i=>money(i.line_total)]])),
    el('div',{class:'two-column'},el('section',{class:'panel'},el('h2',{},t('addresses')),el('p',{},address.recipient_name+' · '+address.phone),el('p',{},[address.region,address.city,address.address_line,address.landmark].filter(Boolean).join(', ')),el('p',{},order.comment),admin?el('p',{},order.customer_name+' · '+order.customer_email):null),
    el('section',{class:'panel'},el('p',{},t('subtotal')+': '+money(order.subtotal)),el('p',{},t('shipping_fee')+': '+money(order.shipping_fee)),el('h2',{},t('total')+': '+money(order.total)),el('p',{},t('cash_on_delivery')))),
    el('section',{class:'panel'},el('h2',{},t('history')),el('ol',{class:'history'},order.history.map(h=>el('li',{},badge(h.new_status),el('span',{},date(h.created_at)),el('p',{},h.reason))))));
}
export async function notificationsPage(url=prefix+'notifications/'){
  const data=await api(url);
  root.replaceChildren(el('div',{class:'toolbar'},button('read_all',async()=>{await mutate(prefix+'notifications/read-all/',{});await notificationsPage();})),
    data.results.length?el('div',{class:'notification-list'},data.results.map(n=>el('article',{class:'panel notification '+(!n.read_at?'unread':'')},
      el('div',{},el('h2',{},t(n.type)),el('p',{},Object.entries(n.data).map(([key,value])=>key==='status'?t(value):value).join(' · ')),el('small',{},date(n.created_at))),
      el('div',{class:'action-row'},link('details',n.internal_target,'button quiet'),!n.read_at?button('mark_read',async()=>{await mutate(prefix+'notifications/'+n.id+'/read/',{});await notificationsPage();}):badge('read'))))):empty(),pagination(data,next=>notificationsPage(next)));
}
export async function settingsPage(){
  const values=await api('settings/');
  const form=makeForm([{name:'preferred_language',type:'select',options:[['uz','O‘zbekcha'],['ru','Русский'],['en','English']]},{name:'marketing_consent',type:'checkbox'}],values,async data=>{await mutate('settings/',data,'PATCH');location.reload();});
  const password=makeForm([{name:'old_password',type:'password',required:true},{name:'new_password',type:'password',required:true}],{},async(data,form)=>{await mutate('auth/change-password/',data);form.reset();},'change_password');
  root.replaceChildren(el('div',{class:'two-column'},el('section',{class:'panel'},form),el('section',{class:'panel'},el('h2',{},t('change_password')),password)));
}
export async function messagesPage(){
  const list=el('div',{class:'conversation-list'}),thread=el('div',{class:'message-thread',role:'log','aria-label':t('messages')});
  const panel=el('section',{class:'chat-panel panel'}),heading=el('h2',{},t('support'));
  let selected=admin?new URLSearchParams(location.search).get('conversation'):null;
  let cursor=0,stop=null,threadVersion=0;
  const input=el('textarea',{name:'body',required:true,maxLength:2000,rows:2,'aria-label':t('body')});
  const order=new URLSearchParams(location.search).get('order');if(order)input.value=t('public_number')+': '+order+'\n';
  const submit=el('button',{type:'submit'},t('send'));
  const sendForm=el('form',{class:'message-form'},input,submit);
  const endpoint=()=>admin?'admin/conversations/'+selected+'/':'conversation/';
  panel.append(heading,thread,sendForm);root.replaceChildren(el('div',{class:admin?'chat-layout':'chat-layout customer-chat'},admin?list:null,panel));
  const add=message=>el('article',{'data-message-id':message.id,'data-created-at':message.created_at,class:'message '+(message.sender_role===(admin?'ADMIN':'CUSTOMER')?'own':'')},el('strong',{},message.sender_name||t('support')),el('p',{class:'preserve-text'},message.body),el('small',{},date(message.created_at)+' · '+t(message.read_at?'read':'unread')));
  async function fetchMessages(){
    if(admin&&!selected)return;
    const version=threadVersion;
    const atBottom=thread.scrollHeight-thread.scrollTop-thread.clientHeight<60;
    let next=endpoint()+'messages/?after_id='+cursor+'&page_size=48';
    while(next){const data=await api(next);if(version!==threadVersion)return;for(const message of data.results){thread.append(add(message));cursor=Math.max(cursor,message.id);}for(const node of thread.querySelectorAll('.message.own')){if(Number(node.dataset.messageId)<=data.read_through)node.querySelector('small').textContent=date(node.dataset.createdAt)+' · '+t('read');}next=data.next?new URL(data.next).pathname+new URL(data.next).search:null;}
    if(cursor&&!document.hidden&&atBottom){thread.scrollTop=thread.scrollHeight;await api(endpoint()+'read/',{method:'POST',body:{last_seen_message_id:cursor}});}
  }
  async function choose(id,name){selected=id;threadVersion++;cursor=0;thread.replaceChildren();heading.textContent=name||t('support');if(stop)stop();sendForm.hidden=false;await fetchMessages();stop=poll(fetchMessages,5000);}
  sendForm.addEventListener('submit',async event=>{event.preventDefault();if(!input.value.trim())return;await busy(submit,async()=>{try{await api(endpoint()+'messages/',{method:'POST',body:{body:input.value}});input.value='';await fetchMessages();}catch(exc){toast(t(exc.data?.code||'error'));}});});
  if(admin){
    const search=field('search'),unread=field({name:'unread',type:'checkbox'}),conversations=el('div');list.append(search,unread,conversations);
    const refresh=async()=>{const q=new URLSearchParams({search:search.querySelector('input').value,unread:unread.querySelector('input').checked});const data=await all('admin/conversations/?'+q);conversations.replaceChildren(...(data.length?data.map(c=>el('button',{class:'conversation '+(String(c.id)===String(selected)?'selected':''),onclick:()=>choose(c.id,c.customer_name)},el('strong',{},c.customer_name),el('span',{},c.last_message||''),el('small',{},date(c.updated_at)),c.unread_count?badge(String(c.unread_count)):null)):[empty()]));};
    let timer;search.addEventListener('input',()=>{clearTimeout(timer);timer=setTimeout(refresh,300);});unread.addEventListener('change',refresh);await refresh();poll(refresh,10000);
    if(selected)await choose(selected);else{thread.append(empty());sendForm.hidden=true;}
  }else await choose(null);
}
