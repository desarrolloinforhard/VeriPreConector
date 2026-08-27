class SynchronizationError(RuntimeError):
    code = "sync_error"

    def __init__(self, message, resource, operation):
        super().__init__(message)
        self.resource = resource
        self.operation = operation

    def as_dict(self):
        return {
            "codigo": self.code,
            "recurso": self.resource,
            "operacion": self.operation,
            "mensaje": str(self),
        }


class SynchronizationReadError(SynchronizationError):
    code = "sync_read_error"


class SynchronizationValidationError(SynchronizationError):
    code = "sync_validation_error"


class SynchronizationPersistenceError(SynchronizationError):
    code = "sync_persistence_error"
