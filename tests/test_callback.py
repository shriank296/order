from unittest.mock import MagicMock, patch

from pika import BasicProperties
from pika.spec import Basic

from workers.order_worker import callback


def test_callback_success():
    mock_channel = MagicMock()
    mock_method = MagicMock()
    mock_settings = MagicMock()
    mock_session_factory = MagicMock()
    mock_session = MagicMock()
    with patch("workers.order_worker.get_app_settings", return_value=mock_settings):
        with patch(
            "workers.order_worker.get_session_factory",
            return_value=mock_session_factory,
        ):
            with patch("workers.order_worker.process_order") as mock_process_order:
                mock_session_factory.return_value.__enter__.return_value = mock_session
                body = b'{"order_id":"00000000-0000-0000-0000-000000000000"}'
                callback(mock_channel, mock_method, BasicProperties(), body)
        mock_process_order.assert_called_once_with(
            {"order_id": "00000000-0000-0000-0000-000000000000"}, mock_session
        )
        mock_channel.basic_ack.assert_called_once()
        mock_channel.basic_nack.assert_not_called()
