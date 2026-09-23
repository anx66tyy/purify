class PurifyError(Exception):
    pass


class ConfigurationError(PurifyError):
    pass


class PermissionError(PurifyError):
    pass
