""" Copyright (c) 2021 Cisco and/or its affiliates.
This software is licensed to you under the terms of the Cisco Sample
Code License, Version 1.1 (the "License"). You may obtain a copy of the
License at
           https://developer.cisco.com/docs/licenses
All use of the material herein must be in accordance with the terms of
the License. All rights not expressly granted by the License are
reserved. Unless required by applicable law or agreed to separately in
writing, software distributed under the License is distributed on an "AS
IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express
or implied.
"""

# Import Section
from flask import Flask, render_template, request, redirect, send_file, Response
from datetime import datetime
import requests
import json
from dotenv import load_dotenv
import os
from io import BytesIO
import time
from models import db, APStatus, System, APClient, APBandwidth, Client, SwitchStatus, AP, Switch
from sqlalchemy_utils import database_exists
from threading import Thread
from poll_ap import poll_ap_status, get_all_aps, poll_ap_client, poll_ap_bandwidth, poll_client_performance, alert, poll_switch_status, poll_switch_ports, get_all_switches, poll_devices
from helper import getSystemTimeAndLocation, meraki_api, time_between
from xlsxwriter.workbook import Workbook
from NetworkMap import NetworkMapManager
from sqlalchemy import func
from flask_cors import CORS

# load all environment variables
load_dotenv()
DB_PATH = os.getenv("DB_PATH")
AP_BANDWIDTH_THRESHOLD = os.getenv("BANDWIDTH_THRESHOLD")
#MERAKI_SCANNING_VALIDATOR = os.getenv("MERAKI_SCANNING_VALIDATOR")

#Startup functions
def on_startup():
    # Create an instance of NetworkMapManager
    network_map_manager = NetworkMapManager()
    print(network_map_manager.get_map())

    # Adjusted to use the instance method directly
    network_mapping_service = Thread(target=network_map_manager.refresh_network_map, args=(3000,))
    network_mapping_service.daemon = True
    network_mapping_service.start()

    # start polling devices
    devices_thread = Thread(target=poll_devices, args=(network_map_manager,))
    devices_thread.daemon = True
    devices_thread.start()


    # start polling AP status
    ap_status_thread = Thread(target=poll_ap_status)
    ap_status_thread.daemon = True
    ap_status_thread.start()

    # start polling AP clients
    ap_client_thread = Thread(target=poll_ap_client)
    ap_client_thread.daemon = True
    ap_client_thread.start()

    # start polling AP bandwidth
    ap_bandwidth_thread = Thread(target=poll_ap_bandwidth)
    ap_bandwidth_thread.daemon = True
    ap_bandwidth_thread.start()

    # start polling Client performance
    client_performance_thread = Thread(target=poll_client_performance)
    client_performance_thread.daemon = True
    client_performance_thread.start()

    # start polling Client performance
    alert_thread = Thread(target=alert)
    alert_thread.daemon = True
    alert_thread.start()

    # start polling Switch Status
    switch_status_thread = Thread(target=poll_switch_status)
    switch_status_thread.daemon = True
    switch_status_thread.start()

    # start polling Switch Port Status
    switchport_status_thread = Thread(target=poll_switch_ports)
    switchport_status_thread.daemon = True
    switchport_status_thread.start()



def create_app():
    on_startup()
    return Flask(__name__)

#Flask app
app = create_app()
CORS(app, expose_headers=["content-disposition", "x-filename"])
app.config['SQLALCHEMY_DATABASE_URI'] = DB_PATH
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# initialize DB
db.app = app
db.init_app(app)
if not database_exists(DB_PATH):
    db.create_all()

    # mark date of start using system
    now = datetime.now()
    system_start = datetime.strptime(now.strftime("%Y-%m-%d") + " 00:00:00", "%Y-%m-%d %H:%M:%S")
    system = System(start=system_start)
    db.session.add(system)
    db.session.commit()

