from fastapi import HTTPException
import openai
from dotenv import load_dotenv
import os, json
import logging
import base64
import requests
from PIL import Image
from io import BytesIO

# Load environment variables from .env file
load_dotenv()

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# System prompt to guide the model
SYSTEM_PROMPT = """
You're an experienced AI-powered arhictecture reviewer.
German is your native language
You're familiar with the German building codes and regulations.
Must provide area and volume details if foun in the content
Display the details about by extracting info from text and analyse images to understand about the architecture in pdfs:
- Project title 
- Project location
- client/Applicant
- Project type 
- Building class (for example GK3, etc..)
- building usage (for which they're constructing a building)
- number of floors
- Gross area of the building
- volume of the building
- Technical Data (like Fire resistance classes (EI 90-M, EI 60-M, F90, F60, etc), following strandard heating system or not, etc..)
- Relevant authorities
"""

# OpenAI API key
def get_api_key(OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")):
    if not OPENAI_API_KEY:
        logger.error("OpenAI API key is missing. Ensure it's set in the environment variables.")
        raise RuntimeError("OpenAI API key is not set")
    OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
    return OPENAI_API_KEY

openai.api_key = get_api_key()


def encode_images_to_base64(images_path):
    
    image_files = [os.path.join(images_path, file) for file in os.listdir(images_path) if file.endswith(".png")]
    print("image file:", len(image_files))
    encoded_images = []    
    for file in image_files:
        try:
            with Image.open(file) as img:  # Open the image file
                img = img.resize((1024, 1024)) 
                buffered = BytesIO()  # Create a buffer to store the image bytes
                img.save(buffered, format="PNG")  # Save the image to the buffer in PNG format
                img_data = buffered.getvalue()  # Get the raw image data from the buffer
                encoded_image = base64.b64encode(img_data).decode('utf-8')  # Encode the image data as base64
                encoded_images.append(encoded_image)
                # print("Image read successfully")
        except Exception as e:
            logger.error(f"Error processing image {file}: {e}")
            raise HTTPException(status_code=500, detail=f"Error processing image {file}: {e}")
    return encoded_images


def parse_response_data(data):

    # Strip the data and split it into lines
    data = data.replace("**","")
    data = data.replace("-","")
    data = data.replace("\"","")
    lines = data.strip().split("\n")
    print(lines)
    
    result ={}
    for line in lines:
        print(line)
        line_key = line.split(":")[0]
        line_value = line.split(":")[1]
        result[line_key] = line_value
        
    return result



def send_to_gpt(encoded_images:list):
    i=0
    responses = []
    # Send the request to the OpenAI API
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {get_api_key()}"
    }
    
    # sending each image as a message to gpt for analysis
    for  encoded_image in encoded_images:
        i+=1
        print(i)
        payload = {
            "model": "gpt-4o",
            "messages": [
                {
                    "role": "system",
                    "content": SYSTEM_PROMPT
                },
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:image/jpeg;base64,{encoded_image}"
                            }
                        }
                    ]
                }
            ],
            "max_tokens": 4095
        }

        response = requests.post("https://api.openai.com/v1/chat/completions", headers=headers, json=payload)

        # Handle the response from the OpenAI API
        if response.status_code != 200:
            raise HTTPException(status_code=response.status_code, detail=f"OpenAI API Error: {response.text}")

        response_json = response.json()

        # Extract the assistant's message from the response
        assistant_message = response_json['choices'][0]['message']['content']
        # print(assistant_message)
        
        responses.append(assistant_message)

    logger.info("Successfully processed images and generated responses.")

    final_msg = final_response(responses)
    # return json.dumps(final_msg)
    return final_msg  


def final_response(responses:list):
    prompt = """You will recieve a list of responses. You task is to select the most appropriate detail from it. The format you should follow:
- Project title 
- Project location
- client/Applicant
- Project type 
- Building class (for example GK3, etc..)
- building usage (for which they're constructing a building)
- number of floors
- Gross floor area (total area)
- volume of the building
- Technical Data (like Fire resistance classes (EI 90-M, EI 60-M, F90, F60, etc), following strandard heating system or not, etc..) must be in one line
- Relevant authorities
    """
    responses = " ".join([response for response in responses])
    # print(responses)
    payload = {
            "model": "gpt-4o",
            "messages": [
                {
                    "role": "system",
                    "content": prompt
                },
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "text",
                            "text": responses
                        }
                    ]
                }
            ],
            "max_tokens": 4095
        }
    # Send the request to the OpenAI API
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {get_api_key()}"
    }
    response = requests.post("https://api.openai.com/v1/chat/completions", headers=headers, json=payload)

    # Handle the response from the OpenAI API
    if response.status_code != 200:
        raise HTTPException(status_code=response.status_code, detail=f"OpenAI API Error: {response.text}")

    response_json = response.json()

    # Extract the assistant's message from the response
    assistant_message = response_json['choices'][0]['message']['content']
    response = parse_response_data(assistant_message.replace("**",""))
    print("recieved response")
    return response

# Final method 
def upload_image_as_message(images_path = os.path.join(os.getcwd(), "uploads", "images")):
    """
    Method to analyze images that were converted from PDFs.
    """
    try:
        # Ensure the image directory exists
        if not os.path.exists(images_path):
            raise HTTPException(status_code=404, detail="No images found for analysis.")

        # Convert each image to base64
        encoded_images = encode_images_to_base64(images_path=images_path)
        # print(encoded_images)
        print("encoded images", len(encoded_images))
        return send_to_gpt(encoded_images=encoded_images)
    
    except Exception as e:
        logger.error(f"Error processing image: {e}")
        raise HTTPException(status_code=500, detail="An error occurred while processing the image.")

