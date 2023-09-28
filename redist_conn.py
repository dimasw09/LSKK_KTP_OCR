#redis_conn.py

from rq import Queue
from redis import Redis

# Buat koneksi Redis
redis_conn = Redis(host='localhost', port=6379, db=0)

# Buat antrian Redis Queue
redis_queue = Queue('dimas', connection=redis_conn)
