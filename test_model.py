import os
import logging
from transformers import pipeline

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

models_path = os.path.expanduser("~/.cache/huggingface/hub")

def list_models():
    """Lists available models in the Hugging Face cache directory."""
    if os.path.exists(models_path):
        models = [f for f in os.listdir(models_path) if os.path.isdir(os.path.join(models_path, f))]
        logging.info(f"Available models: {models}")
        return models
    logging.info("No cached models found.")
    return []

def delete_model(model_name):
    """Deletes a specific cached model by name."""
    model_path = os.path.join(models_path, model_name)
    if os.path.exists(model_path):
        try:
            import shutil
            shutil.rmtree(model_path)
            logging.info(f"Deleted model: {model_name}")
        except Exception as e:
            logging.error(f"Error deleting model: {e}")
    else:
        logging.warning(f"Model '{model_name}' not found.")

# List available models before loading
available_models = list_models()

# Correct the model path if needed
model_name = "models--Salesforce--codet5p-220m"
if model_name not in available_models:
    logging.warning(f"Model {model_name} not found. Did you mean one of these? {available_models}")

# Example of deleting a model
delete_model("models--Salesforce--codet5p-220m")  # Uncomment to delete
available_models = list_models()