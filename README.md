# TaskManager - Django Task Management System

A comprehensive task management system built with Django REST Framework, featuring user management, task tracking, comments, attachments, and real-time collaboration.

## 🚀 Features

### Core Functionality
- **User Management**: Registration, authentication, profile management
- **Task Management**: Create, update, delete, and track tasks
- **Subtask Support**: Hierarchical task organization
- **Comment System**: Real-time task discussions
- **File Attachments**: Document and media file support
- **Tag System**: Flexible task categorization
- **Dashboard**: Analytics and task overview
- **OAuth Integration**: Social login support (Google, GitHub)

### Technical Features
- **RESTful API**: Clean, documented API endpoints
- **Comprehensive Testing**: Unit and integration tests with pytest
- **Modern Django**: Latest Django 5.2.1 with best practices
- **Scalable Architecture**: Modular app structure
- **Security**: JWT authentication, permissions, and validation
- **API Documentation**: OpenAPI/Swagger integration

## 🛠️ Tech Stack

- **Backend**: Django 5.2.1, Django REST Framework 3.16.0
- **Database**: PostgreSQL (recommended) / SQLite (development)
- **Authentication**: JWT, OAuth 2.0 (Google, GitHub)
- **Documentation**: drf-spectacular (OpenAPI/Swagger)
- **Testing**: pytest, pytest-django, pytest-cov
- **Code Quality**: PEP 8 compliant
- **File Handling**: Pillow for image processing
- **CORS**: django-cors-headers for cross-origin requests

## 📋 Prerequisites

- Python 3.11+
- pip
- virtualenv or conda
- Git
- PostgreSQL (optional, SQLite works for development)

## 🏗️ Installation

### 1. Clone the Repository
```bash
git clone <your-repo-url>
cd TaskManager
```

### 2. Create Virtual Environment
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

### 3. Install Dependencies
```bash
pip install -r requirements.txt
```

### 4. Environment Setup
Create a `.env` file in the project root:
```bash
cp env.example .env
# Edit .env with your configuration
```

Example `.env` file:
```env
DEBUG=True
SECRET_KEY=your-secret-key-here
DATABASE_URL=postgresql://user:password@localhost:5432/taskmanager
ALLOWED_HOSTS=localhost,127.0.0.1
GOOGLE_OAUTH2_CLIENT_ID=your-google-client-id
GOOGLE_OAUTH2_CLIENT_SECRET=your-google-client-secret
FRONTEND_BASE_URL=http://localhost:3000
EMAIL_BACKEND=django.core.mail.backends.console.EmailBackend
DEFAULT_FROM_EMAIL=noreply@taskmanager.com
```

### 5. Database Setup
```bash
python manage.py migrate
python manage.py createsuperuser
```

### 6. Run Development Server
```bash
python manage.py runserver
```

## 📚 API Documentation

Once the server is running, access the API documentation at:

- **Swagger UI**: http://localhost:8000/api/docs/
- **ReDoc**: http://localhost:8000/api/redoc/
- **OpenAPI Schema**: http://localhost:8000/api/schema/

The API documentation is automatically generated from your models, serializers, and views using drf-spectacular.

## 🏛️ Project Structure

```
TaskManager/
├── apps/                    # Django applications
│   ├── config/             # App configuration and base models
│   ├── tasks/              # Task management app
│   │   ├── models.py       # Task, Subtask, Comment, Attachment, Tag models
│   │   ├── views.py        # API views and ViewSets
│   │   ├── serializers.py  # Data serialization
│   │   ├── services.py     # Business logic
│   │   ├── urls.py         # URL routing
│   │   └── tests/          # Test suite
│   └── users/              # User management app
│       ├── models.py       # CustomUser model
│       ├── views.py        # Authentication and user views
│       ├── serializers.py  # User serialization
│       ├── services.py     # User business logic
│       ├── urls.py         # User URL routing
│       └── tests/          # User tests
├── core/                   # Core Django settings
│   ├── settings.py         # Main settings file
│   ├── urls.py            # Main URL configuration
│   └── wsgi.py            # WSGI application
├── templates/              # HTML templates
├── tests/                  # Test configuration and base classes
├── media/                  # User uploaded files
├── logs/                   # Application logs
├── requirements.txt         # Python dependencies
└── manage.py               # Django management script
```

## 🧪 Testing

Run the comprehensive test suite:

```bash
# Run all tests
pytest

# Run specific app tests
pytest tests/tasks/
pytest tests/users/

# Run with coverage
pytest --cov=apps --cov-report=html

# Run tests with verbose output
pytest -v

# Run specific test file
pytest tests/tasks/test_task_views.py
```

### Test Coverage
The project includes tests for:
- Models and their methods
- API views and endpoints
- Serializers and validation
- Business logic services
- Utility functions
- Authentication and permissions

## 🔐 Authentication & Authorization

### JWT Authentication
- Access tokens for API requests
- Refresh tokens for token renewal
- Token blacklisting for security

### OAuth Integration
- Google OAuth2 support
- GitHub OAuth2 support
- Social account linking

### Permissions
- User-based permissions
- Task ownership validation
- Comment and attachment access control

