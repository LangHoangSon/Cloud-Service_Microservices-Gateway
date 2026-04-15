# Terminal 1 – Auth Service
cd services/auth_service
pip install -r requirements.txt
python main.py
# → http://localhost:8001

# Terminal 2 – Product Service
cd services/product_service
pip install -r requirements.txt
python main.py
# → http://localhost:8002

<!-- chạy môi trường ảo -->
<!-- python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt -->

<!-- bị lỗi thì hạ bản flask -->
<!-- pip install flask==2.3.2 -->

curl.exe -g -X POST "http://localhost:8000/api/orders" `
-H "Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ1c2VyIjoic29uIiwiZXhwIjoxNzc2MjQxMTIxfQ.twHqXTjnQn5jSaxN1WPBboblZBtDUggTRtdEsiFz7PI" `
-H "Content-Type: application/json" `
-d '{"user":"son","product":"Laptop","price":1000}'