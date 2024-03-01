# Build Docker Image:
#   docker build -t image-name .

# Run Docker Container:
#   docker run -it --rm -v host/path/to/static:/gribapi/public -v host/path/to/logs:/gribapi/logs image-name [date1] [cycle1] [date2] [cycle2] ...
#   - [date1], [date2], ...: YYYYMMDD format.
#   - [cycle1], [cycle2], ...: Digit in [0, 6, 12, 18].
# Example: docker run -it --rm -v /opt/watsen-utils/public:/gribapi/public -v /opt/watsen-utils/logs:/gribapi/logs watsen-gribapi 20231210 0 20231210 6

# Check which GFS data is available:
#   - https://nomads.ncep.noaa.gov/gribfilter.php?ds=gfs_0p25

FROM python:3.9

ENV TZ=Europe/Moscow
RUN ln -snf /usr/share/zoneinfo/$TZ /etc/localtime && echo $TZ > /etc/timezone

WORKDIR /gribapi

COPY eccodes-2.31.0-Source.tar.gz .

RUN apt-get update && apt-get upgrade -y && \
    apt-get install -y build-essential cmake gfortran libaec-dev && \
    tar -xzf eccodes-2.31.0-Source.tar.gz && \
    mkdir build && \
    cd build && \
    cmake -DCMAKE_INSTALL_PREFIX=/usr/local ../eccodes-2.31.0-Source && \
    make -j$(nproc) && \
    make install && \
    cd ../ && \
    apt-get update && apt-get upgrade -y && \
    pip install eccodes requests numpy schedule pyyaml mysql-connector-python git+https://github.com/ecmwf/ecmwf-opendata.git && \
    apt-get install -y libgdal-dev gdal-bin && \
    pip install GDAL=="$(gdal-config --version).*" --global-option=build_ext --global-option="-I/usr/include/gdal"

ENV LD_LIBRARY_PATH=/usr/local/lib:$LD_LIBRARY_PATH
ENV PYTHONPATH=/usr/local/lib:$PYTHONPATH

ENTRYPOINT ["/bin/bash", "entrypoint.sh"]