##Routes
@app.route('/')
def get_base():
    #try:
        # get Meraki API Key
        #if MERAKI_API_KEY:
        #    headers['X-Cisco-Meraki-API-Key'] = MERAKI_API_KEY
    return redirect('/all_devices')

        #Page without error message and defined header links
        #return render_template('login.html', timeAndLocation=getSystemTimeAndLocation())
    #except Exception as e:
    #    print(e)
        #OR the following to show error message
    #    return render_template('login.html', error=True, errormessage=f"Error: {e}", timeAndLocation=getSystemTimeAndLocation())

#@app.route('/', methods=['POST'])
#def post_base():
#    try:
#        if not MERAKI_API_KEY:
#            headers['X-Cisco-Meraki-API-Key'] = request.form.get("key")
#
#        #Page without error message and defined header links
#        return redirect('/ap_uptime')
#    except Exception as e:
#        print(e)
#        #OR the following to show error message
#        return render_template('login.html', error=True, errormessage=f"ERROR: {e}", timeAndLocation=getSystemTimeAndLocation())

@app.route('/ap_uptime')
def get_ap_uptime():
    try:
        system_start = System.query.first()
        system_start = system_start.start

        #Page without error message and defined header links
        return render_template('ap_uptime.html', system_start=system_start.strftime("%Y-%m-%d"), timeAndLocation=getSystemTimeAndLocation())
    except Exception as e:
        print("An error occured during get_ap_uptime!")
        print(e)
        #OR the following to show error message
        return render_template('ap_uptime.html', error=True, errormessage=f"Error: {e}", timeAndLocation=getSystemTimeAndLocation())

@app.route('/switch_uptime')
def get_switch_uptime():
    try:
        system_start = System.query.first()
        system_start = system_start.start
        #Page without error message and defined header links
        return render_template('switch_uptime.html', system_start=system_start.strftime("%Y-%m-%d"), timeAndLocation=getSystemTimeAndLocation())
    except Exception as e:
        print("An error occured during get_switch_uptime!")
        print(e)
        #OR the following to show error message
        return render_template('switch_uptime.html', error=True, errormessage=f"Error: {e}", timeAndLocation=getSystemTimeAndLocation())

@app.route('/ap_uptime', methods=['POST'])
def post_ap_uptime():
    try:
        system_start = System.query.first()
        system_start = system_start.start

        data = json.loads(request.form['data'])
        start_time = datetime.strptime(data['start_time'] + " 00:00:00", "%Y-%m-%d %H:%M:%S")
        end_time = datetime.strptime(data['end_time'] + " 23:59:59", "%Y-%m-%d %H:%M:%S")

        # date validation
        if start_time < system_start:
            return f"Error: Start Date must be greater than system start date"
        if end_time < start_time:
            return f"Error: End Date must be greater than Start Date"

        # selected time range
        time_range = time_between(start_time, end_time)

        # add down APs data
        data_in_range = APStatus.query.filter(APStatus.start_time >= start_time, APStatus.end_time <= end_time).all()
        data_by_ap = dict()
        for ap in data_in_range:
            if ap.mac not in data_by_ap:
                data_by_ap[ap.mac] = dict()
                data_by_ap[ap.mac]['occurence'] = 0
                data_by_ap[ap.mac]['total_down'] = 0
            data_by_ap[ap.mac]['name'] = ap.name
            data_by_ap[ap.mac]['occurence'] += 1
            data_by_ap[ap.mac]['total_down'] += time_between(ap.start_time, ap.end_time)

        for key in data_by_ap:
            data_by_ap[key]['uptime'] = str(round((1 - data_by_ap[key]['total_down'] / time_range) * 100, 4))

        # add healthy APs
        aps = get_all_aps()
        for i in range(len(aps[0])):
            if aps[1][i] not in data_by_ap:
                data_by_ap[aps[1][i]] = dict()
                data_by_ap[aps[1][i]]['name'] = aps[0][i]
                data_by_ap[aps[1][i]]['occurence'] = 0
                data_by_ap[aps[1][i]]['uptime'] = 100

        return json.dumps(data_by_ap)
    except Exception as e:
        print("An error occured during post_ap_uptime!")
        print(e)
        return "Error: Unexpected error"

