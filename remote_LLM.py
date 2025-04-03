import logging
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import uvicorn
import sys
from datetime import datetime
import requests


class GenerateRequest(BaseModel):
    prompt: str
    model: str = "llama2"  # Default model
    max_length: int = 750
    temperature: float = 0.7


# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)  # Log to stdout
    ]
)

logger = logging.getLogger(__name__)  # Get a logger for this module

app = FastAPI(debug=True)

# Ollama API endpoint - updated to 192.168.1.13:11434
OLLAMA_API_URL = "http://192.168.1.13:11434/api/generate"
OLLAMA_TIMEOUT = 300  # Adjust based on your needs



@app.get("/")
def hello() -> str:
    return "hello"


@app.post("/generate")
async def generate_text(request: GenerateRequest):
    """Generate text using Ollama LLM."""
    prompt = request.prompt
    logger.info(f"Received prompt: {prompt[:100]}...")  # Log first 100 chars

    try:
        # Create the request payload for Ollama
        ollama_payload = {
            "prompt": prompt,
            "model": request.model,
            "options": {
                "temperature": request.temperature,
                "num_predict": request.max_length,
            }
        }

        # Make the request to Ollama
        response = requests.post(OLLAMA_API_URL, json=ollama_payload, timeout=OLLAMA_TIMEOUT)

        if response.status_code != 200:
            logger.error(f"Ollama API error: {response.status_code} - {response.text}")
            raise HTTPException(status_code=500, detail="Error communicating with Ollama API")

        # Extract the generated text from Ollama's response
        response_data = response.json()
        generated_text = response_data.get("response", "")

        logger.info(f"Generated response of length {len(generated_text)}")
        return {"generated_text": prompt + generated_text}

    except requests.RequestException as e:
        logger.error(f"Error connecting to Ollama: {str(e)}")
        raise HTTPException(status_code=503, detail="Ollama service unavailable")

    except Exception as e:
        logger.error(f"Unexpected error in generate_text: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


# Log startup information
@app.on_event("startup")
async def startup_event():
    logger.info(f"Starting up application at {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')} UTC")
    logger.info(f"User: {sys.argv[0] if len(sys.argv) > 0 else 'unknown'}")

    # Check if Ollama is available
    try:
        # Test connection to Ollama
        models_response = requests.get("http://192.168.1.13:11434/api/tags")
        if models_response.status_code == 200:
            models = models_response.json().get("models", [])
            logger.info(f"Connected to Ollama. Available models: {[m.get('name') for m in models]}")
        else:
            logger.warning(f"Ollama responded with status code {models_response.status_code}")
    except requests.RequestException as e:
        logger.warning(f"Could not connect to Ollama: {str(e)}")
        logger.warning("Make sure Ollama is running on 192.168.1.13:11434")


if __name__ == "__main__":
    # Configure uvicorn to use the same logging configuration
    uvicorn.run(app, host="192.168.1.13", port=9000, log_level="info")
