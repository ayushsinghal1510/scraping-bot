FROM python:3.10.10-slim

WORKDIR /app

COPY . .

# RUN python3 -m venv venv 
# RUN source venv/bin/activate

# RUN redis-server

RUN pip install -r requirements.txt

CMD ["python" , "app.py"]