import asyncio
import logging
import random
import json
from aioconsole import ainput
from copy import copy
from monstr.client.client import ClientPool, Client
from monstr.event.event import Event
from monstr.encrypt import Keys
from util import ConfigError


def get_args():
    pass


class RouteException(Exception):
    pass


class RouterService:
    """
        tracks re-publishers and can be used to create the wrapped republish events
        pretty simple implementation many other things could/should be taken into consideration
        when relaying events e.g. maybe monitor for bad relays ( that are not sending on messages...)
        by sending a message on through a relay and seeing if the unwrapped version makes it to the network
    """
    def __init__(self,
                 relays,
                 preferred_peers=None,
                 min_hops=1,
                 enable_discovery=True,
                 keys=None):

        # relayers handed into, this will be selected from first and only if there are not
        # enough will we use peers we descovered
        # in future we may want track so info on peers to better pick but for now just keep the pkeys
        self._preferred_peers = [c_peer for c_peer in preferred_peers]

        # peers discovered by seeing messages posted by them
        self._discovered_peers = []

        # discovered_peers will only be added if this is true else only preferred peers will ever be available
        self._enable_discovery = enable_discovery

        # min n hops for routes unless otherwise supplied
        self._min_hops = min_hops

        # suggested relays for the relayer to use in wrapped events
        # also if monitor network these are the relays we look at for events
        self._relays = relays
        if isinstance(relays, str):
            self._relays = relays.split(',')

        # keys used for the first message to be relayed, if None then new keys will be generated each time
        self._keys = keys

        self._clients = None

    def get_route(self, min_hops=None):
        """
            select a route from available relayers, at the moment this is random except
            preferrerd_peers will always be selected ahead of discovered peers
            in future we might want to take other metrics into account, for example last seen for discovered peers
        """
        ret = []
        if min_hops is None:
            min_hops = self._min_hops
        print('attempting to create a route with %s hops' % min_hops)

        # first we'll select as many as we can from the preferred peers
        select_from = copy(self._preferred_peers)
        random.shuffle(select_from)
        ret = select_from[:min_hops]

        # managed to create with only our preferred peers
        if len(ret) >= min_hops:
            logging.info('ServiceIndexer::get_route - route creation with only preferred peers')
        # didn't mange to create with only preferred peers but we have discovered some, try those
        elif self._discovered_peers:
            logging.info('ServiceIndexer::get_route - need more relays, adding selection from discovered peers')
            select_from = copy(self._discovered_peers)
            random.shuffle(select_from)
            ret = (ret + select_from)[:min_hops]



        if len(ret) < min_hops:
            raise RouteException('ServiceIndexer::get_route - unable to create route of %s hops with available peers' % min_hops)

        return ret

    def _get_wrapped_event(self, evts, use_keys, hop_key) -> Event:
        ret = Event(kind=Event.KIND_REPUBLISH,
                    content=json.dumps({
                        'events': [c_evt.event_data() for c_evt in evts],
                        'padding': 'TODO'
                    }),
                    pub_key=use_keys.public_key_hex(),
                    tags=[
                        ['p', hop_key],
                        ['relays'] + self._relays
                    ]
                    )
        ret.sign(use_keys.private_key_hex())
        return ret

    def create_wrapped_event(self, evts: [Event], min_hops=None) -> Event:
        c_evt: Event
        if not hasattr(evts, '__iter__'):
            evts = [evts]

        my_route = self.get_route(min_hops)

        ret = None

        for c_hop in my_route:
            if self._keys:
                use_keys = self._keys
            else:
                use_keys = Keys()

            if ret is None:
                # the very inner event (and only event if just 1 hop)
                # this is the final one to be unrapped before revealing the actual event the user wanted posted
                ret = self._get_wrapped_event(evts=evts,
                                              use_keys=use_keys,
                                              hop_key=c_hop)

            else:
                # any other hop is just a wrap around the first event and will only contain single events
                ret = self._get_wrapped_event(evts=[ret],
                                              use_keys=use_keys,
                                              hop_key=c_hop)

        print(ret)
        return ret

    def do_event(self, the_client: Client, sub_id, evt: Event):
        peer_key = evt.pub_key
        if peer_key not in set(self._preferred_peers) and \
                peer_key not in set(self._discovered_peers):
            self._discovered_peers.append(peer_key)

            print('discovered new peer - %s' % peer_key)


    async def start(self):
        def on_connect(the_client: Client):
            if self._enable_discovery:
                the_client.subscribe(sub_id='monitor_repub_adds',
                                     handlers=self,
                                     filters={
                                         'kinds': [Event.KIND_REPUBLISH]
                                     })

        self._clients = ClientPool(self._relays,
                                   on_connect=on_connect)
        asyncio.create_task(self._clients.run())

    def publish(self, evt: Event, min_hops=None):
        try:
            wrapped_evt = self.create_wrapped_event(evt,
                                                    min_hops=min_hops)
            self._clients.publish(wrapped_evt)
        except RouteException as re:
            print(re)
        except Exception as e:
            print(e)


async def main(args):
    relay = 'ws://localhost:8081'
    my_router = RouterService(relays=relay,
                              preferred_peers=['e50bf090e2bde490aae6f77fd6b298250a18dd13725e8c4e28201516bf3b3df5'],
                              min_hops=2,
                              enable_discovery=True)

    await my_router.start()

    def do_post(msg: str, keys: Keys=None):
        if keys is None:
            keys = Keys()

        # the actual final event we want to put out
        n_evt = Event(kind=Event.KIND_TEXT_NOTE,
                      content=msg,
                      pub_key=keys.public_key_hex())
        n_evt.sign(keys.private_key_hex())
        my_router.publish(n_evt)

    while True:
        send_txt = await ainput('>')
        do_post(send_txt)

if __name__ == "__main__":
    logging.getLogger().setLevel(logging.DEBUG)
    try:
        asyncio.run(main(get_args()))
    except ConfigError as ce:
        print(ce)