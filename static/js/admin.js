import {root,el,button,link,badge,empty,image,load,all,pagination,table,field,makeForm,editDialog,dialog,mutate,orderTable,api,t,money,date,toast,poll} from './components/ui.js';
import {ordersPage,orderDetail,messagesPage,notificationsPage} from './pages/shared.js';
const page=document.body.dataset.page;
const translatedFields=['uz','ru','en'].map(lang=>({name:'name_'+lang,required:lang==='uz'}));
const checkbox=name=>({name,type:'checkbox'}),number=name=>({name,type:'number',min:0}),decimal=name=>({name,type:'decimal',min:0.01});
async function definitions(kind){
  if(kind==='categories')return {fields:[...translatedFields,{name:'slug',required:true},number('sort_order'),checkbox('is_active'),{name:'image',type:'file'}],columns:[['name',r=>r.name],['slug'],['is_active',r=>badge(r.is_active?'yes':'no')]]};
  if(kind==='products'){
    const categories=await all('admin/categories/');
    return {fields:[...translatedFields,{name:'slug',required:true},{name:'category',type:'select',options:categories.map(c=>[c.id,c.name]),required:true},...['uz','ru','en'].flatMap(lang=>[{name:'short_description_'+lang},{name:'description_'+lang,type:'textarea'}]),{name:'specifications',type:'json'},decimal('default_price'),checkbox('is_active'),checkbox('is_trending')],columns:[['product',r=>el('div',{class:'table-product'},image(r.images[0]?.image,r.name),el('span',{},r.name))],['category',r=>r.category_name],['price',r=>money(r.min_price)],['is_active',r=>badge(r.is_active?'yes':'no')]]};
  }
  const products=await all('admin/products/');
  return {fields:[{name:'product',type:'select',options:products.map(p=>[p.id,p.name]),required:true},{name:'sku',required:true},{name:'attributes',type:'json'},decimal('price'),decimal('compare_at_price'),number('low_stock_threshold'),checkbox('is_active'),{name:'image',type:'file'}],columns:[['sku'],['product',r=>products.find(p=>p.id===r.product)?.name||r.product],['price',r=>money(r.price)],['stock'],['is_active',r=>badge(r.is_active?'yes':'no')]]};
}
async function crud(kind){
  const definition=await definitions(kind),target=el('div'),search=field('search');
  const edit=record=>{const specs=definition.fields.filter(f=>!(record&&f.name==='default_price'));editDialog(record?'edit':'create',specs,record||{is_active:kind!=='products',sort_order:0,low_stock_threshold:5},async values=>{await mutate('admin/'+kind+'/'+(record?record.id+'/':''),values,record?'PATCH':'POST');await refresh();});};
  const toolbar=el('div',{class:'toolbar'},search,button('create',()=>edit(),''));root.replaceChildren(toolbar,target);
  let current='admin/'+kind+'/'+location.search;
  async function refresh(url){if(url)current=url;const data=await api(current);target.replaceChildren(table(data.results,[...definition.columns,['actions',record=>el('div',{class:'table-actions'},button('edit',()=>edit(record)),kind==='products'?button('images',()=>images(record)):null,kind==='products'?link('variants','/admin/variants/?product='+record.id,'button quiet'):null,button(record.is_active?'archive':'activate',async()=>{await mutate('admin/'+kind+'/'+record.id+'/',{is_active:!record.is_active},'PATCH');await refresh();}),button('delete',async()=>{if(confirm(t('confirm'))){await mutate('admin/'+kind+'/'+record.id+'/',undefined,'DELETE');await refresh();}}))]]),pagination(data,refresh));}
  let timer;search.addEventListener('input',()=>{clearTimeout(timer);timer=setTimeout(()=>refresh('admin/'+kind+'/?search='+encodeURIComponent(search.querySelector('input').value)),300);});
  async function images(product){
    const content=el('div');const modal=dialog('images',content);
    const render=async()=>{const current=await api('admin/products/'+product.id+'/');content.replaceChildren(el('div',{class:'image-manager'},current.images.map(img=>el('div',{},image(img.image,current.name),button('delete',async()=>{if(confirm(t('confirm'))){await mutate('admin/images/'+img.id+'/',undefined,'DELETE');await render();await refresh();}})))),makeForm([{name:'image',type:'file',required:true},'alt_uz','alt_ru','alt_en',number('sort_order'),checkbox('is_primary')],{sort_order:0,is_primary:!current.images.length},async data=>{data.append('product',product.id);await mutate('admin/images/',data);await render();await refresh();},'create'));};await render();
  }
  await refresh();
}
async function inventory(){
  const holder=el('div'),movements=el('div');root.replaceChildren(el('div',{class:'toolbar'},button('refresh',()=>refresh()),button('movements',()=>showMovements())),holder,movements);
  async function refresh(url='admin/inventory/') {const data=await api(url);holder.replaceChildren(table(data.results,[['sku'],['price',r=>money(r.price)],['stock'],['low_stock_threshold'],['actions',r=>button('adjust',()=>editDialog('adjust',[{name:'delta',type:'number',required:true},{name:'reason',required:true},{name:'type',type:'select',options:['RESTOCK','ADJUSTMENT','INITIAL']}],{},async data=>{await mutate('admin/inventory/'+r.id+'/adjust/',data);await refresh();}))]]),pagination(data,refresh));}
  async function showMovements(url='admin/inventory/movements/'){const data=await api(url);movements.replaceChildren(el('h2',{},t('movements')),table(data.results,[['date',r=>date(r.created_at)],['sku'],['type',r=>t(r.type)],['delta'],['reason']]),pagination(data,showMovements));}
  await refresh();
}
async function customers(){
  const search=field('search'),holder=el('div');root.replaceChildren(el('div',{class:'toolbar'},search),holder);
  async function details(customer){dialog('profile',el('div',{},el('h3',{},customer.full_name),el('p',{},customer.email),el('p',{},customer.phone),el('p',{},date(customer.date_joined)),link('orders','/admin/orders/?customer='+customer.id,'button')));}
  async function refresh(url='admin/customers/') {const data=await api(url);holder.replaceChildren(table(data.results,[['full_name'],['email'],['phone'],['order_count'],['is_active',c=>badge(c.is_active?'yes':'no')],['actions',c=>el('div',{class:'table-actions'},button('details',()=>details(c)),button(c.is_active?'deactivate':'activate',()=>editDialog(c.is_active?'deactivate':'activate',[{name:'reason',required:true}],{},async values=>{await mutate('admin/customers/'+c.id+'/set-active/',{...values,is_active:!c.is_active});await refresh();})))]]),pagination(data,refresh));}
  let timer;search.addEventListener('input',()=>{clearTimeout(timer);timer=setTimeout(()=>refresh('admin/customers/?search='+encodeURIComponent(search.querySelector('input').value)),300);});await refresh();
}
async function storeSettings(){
  const values=await api('admin/store-settings/');
  const specs=[{name:'name',required:true},{name:'logo',type:'file'},...['uz','ru','en'].map(lang=>({name:'landing_'+lang,type:'textarea'})),{name:'support_phone'},{name:'support_email',type:'email'},{name:'shipping_fee',type:'decimal',min:0},number('default_low_stock_threshold')];
  root.replaceChildren(el('section',{class:'panel narrow'},makeForm(specs,values,async data=>{await mutate('admin/store-settings/',data,'PATCH');})));
}
async function dashboard(){
  const filters=el('form',{class:'filters'},field({name:'date_from',type:'date'}),field({name:'date_to',type:'date'}),field({name:'days',type:'select',options:[['30','30'],['7','7']]}));
  const holder=el('div');root.replaceChildren(filters,holder);
  const refresh=async()=>{const data=await api('admin/dashboard/?'+new URLSearchParams(new FormData(filters)));holder.replaceChildren(
    el('div',{class:'stats-grid'},['revenue','total_orders','new_orders','active_customers','active_products','low_stock_count','unread_messages'].map(key=>el('article',{class:'stat-card'},el('p',{},t(key)),el('strong',{},key==='revenue'?money(data[key]):data[key])))),
    el('section',{class:'panel'},el('h2',{},t('orders')),chart(data.chart,'orders'),el('h2',{},t('revenue')),chart(data.chart,'revenue')),
    el('section',{class:'panel'},el('h2',{},t('recent_orders')),orderTable(data.recent_orders)),
    el('section',{class:'panel'},el('h2',{},t('low_stock')),table(data.low_stock,[['sku'],['stock'],['low_stock_threshold']]),link('inventory','/admin/inventory/','button quiet')));};
  filters.addEventListener('submit',e=>{e.preventDefault();load(holder,refresh);});filters.addEventListener('change',()=>filters.requestSubmit());await refresh();
}
function chart(rows,key){const max=Math.max(1,...rows.map(row=>Number(row[key])));return el('div',{class:'chart',role:'img','aria-label':t(key)},rows.map(row=>el('div',{class:'chart-column',title:row.date+': '+row[key]},el('div',{class:'chart-bar',style:'height:'+Math.max(2,Number(row[key])/max*140)+'px'},el('span',{class:'sr-only'},row.date+': '+row[key])),el('small',{},row.date.slice(8)))));}
const pages={dashboard,products:()=>crud('products'),categories:()=>crud('categories'),variants:()=>crud('variants'),inventory,orders:ordersPage,order_detail:orderDetail,customers,messages:messagesPage,notifications:notificationsPage,settings:storeSettings};
load(root,()=> (pages[page]||dashboard)());
