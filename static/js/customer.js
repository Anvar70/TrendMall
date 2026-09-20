import {root,el,button,link,badge,empty,image,busy,load,all,pagination,table,field,makeForm,editDialog,dialog,mutate,productCard,orderTable,api,t,money,date,toast,lang,params,poll} from './components/ui.js';
import {ordersPage,orderDetail,messagesPage,notificationsPage,settingsPage} from './pages/shared.js';
const page=document.body.dataset.page;
const addressFields=['label','recipient_name','phone','region','city','address_line','landmark'].map(name=>({name,required:name!=='landmark'})).concat({name:'is_default',type:'checkbox'});

async function home(){
  const [categories,trend,latest]=await Promise.all([api('categories/?page_size=6'),api('products/?trending=true&page_size=4'),api('products/?page_size=8')]);
  root.replaceChildren(el('section',{class:'shop-banner'},el('div',{},el('p',{class:'eyebrow'},'TRENDBOX'),el('h2',{},t('shop_intro')),link('browse_catalog','/shop/catalog/','button')),el('span',{'aria-hidden':'true',class:'banner-symbol'},'\u2197')),
    el('div',{class:'category-chips'},categories.results.map(c=>link(c.name,'/shop/catalog/?category='+c.id,'chip'))));
  for(const [key,data] of [['trending',trend],['new_arrivals',latest]])root.append(el('section',{class:'product-section'},el('div',{class:'section-heading'},el('h2',{},t(key)),link('all','/shop/catalog/')),data.results.length?el('div',{class:'product-grid'},data.results.map(p=>productCard(p))):empty()));
}
async function catalog(){
  const categories=await all('categories/');
  const query=new URLSearchParams(location.search);
  const filters=el('form',{class:'filters'},
    field({name:'search'},query.get('search')),
    field({name:'category',type:'select',options:[['',t('all')],...categories.map(c=>[c.id,c.name])]},query.get('category')),
    field({name:'min_price',type:'number',min:0},query.get('min_price')),
    field({name:'max_price',type:'number',min:0},query.get('max_price')),
    field({name:'ordering',type:'select',options:[['new',t('new')],['price',t('price_asc')],['-price',t('price_desc')],['name',t('name')]]},query.get('ordering')||'new'),
    field({name:'in_stock',type:'checkbox'},query.get('in_stock')==='true'),field({name:'trending',type:'checkbox'},query.get('trending')==='true'));
  const results=el('div');root.replaceChildren(filters,results);
  let sequence=0,timer;
  async function fetchProducts(pageUrl){
    const current=++sequence;let search;
    if(pageUrl)search=new URL(pageUrl,location.origin).search.slice(1);
    else{const q=new URLSearchParams();for(const input of filters.querySelectorAll('[name]')){if(input.type==='checkbox'){if(input.checked)q.set(input.name,'true');}else if(input.value)q.set(input.name,input.value);}search=q.toString();}
    history.replaceState({},'',location.pathname+(search?'?'+search:''));
    results.setAttribute('aria-busy','true');
    try{const data=await api('products/?'+search);if(current!==sequence)return;results.replaceChildren(data.results.length?el('div',{class:'product-grid'},data.results.map(p=>productCard(p))):empty(),pagination(data,fetchProducts));}
    catch(exc){if(current===sequence){results.replaceChildren(el('p',{class:'error'},t('error')),button('retry',()=>fetchProducts()));}}
    finally{if(current===sequence)results.removeAttribute('aria-busy');}
  }
  filters.addEventListener('submit',event=>{event.preventDefault();fetchProducts();});
  filters.addEventListener('input',()=>{clearTimeout(timer);timer=setTimeout(()=>fetchProducts(),300);});
  await fetchProducts(location.href);
}
async function product(){
  const p=await api('products/'+params.slug+'/');
  const variants=p.variants.filter(v=>v.is_active);
  const hero=image(p.images[0]?.image,p.name,'detail-image');
  const gallery=el('div',{class:'product-gallery'},hero,el('div',{class:'thumbnails'},p.images.map(img=>el('button',{type:'button',class:'thumbnail',onclick:()=>hero.src=img.image},image(img.image,img['alt_'+lang]||p.name)))));
  const selector=el('select',{'aria-label':t('choose_variant')},el('option',{value:''},t('choose_variant')),variants.map(v=>el('option',{value:v.id},Object.entries(v.attributes).map(([k,value])=>k+': '+value).join(' / ') || v.sku)));
  const quantity=el('input',{type:'number',min:1,value:1,'aria-label':t('quantity')});
  const price=el('div',{class:'detail-price'}),stock=el('p');
  const add=button('add_cart',async()=>{await mutate('cart/items/',{variant:Number(selector.value),quantity:Number(quantity.value)});},'');add.disabled=true;
  function update(){const v=variants.find(v=>v.id===Number(selector.value));price.replaceChildren(v?el('strong',{},money(v.price)):el('span',{},money(p.min_price)));if(v?.compare_at_price)price.append(el('del',{},money(v.compare_at_price)));stock.textContent=v?t('stock')+': '+v.stock:'';quantity.max=v?.stock||1;quantity.value=1;add.disabled=!v||v.stock<1;if(v?.image)hero.src=v.image;}
  selector.addEventListener('change',update);if(variants.length===1)selector.value=variants[0].id;update();
  root.replaceChildren(el('div',{class:'product-detail'},gallery,el('section',{class:'product-copy'},el('p',{class:'eyebrow'},p.category_name),el('h2',{},p.name),el('p',{},p.short_description),price,el('label',{},t('variant'),selector),stock,el('label',{},t('quantity'),quantity),el('div',{class:'action-row'},add,button('add_favorite',()=>mutate('favorites/',{product:p.id}))),el('p',{},t('cash_on_delivery')))),el('section',{class:'panel'},el('h2',{},p.name),el('p',{class:'preserve-text'},p.description),table(Object.entries(p.specifications).map(([key,value])=>({key,value})),[['specifications',r=>r.key],['details',r=>typeof r.value==='object'?(r.value[lang]||r.value.uz||JSON.stringify(r.value)):r.value]])));
}
async function favorites(url='favorites/') {const data=await api(url);root.replaceChildren(data.results.length?el('div',{class:'product-grid'},data.results.map(f=>productCard(f.product,true))):empty(),pagination(data,next=>load(root,()=>favorites(next))));}
async function cart(){
  const data=await api('cart/');if(!data.items.length){root.replaceChildren(empty(),link('browse_catalog','/shop/catalog/','button'));return;}
  const rows=data.items.map(item=>el('article',{class:'cart-row'},image(item.image,item.name),el('div',{},link(item.name,'/shop/products/'+item.slug+'/','product-name'),el('p',{},item.sku),!item.available?badge('not_available'):null,item.price_changed?badge('price_changed'):null),el('strong',{},money(item.price)),el('input',{type:'number',min:1,max:item.stock||1,value:item.quantity,'aria-label':t('quantity'),onchange:async e=>{try{await mutate('cart/items/'+item.id+'/',{quantity:Number(e.target.value)},'PATCH');await cart();}catch{toast(t('conflict'));e.target.value=item.quantity;}}}),el('strong',{},money(item.line_total)),button('delete',async()=>{if(confirm(t('confirm'))){await mutate('cart/items/'+item.id+'/',undefined,'DELETE');await cart();}})));
  root.replaceChildren(el('div',{class:'panel cart-list'},rows),el('section',{class:'cart-summary panel'},el('h2',{},t('subtotal')+': '+money(data.subtotal)),data.items.every(i=>i.available)?link('checkout','/shop/checkout/','button'):el('p',{class:'error'},t('unavailable_cart'))));
}
async function addresses(){
  const data=await all('addresses/');
  const edit=address=>editDialog(address?'edit':'new_address',addressFields,address,async values=>{await mutate('addresses/'+(address?address.id+'/':''),values,address?'PATCH':'POST');await addresses();});
  const cards = data.map(a => el('article', {class:'panel'},
    el('h2', {}, a.label), a.is_default ? badge('is_default') : null,
    el('p', {}, a.recipient_name + ' · ' + a.phone),
    el('p', {}, [a.region,a.city,a.address_line,a.landmark].filter(Boolean).join(', ')),
    el('div', {class:'action-row'}, button('edit', () => edit(a)),
      !a.is_default ? button('set_default', async () => { await mutate('addresses/'+a.id+'/set-default/',{}); await addresses(); }) : null,
      button('delete', async () => { if(confirm(t('confirm'))) { await mutate('addresses/'+a.id+'/',undefined,'DELETE'); await addresses(); } }))));
  root.replaceChildren(el('div',{class:'toolbar'},button('new_address',()=>edit(),'')), data.length ? el('div',{class:'address-grid'},cards) : empty());
}
async function profile(){
  const user=await api('profile/');
  const form=makeForm([{name:'full_name',required:true},{name:'phone',required:true},{name:'avatar',type:'file'}],user,async data=>{await mutate('profile/',data,'PATCH');await profile();});
  root.replaceChildren(el('section',{class:'panel narrow'},image(user.avatar,user.full_name,'profile-avatar'),el('p',{},t('email')+': '+user.email),el('p',{},t('date_joined')+': '+date(user.date_joined)),form));
}
async function checkoutPage(){
  const [addresses,user,cart]=await Promise.all([all('addresses/'),api('auth/me/'),api('cart/')]);
  const key='trendbox-checkout-'+user.id;
  let pending;try{pending=JSON.parse(sessionStorage.getItem(key)||'null');}catch{pending=null;}
  if(!cart.items.length && !pending){root.replaceChildren(empty(),link('cart','/shop/cart/','button'));return;}
  const select=field({name:'address_id',type:'select',options:[['new',t('new_address')],...addresses.map(a=>[a.id,a.label+' · '+a.address_line])]},addresses.find(a=>a.is_default)?.id || 'new');
  const addressInputs=el('div',{class:'form-grid'},addressFields.filter(f=>!['label','is_default'].includes(f.name)).map(f=>field(f)));
  const form=el('form',{class:'panel'},select,addressInputs,field({name:'comment',type:'textarea'}),el('p',{},t('cash_on_delivery')));
  const previewButton=el('button',{type:'submit'},t('preview'));form.append(previewButton);
  const summary=el('section',{class:'panel checkout-summary'});root.replaceChildren(el('div',{class:'checkout-grid'},form,summary));
  const chosen=select.querySelector('select');
  function toggle(){addressInputs.hidden=chosen.value!=='new';for(const input of addressInputs.querySelectorAll('input'))input.disabled=addressInputs.hidden;}
  chosen.addEventListener('change',toggle);toggle();
  function invalidate(){pending=null;sessionStorage.removeItem(key);summary.replaceChildren();}
  form.addEventListener('input',invalidate);
  function renderQuote(quote){summary.replaceChildren(el('h2',{},t('preview')),el('p',{},t('subtotal')+': '+money(quote.subtotal)),el('p',{},t('shipping_fee')+': '+money(quote.shipping_fee)),el('strong',{class:'order-total'},t('total')+': '+money(quote.total)),el('p',{},[quote.address.recipient_name,quote.address.phone,quote.address.region,quote.address.city,quote.address.address_line].join(', ')),button('place_order',async()=>{
    try{const order=await api('orders/',{method:'POST',body:pending.payload});sessionStorage.removeItem(key);location.assign('/shop/orders/'+order.public_number+'/?created=1');}
    catch(exc){if(exc.status===409){invalidate();toast(t('conflict'));}else toast(t('error'));}
  },''));}
  if(pending){renderQuote(pending.quote);}
  form.addEventListener('submit',async event=>{event.preventDefault();await busy(previewButton,async()=>{try{
    const data={comment:form.querySelector('[name=comment]').value};
    if(chosen.value==='new'){data.address={};for(const input of addressInputs.querySelectorAll('[name]'))data.address[input.name]=input.value;}else data.address_id=Number(chosen.value);
    const quote=await api('checkout/preview/',{method:'POST',body:data});
    pending={payload:{...data,quote_token:quote.quote_token,idempotency_key:crypto.randomUUID()},quote};sessionStorage.setItem(key,JSON.stringify(pending));renderQuote(quote);
  }catch(exc){toast(t(exc.data?.code||'error'));}});});
}
const pages={home,catalog,product_detail:product,favorites,cart,addresses,profile,checkout:checkoutPage,orders:ordersPage,order_detail:orderDetail,messages:messagesPage,notifications:notificationsPage,settings:settingsPage,order_success:ordersPage};
load(root,()=> (pages[page]||home)());
