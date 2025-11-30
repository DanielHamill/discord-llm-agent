import pika
import json

# input configuration data
EXCHANGE = input("Enter the exchange name: ")
HOST = input("Enter the pub/sub host: ")

# establish connection to RabbitMQ server
connection = pika.BlockingConnection(
    pika.ConnectionParameters(host=HOST, port=30672))
channel = connection.channel()
channel.exchange_declare(exchange=EXCHANGE, exchange_type='fanout')

result = channel.queue_declare(queue='', exclusive=True)
queue_name = result.method.queue
channel.queue_bind(exchange=EXCHANGE, queue=queue_name)


# start listener
print(' [*] Waiting for messages. To exit press CTRL+C')
def callback(ch, method, properties, body):
    # print paylload content, or do something else with it
    print(json.loads(body)["content"])

channel.basic_consume(
    queue=queue_name, on_message_callback=callback, auto_ack=True)

channel.start_consuming()