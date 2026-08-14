import urllib.request, urllib.error
req=urllib.request.Request('http://127.0.0.1:14398/bundle.js')
try:
    resp = urllib.request.urlopen(req)
    print('Error code:', resp.getcode())
    print('Headers:', resp.headers.items())
except urllib.error.HTTPError as e:
    print('Error code:', e.code)
    print('Headers:', e.headers.items())
