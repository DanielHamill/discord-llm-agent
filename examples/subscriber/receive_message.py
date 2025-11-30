import pika
import json

EXCHANGE = input("Enter the exchange name: ")
HOST = input("Enter the pub/sub host: ")

connection = pika.BlockingConnection(
    pika.ConnectionParameters(host=HOST, port=30672))
channel = connection.channel()

channel.exchange_declare(exchange=EXCHANGE, exchange_type='fanout')

result = channel.queue_declare(queue='', exclusive=True)
queue_name = result.method.queue

channel.queue_bind(exchange=EXCHANGE, queue=queue_name)

print(' [*] Waiting for messages. To exit press CTRL+C')

def callback(ch, method, properties, body):
    print(json.loads(body)["content"])

channel.basic_consume(
    queue=queue_name, on_message_callback=callback, auto_ack=True)

channel.start_consuming()