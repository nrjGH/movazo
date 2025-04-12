import streamlit as st
# import chatbot
import requests
import json
from groq import Groq
import urllib.parse
from datetime import date
import os
from dotenv import load_dotenv

load_dotenv()

chat_history = [
    {
        "role": "system",
        "content": (
            "You are a helpful assistant designed to help users find current movie showtimes in theatres.\n\n"
            "Your task is to collect the following 4 required details from the user:\n"
            "1. Movie name\n"
            "2. Location (area/place where user wants to watch movie) \n"
            "3. Date (user can say today or tomorrow)\n"
            "4. Preferred part of the day (morning / afternoon / evening / night)\n\n"
            "Do not assume or guess any detail. If something is missing, ask the user directly to provide it.\n"
            "Only when all 4 inputs are provided, use the `filmShowDetails` tool to fetch available showtimes.\n\n"
            "Once you have the tool output:\n"
            "- Select top 5 showtimes based on user's preferred part of day.\n"
            "- Always mention the cinema name and show timing.\n"
            "- If no shows match, tell the user clearly that there are no available showtimes.\n"
            "- Never invent, assume, or guess data. Avoid all dummy or sample outputs.\n\n"
            "Your tone should be short, clear, and conversational — like a smart movie assistant.\n"
            f"Today's date is {date.today().strftime('%Y-%m-%d')}.\n"
        )
    }
]

def getLatitudeLongitude(city):

    encoded_name = urllib.parse.quote_plus(city)
    try:
        url = f"https://geocode.maps.co/search?q={encoded_name}&api_key={os.getenv('GEOCODE_API_KEY')}"
        response = requests.get(url)
        response.raise_for_status()
        data = response.json()
        if not data:
            return None

        lat = data[0]["lat"][:-1]  # Trim precision
        lon = data[0]["lon"][:-1]
        return f"{lat};{lon}"
    except requests.exceptions.RequestException as e:
        print(f"[GeoError] {e}")
        return None

def searchMovie(movie_name):

    encoded_name = urllib.parse.quote_plus(movie_name)
    url = f"https://api-gate2.movieglu.com/filmLiveSearch/?query={encoded_name}"
    HEADERS = {
        "client": os.getenv('MG_HEADER_CLIENT'),
        "x-api-key": os.getenv('MG_HEADER_X_API_KEY'),
        "authorization": os.getenv('MG_HEADER_AUTHORIZATION'),
        "territory": os.getenv('MG_HEADER_TERRITORY'),
        "api-version": os.getenv('MG_HEADER_API_VERSION'),
        "geolocation": "-22.0;14.0",  # Dummy default
        "device-datetime": "2025-03-27T14:45:30.000",
    }
    response = requests.get(url, headers=HEADERS)
    response.raise_for_status()
    data = response.json()
    return data["films"][0]["film_id"] if "films" in data and data["films"] else None

def filmShowDetails(movie_name, location, date):
    # print("Getting show details from the theatres...")
    geo = getLatitudeLongitude(location)
    if geo is None:
        return "Invalid location"

    film_id = searchMovie(movie_name)
    if not film_id:
        return "Movie not found"

    url = f"https://api-gate2.movieglu.com/filmShowTimes/?film_id={film_id}&date={date}"
    HEADERS = {
        "client": os.getenv('MG_HEADER_CLIENT'),
        "x-api-key": os.getenv('MG_HEADER_X_API_KEY'),
        "authorization": os.getenv('MG_HEADER_AUTHORIZATION'),
        "territory": os.getenv('MG_HEADER_TERRITORY'),
        "api-version": os.getenv('MG_HEADER_API_VERSION'),
        "geolocation": geo, 
        "device-datetime": "2025-03-27T14:45:30.000",
    }
    response = requests.get(url, headers=HEADERS)
    response.raise_for_status()

    if response.status_code == 204 or not response.content:
      return "There are no available shows for given time, would you like to try any other date or time?"
    
    data = response.json()
    result = {}
    
    if "cinemas" in data and isinstance(data["cinemas"], list):
        for cinema in data["cinemas"]:
            times = cinema.get("showings", {}).get("Standard", {}).get("times", [])
            if times:
                result[cinema["cinema_name"]] = times
    # print(result)
    return result if result else "No showtimes found."

def chat(user_input):
    groq_api_key = os.getenv("GROQ_API_KEY")
    model_name = "llama-3.3-70b-specdec"
    client = Groq(api_key=groq_api_key)

    tools = [
        {
            "type": "function",
            "function": {
                "name": "filmShowDetails",
                "description": "Gets showtimes for a movie on a date in a given location.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "movie_name": {"type": "string", "description": "Movie name"},
                        "location": {"type": "string", "description": "User's city/location"},
                        "date": {"type": "string", "description": "YYYY-MM-DD format", "format": "date"},
                    },
                    "required": ["movie_name", "location", "date"]
                },
            }
        }
    ]

    chat_history.append({"role": "user", "content": user_input})

    response = client.chat.completions.create(
        model=model_name,
        messages=chat_history,
        tools=tools,
        tool_choice="auto",
        max_completion_tokens=4096
    )

    response_message = response.choices[0].message
    tool_calls = response_message.tool_calls

    if tool_calls:
        available_functions = {"filmShowDetails": filmShowDetails}
        chat_history.append(response_message)

        for tool_call in tool_calls:
            func_name = tool_call.function.name
            func_args = json.loads(tool_call.function.arguments)
            func_result = available_functions[func_name](
                movie_name=func_args.get("movie_name"),
                location=func_args.get("location"),
                date=func_args.get("date")
            )
            chat_history.append({
                "tool_call_id": tool_call.id,
                "role": "tool",
                "name": func_name,
                "content": json.dumps(func_result),
            })

        chat_history.append({
            "role": "assistant",
            "content": (
                "Use the result from the tool call to:\n"
                "- Identify the top 5 best showtimes for the movie.\n"
                "- Show the theatre name and time for each.\n"
                "- Respect the user's preferred part of day.\n"
                "- If there are no results, say: 'There are no available shows for the given time or location.'\n"
                "- Ask if the user would like to try another movie, date, or time.\n"
                "- Do not make up results or provide guesses. If data is unavailable, say so clearly.\n"
                "- Keep your response short, clear, and user-friendly."
            )
        })
        second_response = client.chat.completions.create(
            model=model_name,
            messages=chat_history
        )

        chat_history.append({"role": "assistant", "content": second_response.choices[0].message.content})
        return second_response.choices[0].message.content

    chat_history.append({"role": "assistant", "content": response_message.content})
    return response_message.content

def chatbot(user_input):
        if user_input.lower() == "quit":
            return "Bye! Have fun with your plans."

        result = chat(user_input)
        return "Movazo : " + result

st.set_page_config(
    page_title="Movazo - Your Movie Assistant",  # Title of the browser tab
    page_icon="🎥",  # Emoji or path to an icon file
    layout="centered",  # Layout: 'centered' or 'wide'
)

st.header("Movazo at your service!")
st.subheader(" I can help you with your next movie plan.")

user_input = st.text_input("Ask here:")
if st.button("Send"):
    if user_input:
        response = chatbot(user_input)
        st.write("Chatbot response:")
        st.write(response)
    else:
        st.write("Please enter a message.")