## 📊 API Endpoints

### Authentication
- `POST /api/auth/login/` - User login
- `POST /api/auth/register/` - User registration
- `POST /api/auth/logout/` - User logout
- `POST /api/auth/refresh/` - Token refresh

### Users
- `GET /api/users/` - List users
- `GET /api/users/{id}/` - Get user details
- `PUT /api/users/{id}/` - Update user
- `DELETE /api/users/{id}/` - Delete user

### Tasks
- `GET /api/tasks/` - List tasks with filtering
- `POST /api/tasks/` - Create new task
- `GET /api/tasks/{id}/` - Get task details
- `PUT /api/tasks/{id}/` - Update task
- `PATCH /api/tasks/{id}/` - Partial task update
- `DELETE /api/tasks/{id}/` - Delete task

### Subtasks
- `GET /api/tasks/{task_id}/subtasks/` - List task subtasks
- `POST /api/tasks/{task_id}/subtasks/` - Create subtask
- `PUT /api/subtasks/{id}/` - Update subtask
- `DELETE /api/subtasks/{id}/` - Delete subtask

### Comments
- `GET /api/tasks/{task_id}/comments/` - List task comments
- `POST /api/tasks/{task_id}/comments/` - Create comment
- `PUT /api/comments/{id}/` - Update comment
- `DELETE /api/comments/{id}/` - Delete comment

### Attachments
- `GET /api/tasks/{task_id}/attachments/` - List task attachments
- `POST /api/tasks/{task_id}/attachments/` - Upload attachment
- `DELETE /api/attachments/{id}/` - Delete attachment

### Tags
- `GET /api/tags/` - List all tags
- `POST /api/tags/` - Create new tag
- `PUT /api/tags/{id}/` - Update tag
- `DELETE /api/tags/{id}/` - Delete tag

### Dashboard
- `GET /api/dashboard/stats/` - Get dashboard statistics
- `GET /api/dashboard/recent-tasks/` - Get recent tasks
- `GET /api/dashboard/user-performance/` - Get user performance metrics

## 🔧 Configuration

### Environment Variables
- `DEBUG`: Django debug mode (True/False)
- `SECRET_KEY`: Django secret key for security
- `DATABASE_URL`: Database connection string
- `ALLOWED_HOSTS`: Comma-separated list of allowed hosts
- `GOOGLE_OAUTH2_CLIENT_ID`: Google OAuth client ID
- `GOOGLE_OAUTH2_CLIENT_SECRET`: Google OAuth client secret
- `FRONTEND_BASE_URL`: Frontend application URL
- `EMAIL_BACKEND`: Email backend configuration
- `DEFAULT_FROM_EMAIL`: Default sender email address

### Database Configuration
The system supports multiple databases:
- **SQLite**: Default for development (no additional setup required)
- **PostgreSQL**: Recommended for production
- **MySQL**: Supported with additional configuration

### CORS Configuration
Configured for frontend integration:
- Development: Allows localhost:3000
- Production: Configurable via environment variables

## 🚀 Deployment

### Production Checklist
- [ ] Set `DEBUG=False`
- [ ] Configure production database
- [ ] Set up static file serving
- [ ] Configure media file storage
- [ ] Set up logging and monitoring
- [ ] Configure CORS for production domains
- [ ] Set up SSL/TLS certificates
- [ ] Configure backup strategy
- [ ] Set up environment variables
- [ ] Configure gunicorn/WSGI server

### Docker Deployment
```bash
# Build Docker image
docker build -t taskmanager .

# Run container
docker run -p 8000:8000 -e DATABASE_URL=your-db-url taskmanager
```

### Environment-Specific Settings
The project includes multiple settings files:
- `core/settings.py` - Base settings
- `core/ci_settings.py` - CI/CD settings
- `core/test_settings.py` - Test-specific settings

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

### Development Guidelines
- Follow PEP 8 style guide
- Write comprehensive tests for new features
- Update documentation as needed
- Use meaningful commit messages

## 📝 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🆘 Support

- **Documentation**: Check the API docs at `/api/docs/`
- **Issues**: Report bugs via GitHub Issues
- **Discussions**: Use GitHub Discussions for questions
- **Code**: Review the source code for implementation details

## 🔄 Changelog

### Version 1.0.0
- Initial release
- Complete user management system
- Comprehensive task management system
- Comment and attachment support
- Tag system for task organization
- Dashboard with analytics
- Full API documentation
- Complete test coverage
- OAuth integration (Google, GitHub)
- JWT authentication system

## 📞 Contact

- **Project Link**: [https://github.com/yourusername/TaskManager](https://github.com/yourusername/TaskManager)
- **Issues**: [https://github.com/yourusername/TaskManager/issues](https://github.com/yourusername/TaskManager/issues)
- **Discussions**: [https://github.com/yourusername/TaskManager/discussions](https://github.com/yourusername/TaskManager/discussions)

## 🙏 Acknowledgments

- Django and Django REST Framework communities
- drf-spectacular for excellent API documentation
- All contributors and testers

---

**Made with ❤️ using Django and Django REST Framework**

*Built for modern web applications with scalability and maintainability in mind.*
