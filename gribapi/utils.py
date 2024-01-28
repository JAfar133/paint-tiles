import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry


def download_file(url, output_path=None, header=None, timeout=5):
    session = requests.Session()
    retry = Retry(total=5, backoff_factor=0.1, status_forcelist=[500, 502, 503, 504])
    adapter = HTTPAdapter(max_retries=retry)
    session.mount('http://', adapter)
    session.mount('https://', adapter)

    if header:
        response = session.get(url, headers=header, timeout=timeout)
    else:
        response = session.get(url, timeout=timeout)

    if response.status_code != 200 and response.status_code != 206:
        raise Exception(f"Ошибка при загрузке файла по url = {url}. Код: {response.status_code}")
    if output_path is not None:
        with open(output_path, 'wb') as f:
            f.write(response.content)
            f.close()
    return response.content


