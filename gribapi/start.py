import shutil
import sys
import tempfile
import threading
import time
from multiprocessing import Pool
from datetime import timedelta
import schedule
from utils import *
from config import *
from gdal_processes import *
from gfs_process import *
from ecmwf_process import *
from grib_to_rgb import *
import math
import traceback
from ecmwf.opendata import Client
import contextlib

"""
    Тайлы сохраняются по пути в таком формате: 
    tiles/{data_source}/{weather_date}{weather_cycle_time}/{forecast_date}{forecast_time}/{data_param}/{z}/{x}/{y}.png

    Например тайлы для ветра из ecmwf на 2023-12-08 полученные в 12:00 будут иметь следующий путь:
    1)  tiles/ecmwf/2023120812/2023120812/wind/z/x/y.png - прогноз для 0 часов
    2)  tiles/ecmwf/2023120812/2023120818/wind/z/x/y.png - прогноз для 6 часов
    3)  tiles/ecmwf/2023120812/2023120900/wind/z/x/y.png - прогноз для 12 часов
    4)  tiles/ecmwf/2023120812/2023120906/wind/z/x/y.png - прогноз для 18 часов
    5)  tiles/ecmwf/2023120812/2023120912/wind/z/x/y.png - прогноз для 24 часов
    ...
    12) tiles/ecmwf/2023120812/2023121112/wind/z/x/y.png - прогноз для 72 часов
"""


def remove_old_tiles(folder_path, days_threshold):
    current_time = datetime.now().timestamp()
    root_dirs = [d for d in os.listdir(folder_path) if os.path.isdir(os.path.join(folder_path, d))]
    deleted_folders = []
    for folder in root_dirs:
        folder_full_path = os.path.join(folder_path, folder)
        try:
            folder_mtime = os.path.getmtime(folder_full_path)
            days_difference = (current_time - folder_mtime) / (60 * 60 * 24)
            if days_difference > days_threshold:
                deleted_folders.append(folder_full_path)
                shutil.rmtree(folder_full_path)

        except Exception as e:
            logger.error(f'Ошибка при удаление файлов: {e}')
            pass
    logger.warning(f'Удалены папки и их содержимое: {deleted_folders}')


num_processors = os.cpu_count()


def run_generate_tiles_process(temp_rgb_file, temp_tiff_path, tiles_folder, temp_tiff_name, model):
    tiff_file = f'{temp_tiff_path}/{temp_tiff_name}'
    with open(temp_rgb_file, 'rb') as file:
        rgb_image = np.load(file)

    rgb_to_tif(rgb_image, tiff_file, model)
    create_tiles(tiff_file, tiles_folder)

    os.remove(temp_rgb_file)


def download_additional_apcp_data_file(cycle, weather_date, i):
    step = "f{:03d}".format(i)
    cycle = "{:02d}".format(cycle)
    url = create_gfs_request(step, 'WEATHER_ICON', weather_date, cycle)
    grib_file_path = os.path.join(temp_dir, f'WEATHER_ICON.{weather_date}{cycle}.grib2')
    download_file(url, grib_file_path)
    return grib_file_path



def get_rgb_data(grib_file_path, parameter, model, additional_grib_file=None, second_grib_file_path=None):
    rgb_data = None
    if parameter == 'WIND':
        u_data, ni, nj = read_grib_data(grib_file_path, 2)
        v_data, ni, nj = read_grib_data(grib_file_path, 3)
        rgb_data = encode_wind_to_rgb(u_data, v_data, ni, nj)
    elif parameter == 'APCP':
        if additional_grib_file is not None:
            total_precipitation_6_acc, ni, nj = read_grib_data(grib_file_path, 8)
            total_precipitation_3_acc, ni, nj = read_grib_data(second_grib_file_path, 8)
            total_precipitation = total_precipitation_6_acc - total_precipitation_3_acc
            frozen_precipitation_data, ni, nj = read_grib_data(additional_grib_file, 39)
            rgb_data = encode_precipitation_to_rgb(total_precipitation, frozen_precipitation_data, ni, nj)
    else:
        data, ni, nj = read_grib_data(grib_file_path)
        rgb_data = encode_data_to_rgb(data, ni, nj, parameter, model)

    return rgb_data


@contextlib.contextmanager
def suppress_output():
    new_target = open(os.devnull, 'w')
    old_targets = sys.stdout, sys.stderr
    try:
        sys.stdout, sys.stderr = new_target, new_target
        yield new_target
    finally:
        sys.stdout, sys.stderr = old_targets


def download_grib_file_by_request(request, grib_file_path, model):
    if model == 'GFS':
        download_file(request, grib_file_path)
    elif model == 'ECMWF':
        client = Client(source="ecmwf")
        with suppress_output():
            client.retrieve(request, grib_file_path)


