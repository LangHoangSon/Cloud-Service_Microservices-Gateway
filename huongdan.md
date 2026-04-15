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