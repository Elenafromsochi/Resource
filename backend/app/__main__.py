import logging

import uvicorn
from colorlog import ColoredFormatter

color_handler = logging.StreamHandler()
color_handler.setLevel(logging.DEBUG)
color_handler.setFormatter(ColoredFormatter(
    '%(log_color)s%(asctime)s.%(msecs)03d [%(levelname).1s] (%(name)s.%(funcName)s:%(lineno)d): %(message)s',
    log_colors={
        'DEBUG': 'light_blue',
        'INFO': 'green',
        'WARNING': 'yellow',
        'ERROR': 'red',
        'CRITICAL': 'bold_red',
    },
    datefmt='%Y-%m-%d %H:%M:%S',
))
logging.basicConfig(level=logging.DEBUG, handlers=[color_handler])
logging.getLogger('telethon').setLevel(logging.INFO)
logging.getLogger('pymongo').setLevel(logging.INFO)
logger = logging.getLogger(__name__)

uvicorn.run('app.main:app', host='0.0.0.0', port=8000)
