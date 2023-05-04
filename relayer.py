import asyncio
import logging
import json
from enum import Enum
from json import JSONDecodeError
from monstr.client.client import Client
from monstr.event.event import Event
from monstr.client.event_handlers import EventHandler
from monstr.client.client import ClientPool
from monstr.encrypt import Keys
from util import ConfigError


class ServiceAdvertise(Enum):
    NEVER = 0
    START = 1
    INTERVAL = 2


class RepublishHandler(EventHandler):

    def __init__(self,
                 relays,
                 keys=None,
                 advertise_at=ServiceAdvertise.NEVER,
                 # if advertise interval then time in secs to send the advertise events
                 advertise_interval=10):

        # relays we monitor for events from and advertise at if enabled
        # we may republish to other relays as relays to republish to
        # are defined in the events we receive
        self._relays = relays

        # keys we monitor at and sign with, if undefined new keys will be created
        self._keys = keys
        if self._keys is None:
            self._keys = Keys()

        # describe what advertising is doing
        self._advertise_at = advertise_at
        self._advertise_interval = advertise_interval

        if self._advertise_at in (ServiceAdvertise.START, ServiceAdvertise.INTERVAL):
            # asyncio.create_task(self._do_advertisement())
            pass

    async def republish(self, events, relays):
        async with ClientPool(relays) as cp:
            for c_evt in events:
                try:
                    c_evt = Event.from_JSON(c_evt)
                    cp.publish(c_evt)
                    logging.info('RepublishHandler::republish event republished - %s' % c_evt)
                except Exception as e:
                    logging.debug('RepublishHandler::republish error: %s relaying event - %s' % (e,
                                                                                                 c_evt) )
            await asyncio.sleep(0.5)

    def do_event(self, the_client: Client, sub_id, evt: Event):
        try:
            if not evt.content:
                # probably just an advertise event
                pass
            else:
                # get the pub_k of the sender so we can decrypt
                from_key = evt.get_tags_value('p')
                if from_key:
                    from_key = from_key[0]
                if from_key and Keys.is_hex_key(from_key):
                    # decrypt and relay
                    decrypted = evt.decrypted_content(priv_key=self._keys.private_key_hex(),
                                                      pub_key=evt.pub_key)
                    content = json.loads(decrypted)
                    asyncio.create_task(self.republish(content['events'],
                                                       evt.get_tags_value('relays')))

                else:
                    # we couldn't get pub key so can't do anything with this
                    logging.info('RepublishHandler::do_event - unable to route event: %s, bad or missing pub_k' % evt)

        except JSONDecodeError as je:
            print(je)
        except Exception as e:
            print(e)

    async def start(self):
        def on_connect(the_client: Client):
            the_client.subscribe(sub_id='republish_evts',
                                 handlers=self,
                                 filters={
                                     'kinds': [Event.KIND_REPUBLISH],
                                     '#p': [self._keys.public_key_hex()]
                                 })

        print('started listening for events to republish - %s@%s' % (self._keys.public_key_hex(),
                                                                     self._relays))
        # wait listening for events
        async with ClientPool(clients=self._relays,
                              on_connect=on_connect) as cp:
            last_add = 0
            while True:
                if self._advertise_at != ServiceAdvertise.NEVER:
                    if last_add == 0:
                        last_add = self._advertise_interval
                        add_event = Event(kind=Event.KIND_REPUBLISH,
                                          pub_key=self._keys.public_key_hex(),
                                          content='',
                                          tags=[
                                              ['p', self._keys.public_key_hex()]
                                          ])
                        add_event.sign(self._keys.private_key_hex())
                        cp.publish(add_event)
                    elif self._advertise_at == ServiceAdvertise.INTERVAL:
                        last_add -= 1

                await asyncio.sleep(1)


def get_args():
    print('to get args')


async def main(args):
    # options this are defaults, TODO: from cmd line and toml file
    # relays to output to
    relays = 'ws://localhost:8081'.split(',')
    # relays = 'wss://nostr-pub.wellorder.net'
    # keys for the relayer, we'll pick up messages to this pub_k only
    my_keys = Keys()
    # my_keys = Keys('b1545404b863e0c9de9670496d216154b76b8ad8e3aa0a4639a76a478dfce9a4')

    my_republish = RepublishHandler(
        relays=relays,
        keys=my_keys,
        advertise_at=ServiceAdvertise.INTERVAL
    )

    await my_republish.start()




if __name__ == "__main__":
    logging.getLogger().setLevel(logging.DEBUG)
    try:
        asyncio.run(main(get_args()))
    except ConfigError as ce:
        print(ce)