from config import *

gfs_parameters = {
    'WIND': {
        'full_name': 'wind',
        'level': '10m',
        'level_request': 'lev_10_m_above_ground=on',
        'var_request': 'var_UGRD=on&var_VGRD=on'
    },
    'TMP': {
        'full_name': 'temperature',
        'level': '2m',
        'level_request': 'lev_2_m_above_ground=on',
        'var_request': 'var_TMP=on'
    },
    'APCP': {
        'full_name': 'total precipitation',
        'level': 'surface',
        'level_request': 'lev_surface=on',
        'var_request': 'var_APCP=on'
    },
    'RH': {
        'full_name': 'relative humidity',
        'level': '2m',
        'level_request': 'lev_2_m_above_ground=on',
        'var_request': 'var_RH=on'
    },
    'PRES': {
        'full_name': 'pressure',
        'level': 'mean sea level',
        'level_request': 'lev_mean_sea_level=on',
        'var_request': 'var_PRMSL=on'
    },
    'WEATHER_ICON': {
        'full_name': 'additional to total_precipitation',
        'level': 'surface',
        'level_request': 'lev_surface=on&lev_entire_atmosphere=on',
        'var_request': 'var_CPOFP=on&var_TCDC=on'
    }
}


def create_gfs_request(step, parameter, date, time='00'):
    if isinstance(step, int):
        format_step = "f{:03d}".format(step)
    else:
        format_step = "f{:03d}".format(int(step)) if str(step).isdigit() else step

    url_dir = f'dir=%2Fgfs.{date}%2F{time}%2Fatmos'

    file_url = f'file=gfs.t{time}z.pgrb2.0p25.{format_step}'
    var_url = gfs_parameters[parameter]['var_request']
    level_url = gfs_parameters[parameter]['level_request']

    url = f'{GFS_URL}?{url_dir}&{file_url}&{var_url}&{level_url}'
    return url


def create_gfs_requests(cycle, forecast_step, weather_date, date, parameters=None):
    if parameters is None:
        parameters = ['APCP', 'TMP', 'WIND', 'RH', 'PRES']
    requests = []
    for param in parameters:
        for i in range(0, MAX_FORECAST_STEP + 1, forecast_step):
            step = i
            format_cycle = "{:02d}".format(cycle)
            url_weather_date = weather_date
            if i == 0 and param == 'APCP':
                format_cycle = "{:02d}".format((cycle - 6) % 24)
                new_date = date - timedelta(hours=6)
                url_weather_date = new_date.strftime('%Y%m%d')
                step = 6
            requests.append({
                'param': param,
                'request': create_gfs_request(step, param, url_weather_date, format_cycle),
                'second_request': create_gfs_request(step - 3, param, url_weather_date, format_cycle) if param == 'APCP' else None,
                'step': i
            })

    return requests

