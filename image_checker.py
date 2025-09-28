import requests
import time
import random
import re
from urllib.parse import urljoin

# Base URL - Replace with your actual base domain URL ending with '/'
base_url = 'https://user-gen-media-assets.s3.amazonaws.com/gemini_images/'


# Given image names to identify pattern
image_names = [
    '5df452ce-91b6-433d-bb97-abe2eed3aab8.png',
    'ce164af9-72be-4713-97fa-f07257cd09dd.png'
]

# Regex pattern for UUID-based image names (simple UUID + .png)
pattern = re.compile(r'([0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12})\.png')

# Extract base UUID parts from given image names
base_uuids = []
for name in image_names:
    match = pattern.match(name)
    if match:
        base_uuids.append(match.group(1))

def generate_guesses(base_uuids, limit=10):
    guesses = []
    hex_chars = '0123456789abcdef'
    for base_uuid in base_uuids:
        for i in range(limit):
            # Change last character of UUID by cycling through hex characters
            guess_uuid = base_uuid[:-1] + hex_chars[i % 16]
            guess_name = guess_uuid + '.png'
            guesses.append(guess_name)
    return guesses

def check_images(base_url, guesses, limit):
    success_urls = []
    for guess_name in guesses:
        if len(success_urls) >= limit:
            break
        url = urljoin(base_url, guess_name)
        print(f'Requesting URL: {url}')
        try:
            response = requests.head(url, timeout=10)
            if response.status_code == 200:
                print(f'Success: {url}')
                success_urls.append(url)
            else:
                print(f'Failed (status {response.status_code}): {url}')
        except Exception as e:
            print(f'Error: {e} for URL: {url}')
        delay = random.randint(120, 180)
        print(f'Sleeping for {delay} seconds\n')
        time.sleep(delay)
    return success_urls

if __name__ == '__main__':
    # Set how many successful entries to gather
    limit = 5
    print(f'Starting with limit={limit}\n')
    guesses = generate_guesses(base_uuids, limit*2)  # Generate more to hit limit
    successes = check_images(base_url, guesses, limit)

    with open('success_urls.txt', 'w') as file:
        for url in successes:
            file.write(url + '\n')
    print(f'\nCompleted checking. {len(successes)} success URLs saved in success_urls.txt')
