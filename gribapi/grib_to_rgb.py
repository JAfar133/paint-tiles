import random
from config import *
import eccodes
import numpy as np



def read_grib_data(file_path, parameter_number=None):
    with open(file_path, 'rb') as file:
        codes = eccodes.codes_grib_new_from_file(file)

        while codes is not None:
            if parameter_number is None or eccodes.codes_get(codes, 'parameterNumber') == parameter_number:
                ni = eccodes.codes_get(codes, 'Ni')
                nj = eccodes.codes_get(codes, 'Nj')
                data = eccodes.codes_get_values(codes)
                eccodes.codes_release(codes)
                return data, ni, nj

            eccodes.codes_release(codes)
            codes = eccodes.codes_grib_new_from_file(file)
        file.close()
    return None


def encode_data(data, max_value, min_value):
    return np.clip((data - min_value) / (max_value - min_value), 0, 1)


def encode_data_to_rgb(data, ni, nj, data_name, model):
    if data is None:
        return None

    if data_name == 'TMP':
        red_channel = encode_data(data, TEMP_MAX, TEMP_MIN) * 255
        green_channel = np.where(data < 273, random.randint(50, 60), random.randint(70, 80))
        blue_channel = np.clip(data / 273, 0, 1) * 255

    elif data_name == 'RH':
        red_channel = encode_data(data, HUMIDITY_MAX, 0) * 255
        green_channel = np.clip(data / 6, 0, 1) * 255
        blue_channel = np.clip(data / 50, 0, 1) * 255

    elif data_name == 'PRES':
        red_channel = encode_data(data, PRES_MAX, PRES_MIN) * 255
        green_channel = np.clip(data / PRES_MIN, 0, 1) * 255
        blue_channel = np.clip(data / PRES_MIN, 0, 1) * 255

    elif data_name == 'TCDC':
        red_channel = encode_data(data, CLOUD_MAX, 0) * 255
        green_channel = np.clip(data / 40, 0, 1) * 255
        blue_channel = np.clip(data / 20, 0, 1) * 255
    else:
        return None

    rgb_image = np.stack([red_channel, green_channel, blue_channel], axis=-1)
    rgb_image = rgb_image.reshape(nj, ni, 3)
    return rgb_image


def encode_wind_to_rgb(u_data, v_data, ni, nj):
    if u_data is None or v_data is None:
        return None

    wind_speed = np.sqrt(u_data ** 2 + v_data ** 2)
    wind_direction = np.arctan2(v_data, u_data)

    normalized_direction = np.clip(abs(wind_direction) / np.pi, 0, 1)
    normalized_speed = np.clip(wind_speed / 40.0, 0, 1)

    red_channel = np.where(wind_direction < 0, random.randint(50, 60), random.randint(70, 80))
    red_channel = np.broadcast_to(red_channel, normalized_direction.shape)
    green_channel = normalized_direction * 255
    blue_channel = normalized_speed * 255

    rgb_image = np.stack([red_channel, green_channel, blue_channel], axis=-1)

    # Reshape the image
    rgb_image = rgb_image.reshape(nj, ni, 3)

    return rgb_image


def encode_precipitation_to_rgb(apcp_data, cpofp_data, ni, nj):
    if apcp_data is None or cpofp_data is None:
        return None
    red_channel = np.clip(apcp_data / 35, 0, 1) * 255
    green_channel = np.clip(np.where(cpofp_data >= 35, 1, 0), 0, 1) * 255
    blue_channel = np.clip(np.where(apcp_data > 15, 1, 0), 0, 1) * 255

    rgb_image = np.stack([red_channel, green_channel, blue_channel], axis=-1)

    rgb_image = rgb_image.reshape(nj, ni, 3)

    return rgb_image