def run_process(cycle, forecast_step, date, model):
    start_time = time.time()
    weather_date = date.strftime('%Y%m%d')
    weather_time = "{:02d}".format(cycle)

    pool = Pool(processes=num_processors)
    os.makedirs(temp_dir, exist_ok=True)

    if model == 'ECMWF':
        requests = create_ecmwf_requests(cycle, forecast_step, weather_date, date, ecmwf_parameters)
    elif model == 'GFS':
        requests = create_gfs_requests(cycle, forecast_step, weather_date, date, gfs_parameters)
    else:
        requests = None
    if requests is not None and len(requests) > 0:
        for request in requests:
            param = request["param"]
            i = request['step']

            step = "{:02d}".format(i)
            forecast_time = "{:02d}".format((i + cycle) % 24)
            forecast_date = (date + timedelta(hours=i)).strftime('%Y%m%d')

            grib_file_path = os.path.join(temp_dir, f'{param}.{forecast_date}{forecast_time}.grib2')
            main_request = request['request']
            second_request = request['second_request']
            additional_grib_file = None
            second_grib_file_path = None

            try:
                if param == 'APCP':
                    additional_grib_file = download_additional_apcp_data_file(cycle, weather_date, i)
                if second_request is not None:
                    second_grib_file_path = os.path.join(temp_dir,
                                                         f'{param}.{forecast_date}{forecast_time}.03acc.grib2')
                    download_grib_file_by_request(second_request, second_grib_file_path, model)

                download_grib_file_by_request(main_request, grib_file_path, model)
                rgb_data = get_rgb_data(grib_file_path, request["param"], model, additional_grib_file, second_grib_file_path)
                if rgb_data is not None:
                    tiles_folder = f'{tiles_path}/ecmwf/{weather_date}{weather_time}/{forecast_date}{forecast_time}/{request["param"].lower()}'
                    os.makedirs(tiles_folder, exist_ok=True)

                    temp_rgb_file = tempfile.NamedTemporaryFile(suffix=".npy", delete=False).name
                    np.save(temp_rgb_file, rgb_data)
                    pool.apply_async(run_generate_tiles_process,
                                     (temp_rgb_file, temp_dir, tiles_folder,
                                      f'temp.{weather_date}{step}.{request["param"]}.{model}', model))

                else:
                    logger.error("Data not available for the specified parameter number.")
            finally:
                if os.path.exists(grib_file_path):
                    os.remove(grib_file_path)
                if additional_grib_file is not None and os.path.exists(additional_grib_file):
                    os.remove(additional_grib_file)
                if second_grib_file_path is not None and os.path.exists(second_grib_file_path):
                    os.remove(second_grib_file_path)

    else:
        raise Exception("Не получилось сформировать urls для скачивания")
    pool.close()
    pool.join()
    logger.debug(f"Процесс импортирования данных модели {model} занял {time.time() - start_time} секунд")


def start(cycle, date,  model, try_count=0):
    try:
        logger.debug(
            f'Начат процесс импортирования данных модели {model} на {date.strftime("%Y-%m-%d")} для цикла = {"{:02d}".format(cycle)}:00. Попытка # {try_count + 1}')
        run_process(cycle, 6, date, model)
        logger.warning(
            f"Импортированы данные модели {model} {date.strftime('%Y-%m-%d')} для цикла = {'{:02d}'.format(cycle)}")
    except Exception as e:
        logger.error(
            f'Ошибка импортирования данных модели {model} на {date.strftime("%Y-%m-%d")} для цикла = {"{:02d}".format(cycle)}:00: : {e}', exc_info=True)
        try_count += 1

        if try_count <= 15:
            threading.Timer(3 * 60, lambda: start(cycle, date, model, try_count)).start()
        else:
            logger.error(
                f"Превышен лимит попыток. Не удается получить данные на {date.strftime('%Y-%m-%d')} для цикла = {'{:02d}'.format(cycle)}", exc_info=True)
            threading.Timer(30 * 60 * 60, lambda: start(cycle, date, model, 0)).start()


def run(cycle, date):
    date = date.replace(hour=cycle, minute=0, second=0)
    start(cycle, date, 'ECMWF')
    start(cycle, date, 'GFS')


if __name__ == "__main__":

    # ECMWF решили поставлять данные для 0 часов ночи и 12 часов дня на пол часа позже
    time_delta_6_18 = timedelta(hours=10, minutes=25)
    time_delta_0_12 = timedelta(hours=10, minutes=55)
    # Данные для ecmwf становятся доступны примерно через 10 часов 20 минут после даты формирования прогноза
    schedule.every().day.at("04:25").do(lambda: run(18, datetime.now() - time_delta_6_18))
    schedule.every().day.at("10:55").do(lambda: run(0, datetime.now() - time_delta_0_12))
    schedule.every().day.at("16:25").do(lambda: run(6, datetime.now() - time_delta_6_18))
    schedule.every().day.at("22:55").do(lambda: run(12, datetime.now() - time_delta_0_12))

    # schedule.every().day.at("03:00").do(lambda: remove_old_tiles(f'{tiles_path}/gfs/', 1))
    schedule.every().day.at("03:05").do(lambda: remove_old_tiles(f'{tiles_path}/ecmwf/', 1))
    logger.warning(f"Планировщик задач запущен")


    def is_valid_date(date_str):
        try:
            datetime.strptime(date_str, '%Y%m%d')
            return True
        except ValueError:
            return False


    def is_valid_cycle(cycle_str):
        try:
            cycle = int(cycle_str)
            return cycle in [0, 6, 12, 18]
        except ValueError:
            return False


    if len(sys.argv) >= 3:
        if len(sys.argv) % 2 != 1:
            logger.error("Некорректно переданы аргументы.")
        else:
            for i in range(1, len(sys.argv), 2):
                weather_date = sys.argv[i]
                weather_cycle = sys.argv[i + 1]

                if not is_valid_date(weather_date):
                    logger.error(f"Некорректный формат даты: {weather_date}")
                    continue

                if not is_valid_cycle(weather_cycle):
                    logger.error(f"Некорректный формат цикла: {weather_cycle}")
                    continue

                dt = datetime.strptime(weather_date, '%Y%m%d')
                dt = dt.replace(hour=int(weather_cycle))
                run(int(weather_cycle), dt)

    schedule.every().day.at("00:00").do(lambda: create_new_log_file())

    while True:
        schedule.run_pending()
        time.sleep(1)
