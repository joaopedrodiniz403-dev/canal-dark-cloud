"""Bounded ingestion from an operator-approved HTTPS object URL stored in a secret.

Never store the URL, query, response body, or request errors in public reports.
"""
import hashlib
import ipaddress
import os
import re
import tempfile
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path
from .engine import digest, probe, reject_test_source, validate_rights

MAX_BYTES = 2 * 1024**3
MAX_SECONDS = 900


class IngestError(ValueError):
    """Only fixed, secret-free messages may leave this module."""


def checked_url(url, hosts):
    try:
        parsed = urllib.parse.urlsplit(url)
        host = parsed.hostname
        if parsed.scheme != 'https' or not host or host not in hosts or parsed.port not in (None, 443):
            raise ValueError()
        if parsed.username is not None or parsed.password is not None or parsed.fragment:
            raise ValueError()
        try:
            ipaddress.ip_address(host)
        except ValueError:
            pass
        else:
            raise ValueError()
        if not re.fullmatch(r'(?=.{1,253}$)(?:[a-z0-9](?:[a-z0-9-]*[a-z0-9])?\.)+[a-z]{2,63}', host):
            raise ValueError()
        if host.endswith(('.localhost', '.local', '.internal', '.test', '.invalid')):
            raise ValueError()
    except (ValueError, TypeError):
        raise IngestError('MEDIA_URL_REJECTED') from None
    return url


class CheckedRedirect(urllib.request.HTTPRedirectHandler):
    def __init__(self, hosts):
        self.hosts = hosts

    def redirect_request(self, req, fp, code, msg, headers, newurl):
        checked_url(newurl, self.hosts)
        return super().redirect_request(req, fp, code, msg, headers, newurl)


def materialize(source, root, *, environ=None, opener=None, inspector=probe):
    """Return public-safe provenance; download only after rights and path validation."""
    reject_test_source(source)
    validate_rights(source)
    remote = source.get('remote')
    if remote is None:
        return {'mode': 'local'}
    if not isinstance(remote, dict):
        raise IngestError('MEDIA_CONFIG_INVALID')
    variable = remote.get('url_env', '')
    expected = remote.get('sha256', '')
    hosts = remote.get('allowed_hosts', [])
    maximum = remote.get('max_bytes', 500 * 1024**2)
    if (not isinstance(variable, str) or not re.fullmatch(r'NUVEM_MEDIA_URL_[1-5]', variable)
            or not isinstance(expected, str) or not re.fullmatch(r'[0-9a-f]{64}', expected)
            or not isinstance(hosts, list) or not hosts or not all(isinstance(h, str) for h in hosts)
            or isinstance(maximum, bool) or not isinstance(maximum, int) or not 0 < maximum <= MAX_BYTES):
        raise IngestError('MEDIA_CONFIG_INVALID')
    root = Path(root).resolve()
    name = source.get('path')
    if not isinstance(name, str) or not name:
        raise IngestError('MEDIA_PATH_REJECTED')
    target = (root/name).resolve()
    if not target.is_relative_to(root) or target == root:
        raise IngestError('MEDIA_PATH_REJECTED')
    if target.exists():
        if not target.is_file() or target.stat().st_size > maximum or digest(target) != expected:
            raise IngestError('MEDIA_EXISTING_FILE_CONFLICT')
        return {'mode': 'verified_cache', 'sha256': expected, 'bytes': target.stat().st_size}
    url = (environ if environ is not None else os.environ).get(variable)
    if not url:
        raise IngestError('MEDIA_SECRET_MISSING: ' + variable)
    checked_url(url, hosts)
    client = opener or urllib.request.build_opener(CheckedRedirect(hosts))
    target.parent.mkdir(parents=True, exist_ok=True)
    temporary = None
    started = time.monotonic()
    try:
        request = urllib.request.Request(url, headers={'User-Agent': 'NuvemEscura/1', 'Accept-Encoding': 'identity'})
        with client.open(request, timeout=30) as response:
            checked_url(response.geturl(), hosts)
            length = response.headers.get('Content-Length')
            if length is not None and (not str(length).isdigit() or int(length) > maximum):
                raise IngestError('MEDIA_SIZE_REJECTED')
            count, checksum = 0, hashlib.sha256()
            with tempfile.NamedTemporaryFile(dir=target.parent, suffix='.part', delete=False) as file:
                temporary = Path(file.name)
                while True:
                    if time.monotonic() - started > MAX_SECONDS:
                        raise IngestError('MEDIA_DOWNLOAD_DEADLINE')
                    block = response.read(min(1024**2, maximum-count+1))
                    if not block:
                        break
                    count += len(block)
                    if count > maximum:
                        raise IngestError('MEDIA_SIZE_REJECTED')
                    checksum.update(block)
                    file.write(block)
            if length is not None and count != int(length):
                raise IngestError('MEDIA_LENGTH_MISMATCH')
            if checksum.hexdigest() != expected:
                raise IngestError('MEDIA_CHECKSUM_MISMATCH')
        # Probe only local bytes; never hand a secret URL to ffmpeg or the backend.
        streams = inspector(temporary).get('streams', [])
        if not all(any(s.get('codec_type') == kind for s in streams) for kind in ('video', 'audio')):
            raise IngestError('MEDIA_AUDIO_VIDEO_REQUIRED')
        temporary.replace(target)
        return {'mode': 'downloaded', 'sha256': expected, 'bytes': count}
    except IngestError:
        raise
    except Exception:
        # urllib exceptions often embed signed URLs; suppress those details completely.
        raise IngestError('MEDIA_FETCH_OR_PROBE_FAILED') from None
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)
