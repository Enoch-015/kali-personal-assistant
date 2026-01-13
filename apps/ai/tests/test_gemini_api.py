from google import genai

# Initialize the client
client = genai.Client(api_key='')

try:
    # Send a simple test prompt
    response = client.models.generate_content(
        model='gemini-2.0-flash', 
        contents='Write a one-sentence greeting to verify the API is working.'
    )
    
    # Print the response text
    print("Success! Gemini says:")
    print(response.text)

except Exception as e:
    print(f"An error occurred: {e}")