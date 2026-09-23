"""Read-only HTTP smoke check for a running local demo (creates only sessions)."""
import json
import os
import sys
from http.cookiejar import CookieJar
from pathlib import Path
from urllib.error import HTTPError
from urllib.parse import urlparse
from urllib.request import build_opener, HTTPCookieProcessor, Request
from dotenv import load_dotenv

BASE = sys.argv[1] if len(sys.argv) > 1 else 'http://127.0.0.1:8000'
if urlparse(BASE).hostname not in ('127.0.0.1', 'localhost'):
    raise SystemExit('Only a local development server is allowed.')
load_dotenv(Path(__file__).resolve().parents[1] / '.env')
opener = build_opener(HTTPCookieProcessor(CookieJar()))
checks = 0


def request(path, data=None, expected=200):
    global checks
    headers = {}
    if data is not None:
        csrf = request('/api/v1/auth/csrf/')['csrfToken']
        headers = {'Content-Type': 'application/json', 'X-CSRFToken': csrf}
    req = Request(BASE + path, data=json.dumps(data).encode() if data is not None else None, headers=headers)
    try:
        response = opener.open(req, timeout=15)
    except HTTPError as error:
        response = error
    body = response.read()
    assert response.status == expected, (path, response.status, expected)
    checks += 1
    if 'application/json' in response.headers.get('Content-Type', ''):
        return json.loads(body)
    assert body or expected == 204, path
    return body


request('/')
request('/api/v1/products/', expected=403)
for role, email, variable, paths in [
    ('customer', 'customer1@trendbox.local', 'DEMO_CUSTOMER_PASSWORD',
     ['home', 'catalog', 'favorites', 'cart', 'checkout', 'orders', 'messages', 'notifications', 'addresses', 'profile', 'settings']),
    ('admin', 'admin@trendbox.local', 'DEMO_ADMIN_PASSWORD',
     ['dashboard', 'products', 'categories', 'variants', 'inventory', 'orders', 'customers', 'messages', 'notifications', 'settings']),
]:
    login = 'admin-login' if role == 'admin' else 'login'
    password = os.environ.get(variable)
    if not password:
        raise SystemExit('Set ' + variable)
    request('/api/v1/auth/' + login + '/', {'email': email, 'password': password})
    for page in paths:
        path = ('/admin/' if role == 'admin' else '/shop/') + ('' if page == 'home' else page + '/')
        html = request(path).decode()
        assert 'id="page-content"' in html and 'id="sidebar"' in html, path
    api_paths = (['admin/dashboard/', 'admin/products/', 'admin/categories/', 'admin/variants/', 'admin/inventory/',
                  'admin/inventory/movements/', 'admin/orders/', 'admin/customers/', 'admin/conversations/', 'admin/notifications/', 'admin/store-settings/']
                 if role == 'admin' else
                 ['products/', 'categories/', 'cart/', 'favorites/', 'orders/', 'addresses/', 'profile/', 'settings/', 'conversation/messages/', 'notifications/'])
    for path in api_paths:
        request('/api/v1/' + path)
    if role == 'customer':
        catalog = request('/api/v1/products/')
        request('/shop/products/' + catalog['results'][0]['slug'] + '/')
    orders = request('/api/v1/' + ('admin/' if role == 'admin' else '') + 'orders/')
    request(('/admin/' if role == 'admin' else '/shop/') + 'orders/' + orders['results'][0]['public_number'] + '/')
    request('/api/v1/auth/logout/', {})
for path in ['/static/css/base.css', '/static/css/shop.css', '/static/js/customer.js', '/static/js/admin.js',
             '/static/js/pages/shared.js', '/static/images/placeholder.svg', '/api/schema/', '/api/docs/']:
    request(path)
print(f'PASS: {checks} local HTTP checks; guest, customer, admin, page routes, API responses and static assets.')

