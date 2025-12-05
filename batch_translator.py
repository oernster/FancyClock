import json
import os
import time
import multiprocessing 
import functools     
from translate import Translator 
from tqdm import tqdm

# --- Core Configuration Change ---
# Determine the number of processes to run concurrently.
# We cap the number of processes at 12 or use the detected core count, 
# whichever is lower, to maximize speed while leaving some resources free.
# Your AMD 9900X/7950X has many cores, so 12 is a good balance.
CPU_COUNT = os.cpu_count() or 1
MAX_PROCESSES = min(12, CPU_COUNT) 
# ---------------------------------

# --- Helper Functions (Unchanged) ---

def get_target_language(file_path):
    """Extracts the language code (e.g., 'ar') from the file name (e.g., 'ar_SA.json')."""
    file_name = os.path.basename(file_path)
    base_name = os.path.splitext(file_name)[0]
    language_code = base_name.split('_')[0]
    return language_code 

def translate_text(text, target_language, translator):
    """
    Translates text using the 'translate' library with retries and delays.
    """
    if not text or not isinstance(text, str):
        return text
    
    # Use 5 attempts for flaky free API
    for attempt in range(5): 
        try:
            result = translator.translate(text)
            
            # Add a short delay (ESSENTIAL for any free API)
            time.sleep(0.5) 
            
            return result
            
        except Exception as e:
            # Catch all errors (network, timeouts, rate limits, etc.)
            tqdm.write(f"[Core {os.getpid()}] Warning: Translation failed (Attempt {attempt + 1}/5) for language {target_language}. Error: {e}")
            time.sleep(3) # Wait longer on failure before retrying

    tqdm.write(f"[Core {os.getpid()}] Error: Final translation attempt failed for language {target_language}. Skipping key.")
    return text # Return original text if all attempts fail

# --- Worker Function (Refactored from translate_json_file) ---

def process_translation_file(filename, source_data, translations_dir):
    """
    Worker function executed by each process in the Pool.
    It translates a single file.
    """
    file_path = os.path.join(translations_dir, filename)
    target_language = get_target_language(file_path)
    
    # Initialize translator inside the worker function (essential for multiprocessing)
    try:
        # We specify service URLs here to help prevent rate limiting issues for each worker
        translator = Translator(to_lang=target_language, from_lang="en", service_urls=[
            'translate.google.com',
            'translate.google.co.kr',
            'translate.google.co.jp',
        ])
    except Exception as e:
        tqdm.write(f"[Core {os.getpid()}] Could not initialize Translator for {target_language}: {e}")
        return

    # Read the existing target file data
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            target_data = json.load(f)
    except FileNotFoundError:
        target_data = {}

    tqdm.write(f"Starting translation of {filename} (to {target_language}) on Core {os.getpid()}...")

    translated_count = 0
    total_keys = len(source_data)
    
    # Iterate through keys in the source data and translate the corresponding values
    for key, value in source_data.items():
        if isinstance(value, str):
            target_data[key] = translate_text(value, target_language, translator)
        else:
            target_data[key] = value
        
        translated_count += 1
        # Print progress every 100 keys for monitoring
        if translated_count % 100 == 0:
            tqdm.write(f"Core {os.getpid()} progress for {filename}: {translated_count}/{total_keys} keys translated.")

    # Write the resulting translated data back to the file
    with open(file_path, 'w', encoding='utf-8') as f:
        json.dump(target_data, f, ensure_ascii=False, indent=4)
        
    tqdm.write(f"Finished translation of {filename} on Core {os.getpid()}.")
    return filename # Return the filename for the main process to track completion


def main():
    """Main function to parallelize the translation across multiple processes."""
    
    tqdm.write("Free MyMemory/Translate client ready.")

    # Define paths
    base_dir = os.path.dirname(__file__)
    translations_dir = os.path.join(base_dir, 'localization', 'translations')
    source_file = os.path.join(translations_dir, 'en_GB.json')

    # Load source data
    try:
        with open(source_file, 'r', encoding='utf-8') as f:
            source_data = json.load(f)
        tqdm.write(f"Loading source data from: {source_file}")
    except FileNotFoundError:
        tqdm.write(f"Error: Source file not found at {source_file}")
        return

    # Filter files for translation
    files_to_translate = [f for f in os.listdir(translations_dir) if f.endswith('.json') and f not in ['en_GB.json', 'key_reference.json']]
    tqdm.write(f"--- Found {len(files_to_translate)} files to translate. Using {MAX_PROCESSES} concurrent processes on {CPU_COUNT} available cores. ---")
    
    # Use functools.partial to fix the source_data and translations_dir arguments
    worker = functools.partial(process_translation_file, source_data=source_data, translations_dir=translations_dir)

    # NEW: Create a multiprocessing Pool
    try:
        with multiprocessing.Pool(processes=MAX_PROCESSES) as pool:
            
            # Use imap_unordered for a dynamic progress bar and completion in any order
            results = list(tqdm(
                pool.imap_unordered(worker, files_to_translate), 
                total=len(files_to_translate), 
                desc="Overall File Translation Progress", 
                unit="file", 
                dynamic_ncols=True
            ))
            
            tqdm.write("\nAll translation files processed.")

    except Exception as e:
        tqdm.write(f"An error occurred during multiprocessing: {e}")

if __name__ == '__main__':
    # Add freezing guard for Windows compatibility
    multiprocessing.freeze_support()
    main()