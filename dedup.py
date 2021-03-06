# De-duplicate gphotos takeout
import sys
import os
import hashlib
import json

# Consts
BLOCKSIZE = 1024**2
_hashtbl = {}


def hash_file(thepath):
    hasher = hashlib.md5()
    with open(thepath, 'rb') as thefile:
        buf = thefile.read(BLOCKSIZE)
        while len(buf) > 0:
            hasher.update(buf)
            buf = thefile.read(BLOCKSIZE)
    return hasher.hexdigest()


class MediaItem:
    def __init__(self, item_name, item_path, album_name, album_path):
        self.item = {
            'name': item_name,
            'path': item_path
        }
        self.album = {
            'name': album_name,
            'path': album_path
        }


def hash_dir(album):
    for item in os.scandir(album.path):
        if not item.name.endswith('.json'):
            thehash = hash_file(item.path)
            mediaobj = MediaItem(item.name, item.path, album.name, album.path).__dict__
            if thehash in _hashtbl:
                _hashtbl[thehash].append(mediaobj)
            else:
                _hashtbl[thehash] = [mediaobj, ]


def rmdupes(dirpath):
    for item in os.scandir(dirpath):
        if not item.name.endswith('.json'):
            thehash = hash_file(item.path)
            if thehash in _hashtbl:
                print('Deleting duplicate:', item.path, end='')
                os.unlink(item)
                json_equiv = item.path + '.json'
                if os.path.exists(json_equiv):
                    print(' (and .json)')
                    os.unlink(json_equiv)
                else:
                    print()


def dedupe_albums(parentpath):
    for itemhash in _hashtbl:
        items = _hashtbl[itemhash]
        if len(items) > 1: # this media file is duplicated across multiple albums
            multialb_name = ' _, '.join([x['album']['name'] for x in items])
            multialb_path = parentpath + '/' + multialb_name
            if not os.path.exists(multialb_path):
                print('Creating multi-album:', multialb_name)
                os.mkdir(multialb_path)

            item_mv = items[0]['item']
            print('Moving', item_mv['path'], 'to', multialb_name, end='')
            os.rename(item_mv['path'], multialb_path+'/'+item_mv['name'])
            if os.path.exists(item_mv['path']+'.json'):
                print(' (and .json)')
                os.rename(item_mv['path']+'.json', multialb_path+'/'+item_mv['name']+'.json')
            else:
                print()

            # delete other items of the same hash
            for item in items[1:]:
                print('Deleting residual:', item['item']['path'], end='')
                os.unlink(item['item']['path'])
                if os.path.exists(item['item']['path']+'.json'):
                    print(' (and .json)')
                    os.unlink(item['item']['path']+'.json')
                else:
                    print()


if __name__ == '__main__':
    if len(sys.argv) < 2:
        print('Specify the dir containing all the taken-out albums')
        exit(1)

    albums = []
    nonalbums = []
    for item in os.scandir(sys.argv[1]):
        if os.path.isdir(item.path):
            if item.name.startswith('Photos from'):
                nonalbums.append(item)
            else:
                albums.append(item)

    print('=== Building hashtable ===')
    if os.path.exists('dedup_hash.json'):
        print('Loading hashes from dump')
        with open('dedup_hash.json', 'r') as dump:
            _hashtbl = json.load(dump)

    else:
        for album in albums:
            print('Hashing', album.name)
            hash_dir(album)
        print('Dumping hashes')
        with open('dedup_hash.json', 'w') as dump:
            json.dump(_hashtbl, dump)

    print('=== Deleting dupes outside albums ===')
    for nonalb in nonalbums:
        rmdupes(nonalb)

    print('=== Reorganising in-album dupes ===')
    dedupe_albums(sys.argv[1])

    print('Done.')