@app.route('/all_devices', methods=['GET'])
def get_all_devices():
    try:

        online_aps_macs = get_all_aps()[1]
        online_switches_macs = get_all_switches()[1]
        all_devices = []

        # Process all APs
        for ap in AP.query.all():
            ap_dict = {
                'id': ap.id,
                'name': ap.name,
                'mac': ap.mac,
                'type': 'AP',
                'status': 'online' if ap.mac in online_aps_macs else 'offline',
                'network': ap.network
            }
            all_devices.append(ap_dict)

        # Process all switches
        for switch in Switch.query.all():
            switch_dict = {
                'id': switch.id,
                'name': switch.name,
                'mac': switch.mac,
                'type': 'Switch',
                'status': 'online' if switch.mac in online_switches_macs else 'offline',
                'network': switch.network
            }
            all_devices.append(switch_dict)

        # Render template with all devices
        return render_template('devices.html', devices=all_devices, timeAndLocation=getSystemTimeAndLocation())

    except Exception as e:
        print(e)
        return render_template('ap_summary.html', error=True, errormessage=f"Error: {e}", timeAndLocation=getSystemTimeAndLocation())

@app.route('/switch_uptime', methods=['POST'])
def post_switch_uptime():
    try:
        system_start = System.query.first()
        system_start = system_start.start

        data = json.loads(request.form['data'])
        start_time = datetime.strptime(data['start_time'] + " 00:00:00", "%Y-%m-%d %H:%M:%S")
        end_time = datetime.strptime(data['end_time'] + " 23:59:59", "%Y-%m-%d %H:%M:%S")

        # date validation
        if start_time < system_start:
            return f"Error: Start Date must be greater than system start date"
        if end_time < start_time:
            return f"Error: End Date must be greater than Start Date"

        # selected time range
        time_range = time_between(start_time, end_time)

        # add down APs data
        data_in_range = SwitchStatus.query.filter(SwitchStatus.start_time >= start_time, SwitchStatus.end_time <= end_time).all()
        data_by_switch = dict()
        for switch in data_in_range:
            if switch.mac not in data_by_switch:
                data_by_switch[switch.mac] = dict()
                data_by_switch[switch.mac]['occurence'] = 0
                data_by_switch[switch.mac]['total_down'] = 0
            data_by_switch[switch.mac]['name'] = switch.name
            data_by_switch[switch.mac]['occurence'] += 1
            data_by_switch[switch.mac]['total_down'] += time_between(switch.start_time, switch.end_time)

        for key in data_by_switch:
            data_by_switch[key]['uptime'] = str(round((1 - data_by_switch[key]['total_down'] / time_range) * 100, 4))

        # add healthy Switches
        switches = get_all_switches()
        for i in range(len(switches[0])):
            if switches[1][i] not in data_by_switch:
                data_by_switch[switches[1][i]] = dict()
                data_by_switch[switches[1][i]]['name'] = switches[0][i]
                data_by_switch[switches[1][i]]['occurence'] = 0
                data_by_switch[switches[1][i]]['uptime'] = 100

        return json.dumps(data_by_switch)
    except Exception as e:
        print("An error occured during post_switch_uptime!")
        print(e)
        return "Error: Unexpected error"


