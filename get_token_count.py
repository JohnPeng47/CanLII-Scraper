import tiktoken
import os

def count_tokens(text):
    encoding = tiktoken.encoding_for_model("gpt-3.5-turbo")
    return len(encoding.encode(text))

def load_and_count_tokens():
    cases_dir = "cases"
    combined_text = ""
    
    # Load and concatenate all files in cases directory
    for filename in os.listdir(cases_dir):
        file_path = os.path.join(cases_dir, filename)
        if os.path.isfile(file_path):
            with open(file_path, "r", encoding="utf-8") as f:
                combined_text += f.read()
    
    # Count tokens in combined text
    token_count = count_tokens(combined_text)
    print(f"Total tokens across all case files: {token_count}")

if __name__ == "__main__":
    load_and_count_tokens()
