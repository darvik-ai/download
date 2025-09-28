import requests
import time
import random
import uuid
from urllib.parse import urljoin

# Base URL - replace with your actual base URL ending with '/'
base_url = 'https://user-gen-media-assets.s3.amazonaws.com/gemini_images/'

# HTTP headers with User-Agent
headers = {
    'User-Agent': 'Mozilla/5.0 (compatible; UUIDImageChecker/1.0)'
}

def generate_unique_uuids(seen):
    while True:
        new_uuid = str(uuid.uuid4())
        if new_uuid not in seen:
            seen.add(new_uuid)
            yield new_uuid

def check_images(base_url, success_limit):
    success_urls = []
    seen_uuids = set()
    uuid_gen = generate_unique_uuids(seen_uuids)

    while len(success_urls) < success_limit:
        image_uuid = next(uuid_gen)
        img_name = image_uuid + '.png'
        url = urljoin(base_url, img_name)
        print(f'Requesting URL: {url}')
        try:
            response = requests.get(url, headers=headers, timeout=10)
            if response.status_code == 200:
                print(f'Success: {url}')
                success_urls.append(url)
            elif response.status_code == 403:
                print(f'Forbidden (403): {url}')
            else:
                print(f'Failed (status {response.status_code}): {url}')
        except Exception as e:
            print(f'Error: {e} for URL: {url}')
        delay = random.randint(120, 180)
        print(f'Sleeping for {delay} seconds\n')
        time.sleep(delay)

    return success_urls

if __name__ == '__main__':
    success_limit = 50  # Number of successful URLs to find
    print(f'Starting UUID image check until {success_limit} successes\n')
    successes = check_images(base_url, success_limit)

    with open('success_urls.txt', 'w') as f:
        for url in successes:
            f.write(url + '\n')

    print(f'Completed. Found {len(successes)} successful URLs saved to success_urls.txt')
