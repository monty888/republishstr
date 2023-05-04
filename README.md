# republishstr
Nostr events republished over a number of events, each hop the outer event is decrypted to reveal the next until the
final event is published, breaking the link of the posters ip to the final event.
see [NIP-705](https://github.com/motorina0/nips/blob/republish_events/705.md)

# poster
Runs a simple text post, type text that will be posted to nostr over n hops
as kind 1 events.

```
$ python poster.py
```

To use for other event kinds do....

# relayer

Runs a relayer service that will listen for republish events on given relay with its public key
unwrap and post them on
```
$ python relayer.py
```

# monitor
Simple service that lists the relayers it's since and when it last saw them.
```
$ python monitor.py
```