@app.route('/download_records', methods=['POST'])
def download_records():
    try:
        data = request.get_json()
        start_time = datetime.strptime(data['start_time'] + " 00:00:00", "%Y-%m-%d %H:%M:%S")
        end_time = datetime.strptime(data['end_time'] + " 23:59:59", "%Y-%m-%d %H:%M:%S")
        data_in_range = APStatus.query.filter(APStatus.start_time >= start_time, APStatus.end_time <= end_time).all()

        # selected time range
        time_range = time_between(start_time, end_time)

        # Fetch all devices
        all_aps = AP.query.all()
        all_switches = Switch.query.all()

        # Query data for AP and Switch statuses
        ap_status = APStatus.query.filter(APStatus.start_time >= start_time, APStatus.end_time <= end_time).all()
        switch_status = SwitchStatus.query.filter(SwitchStatus.start_time >= start_time,
                                                  SwitchStatus.end_time <= end_time).all()


        # Initialize device data
        data_by_device = {}
        initialize_device_data(data_by_device, all_aps, 'AP')
        initialize_device_data(data_by_device, all_switches, 'Switch')

        # Prepare data aggregation
        aggregate_data(data_by_device, ap_status, time_range, 'AP')
        aggregate_data(data_by_device, switch_status, time_range, 'Switch')

        # Create an Excel workbook
        output = BytesIO()
        workbook = Workbook(output)
        write_device_data_to_workbook(workbook, data_by_device, 'AP')
        write_device_data_to_workbook(workbook, data_by_device, 'Switch')
        workbook.close()

        # Prepare and send the response
        output.seek(0)
        filename = f"Device_Status_Report_{data['start_time']}_to_{data['end_time']}.xlsx"
        return send_file(output, attachment_filename=filename, as_attachment=True,
                         mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
    except Exception as e:
        print(e)
        return "Error: Unexpected error occurred"
    except Exception as e:
        print(e)
        return "Error: Unexpected error"

def initialize_device_data(data_by_device, devices, device_type):
    for device in devices:
        device_key = (device.mac, device.name)
        data_by_device[device_key] = {'occurrences': 0, 'total_down': 0, 'uptime': '100%', 'type': device_type}


def aggregate_data(data_by_device, status_data, time_range, device_type):
    for status in status_data:
        device_key = (status.mac, status.name)
        if device_key in data_by_device:
            data_by_device[device_key]['occurrences'] += 1
            downtime = (status.end_time - status.start_time).total_seconds()
            data_by_device[device_key]['total_down'] += downtime
            uptime_percentage = (1 - data_by_device[device_key]['total_down'] / time_range) * 100
            data_by_device[device_key]['uptime'] = f"{uptime_percentage:.2f}%"


def write_device_data_to_workbook(workbook, data_by_device, device_type):
    worksheet = workbook.add_worksheet(f"{device_type} Status")
    headers = ["Name", "MAC Address", "Outage Occurrences", "Uptime Percentage"]
    for index, header in enumerate(headers):
        worksheet.write(0, index, header)

    row = 1
    for (mac, name), data in sorted(data_by_device.items()):
        if data['type'] == device_type:
            worksheet.write(row, 0, name)
            worksheet.write(row, 1, mac)
            worksheet.write(row, 2, data['occurrences'])
            worksheet.write(row, 3, data['uptime'])
            row += 1
            row += 1
@app.route('/vip_client')
def get_vip_client():
    try:
        vip_clients = Client.query.filter_by(vip=True)

        #Page without error message and defined header links
        return render_template('vip_client.html', vip_clients=vip_clients, timeAndLocation=getSystemTimeAndLocation())
    except Exception as e:
        print(e)
        #OR the following to show error message
        return render_template('vip_client.html', error=True, errormessage=f"Error: {e}", timeAndLocation=getSystemTimeAndLocation())

@app.route('/vip_client', methods=['POST'])
def post_vip_client():
    try:
        data = json.loads(request.form['data'])
        client_name = data['client_name']
        client_mac = data['client_mac'].lower()
        action = data['action']

        if action == "ADD":
            check_VIPClient = Client.query.filter_by(mac=client_mac)
            if check_VIPClient.count() == 0:
                new_VIPClient = Client(mac=client_mac, name=client_name, vip=True, alert=False)
                db.session.add(new_VIPClient)
            else:
                check_VIPClient.first().name = client_name
                check_VIPClient.first().vip = True
            db.session.commit()
            return "Y"
        elif action == "DELETE":
            delete_VIPClient = Client.query.filter_by(mac=client_mac).first()
            delete_VIPClient.vip = False
            db.session.commit()
            return "Y"
    except Exception as e:
        print(e)
        return f"Error: {e}"

@app.route('/client_performance')
def get_client_performance():
    try:
        clients = Client.query.all()

        #Page without error message and defined header links
        return render_template('client_performance.html', clients=clients, timeAndLocation=getSystemTimeAndLocation())
    except Exception as e:
        print(e)
        #OR the following to show error message
        return render_template('client_performance.html', error=True, errormessage=f"Error: {e}", timeAndLocation=getSystemTimeAndLocation())

#@app.route('/scanning')
#def get_scanning():
#    return MERAKI_SCANNING_VALIDATOR

#@app.route('/scanning', methods=['POST'])
#def post_scanning():
#    data = request.json
#    print(data)
#    return Response(status=200)

@app.route('/ap_summary')
def get_client_count():
    try:
        aps = AP.query.all()
        # Aggregates number of APs per network
        aps_per_network = db.session.query(
            AP.network, func.count(AP.id).label('ap_count')
        ).group_by(AP.network).all()

        # Aggregates number of clients per AP, then sums it up per network
        clients_per_network = db.session.query(
            AP.network, func.sum(APClient.count).label('client_count')
        ).join(AP, AP.id == APClient.ap_id).group_by(AP.network).all()

        # Aggregates total bandwidth per network
        bandwidth_per_network = db.session.query(
            AP.network, func.sum(APBandwidth.bandwidth).label('total_bandwidth')
        ).join(AP, AP.id == APBandwidth.ap_id).group_by(AP.network).all()

        # Initialize the network summary dictionary
        network_summary = {net[0]: {'ap_count': net[1], 'client_count': 0, 'total_bandwidth': 0} for net in
                           aps_per_network}

        # Update the dictionary with client counts
        for net in clients_per_network:
            if net[0] in network_summary:
                network_summary[net[0]]['client_count'] = net[1]

        # Update the dictionary with bandwidth totals
        for net in bandwidth_per_network:
            if net[0] in network_summary:
                network_summary[net[0]]['total_bandwidth'] = net[1]

        print(network_summary)
        BANDWIDTH_THRESHOLD = int(AP_BANDWIDTH_THRESHOLD) * len(network_summary)
        #Page without error message and defined header links
        return render_template('ap_summary.html', aps_data=aps, network_summary=network_summary, BANDWIDTH_THRESHOLD=int(BANDWIDTH_THRESHOLD), timeAndLocation=getSystemTimeAndLocation())
    except Exception as e:
        print(e)
        #OR the following to show error message
        return render_template('ap_summary.html', error=True, errormessage=f"Error: {e}", timeAndLocation=getSystemTimeAndLocation())

@app.route('/bandwidth')
def get_bandwidth():
    try:
        aps = AP.query.all()
        aps_bandwidth = APBandwidth.query.all()
        # Aggregates number of APs per network
        aps_per_network = db.session.query(
            AP.network, func.count(AP.id).label('ap_count')
        ).group_by(AP.network).all()

        # Aggregates number of clients per AP, then sums it up per network
        clients_per_network = db.session.query(
            AP.network, func.sum(APClient.count).label('client_count')
        ).join(AP, AP.id == APClient.ap_id).group_by(AP.network).all()

        # Aggregates total bandwidth per network
        bandwidth_per_network = db.session.query(
            AP.network, func.sum(APBandwidth.bandwidth).label('total_bandwidth')
        ).join(AP, AP.id == APBandwidth.ap_id).group_by(AP.network).all()

        # Initialize the network summary dictionary
        network_summary = {net[0]: {'ap_count': net[1], 'client_count': 0, 'total_bandwidth': 0} for net in
                           aps_per_network}

        # Update the dictionary with client counts
        for net in clients_per_network:
            if net[0] in network_summary:
                network_summary[net[0]]['client_count'] = net[1]

        # Update the dictionary with bandwidth totals
        for net in bandwidth_per_network:
            if net[0] in network_summary:
                network_summary[net[0]]['total_bandwidth'] = net[1]

        print(network_summary)

        #Page without error message and defined header links
        return render_template('bandwidth.html', aps_bandwidth=aps_bandwidth, aps_data=aps, timeAndLocation=getSystemTimeAndLocation())
    except Exception as e:
        print(e)
        #OR the following to show error message
        return render_template('bandwidth.html', error=True, errormessage=f"Error: {e}", timeAndLocation=getSystemTimeAndLocation())


#Main Function
if __name__ == "__main__":
    app.run(host='0.0.0.0', debug=True, port=5555)

