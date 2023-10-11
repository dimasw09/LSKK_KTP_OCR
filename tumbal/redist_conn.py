#redis_conn.py
from rq import Queue
from redis import Redis

# Buat koneksi Redis
redis_conn = Redis(host='127.0.0.1', port=6379, db=1)

# Buat antrian Redis Queue
redis_queue = Queue('dimas', connection=redis_conn)