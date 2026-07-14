#!/usr/bin/env python3
"""Verify CapSkip is running and reachable."""

import argparse
import sys


def main():
    parser = argparse.ArgumentParser(description='Check CapSkip API connectivity')
    parser.add_argument('--host', default='127.0.0.1')
    parser.add_argument('--port', type=int, default=8080)
    parser.add_argument('--api-key', default='capskip')
    args = parser.parse_args()

    try:
        import capskip
        from capskip import ApiClient
        from capskip.exceptions import ApiException, NetworkException
    except ImportError:
        print('ERROR: capskip not installed. Run: pip install -e .')
        sys.exit(1)

    client = ApiClient(host=args.host, port=args.port)
    print(f'CapSkip SDK : {capskip.__version__}')
    print(f'Target      : {client.base_url}')

    try:
        client.res(key=args.api_key, action='get', id='0')
        print('Status      : OK — CapSkip is reachable')
    except NetworkException as e:
        print(f'Status      : FAILED — {e}')
        sys.exit(1)
    except ApiException as e:
        print('Status      : OK — CapSkip is reachable')
        print(f'Response    : {e}')

    print('Try: python examples/recaptcha.py')


if __name__ == '__main__':
    main()
