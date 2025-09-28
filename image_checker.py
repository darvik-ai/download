import requests
import time
import random
import uuid
from urllib.parse import urljoin

base_url = 'https://user-gen-media-assets.s3.amazonaws.com/gemini_images/'

headers = {
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8',
    'Accept-Encoding': 'gzip, deflate, br, zstd',
    'Accept-Language': 'en-US,en;q=0.5',
    'Cache-Control': 'max-age=0',
    'Connection': 'keep-alive',
    'DNT': '1',
    'Host': 'user-gen-media-assets.s3.amazonaws.com',
    'Upgrade-Insecure-Requests': '1',
    'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/140.0.0.0 Safari/537.36',
    # No Referer header here
    # Sec-Fetch-* and sec-ch-ua headers can be added if needed, but usually not essential for scripts
}

def is_image_response(response):
    content_type = response.headers.get('Content-Type', '')
    # Check for PNG image type or similar image content
    if 'image/png' in content_type:
        return True
    # Additional check if content looks like PNG magic bytes in response.content
    if response.content.startswith(b'\x89PNG\r\n\x1a\n'):
        return True
    return False

def check_images(base_url, success_limit):
    success_urls = []
    seen_uuids = set()

    while len(success_urls) < success_limit:
        new_uuid = str(uuid.uuid4())
        if new_uuid in seen_uuids:
            continue
        seen_uuids.add(new_uuid)

        img_name = new_uuid + '.png'
        url = urljoin(base_url, img_name)
        print(f'Requesting URL: {url}')

        try:
            response = requests.get(url, headers=headers, timeout=10)
            if response.status_code == 200:
                if is_image_response(response):
                    print(f'Success (valid image): {url}')
                    success_urls.append(url)
                else:
                    # Likely access denied XML, log content summary
                    print(f'Failed (status 200 but invalid image or Access Denied content): {url}')
                    print('Response content preview:', response.text[:200].replace('\n', ' '))
            elif response.status_code == 403:
                print(f'Forbidden (403): {url}')
            else:
                print(f'Failed (status {response.status_code}): {url}')
        except Exception as e:
            print(f'Error: {e} for URL: {url}')

        delay = random.randint(0, 30)
        print(f'Sleeping for {delay} seconds\n')
        time.sleep(delay)

    return success_urls

if __name__ == '__main__':
    success_limit = 5
    print(f'Starting UUID image check until {success_limit} successes\n')
    successes = check_images(base_url, success_limit)

    with open('success_urls.txt', 'w') as f:
        for u in successes:
            f.write(u + '\n')

    print(f'Completed. Found {len(successes)} successful URLs saved to success_urls.txt')
