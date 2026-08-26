"""Initial schema: all application tables (model parity, pre-Phase-1 state).

Revision ID: 0001_initial
Revises: 
Create Date: 2026-08-26 00:00:00.000000

Creates the complete baseline schema in dependency order. The
`notifications` table here intentionally lacks the Phase-1 delivery-
tracking columns (`channel`, `emergency_contact_id`, `failure_reason`)
and their indexes/FK: those are added by revision 0002_notification,
keeping the Alembic chain runnable from an empty database.
"""

from alembic import op

# revision identifiers, used by Alembic.
revision = '0001_initial'
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute('''
CREATE TABLE users (
	id VARCHAR(36) NOT NULL, 
	email VARCHAR(255) NOT NULL, 
	mobile_number VARCHAR(32) NOT NULL, 
	password_hash VARCHAR(255) NOT NULL, 
	is_verified BOOL NOT NULL, 
	is_active BOOL NOT NULL, 
	created_at DATETIME NOT NULL, 
	updated_at DATETIME NOT NULL, 
	PRIMARY KEY (id)
)
    ''')
    op.execute('''
CREATE UNIQUE INDEX ix_users_email ON users (email)
    ''')
    op.execute('''
CREATE UNIQUE INDEX ix_users_mobile_number ON users (mobile_number)
    ''')
    op.execute('''
CREATE TABLE audit_logs (
	id VARCHAR(36) NOT NULL, 
	user_id VARCHAR(36), 
	action VARCHAR(255) NOT NULL, 
	resource_type VARCHAR(255) NOT NULL, 
	resource_id VARCHAR(255) NOT NULL, 
	ip_address VARCHAR(45), 
	created_at DATETIME NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(user_id) REFERENCES users (id) ON DELETE SET NULL
)
    ''')
    op.execute('''
CREATE INDEX ix_audit_logs_resource_id ON audit_logs (resource_id)
    ''')
    op.execute('''
CREATE INDEX ix_audit_logs_resource_type ON audit_logs (resource_type)
    ''')
    op.execute('''
CREATE INDEX ix_audit_logs_user_id ON audit_logs (user_id)
    ''')
    op.execute('''
CREATE TABLE chat_sessions (
	id VARCHAR(36) NOT NULL, 
	user_id VARCHAR(36) NOT NULL, 
	title VARCHAR(255) NOT NULL, 
	created_at DATETIME NOT NULL, 
	updated_at DATETIME NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(user_id) REFERENCES users (id) ON DELETE CASCADE
)
    ''')
    op.execute('''
CREATE INDEX ix_chat_sessions_user_id ON chat_sessions (user_id)
    ''')
    op.execute('''
CREATE TABLE emergency_contacts (
	id VARCHAR(36) NOT NULL, 
	user_id VARCHAR(36) NOT NULL, 
	name VARCHAR(255) NOT NULL, 
	phone VARCHAR(32) NOT NULL, 
	email VARCHAR(255), 
	relationship_type VARCHAR(128), 
	group_name VARCHAR(128), 
	priority INTEGER NOT NULL, 
	is_primary BOOL NOT NULL, 
	is_active BOOL NOT NULL, 
	created_at DATETIME NOT NULL, 
	updated_at DATETIME NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(user_id) REFERENCES users (id) ON DELETE CASCADE
)
    ''')
    op.execute('''
CREATE INDEX ix_emergency_contacts_user_id ON emergency_contacts (user_id)
    ''')
    op.execute('''
CREATE TABLE fake_calls (
	id VARCHAR(36) NOT NULL, 
	user_id VARCHAR(36) NOT NULL, 
	caller_name VARCHAR(255) NOT NULL, 
	caller_number VARCHAR(32) NOT NULL, 
	delay_seconds INTEGER NOT NULL, 
	ringtone VARCHAR(255), 
	scheduled_at DATETIME NOT NULL, 
	status ENUM('SCHEDULED','TRIGGERED','COMPLETED','CANCELLED') NOT NULL, 
	created_at DATETIME NOT NULL, 
	updated_at DATETIME NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(user_id) REFERENCES users (id) ON DELETE CASCADE
)
    ''')
    op.execute('''
CREATE INDEX ix_fake_calls_scheduled_at ON fake_calls (scheduled_at)
    ''')
    op.execute('''
CREATE INDEX ix_fake_calls_user_id ON fake_calls (user_id)
    ''')
    op.execute('''
CREATE TABLE geofences (
	id VARCHAR(36) NOT NULL, 
	user_id VARCHAR(36) NOT NULL, 
	name VARCHAR(255) NOT NULL, 
	latitude FLOAT(10) NOT NULL, 
	longitude FLOAT(10) NOT NULL, 
	radius FLOAT NOT NULL, 
	is_active BOOL NOT NULL, 
	created_at DATETIME NOT NULL, 
	updated_at DATETIME NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(user_id) REFERENCES users (id) ON DELETE CASCADE
)
    ''')
    op.execute('''
CREATE INDEX ix_geofences_user_id ON geofences (user_id)
    ''')
    op.execute('''
CREATE TABLE locations (
	id VARCHAR(36) NOT NULL, 
	user_id VARCHAR(36) NOT NULL, 
	latitude FLOAT(10) NOT NULL, 
	longitude FLOAT(10) NOT NULL, 
	accuracy FLOAT, 
	speed FLOAT, 
	timestamp DATETIME NOT NULL, 
	created_at DATETIME NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(user_id) REFERENCES users (id) ON DELETE CASCADE
)
    ''')
    op.execute('''
CREATE INDEX ix_locations_timestamp ON locations (timestamp)
    ''')
    op.execute('''
CREATE INDEX ix_locations_user_id ON locations (user_id)
    ''')
    op.execute('''
CREATE TABLE medical_information (
	id INTEGER NOT NULL AUTO_INCREMENT, 
	user_id VARCHAR(36) NOT NULL, 
	blood_group VARCHAR(16), 
	allergies VARCHAR(1000), 
	medical_conditions VARCHAR(1000), 
	medications VARCHAR(1000), 
	additional_information VARCHAR(1000), 
	created_at DATETIME NOT NULL, 
	updated_at DATETIME NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(user_id) REFERENCES users (id) ON DELETE CASCADE
)
    ''')
    op.execute('''
CREATE UNIQUE INDEX ix_medical_information_user_id ON medical_information (user_id)
    ''')
    op.execute('''
CREATE TABLE otp_verifications (
	id VARCHAR(36) NOT NULL, 
	user_id VARCHAR(36) NOT NULL, 
	otp_code VARCHAR(16) NOT NULL, 
	purpose VARCHAR(128) NOT NULL, 
	expires_at DATETIME NOT NULL, 
	is_verified BOOL NOT NULL, 
	created_at DATETIME NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(user_id) REFERENCES users (id) ON DELETE CASCADE
)
    ''')
    op.execute('''
CREATE INDEX ix_otp_verifications_user_id ON otp_verifications (user_id)
    ''')
    op.execute('''
CREATE TABLE route_requests (
	id VARCHAR(36) NOT NULL, 
	user_id VARCHAR(36) NOT NULL, 
	start_latitude FLOAT(9) NOT NULL, 
	start_longitude FLOAT(9) NOT NULL, 
	destination_latitude FLOAT(9) NOT NULL, 
	destination_longitude FLOAT(9) NOT NULL, 
	created_at DATETIME NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(user_id) REFERENCES users (id) ON DELETE CASCADE
)
    ''')
    op.execute('''
CREATE INDEX ix_route_requests_user_id ON route_requests (user_id)
    ''')
    op.execute('''
CREATE TABLE sos_incidents (
	id VARCHAR(36) NOT NULL, 
	user_id VARCHAR(36) NOT NULL, 
	latitude FLOAT NOT NULL, 
	longitude FLOAT NOT NULL, 
	status ENUM('ACTIVE','CANCELLED','RESOLVED') NOT NULL, 
	activated_at DATETIME NOT NULL, 
	cancelled_at DATETIME, 
	resolved_at DATETIME, 
	created_at DATETIME NOT NULL, 
	updated_at DATETIME NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(user_id) REFERENCES users (id) ON DELETE CASCADE
)
    ''')
    op.execute('''
CREATE INDEX ix_sos_incidents_status ON sos_incidents (status)
    ''')
    op.execute('''
CREATE INDEX ix_sos_incidents_user_id ON sos_incidents (user_id)
    ''')
    op.execute('''
CREATE TABLE threat_assessments (
	id VARCHAR(36) NOT NULL, 
	user_id VARCHAR(36) NOT NULL, 
	latitude NUMERIC(10, 6) NOT NULL, 
	longitude NUMERIC(10, 6) NOT NULL, 
	speed NUMERIC(10, 2), 
	risk_score INTEGER NOT NULL, 
	risk_level ENUM('LOW','MODERATE','HIGH','CRITICAL') NOT NULL, 
	risk_factors JSON, 
	recommendation VARCHAR(1000), 
	assessed_at DATETIME NOT NULL, 
	created_at DATETIME NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(user_id) REFERENCES users (id) ON DELETE CASCADE
)
    ''')
    op.execute('''
CREATE INDEX ix_threat_assessments_assessed_at ON threat_assessments (assessed_at)
    ''')
    op.execute('''
CREATE INDEX ix_threat_assessments_user_id ON threat_assessments (user_id)
    ''')
    op.execute('''
CREATE TABLE user_profiles (
	id INTEGER NOT NULL AUTO_INCREMENT, 
	user_id VARCHAR(36) NOT NULL, 
	full_name VARCHAR(255) NOT NULL, 
	date_of_birth DATE, 
	gender VARCHAR(32), 
	address VARCHAR(500), 
	city VARCHAR(128), 
	state VARCHAR(128), 
	profile_image VARCHAR(500), 
	created_at DATETIME NOT NULL, 
	updated_at DATETIME NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(user_id) REFERENCES users (id) ON DELETE CASCADE
)
    ''')
    op.execute('''
CREATE UNIQUE INDEX ix_user_profiles_user_id ON user_profiles (user_id)
    ''')
    op.execute('''
CREATE TABLE audio_recordings (
	id VARCHAR(36) NOT NULL, 
	user_id VARCHAR(36) NOT NULL, 
	sos_incident_id VARCHAR(36), 
	filename VARCHAR(255) NOT NULL, 
	storage_path VARCHAR(1000) NOT NULL, 
	mime_type VARCHAR(128) NOT NULL, 
	file_size INTEGER NOT NULL, 
	duration FLOAT(10), 
	recorded_at DATETIME NOT NULL, 
	created_at DATETIME NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(user_id) REFERENCES users (id) ON DELETE CASCADE, 
	FOREIGN KEY(sos_incident_id) REFERENCES sos_incidents (id) ON DELETE SET NULL
)
    ''')
    op.execute('''
CREATE INDEX ix_audio_recordings_sos_incident_id ON audio_recordings (sos_incident_id)
    ''')
    op.execute('''
CREATE INDEX ix_audio_recordings_user_id ON audio_recordings (user_id)
    ''')
    op.execute('''
CREATE TABLE chat_messages (
	id VARCHAR(36) NOT NULL, 
	session_id VARCHAR(36) NOT NULL, 
	user_id VARCHAR(36) NOT NULL, 
	`role` ENUM('USER','ASSISTANT','SYSTEM') NOT NULL, 
	message TEXT NOT NULL, 
	created_at DATETIME NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(session_id) REFERENCES chat_sessions (id) ON DELETE CASCADE, 
	FOREIGN KEY(user_id) REFERENCES users (id) ON DELETE CASCADE
)
    ''')
    op.execute('''
CREATE INDEX ix_chat_messages_role ON chat_messages (`role`)
    ''')
    op.execute('''
CREATE INDEX ix_chat_messages_session_id ON chat_messages (session_id)
    ''')
    op.execute('''
CREATE INDEX ix_chat_messages_user_id ON chat_messages (user_id)
    ''')
    op.execute('''
CREATE TABLE notifications (
	id VARCHAR(36) NOT NULL, 
	user_id VARCHAR(36) NOT NULL, 
	sos_incident_id VARCHAR(36), 
	type ENUM('INFO','WARNING','ALERT') NOT NULL, 
	recipient VARCHAR(255) NOT NULL, 
	message TEXT NOT NULL, 
	status ENUM('PENDING','SENT','FAILED') NOT NULL, 
	sent_at DATETIME, 
	created_at DATETIME NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(user_id) REFERENCES users (id) ON DELETE CASCADE, 
	FOREIGN KEY(sos_incident_id) REFERENCES sos_incidents (id) ON DELETE SET NULL
)
    ''')
    op.execute('''
CREATE INDEX ix_notifications_sos_incident_id ON notifications (sos_incident_id)
    ''')
    op.execute('''
CREATE INDEX ix_notifications_status ON notifications (status)
    ''')
    op.execute('''
CREATE INDEX ix_notifications_type ON notifications (type)
    ''')
    op.execute('''
CREATE INDEX ix_notifications_user_id ON notifications (user_id)
    ''')
    op.execute('''
CREATE TABLE route_results (
	id VARCHAR(36) NOT NULL, 
	route_request_id VARCHAR(36) NOT NULL, 
	route_type ENUM('RECOMMENDED','ALTERNATIVE') NOT NULL, 
	distance FLOAT(10) NOT NULL, 
	estimated_duration FLOAT(10) NOT NULL, 
	risk_score INTEGER NOT NULL, 
	route_data JSON NOT NULL, 
	created_at DATETIME NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(route_request_id) REFERENCES route_requests (id) ON DELETE CASCADE
)
    ''')
    op.execute('''
CREATE INDEX ix_route_results_route_request_id ON route_results (route_request_id)
    ''')
    op.execute('''
CREATE INDEX ix_route_results_route_type ON route_results (route_type)
    ''')
    op.execute('''
CREATE TABLE video_recordings (
	id VARCHAR(36) NOT NULL, 
	user_id VARCHAR(36) NOT NULL, 
	sos_incident_id VARCHAR(36), 
	filename VARCHAR(255) NOT NULL, 
	storage_path VARCHAR(1000) NOT NULL, 
	mime_type VARCHAR(128) NOT NULL, 
	file_size INTEGER NOT NULL, 
	duration FLOAT(10), 
	recorded_at DATETIME NOT NULL, 
	created_at DATETIME NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(user_id) REFERENCES users (id) ON DELETE CASCADE, 
	FOREIGN KEY(sos_incident_id) REFERENCES sos_incidents (id) ON DELETE SET NULL
)
    ''')
    op.execute('''
CREATE INDEX ix_video_recordings_sos_incident_id ON video_recordings (sos_incident_id)
    ''')
    op.execute('''
CREATE INDEX ix_video_recordings_user_id ON video_recordings (user_id)
    ''')


def downgrade() -> None:
    op.drop_table('video_recordings')
    op.drop_table('route_results')
    op.drop_table('notifications')
    op.drop_table('chat_messages')
    op.drop_table('audio_recordings')
    op.drop_table('user_profiles')
    op.drop_table('threat_assessments')
    op.drop_table('sos_incidents')
    op.drop_table('route_requests')
    op.drop_table('otp_verifications')
    op.drop_table('medical_information')
    op.drop_table('locations')
    op.drop_table('geofences')
    op.drop_table('fake_calls')
    op.drop_table('emergency_contacts')
    op.drop_table('chat_sessions')
    op.drop_table('audit_logs')
    op.drop_table('users')
