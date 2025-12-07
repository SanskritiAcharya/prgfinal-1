# Ecotrack - Smart Waste Management & Recycling Assistant

Ecotrack is a Flask-based web application designed to help users in Nepal track and manage household waste disposal, find nearby recycling centers, view pickup schedules, and learn about proper waste segregation.

## Features

- **User Authentication & Session Management**: Secure user registration, login, and session handling
- **Waste Tracking**: Track household waste entries with type, weight, and description
- **Recycling Centers**: Interactive map showing nearby recycling centers with Google Maps integration
- **Pickup Schedules**: View waste collection schedules by area
- **Waste Tips**: Educational content on proper waste segregation and disposal
- **Real-time Chat**: Socket.IO powered chatbot assistant for waste management queries
- **RESTful APIs**: JSON APIs for waste entries, recycling centers, and pickup schedules
- **Database**: SQLite database for storing user data, waste entries, and recycling information

## Technology Stack

- **Backend**: Flask 3.0.0
- **Database**: SQLAlchemy (SQLite)
- **Authentication**: Flask-Login
- **Real-time Communication**: Flask-SocketIO
- **Maps**: Google Maps API
- **Frontend**: HTML5, CSS3, JavaScript
- **Styling**: Modern responsive design with custom CSS

## Installation

### Prerequisites

- Python 3.8 or higher
- pip (Python package manager)
- Google Maps API Key (optional, for map functionality)

### Setup Instructions

1. **Clone or navigate to the project directory**:
   ```bash
   cd prg-1
   ```

2. **Create and activate a virtual environment** (if not already created):
   ```bash
   python3 -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

4. **Set up environment variables** (optional):
   ```bash
   export SECRET_KEY='your-secret-key-here'
   export GOOGLE_MAPS_API_KEY='your-google-maps-api-key'
   export DATABASE_URL='sqlite:///ecotrack.db'
   ```

   Or create a `.env` file:
   ```
   SECRET_KEY=your-secret-key-here
   GOOGLE_MAPS_API_KEY=your-google-maps-api-key
   DATABASE_URL=sqlite:///ecotrack.db
   ```

5. **Run the application**:
   ```bash
   python app.py
   ```

6. **Access the application**:
   Open your browser and navigate to `http://localhost:5000`

## Project Structure

```
prg-1/
├── app.py                 # Main Flask application
├── requirements.txt       # Python dependencies
├── README.md             # This file
├── templates/            # HTML templates
│   ├── base.html
│   ├── index.html
│   ├── login.html
│   ├── register.html
│   ├── dashboard.html
│   ├── track_waste.html
│   ├── recycling_centers.html
│   ├── pickup_schedules.html
│   └── waste_tips.html
├── static/
│   ├── css/
│   │   └── style.css     # Main stylesheet
│   └── js/
│       └── main.js       # JavaScript for interactivity
└── instance/
    └── ecotrack.db       # SQLite database (created automatically)
```

## Database Models

- **User**: User accounts with authentication
- **WasteEntry**: Individual waste disposal records
- **RecyclingCenter**: Recycling center information with location data
- **PickupSchedule**: Waste collection schedules by area
- **ChatMessage**: Chat conversation history

## API Endpoints

### Waste Entries
- `GET /api/waste-entries` - Get all waste entries for current user
- `POST /api/waste-entries` - Create a new waste entry

### Recycling Centers
- `GET /api/recycling-centers?lat=<latitude>&lng=<longitude>` - Get nearby recycling centers

### Pickup Schedules
- `GET /api/pickup-schedules?area=<area_name>` - Get pickup schedules by area

## Socket.IO Events

- `connect` - Client connects to server
- `chat_message` - Send a message to the chatbot
- `chat_response` - Receive response from chatbot

## Google Maps API Setup

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create a new project or select an existing one
3. Enable the Maps JavaScript API
4. Create credentials (API Key)
5. Set the `GOOGLE_MAPS_API_KEY` environment variable

**Note**: The application will work without the Google Maps API key, but map functionality will be limited.

## Usage

1. **Register**: Create a new account with username, email, and password
2. **Login**: Access your dashboard
3. **Track Waste**: Add waste entries with type, weight, and description
4. **Find Centers**: Browse recycling centers on an interactive map
5. **View Schedules**: Check waste pickup schedules for your area
6. **Get Tips**: Learn about proper waste segregation
7. **Chat**: Use the chat assistant for help with waste management

## Sample Data

The application automatically creates sample recycling centers and pickup schedules for the Kathmandu area when first run.

## Security Notes

- Passwords are hashed using Werkzeug's password hashing
- Session management handled by Flask-Login
- SQL injection protection via SQLAlchemy ORM
- CSRF protection recommended for production (add Flask-WTF)

## Production Deployment

For production deployment:

1. Set a strong `SECRET_KEY` environment variable
2. Use a production database (PostgreSQL recommended)
3. Configure proper CORS settings
4. Use a production WSGI server (Gunicorn, uWSGI)
5. Set up HTTPS/SSL
6. Configure proper logging
7. Add rate limiting
8. Implement CSRF protection

## Contributing

This is a project for educational purposes. Feel free to fork and modify as needed.

## License

This project is provided as-is for educational purposes.

## Support

For issues or questions, please check the code comments or create an issue in the repository.

---

**Ecotrack** - Making waste management smarter for Nepal 🌱

