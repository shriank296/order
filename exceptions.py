class RetryableException(Exception):
    pass


class NonRetryableException(Exception):
    pass


class DatabaseException(RetryableException):
    pass


class OrderNotFound(NonRetryableException):
    def __init__(self, order_id):
        self.order_id = order_id
        super().__init__(f"Order with id:{order_id} not found")


class InvalidMessage(NonRetryableException):
    pass
