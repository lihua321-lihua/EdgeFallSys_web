import urllib.request, json
# Test login
req = urllib.request.Request(
    'http://127.0.0.1:8000/api/v1/admin/auth/login',
    data=json.dumps({'username':'zhang_grid','password':'123456'}).encode(),
    headers={'Content-Type':'application/json'}
)
resp = urllib.request.urlopen(req)
d = json.loads(resp.read())
print('Login:', d.get('code'), d.get('data',{}).get('user',{}).get('display_name',''))

# Test alerts
token = d['data']['token']
req2 = urllib.request.Request(
    'http://127.0.0.1:8000/api/v1/admin/alerts?status=pending',
    headers={'Authorization': f'Bearer {token}'}
)
resp2 = urllib.request.urlopen(req2)
d2 = json.loads(resp2.read())
print('Alerts:', len(d2.get('data',[])), 'pending')

# Test elders
req3 = urllib.request.Request(
    'http://127.0.0.1:8000/api/v1/admin/elders?page=1&size=10',
    headers={'Authorization': f'Bearer {token}'}
)
resp3 = urllib.request.urlopen(req3)
d3 = json.loads(resp3.read())
print('Elders:', d3.get('data',{}).get('total',0), 'total')
