import {api, showError, toast} from '../api.js';
import {t, money} from '../i18n.js';
export {api, showError, toast, t, money};
export const root = document.getElementById('page-content');
export const lang = document.documentElement.lang;
export const admin = document.body.dataset.section === 'admin_panel';
export const prefix = admin ? 'admin/' : '';
export const params = JSON.parse(document.getElementById('route-params')?.textContent || '{}');
export const date = value => value ? new Date(value).toLocaleString(lang) : '';
export function el(tag, attrs = {}, ...children) {
  const node = document.createElement(tag);
  for (const [key, value] of Object.entries(attrs)) {
    if (key.startsWith('on')) node.addEventListener(key.slice(2), value);
    else if (key === 'class') node.className = value;
    else if (value !== undefined && value !== null && value !== false) {
      if (key in node && !key.startsWith('aria-')) node[key] = value;
      else node.setAttribute(key, value === true ? '' : value);
    }
  }
  for (const child of children.flat(Infinity)) if (child !== null && child !== undefined) node.append(child instanceof Node ? child : document.createTextNode(String(child)));
  return node;
}
export const button = (label, onclick, style='quiet') => el('button', {type:'button', class:style, onclick:async event => {
  const btn = event.currentTarget;
  await busy(btn, async () => { try { await onclick(event); } catch(error) { toast(t(error.data?.code || 'error')); } });
}}, t(label));
export const link = (label, href, style='') => el('a', {href, class:style}, t(label));
export const badge = value => el('span', {class:'badge status-' + value}, t(value));
export const empty = () => el('div', {class:'empty-state'}, el('span', {class:'empty-symbol', 'aria-hidden':'true'}, '\u25a1'), el('p', {}, t('empty')));
export function image(src, alt, className='') {
  return el('img', {src:src || '/static/images/placeholder.svg', alt, class:className, loading:'lazy', width:400, height:400,
    onerror:event => {event.target.onerror=null; event.target.src='/static/images/placeholder.svg';}});
}
export async function busy(btn, task) { btn.disabled=true; try {return await task();} finally {btn.disabled=false;} }
export async function load(target, task) {
  target.replaceChildren(el('p', {class:'loading', role:'status'}, t('loading')));
  try {await task();} catch(error) { const box=el('div',{class:'error',role:'alert'});showError(box,error);target.replaceChildren(box,button('retry',()=>load(target,task))); }
}
export async function all(path) {
  let next=path + (path.includes('?') ? '&' : '?') + 'page_size=48', results=[];
  while(next) {const data=await api(next);results.push(...data.results);next=data.next ? new URL(data.next,location.origin).pathname + new URL(data.next,location.origin).search : null;}
  return results;
}
export function pagination(data, callback) {
  const previous=button('previous',()=>callback(data.previous)),next=button('next',()=>callback(data.next));
  previous.disabled=!data.previous;next.disabled=!data.next;
  return el('div',{class:'pagination'},previous,el('span',{},data.count),next);
}
export function table(rows, columns) {
  if (!rows.length) return empty();
  const body=el('tbody');
  for(const row of rows) body.append(el('tr',{},columns.map(([name,render])=>el('td',{},render ? render(row) : row[name] ?? ''))));
  return el('div',{class:'table-wrap'},el('table',{},el('thead',{},el('tr',{},columns.map(([name])=>el('th',{scope:'col'},t(name))))),body));
}
export function field(spec, value) {
  if(typeof spec === 'string') spec={name:spec};
  const {name,type='text',options,required=false}=spec;
  let input;
  if(type==='select') {
    input=el('select',{name,required});
    for(const option of options || []) {const [v,label]=Array.isArray(option)?option:[option,t(option)]; input.append(el('option',{value:v},label));}
    if(value!==undefined && value!==null)input.value=value;
  } else if(type==='textarea' || type==='json') input=el('textarea',{name,required,rows:type==='json'?3:4,value:type==='json'?JSON.stringify(value || {},null,2):value || ''});
  else input=el('input',{name,type:type==='decimal'?'number':type,required,value:type==='file'||type==='checkbox'?undefined:value??'',checked:type==='checkbox'?!!value:undefined,step:type==='decimal'?'0.01':undefined,min:spec.min,max:spec.max,maxLength:spec.maxLength,accept:type==='file'?'image/png,image/jpeg,image/webp':undefined});
  input.dataset.kind=type;
  const label=el('label',{class:type==='checkbox'?'checkbox':''},t(name),input);
  if(type==='file')label.append(el('small',{},t('image_hint')));
  if(type==='json')label.append(el('small',{},t('json_hint')));
  return label;
}
export function formData(form) {
  const data={}; let files=false;
  for(const input of form.querySelectorAll('[name]')) {
    if(input.disabled)continue;
    const kind=input.dataset.kind;
    if(kind==='file') {if(input.files[0]){data[input.name]=input.files[0];files=true;}continue;}
    data[input.name]=kind==='checkbox'?input.checked:kind==='json'?JSON.parse(input.value || '{}'):kind==='number'?Number(input.value):input.value;
    if(kind==='decimal' && input.value==='')data[input.name]=null;
  }
  if(!files)return data;
  const multipart=new FormData();
  for(const [key,value] of Object.entries(data)) if(value!==null) multipart.append(key,value instanceof File?value:typeof value==='object'?JSON.stringify(value):String(value));
  return multipart;
}
export function makeForm(specs, values, save, label='save') {
  const error=el('div',{class:'error',role:'alert',hidden:true});
  const form=el('form',{class:'data-form'},error,specs.map(spec=>field(spec,values?.[typeof spec==='string'?spec:spec.name])));
  const submit=el('button',{type:'submit'},t(label));form.append(submit);
  form.addEventListener('submit',async event=>{event.preventDefault();error.hidden=true;await busy(submit,async()=>{try{await save(formData(form),form);}catch(exc){showError(error,exc);}});});
  return form;
}
export function dialog(title, content) {
  const titleId='dialog-'+crypto.randomUUID();
  const heading=el('h2',{id:titleId},t(title));
  const modal=el('dialog',{'aria-labelledby':titleId,class:'form-dialog'},el('div',{class:'dialog-heading'},heading,button('close',()=>modal.close())),content);
  document.body.append(modal);modal.addEventListener('close',()=>modal.remove());modal.showModal();return modal;
}
export function editDialog(title,specs,values,save) {
  let modal;
  const form=makeForm(specs,values,async(data)=>{await save(data);toast(t('saved'));modal.close();});
  modal=dialog(title,form);return modal;
}
export async function mutate(path, body, method='POST') {const result=await api(path,{method,body});toast(t('saved'));return result;}
export function poll(task,interval=5000) {
  let timer,stopped=false,delay=interval,running=false;
  const tick=async()=>{clearTimeout(timer);if(stopped || document.hidden || running)return;running=true;try{await task();delay=interval;}catch{delay=Math.min(delay*2,60000);}finally{running=false;if(!stopped && !document.hidden)timer=setTimeout(tick,delay);}};
  const visibility=()=>{clearTimeout(timer);if(!document.hidden)tick();};
  document.addEventListener('visibilitychange',visibility);timer=setTimeout(tick,interval);
  const stop=()=>{stopped=true;clearTimeout(timer);document.removeEventListener('visibilitychange',visibility);};
  window.addEventListener('pagehide',stop,{once:true});return stop;
}
export function productCard(product, favorite=false) {
  const available=product.is_active && product.variants.some(v=>v.is_active && v.stock>0);
  return el('article',{class:'product-card'},linkImage(),el('div',{class:'product-info'},el('p',{class:'category-label'},product.category_name),link(product.name,'/shop/products/'+product.slug+'/','product-name'),el('div',{class:'product-bottom'},el('strong',{},money(product.min_price ?? product.variants[0]?.price ?? 0)),badge(available?'in_stock':'out_of_stock')),favorite?button('remove_favorite',async()=>{await mutate('favorites/'+product.id+'/',undefined,'DELETE');location.reload();}):null));
  function linkImage(){return el('a',{href:'/shop/products/'+product.slug+'/',class:'product-image'},image(product.images[0]?.image,product.name),product.is_trending?el('span',{class:'trend-tag'},t('trending')):null);}
}
export function orderTable(rows) {return table(rows,[['public_number',o=>link(o.public_number,(admin?'/admin/':'/shop/')+'orders/'+o.public_number+'/')],['date',o=>date(o.created_at)],['status',o=>badge(o.status)],['total',o=>money(o.total)],['details',o=>link('details',(admin?'/admin/':'/shop/')+'orders/'+o.public_number+'/')]]);}
