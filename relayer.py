import asyncio
import logging

from monstr.client.client import Client
from monstr.event.event import Event
from monstr.client.event_handlers import EventHandler
from monstr.client.client import ClientPool
from util import ConfigError

class RepublishHandler(EventHandler):

    def do_event(self, the_client: Client, sub_id, evt: Event):
        print('do republish you mother fucker!')


def get_args():
    print('to get args')


async def main(args):
    # options this are defaults, TODO: from cmd line and toml file
    # relays to output to
    relays = 'ws://localhost:8081'.split(',')
    # default to main net
    network = 'any'

    def on_connect(the_client: Client):
        the_client.subscribe(sub_id='btc_txs',
                             handlers=RepublishHandler(),
                             filters={
                                 'kinds': [Event.KIND_REPUBLISH]
                             })

    print('started listening for events to republish at: %s' % relays)
    # wait listening for events
    async with ClientPool(clients=relays,
                          on_connect=on_connect) as c:
        while True:
            await asyncio.sleep(0.5)

if __name__ == "__main__":
    logging.getLogger().setLevel(logging.ERROR)
    try:
        asyncio.run(main(get_args()))
    except ConfigError as ce:
        print(ce)