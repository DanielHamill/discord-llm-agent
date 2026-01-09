from abc import ABC, abstractmethod
import json
import csv
from logging import Logger

import pika

from data import MessagePayload


def get_exporter(exporter_type, **kwargs):
    """Get an exporter instance based on the type."""
    if exporter_type == 'json':
        return JSONExporter(**kwargs)
    elif exporter_type == 'csv':
        return CSVExporter(**kwargs)
    elif exporter_type == 'amqp':
        return AMQPExporter(**kwargs)
    else:
        raise ValueError(f"Unknown exporter type: {exporter_type}")
    

class Exporter(ABC):
    """Abstract exporter interface for exporting messages."""
    @abstractmethod
    def export_message(self, logger: Logger, message: MessagePayload):
        pass

    def close(self):
        pass


class JSONExporter(Exporter):
    """Export messages to JSON
    
    Exporting to JSON is serializable and includes all message metadata but is less
    human readable than CSV."""
    def __init__(self, file_path):
        self.file = open(file_path, 'w', encoding='utf-8')

    def export_message(self, logger: Logger, message: MessagePayload):
        json.dump(message, self.file, ensure_ascii=False)
        self.file.write('\n')

    def close(self):
        self.file.close()


class CSVExporter(Exporter):
    """Export messages to CSV
    
    Exports message content only and does not include any message metadata."""
    def __init__(self, file_path):
        self.file = open(file_path, 'w', newline='', encoding='utf-8')
        self.writer = csv.DictWriter(self.file, fieldnames=['message_id', 'author', 'content', 'created_at'])

    def export_message(self, logger: Logger, message: MessagePayload):
        logger.debug(f"Exporting message: {message.content}")
        self.writer.writerow({"message_id": message.message_id, "author": message.author.name, "content": message.content, "created_at": message.created_at})

    def close(self):
        self.file.close()
        

class AMQPExporter(Exporter):
    """Export messages to an AMQP queue."""
    def __init__(self, amqp_url, queue_name):
        self.connection = pika.BlockingConnection(pika.URLParameters(amqp_url))
        self.channel = self.connection.channel()
        self.queue_name = queue_name
        self.channel.queue_declare(queue=queue_name, durable=True)

    def export_message(self, logger: Logger, message: MessagePayload):
        self.channel.basic_publish(
            exchange='',
            routing_key=self.queue_name,
            body=json.dumps(message.model_dump()),
            properties=pika.BasicProperties(
                delivery_mode=2,  # make message persistent
            ))

    def close(self):
        self.connection.close()