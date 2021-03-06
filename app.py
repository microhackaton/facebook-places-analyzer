#!/usr/bin/env python
# -*- coding: utf-8 -*-
import logging
import json
import latlontool

import pika
import facebook_correlator
import settings

from service_discovery import ServiceDiscovery


def place_data(location):
    return latlontool.place_data(location["latitude"], location["longitude"])


def place_with_probability(place):
    place_extended = dict()
    place_extended["place"] = place
    place_extended["origin"] = "facebook"
    return place_extended


def prepare_json_output(data):
    f = open('fake_message.json', 'r')
    data = f.read()
    profileLocation = data["profile"]["hometown"]["location"]
    profileHometown = data["profile"]["location"]["location"]
    places = list()
    profileLocationCode = place_data(profileLocation)
    places.append(place_with_probability(profileLocationCode))
    profileHometownCode = place_data(profileHometown)
    places.append(place_with_probability(profileHometownCode))
    posts = data["posts"]
    for post in posts:
        print post["created_time"]
        if "place" in post:
            location = post["place"]["location"]
            code = place_data(location)
            places.append(place_with_probability(code))
            print post["place"]["location"]
    output = dict()
    output["corelationId"] = data["corelationId"]
    output["pairId"] = data["pairId"]
    output["places"] = places
    return output

def consume_posts(ch, method, properties, body):
    data = json.loads(body)

    output = prepare_json_output(data)
    facebook_correlator.post_localizations(output)
    print "Consuming posts: {}".format(data)

facebook_correlator_url = 'private-2876e-microservice1.apiary-mock.com'

if __name__ == '__main__':

    logging.basicConfig(
        filename=settings.LOGGING_FILE,
        level=logging.INFO,
        format=u"%(asctime)s.%(msecs).03d+0200 | %(levelname)s | | walSięGościu | | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    logging.info("Initializing app")

    logging.info("Connecting to queue")

    sd = ServiceDiscovery('/pl/pl/microhackaton', 'zookeeper.microhackathon.pl:2181')
    sd.register("facebook-places-analyser", "", 0)

    queue_host = settings.RABBITMQ_HOST

    try:
        facebook_correlator_url = sd.get_instance('common-places-correlator')
    except:
        pass

    connection = pika.BlockingConnection(
        pika.ConnectionParameters(host=queue_host)
    )

    channel = connection.channel()

    # Make sure the queue exists
    queue = channel.queue_declare()
    queue_name = queue.method.queue

    channel.queue_bind(exchange='facebook',
                   queue=queue_name)


    print ' [*] Waiting for messages. To exit press CTRL+C'

    channel.basic_consume(consume_posts, queue=queue_name)

    channel.start_consuming()
