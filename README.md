# Movazo - Your Movie Assistant 🎥

Movazo is a smart movie assistant designed to help users find current movie showtimes in theaters. It provides a conversational interface to gather user preferences and fetch relevant showtimes based on location, date, and time of day.

## Features
- **User-Friendly Chat Interface**: Collects movie name, location, date, and preferred time of day.
- **Real-Time Showtimes**: Fetches showtimes from external API.
- **Geolocation Support**: Converts user-provided locations into latitude and longitude.
- **Streamlit UI**: Interactive web interface for seamless user interaction.

## Requirements
- Python 3.9+
- Dependencies listed in [`requirements.txt`](movazo/requirements.txt):
  - `streamlit`
  - `requests`
  - `python-dotenv`
  - `groq`

## Setup
1. Clone the repository and navigate to the project directory.
2. Create a virtual environment:
   ```bash
   python -m venv movazo/fenv
