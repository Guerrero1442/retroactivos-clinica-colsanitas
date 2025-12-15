# src/exceptions.py


class ProjectError(Exception):
    """Base exception for the project."""

    pass


class DatabaseError(ProjectError):
    """Exception raised for database-related errors."""

    pass


class SourceReadError(ProjectError):
    """Exception raised when there's an error reading from a source."""

    pass


class DataProcessingError(ProjectError):
    """Exception raised for errors during data processing."""

    pass


class DataValidationError(ProjectError):
    """Exception raised for errors during data validation."""

    pass


class DateFormatError(DataValidationError):
    """Exception raised for errors in date format."""

    pass


class ConfigError(ProjectError):
    """Exception raised for configuration-related errors."""

    pass
