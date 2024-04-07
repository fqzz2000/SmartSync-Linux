import requests
import threading
import time

def listen_for_events(url):
    print(f"Listening for events at {url}")
    while True:
        try:
            response = requests.get(url, stream=True)
            print(f"Response: {response.status_code}")
            for line in response.iter_lines():
                if line and line[0] != b':'[0]:
                    # log the line with logging
                    print(f'[{time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())}] - Event: {line}')

        except Exception as e:
            print(f"Error listening for events: {e}")


if __name__ == "__main__":
    url = 'https://vcm-39026.vm.duke.edu:5002/events/1234'
    thread = threading.Thread(target=listen_for_events, args=(url,))
    thread.daemon = True
    thread.start()
    while True:
        requests.post('https://vcm-39026.vm.duke.edu:5002/webhook', json={'list_folder': {'accounts': ['1234']}})
        time.sleep(60)