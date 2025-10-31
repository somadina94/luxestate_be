# LuxeState Backend API

A robust and feature-rich real estate backend API built with FastAPI, PostgreSQL, and Docker.

## Features

- 🔐 Authentication & Authorization (JWT with email verification)
- 🏠 Property Management (CRUD, search, filtering)
- 📸 Image Upload (Cloudinary integration)
- ⭐ Favorites System
- 💬 Real-time Chat (WebSocket)
- 🔔 Push Notifications (Web Push & Expo)
- 💳 Stripe Payment Integration
- 🎫 Support Ticket System
- 📢 Announcements
- 📊 Audit Logging
- ⚡ Rate Limiting
- 🧪 Comprehensive Test Suite

## Quick Start

### Prerequisites

- Python 3.11+
- PostgreSQL (or use Docker Compose)
- Docker & Docker Compose (for containerized setup)

### Deployment

**Quick deployment to existing EC2 instance:**

👉 **See [SIMPLIFIED_DEPLOY_SETUP.md](SIMPLIFIED_DEPLOY_SETUP.md)** - Only needs 3 GitHub secrets (no AWS keys needed!)

The app builds directly on EC2 and runs on port 3001, perfect for existing EC2 instances with other applications.

For detailed deployment options, see [README_DEPLOYMENT.md](README_DEPLOYMENT.md).

---

## Local Development

1. **Clone the repository**

   ```bash
   git clone https://github.com/yourusername/luxestate_be.git
   cd luxestate_be
   ```

2. **Create virtual environment**

   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install dependencies**

   ```bash
   pip install -r requirements.txt
   ```

4. **Set up environment variables**

   ```bash
   cp .env.example .env
   # Edit .env with your configuration
   ```

5. **Run database migrations**

   ```bash
   alembic upgrade head
   ```

6. **Run the application**

   ```bash
   uvicorn app.main:app --reload
   ```

7. **Access API**
   - API: http://localhost:8000
   - Docs: http://localhost:8000/docs
   - Health: http://localhost:8000/healthy

### Docker Development

1. **Start services**

   ```bash
   docker-compose up -d
   ```

2. **Run migrations**

   ```bash
   docker-compose exec app alembic upgrade head
   ```

3. **View logs**
   ```bash
   docker-compose logs -f app
   ```

### Running Tests

```bash
# Run all tests
pytest app/tests/ -v

# Run specific test file
pytest app/tests/test_properties.py -v

# With coverage
pytest app/tests/ --cov=app --cov-report=html
```

## API Documentation

Once the server is running, visit:

- **Swagger UI**: http://localhost:3001/docs
- **ReDoc**: http://localhost:3001/redoc

## Project Structure

```
luxestate_be/
├── app/
│   ├── config.py              # Configuration settings
│   ├── database.py            # Database setup
│   ├── main.py                # FastAPI application
│   ├── Middleware/            # Custom middleware
│   ├── models/                # SQLAlchemy models
│   ├── routers/               # API route handlers
│   ├── schemas/                # Pydantic schemas
│   ├── services/               # Business logic
│   ├── tests/                 # Test suite
│   └── utils/                  # Utility functions
├── alembic/                    # Database migrations
├── .github/workflows/          # CI/CD pipelines
├── Dockerfile                  # Docker image definition
├── docker-compose.yml          # Docker Compose configuration
└── requirements.txt            # Python dependencies
```

## Environment Variables

See `.env.example` for all required environment variables.

Key variables:

- `DATABASE_URL` - PostgreSQL connection string (Supabase recommended for production)
- `SECRET_KEY` - JWT secret key
- `CLOUDINARY_*` - Cloudinary credentials
- `STRIPE_*` - Stripe API keys
- `EMAIL_*` - SMTP email configuration

## Deployment

See [deployguide.md](deployguide.md) for detailed deployment instructions to AWS EC2.

### Quick Deploy

1. Set up EC2 instance
2. Configure GitHub Secrets
3. Push to `main` branch
4. GitHub Actions will automatically deploy

## Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## Security

- Change all default passwords
- Use strong `SECRET_KEY`
- Enable HTTPS in production
- Restrict CORS origins
- Regular security updates
- Monitor audit logs

## License

This project is licensed under the MIT License.

## Support

For issues or questions:

- Check [deployguide.md](deployguide.md) for deployment help
- Review application logs
- Check GitHub Issues

---

**Built with ❤️ using FastAPI, PostgreSQL, and Docker**
