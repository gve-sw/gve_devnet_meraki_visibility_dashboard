from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()

#DB Models
class APStatus(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), unique=False, nullable=False)
    mac = db.Column(db.String(20), unique=False, nullable=False)
    start_time = db.Column(db.DateTime, unique=False, nullable=False)
    end_time = db.Column(db.DateTime, unique=False, nullable=False)

class AP(db.Model):
    __tablename__ = 'ap'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), unique=False, nullable=False)
    mac = db.Column(db.String(20), unique=False, nullable=False)
    network = db.Column(db.String(70), unique=False, nullable=False)
    # Define relationships
    clients = db.relationship('APClient', backref='ap', lazy=True)
    bandwidths = db.relationship('APBandwidth', backref='ap', lazy=True)


class Switch(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), unique=False, nullable=False)
    mac = db.Column(db.String(20), unique=False, nullable=False)
    ports = db.relationship('SwitchPort', backref='switch', lazy=True)
    network = db.Column(db.String(70), unique=False, nullable=False)

class SwitchStatus(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), unique=False, nullable=False)
    start_time = db.Column(db.DateTime, unique=False, nullable=False)
    end_time = db.Column(db.DateTime, unique=False, nullable=False)
    mac = db.Column(db.String(20), unique=False, nullable=False)

class SwitchPort(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    switch_id = db.Column(db.Integer, db.ForeignKey('switch.id'), nullable=False)
    enabled = db.Column(db.Boolean, unique=False, nullable=False)
    allowed_vlans = db.Column(db.String(500), unique=False, nullable=False)

class System(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    start = db.Column(db.DateTime, unique=True, nullable=False)

class APClient(db.Model):
    ap_id = db.Column(db.Integer, db.ForeignKey('ap.id'), nullable=False)
    mac = db.Column(db.String(20), primary_key=True)
    name = db.Column(db.String(50), unique=False, nullable=False)
    count = db.Column(db.Integer, unique=False, nullable=False)
    alert = db.Column(db.Boolean, unique=False, nullable=False)

class APBandwidth(db.Model):
    ap_id = db.Column(db.Integer, db.ForeignKey('ap.id'), nullable=False)
    mac = db.Column(db.String(20), primary_key=True)
    name = db.Column(db.String(50), unique=False, nullable=False)
    bandwidth = db.Column(db.Integer, unique=False, nullable=False)
    alert = db.Column(db.Boolean, unique=False, nullable=False)

class Client(db.Model):
    mac = db.Column(db.String(20), primary_key=True)
    name = db.Column(db.String(50), unique=False, nullable=False)
    client_id = db.Column(db.String(20), unique=True, nullable=True)
    ip = db.Column(db.String(20), unique=False, nullable=True)
    ap = db.Column(db.String(50), unique=False, nullable=True)
    ssid = db.Column(db.String(20), unique=False, nullable=True)
    snr = db.Column(db.Integer, unique=False, nullable=True)
    rssi = db.Column(db.Integer, unique=False, nullable=True)
    vip = db.Column(db.Boolean, unique=False, nullable=False)
    alert = db.Column(db.Boolean, unique=False, nullable=False)