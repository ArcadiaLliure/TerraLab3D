import urllib.request, urllib.error
req=urllib.request.Request('http://127.0.0.1:14398/bundle.js_NO_EXISTE')
try:
    urllib.request.urlopen(req)
except urllib.error.HTTPError as e:
    print('Error code:', e.code)
    print('Headers:', e.headers.items())
