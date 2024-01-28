
from config import *


def create_ecmwf_requests(cycle, forecast_step, weather_date, date, parameters=None):
    if parameters is None:
        parameters = ['tp', ('10v', '10u'), '2t', 'r', 'msl']
    requests = []
    for param in parameters:
        for i in range(0, MAX_FORECAST_STEP + 1, forecast_step):
            request = {
                "time": cycle,
                "date": weather_date,
                "type": "fc",
                "step": i,
                "param": param
            }
            requests.append({
                'param': convert_params.get(param),
                'request': request,
                'second_request': None,
                'step': i
            })

    return requests
