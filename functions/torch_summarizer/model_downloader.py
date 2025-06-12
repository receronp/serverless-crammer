import os
import sys
from transformers import pipeline


def download_and_save_model(model_name: str, save_dir: str = "./pipes"):
    os.makedirs(save_dir, exist_ok=True)
    pipe = pipeline(model_name)
    model_path = os.path.join(save_dir, f"{model_name}-model")
    tokenizer_path = os.path.join(save_dir, f"{model_name}-tokenizer")
    pipe.model.save_pretrained(model_path)
    pipe.tokenizer.save_pretrained(tokenizer_path)
    print(f"Model and tokenizer saved to '{model_path}' and '{tokenizer_path}'.")


def main():
    model_name = sys.argv[1] if len(sys.argv) > 1 else "summarization"
    download_and_save_model(model_name)


if __name__ == "__main__":
    main()
