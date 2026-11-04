PRAGMA foreign_keys=ON;
CREATE TABLE catalog_meta(key TEXT PRIMARY KEY,value TEXT NOT NULL);
CREATE TABLE schools(id TEXT PRIMARY KEY,name TEXT NOT NULL,level TEXT NOT NULL CHECK(level IN ('high','middle','elementary')),province TEXT NOT NULL,district TEXT NOT NULL,address TEXT NOT NULL,search_name TEXT NOT NULL,search_region TEXT NOT NULL,active INTEGER NOT NULL DEFAULT 1);
CREATE INDEX schools_region ON schools(level,province,district);
CREATE TABLE challenges(id TEXT PRIMARY KEY,nonce TEXT NOT NULL,fingerprint TEXT NOT NULL,expires_at INTEGER NOT NULL,created_at INTEGER NOT NULL,used INTEGER NOT NULL DEFAULT 0);
CREATE INDEX challenges_owner ON challenges(fingerprint,created_at);
CREATE TABLE reports(id TEXT PRIMARY KEY,school_id TEXT NOT NULL REFERENCES schools(id),fingerprint TEXT NOT NULL,day TEXT NOT NULL,diagnosed_at TEXT NOT NULL,created_at INTEGER NOT NULL,outcome TEXT NOT NULL CHECK(outcome IN ('success','failure')),status TEXT NOT NULL DEFAULT 'pending' CHECK(status IN ('pending','approved','rejected','revoked')),payload TEXT NOT NULL,payload_hash TEXT NOT NULL,public_key TEXT NOT NULL,signature TEXT NOT NULL,source TEXT NOT NULL CHECK(source IN ('online','offline_review')),review_reason TEXT NOT NULL DEFAULT '',reviewed_by TEXT NOT NULL DEFAULT '',UNIQUE(fingerprint,school_id,day));
CREATE INDEX reports_public ON reports(status,outcome,school_id);
CREATE TABLE review_audit(id INTEGER PRIMARY KEY AUTOINCREMENT,report_id TEXT NOT NULL,previous_status TEXT NOT NULL,status TEXT NOT NULL,reason TEXT NOT NULL,actor TEXT NOT NULL,at INTEGER NOT NULL);
CREATE TABLE settings(key TEXT PRIMARY KEY,value INTEGER NOT NULL);
INSERT INTO settings VALUES('snapshot_sequence',0);
CREATE TRIGGER report_quota BEFORE INSERT ON reports BEGIN
 SELECT CASE WHEN (SELECT count(*) FROM reports WHERE fingerprint=NEW.fingerprint AND day=NEW.day)>=3 THEN RAISE(ABORT,'daily_quota') END;
END;
CREATE TRIGGER review_transition BEFORE UPDATE OF status ON reports WHEN NEW.status!=OLD.status BEGIN
 SELECT CASE WHEN NOT ((OLD.status IN ('pending','rejected') AND NEW.status='approved') OR (OLD.status='pending' AND NEW.status='rejected') OR (OLD.status='approved' AND NEW.status='revoked')) THEN RAISE(ABORT,'invalid_review_transition') END;
 SELECT CASE WHEN length(trim(NEW.review_reason))<3 OR length(trim(NEW.reviewed_by))<1 THEN RAISE(ABORT,'review_reason_and_actor_required') END;
END;
CREATE TRIGGER review_log AFTER UPDATE OF status ON reports WHEN NEW.status!=OLD.status BEGIN
 INSERT INTO review_audit(report_id,previous_status,status,reason,actor,at) VALUES(NEW.id,OLD.status,NEW.status,NEW.review_reason,NEW.reviewed_by,unixepoch());
 UPDATE settings SET value=value+1 WHERE key='snapshot_sequence';
END;
