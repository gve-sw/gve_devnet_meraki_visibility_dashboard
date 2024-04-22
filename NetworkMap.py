from helper import meraki_api
import time


def get_org_networks(organization_id):
    print(f"ORG ID: {organization_id}")
    networks = {}
    try:
        all_networks = meraki_api("GET", f'/organizations/{organization_id}/networks')
    except Exception as e:
        print("Unable to get meraki networks... Did you update the .env file with your Meraki API Key?")
    for network in all_networks.json():
        networks[network['id']] = network

    return networks


def get_all_orgs():
    try:
        all_orgs = meraki_api('GET', '/organizations')
    except Exception as e:
        print("Unable to get meraki orgs... Did you update the .env file with your Meraki API Key?")
    return all_orgs.json()


def create_network_map():
    network_map = {}
    for org in get_all_orgs():
        if org != "errors":
            networks = get_org_networks(org['id'])
            network_map = {**network_map, **networks}

    return network_map


class NetworkMapManager:
    def __init__(self):
        self.network_map = create_network_map()

    def refresh_network_map(self, interval):
        while True:
            time.sleep(interval)
            self.network_map = create_network_map()

    def get_map(self):
        return self.network_map
