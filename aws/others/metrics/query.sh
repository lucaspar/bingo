# Metrics
http://demo.robustperception.io:9100/metrics

# Demo
python query_csv.py http://demo.robustperception.io:9090 'irate(process_cpu_seconds_total[1m])'
python query_csv.py http://demo.robustperception.io:9090 'irate(node_memory_MemAvailable_bytes[1m])'
