# Steem/Hive Curation Manager

A sophisticated blockchain-based social media post curation system that provides automated voting, timing optimization, and comprehensive management interfaces for both Steem and Hive blockchains.

![License](https://img.shields.io/badge/license-MIT-blue.svg)
![Python](https://img.shields.io/badge/python-3.7+-blue.svg)
![Flask](https://img.shields.io/badge/flask-2.0+-green.svg)
![Blockchain](https://img.shields.io/badge/blockchain-Steem%20%7C%20Hive-orange.svg)

## 🚀 Features

### Core Functionality
- **Multi-Blockchain Support**: Unified interface for both Steem and Hive blockchains
- **Automated Curation**: Background monitoring and voting on posts with optimal timing
- **Sophisticated Algorithms**: Advanced vote timing optimization using historical data analysis
- **Real-time Analytics**: Live blockchain data and voting performance metrics
- **Multi-User Management**: Support for multiple curator accounts with delegation tracking

### User Interface
- **Modern Web Interface**: Responsive design with dark/light theme support
- **Real-time Updates**: Live blockchain data and voting statistics
- **Mobile Optimized**: Mobile-first design approach with touch-friendly interactions
- **Accessibility**: WCAG compliant with keyboard navigation support

### Technical Excellence
- **High Availability**: Multi-node blockchain connectivity with automatic failover
- **Performance Optimized**: Concurrent processing and efficient resource management
- **Secure**: Comprehensive key management and input validation
- **Extensible**: Modular architecture with clean separation of concerns

## 📋 Table of Contents

- [Quick Start](#-quick-start)
- [Features](#-features)
- [Installation](#-installation)
- [Configuration](#-configuration)
- [Usage](#-usage)
- [API Documentation](#-api-documentation)
- [Architecture](#-architecture)
- [Contributing](#-contributing)
- [License](#-license)
- [Support](#-support)

## ⚡ Quick Start

### Prerequisites
- Python 3.7 or higher
- Git

### Installation

1. **Clone the repository**
   ```bash
   git clone https://github.com/your-username/steem-hive-curation-manager.git
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

5. **Open your browser**
   Navigate to `http://localhost:5000`

## 🔧 Installation

### Development Setup

```bash
# Clone the repository
git clone https://github.com/your-username/steem-hive-curation-manager.git
cd steem-hive-curation-manager

# Create virtual environment
python -m venv venv
source venv/bin/activate  # Linux/Mac
# or
venv\Scripts\activate     # Windows

# Install dependencies
pip install -r requirements.txt

# Set up environment variables
cp .env.example .env
# Edit .env with your configuration

# Initialize database
python -c "
from app import create_app
from curation.components.db import db
app = create_app()
app.app_context().push()
db.create_all()
print('Database initialized successfully!')
"

# Run the application
python app.py
```

### Docker Setup

```bash
# Build and run with Docker Compose
docker-compose up --build

# Or build manually
docker build -t curation-manager .
docker run -p 5000:5000 -v $(pwd)/instance:/app/instance curation-manager
```

## ⚙️ Configuration

### Environment Variables

Create a `.env` file in the project root:

```env
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
```

### Web Interface Configuration

Access the settings page at `http://localhost:5000/settings` to configure:

- **Account Settings**: Add your Steem/Hive accounts with posting keys
- **Voting Parameters**: Set vote weights, timing, and limits
- **Curation Strategy**: Configure automated voting rules
- **Display Preferences**: Choose themes and interface options

## 🎯 Usage

### Manual Curation

1. **Add Your Account**
   - Navigate to Settings
   - Add your Steem or Hive username and posting key
   - Verify account connectivity

2. **Analyze Posts**
   - Enter a post URL or author/permlink
   - View vote analysis and optimal timing
   - See potential curation rewards

3. **Cast Votes**
   - Set vote weight (1-100%)
   - Choose timing (immediate or scheduled)
   - Confirm vote casting

### Automated Curation

1. **Configure Automation**
   - Enable the "Sniper" mode in settings
   - Set target authors or tags
   - Configure vote parameters

2. **Monitor Performance**
   - View real-time voting activity
   - Track curation rewards
   - Analyze performance metrics

### Advanced Features

- **Multi-Account Management**: Manage multiple curator accounts
- **Delegation Tracking**: Monitor voting power delegations
- **Performance Analytics**: Detailed curation performance analysis
- **Voter Analysis**: Study voting patterns of other curators

## 📚 API Documentation

### Authentication

```javascript
// Login
POST /api/login
{
    "username": "your_username",
    "posting_key": "your_posting_key"
}

// Get user info
GET /api/user
```

### Voting Operations

```javascript
// Cast a vote
POST /api/vote
{
    "author": "post_author",
    "permlink": "post_permlink",
    "weight": 100
}

// Get vote analysis
GET /api/vote-analysis?url=https://peakd.com/@author/permlink
```

### Settings Management

```javascript
// Get settings
GET /api/settings

// Update settings
POST /api/settings
{
    "auto_vote": true,
    "vote_weight": 50,
    "vote_delay": 15
}
```

For complete API documentation, see [API.md](API.md).

## 🏗️ Architecture

### System Overview

```
Frontend (React-like Vanilla JS) ↔ Flask API ↔ Blockchain Layer
                                        ↓
                                   SQLite/PostgreSQL
```

### Key Components

- **Flask Application**: RESTful API with modular route handling
- **VoteManager**: Sophisticated voting algorithms and timing optimization
- **Blockchain Layer**: Multi-node connectivity with failover support
- **Service Layer**: UserService and SettingsService for data management
- **Frontend**: Modern responsive interface with real-time updates

### Key Technologies

- **Backend**: Python, Flask, SQLAlchemy, Beem (blockchain library)
- **Frontend**: Vanilla JavaScript (ES6+), CSS3, HTML5
- **Database**: SQLite (development), PostgreSQL (production)
- **Blockchain**: Steem and Hive blockchain APIs

For detailed architecture documentation, see [ARCHITECTURE.md](ARCHITECTURE.md).

## 🚀 Deployment

### Production Deployment

#### Using Docker

```bash
# Build production image
docker build -t curation-manager:production -f Dockerfile.prod .

# Run with production environment
docker run -d \
  --name curation-manager \
  -p 80:5000 \
  -v /path/to/data:/app/instance \
  -e FLASK_ENV=production \
  -e SECRET_KEY=your-production-secret \
  curation-manager:production
```

#### Using WSGI Server

```bash
# Install production server
pip install gunicorn

# Run with Gunicorn
gunicorn -w 4 -b 0.0.0.0:5000 "app:create_app()"
```

#### Nginx Configuration

```nginx
server {
    listen 80;
    server_name your-domain.com;
    
    location / {
        proxy_pass http://127.0.0.1:5000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
    
    location /static {
        alias /path/to/app/static;
        expires 1y;
    }
}
```

For complete deployment documentation, see [DEPLOYMENT.md](DEPLOYMENT.md).

## 🤝 Contributing

We welcome contributions! Please see our [Contributing Guidelines](CONTRIBUTING.md) for details.

### Development Workflow

1. **Fork the repository**
2. **Create a feature branch**
   ```bash
   git checkout -b feature/amazing-feature
   ```

3. **Make your changes**
   - Follow the existing code style
   - Add tests for new features
   - Update documentation as needed

4. **Test your changes**
   ```bash
   python -m pytest tests/
   python -m flake8 curation/
   ```

5. **Submit a pull request**

### Code Style

- **Python**: Follow PEP 8, use type hints where possible
- **JavaScript**: Use ES6+ features, consistent formatting
- **CSS**: Use CSS custom properties, mobile-first approach
- **Documentation**: Clear docstrings and comments

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🆘 Support

### Documentation
- [Architecture Overview](ARCHITECTURE.md) - System design and technical details
- [Deployment Guide](DEPLOYMENT.md) - Production deployment instructions
- [API Reference](API.md) - Complete API documentation
- [User Guide](USER_GUIDE.md) - End-user documentation

### Community Support
- **GitHub Issues**: [Report bugs and request features](https://github.com/your-username/steem-hive-curation-manager/issues)
- **Discussions**: [Community support and questions](https://github.com/your-username/steem-hive-curation-manager/discussions)
- **Discord**: Join our community chat (link in discussions)

### Professional Support
For enterprise deployments and custom development:
- 📧 Email: support@example.com
- 💼 LinkedIn: [Your Profile](https://linkedin.com/in/yourprofile)
- 🐦 Twitter: [@YourHandle](https://twitter.com/yourhandle)

## 🔮 Roadmap

### Version 2.0 (Planned)
- [ ] Advanced analytics dashboard
- [ ] Machine learning vote optimization
- [ ] Mobile application (React Native)
- [ ] Multi-blockchain support (additional chains)
- [ ] Advanced notification system

### Version 2.1 (Future)
- [ ] Microservices architecture
- [ ] GraphQL API
- [ ] Real-time collaboration features
- [ ] Advanced security features
- [ ] Plugin system for extensions

## 🙏 Acknowledgments

- **Steem Community**: For the innovative blockchain social media concept
- **Hive Community**: For continuing the vision with decentralized governance
- **Beem Library**: For excellent Python blockchain integration
- **Flask Community**: For the robust web framework
- **Open Source Contributors**: Everyone who has contributed to this project

---

**Made with ❤️ by the blockchain community**

*Star ⭐ this repository if you find it useful!*
