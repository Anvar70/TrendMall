export const strings = await fetch('/api/v1/translations/', {cache: 'no-store'}).then(r => r.json());
export const t = key => strings[key] || key;
export const money = value => new Intl.NumberFormat(document.documentElement.lang, {style: 'currency', currency: 'UZS', maximumFractionDigits: 0}).format(value);
