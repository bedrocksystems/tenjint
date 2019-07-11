import logging
import logging.config
import inspect

logger = logging.getLogger("tenjint")
"""object: Root logger.

This global variable contains the root logger.
"""

def set_config(config):
    """Configure the logging module.

    This function can be used to configure the logging module and all loggers
    that are used by this package.

    Parameters
    ----------
    config : dict
        The new configuration.
    """
    logging.config.dictConfig(config)

class LoggerMixin(object):
    def __init__(self):
        super().__init__()
        self.__logger = None

    @property
    def _logger(self):
        """Get a logger.

        This property will return the logger for the current object. If no
        logger exists yet, the property will create one taking the package,
        module, and class name into account.

        Returns
        -------
        object
            A logger object.
        """
        if self.__logger is None:
            # Generate logger name
            mod = inspect.getmodule(self.__class__)
            if mod is None:
                mod_name = "tenjint.unknown"
            else:
                mod_name = mod.__name__

            name = ".".join([mod_name,
                             self.__class__.__name__])
            print(name)
            self.__logger = logging.getLogger(name)

        return self.__logger