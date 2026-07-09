import requests
from PIL import Image
from io import BytesIO

# create a small white PNG
img = Image.new('RGB',(100,100),(255,255,255))
b = BytesIO()
img.save(b, format='PNG')
b.seek(0)
files = {'image': ('test.png', b, 'image/png')}
resp = requests.post('http://127.0.0.1:5000/analyze', files=files)
print('Status:', resp.status_code)
try:
    print(resp.json())
except Exception as e:
    print(resp.text)
