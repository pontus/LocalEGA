from urllib.parse import urlencode
import argparse


parser = argparse.ArgumentParser(description='encode data for url inclusion')

parser.add_argument('domain', default=".default", help='default domain')
parser.add_argument('service', help='select what information to encode')

args = parser.parse_args()

if args.service == 'cega':

    data = {'server_name_indication': f'cega-mq{args.domain}'}

elif args.service == 'db':

    data = {'application_name': 'LocalEGA',
            'sslmode': 'verify-full',
            'sslcert': '/etc/ega/ssl.cert',
            'sslkey': '/etc/ega/ssl.key.lega',
            'sslrootcert': '/etc/ega/CA.cert'}

else:
    data = ""

print(urlencode(data, safe='/-_.'))
