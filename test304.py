import urllib.request, urllib.error
req=urllib.request.Request('http://127.0.0.1:14398/', headers={'If-None-Match': '"18cba1aac38962ac-500"'})
try:
    urllib.request.urlopen(req)
except urllib.error.HTTPError as e:
    print('Error code:', e.code)
    print('Headers:', e.headers.items())
