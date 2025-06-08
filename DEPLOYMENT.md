# Deployment and Configuration Guide

## Quick Start

### Prerequisites
- Python 3.7+
- Node.js (for development tools)
- Git

### Installation

1. **Clone the repository**
   ```bash
   git clone <repository-url>
   cd steem-hive-curation-manager
   ```

2. **Set up Python environment**
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   pip install -r requirements.txt
   ```

3. **Initialize the database**
   ```bash
   python -c "from app import create_app; from curation.components.db import db; app = create_app(); app.app_context().push(); db.create_all()"
   ```

4. **Run the application**
   ```bash
   python app.py
   ```

The application will be available at `http://localhost:5000`

## Configuration

### Environment Variables

Create a `.env` file in the project root:

```bash
# Flask Configuration
FLASK_ENV=development
SECRET_KEY=your-secret-key-here

# Database Configuration
DATABASE_URL=sqlite:///instance/curation.db

# Blockchain Configuration
DEFAULT_BLOCKCHAIN=hive
STEEM_NODES=https://api.steemit.com,https://api.steem.buzz
HIVE_NODES=https://api.hive.blog,https://api.deathwing.me

# Voting Configuration
DEFAULT_VOTE_WEIGHT=100
MAX_VOTES_PER_DAY=10
VOTE_DELAY_MINUTES=5

# UI Configuration
DEFAULT_THEME=auto
ENABLE_DARK_MODE=true

# Logging
LOG_LEVEL=INFO
LOG_FILE=logs/curation.log
```

### Application Settings

Settings can be configured through the web interface or directly in the database:

#### Core Settings
- **Blockchain Selection**: Choose between Steem and Hive
- **Node Configuration**: Primary and fallback blockchain nodes
- **Voting Parameters**: Weight, timing, and limits
- **User Interface**: Theme preferences and display options

#### Advanced Settings
- **Curation Strategy**: Automated voting rules and filters
- **Performance Tuning**: Thread counts and timeout values
- **Notification Settings**: Telegram bot integration
- **Security Options**: Key validation and session management

## Production Deployment

### Using Docker

1. **Build the Docker image**
   ```bash
   docker build -t curation-manager .
   ```

2. **Run with Docker Compose**
   ```yaml
   version: '3.8'
   services:
     app:
       build: .
       ports:
         - "5000:5000"
       volumes:
         - ./instance:/app/instance
         - ./logs:/app/logs
       environment:
         - FLASK_ENV=production
         - SECRET_KEY=${SECRET_KEY}
       restart: unless-stopped
   ```

### Using WSGI Server

For production, use a proper WSGI server like Gunicorn:

```bash
pip install gunicorn
gunicorn -w 4 -b 0.0.0.0:5000 "app:create_app()"
```

### Nginx Configuration

Example Nginx configuration for reverse proxy:

```nginx
server {
    listen 80;
    server_name your-domain.com;

    location / {
        proxy_pass http://127.0.0.1:5000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    }

    location /static {
        alias /path/to/app/static;
        expires 1y;
        add_header Cache-Control "public, immutable";
    }
}
```

## Database Setup

### SQLite (Default)
The application uses SQLite by default for simplicity. The database file is created automatically in the `instance/` directory.

### PostgreSQL (Recommended for Production)

1. **Install PostgreSQL dependencies**
   ```bash
   pip install psycopg2-binary
   ```

2. **Update configuration**
   ```bash
   DATABASE_URL=postgresql://username:password@localhost/curation_db
   ```

3. **Initialize database**
   ```bash
   python -c "from app import create_app; from curation.components.db import db; app = create_app(); app.app_context().push(); db.create_all()"
   ```

## Security Configuration

### SSL/TLS Setup

For production deployments, always use HTTPS:

