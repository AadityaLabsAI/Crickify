# Railway-optimized Procfile for Cricket Bot
# Uses worker process type for background bot operation

# Main worker process - Railway-optimized with enhanced monitoring
worker: python -u -W ignore::DeprecationWarning main.py

# Health check process (Railway will monitor this)
health: python -c "import os; print('HEALTHY' if os.getenv('TELEGRAM_BOT_TOKEN') else 'MISSING_TOKEN'); exit(0 if os.getenv('TELEGRAM_BOT_TOKEN') else 1)"

# Alternative web process for Railway health checks (if needed)
# web: python -c "import http.server, socketserver, os; PORT = int(os.getenv('PORT', 5000)); httpd = socketserver.TCPServer(('', PORT), http.server.SimpleHTTPRequestHandler); print(f'Health server on port {PORT}'); httpd.serve_forever()"