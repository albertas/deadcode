try:
    import importlib.metadata

    __version__ = importlib.metadata.version(__package__ or __name__)
except ImportError:
    import importlib_metadata

    __version__ = importlib_metadata.version(__package__ or __name__)
