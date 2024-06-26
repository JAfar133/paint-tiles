import logging
import yaml
from logging.handlers import RotatingFileHandler
from datetime import datetime, timedelta
import json
import time
import os
import traceback

convert_params = {
    'tp': 'APCP',
    '10v': 'WIND',
    '10u': 'WIND',
    ('10v', '10u'): 'WIND',
    '2t': 'TMP',
    'r': 'RH',
    'msl': 'PRES'
}

parameter_mapping = {
    'TMP': 'temp',
    'PRES': 'pressure',
    'RH': 'humidity',
    'APCP': 'total precipitation',
    'WIND': 'wind speed, wind degree',
    'TCDC': 'cloud',
    '10u': 'wind speed, wind degree',
    '10v': 'wind speed, wind degree',
    ('10v', '10u'): 'wind speed, wind degree',
    'tp': 'total precipitation',
    'msl': 'pressure',
    '2t': 'temp',
    'r': 'humidity'
}

weather_condition_mapping = {
    'clear': '01d',
    'fewClouds': '02d',
    'scatteredClouds': '03d',
    'brokenClouds': '04d',
    'showerRain': '09d',
    'rain': '10d',
    'thunderstorm': '11d',
    'snow': '13d',
    'mist': '50d',
}

TEMP_MIN, TEMP_MAX = 200, 320
PRES_MIN, PRES_MAX = 90000, 105000
HUMIDITY_MAX = 100
WIND_MAX = 40
RAIN_MAX = 35
FROZEN_PERCENT_THRESHOLD = 35
CLOUD_MAX = 100


try:
    with open('config.yml') as f:
        config = yaml.safe_load(f)
except Exception:
    pass

tiles_path = config['tiles_path']
temp_dir = config['temp_dir']
GFS_URL = config['GFS_URL']
ECMWF_URL = config['ECMWF_URL']
MAX_FORECAST_STEP = config['MAX_FORECAST_STEP']
text_file_to_save_info = config['text_file_to_save_info']

ecmwf_parameters = [('10v', '10u'), '2t', 'msl']
gfs_parameters = ['APCP', 'RH', 'TCDC']

# start logger config
log_dir = config['log_dir']
os.makedirs(log_dir, exist_ok=True)
logger = logging.getLogger("logger")
logger.setLevel(logging.DEBUG)

log_file = os.path.join(log_dir, f"paint-gribapi-{datetime.now().strftime('%Y-%m-%d')}.log")
file_handler = RotatingFileHandler(log_file, maxBytes=10 * 1024 * 1024, backupCount=15, encoding='utf-8')
file_handler.setLevel(logging.WARNING)

console_handler = logging.StreamHandler()
console_handler.setLevel(logging.DEBUG)

file_formatter = logging.Formatter("%(asctime)s - %(levelname)s - %(pathname)s. Method - %(funcName)s - %(message)s",
                                   datefmt="%Y-%m-%d %H:%M:%S")
console_formatter = logging.Formatter("%(asctime)s - %(levelname)s - %(pathname)s. Method - %(funcName)s - %(message)s",
                                      datefmt="%Y-%m-%d %H:%M:%S")

file_handler.setFormatter(file_formatter)
console_handler.setFormatter(console_formatter)
logger.addHandler(file_handler)
logger.addHandler(console_handler)
# end logger config




def create_new_log_file():
    today = time.strftime('%Y-%m-%d')
    new_log_file = os.path.join(log_dir, f"paint-gribapi-{today}.log")

    # Заменяем старый обработчик новым
    new_file_handler = RotatingFileHandler(new_log_file, maxBytes=10 * 1024 * 1024, backupCount=15,
                                           encoding='utf-8')
    new_file_handler.setLevel(logging.WARNING)
    new_file_handler.setFormatter(file_formatter)

    logger.removeHandler(file_handler)
    logger.addHandler(new_file_handler)