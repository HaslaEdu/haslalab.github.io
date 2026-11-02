"""Keep extractor references explicit; final storage validation lives in store.mjs."""
from urllib.parse import urldefrag


def source_reference(source):
    if not isinstance(source, dict) or not isinstance(source.get('revision'), str) or not source['revision']:
        raise ValueError('A source reference requires its exact revision')
    if source.get('origin') is not None:
        origin = source['origin']
        if (source.get('drive_id') is not None or not isinstance(origin, dict)
                or origin.get('kind') != 'url' or not isinstance(origin.get('url'), str)
                or not origin['url']):
            raise ValueError('A URL source reference requires an unambiguous URL origin')
        return {'origin': {'kind': 'url', 'url': urldefrag(origin['url'])[0]},
                'revision': source['revision']}
    if not isinstance(source.get('drive_id'), str) or not source['drive_id']:
        raise ValueError('A source reference requires Drive identity or an explicit URL origin')
    return {'drive_id': source['drive_id'], 'revision': source['revision']}


def source_key(source):
    reference = source_reference(source)
    if 'origin' in reference:
        return ('url', reference['origin']['url'], reference['revision'])
    return ('drive', reference['drive_id'], reference['revision'])


def select_profile_source(sources, profile, pdf_hash):
    if profile.get('source') is not None:
        if profile.get('drive_id') is not None:
            raise ValueError('A profile cannot combine legacy Drive and explicit source references')
        key = source_key(profile['source'])
        matches = [source for source in sources if source_key(source) == key and source['sha256'] == pdf_hash]
    else:
        if not profile.get('drive_id'):
            raise ValueError('A profile requires a Drive ID or an explicit source reference')
        matches = [source for source in sources
                   if source.get('drive_id') == profile['drive_id'] and source['sha256'] == pdf_hash]
    if len(matches) != 1:
        raise ValueError('Exactly one registered source revision must match the profile and PDF hash')
    return matches[0]