1. **Obtain SSL certificates** (Let's Encrypt recommended)
2. **Configure Nginx with SSL**:
   ```nginx
   server {
       listen 443 ssl;
       ssl_certificate /path/to/certificate.crt;
       ssl_certificate_key /path/to/private.key;
       # ... rest of configuration
   }
   ```

### Security Headers

Add security headers to your web server configuration:

```nginx
add_header X-Frame-Options DENY;
add_header X-Content-Type-Options nosniff;
add_header X-XSS-Protection "1; mode=block";
add_header Strict-Transport-Security "max-age=31536000; includeSubDomains";
```

### Key Management

- **Never commit private keys to version control**
- **Use environment variables for sensitive data**
- **Implement proper key rotation procedures**
- **Use posting keys instead of active keys when possible**

## Monitoring and Maintenance

### Health Checks

The application provides health check endpoints:

- `GET /health` - Basic application health
- `GET /health/blockchain` - Blockchain connectivity status
- `GET /health/database` - Database connection status

### Logging

Configure comprehensive logging:

```python
import logging
from logging.handlers import RotatingFileHandler

# Configure rotating file handler
handler = RotatingFileHandler('logs/curation.log', maxBytes=10000000, backupCount=5)
handler.setFormatter(logging.Formatter(
    '%(asctime)s %(levelname)s: %(message)s [in %(pathname)s:%(lineno)d]'
))
app.logger.addHandler(handler)
app.logger.setLevel(logging.INFO)
```

### Backup Strategy

1. **Database Backups**
   ```bash
   # SQLite
   cp instance/curation.db backups/curation_$(date +%Y%m%d_%H%M%S).db
   
   # PostgreSQL
   pg_dump curation_db > backups/curation_$(date +%Y%m%d_%H%M%S).sql
   ```

2. **Configuration Backups**
   ```bash
   tar -czf backups/config_$(date +%Y%m%d_%H%M%S).tar.gz instance/ .env
   ```

## Performance Optimization

### Application-Level Optimizations

1. **Enable Flask caching**
   ```python
   from flask_caching import Cache
   cache = Cache(app, config={'CACHE_TYPE': 'redis'})
   ```

2. **Optimize database queries**
   - Use database indexing
   - Implement query result caching
   - Use connection pooling

3. **Implement rate limiting**
   ```python
   from flask_limiter import Limiter
   limiter = Limiter(app, key_func=get_remote_address)
   ```

### System-Level Optimizations

1. **Use a CDN for static assets**
2. **Implement Gzip compression**
3. **Optimize image assets**
4. **Use HTTP/2 when possible**

## Troubleshooting

### Common Issues

#### Database Connection Errors
```bash
# Check database file permissions
ls -la instance/curation.db

# Recreate database if corrupted
rm instance/curation.db
python -c "from app import create_app; from curation.components.db import db; app = create_app(); app.app_context().push(); db.create_all()"
```

#### Blockchain Connection Issues
```bash
# Test blockchain connectivity
python -c "
from curation.components.beem import Blockchain
bc = Blockchain()
print(bc.get_blockchain_info())
"
```

#### Permission Errors
```bash
# Fix file permissions
chmod -R 755 static/
chmod -R 755 templates/
chmod 600 instance/curation.db
```

### Debug Mode

Enable debug mode for development:

```bash
export FLASK_ENV=development
export FLASK_DEBUG=1
python app.py
```

### Log Analysis

Monitor application logs for issues:

```bash
# Follow logs in real-time
tail -f logs/curation.log

# Search for errors
grep -i error logs/curation.log

# Analyze access patterns
grep "POST\|GET" logs/curation.log | tail -100
```

## API Documentation

### Authentication Endpoints

- `POST /api/login` - User authentication
- `POST /api/logout` - User logout
- `GET /api/user` - Get current user info

### Voting Endpoints

- `POST /api/vote` - Cast a vote
- `GET /api/votes` - Get voting history
- `GET /api/vote-analysis` - Get vote analysis data

### Settings Endpoints

- `GET /api/settings` - Get user settings
- `POST /api/settings` - Update settings
- `GET /api/blockchain-info` - Get blockchain information

### Example API Usage

```javascript
// Cast a vote
fetch('/api/vote', {
    method: 'POST',
    headers: {
        'Content-Type': 'application/json',
    },
    body: JSON.stringify({
        author: 'username',
        permlink: 'post-permlink',
        weight: 100
    })
})
.then(response => response.json())
.then(data => console.log(data));
```

## Contributing

### Development Setup

1. **Fork the repository**
2. **Create a feature branch**
   ```bash
   git checkout -b feature/new-feature
   ```

3. **Install development dependencies**
   ```bash
   pip install -r requirements-dev.txt
   ```

4. **Run tests**
   ```bash
   python -m pytest tests/
   ```

5. **Submit a pull request**

### Code Style

- Follow PEP 8 for Python code
- Use ESLint for JavaScript code
- Include comprehensive docstrings
- Write unit tests for new features

## Support

### Documentation
- [Architecture Overview](ARCHITECTURE.md)
- [API Reference](API.md)
- [User Guide](USER_GUIDE.md)

### Community
- GitHub Issues: Report bugs and request features
- Discussions: Community support and questions
- Discord: Real-time community chat

### Professional Support
Contact the development team for:
- Custom deployment assistance
- Performance optimization consulting
- Feature development services
- Training and workshops
