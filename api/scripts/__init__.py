from logging.config import dictConfig

LOGGING_CONFIG = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'standard': {
            'format': '%(asctime)s [%(levelname)s] %(name)s: %(message)s',
            'datefmt': '%Y-%m-%d %H:%M:%S'
        },
        'detailed': {
            'format': '%(asctime)s [%(levelname)s] %(name)s:%(lineno)d: %(message)s'
        },
    },
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
            'stream': 'ext://sys.stdout',
            'formatter': 'standard',
            'level': 'INFO',
        },
    },
    'loggers': {
        '': {  # Root logger
            'handlers': ['console'],
            'level': 'DEBUG',
        },
    }
}

dictConfig(LOGGING_CONFIG)
