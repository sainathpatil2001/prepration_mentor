import multiprocessing

# Worker processes
# For high traffic, 2-4 x num_cores is common.
# workers = multiprocessing.cpu_count() * 2 + 1
workers = 4 # Conservative default for typical small VM, scale up as needed

# Worker class
# Use 'gevent' for handling many concurrent connections efficiently (I/O bound)
# Use 'uvicorn.workers.UvicornWorker' if using async views heavily
worker_class = 'gevent'

# Worker connections (max simultaneous clients per worker)
worker_connections = 1000

# Bind
bind = "0.0.0.0:8000"

# Logging
accesslog = "-"
errorlog = "-"
loglevel = "info"

# Timeout
# Increase if you have slow queries/uploads
timeout = 120

# Keepalive (crucial for load balancers)
keepalive = 5

# Daemon
daemon = False
