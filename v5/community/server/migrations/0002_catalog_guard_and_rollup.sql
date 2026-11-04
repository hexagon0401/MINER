INSERT OR IGNORE INTO settings VALUES('catalog_ready',0);
CREATE INDEX reports_daily_quota ON reports(fingerprint,day);
CREATE INDEX reports_school_review ON reports(school_id,status,outcome,diagnosed_at);
CREATE INDEX challenges_expiry ON challenges(expires_at);
CREATE TABLE school_coverage(school_id TEXT PRIMARY KEY REFERENCES schools(id),last_success_day TEXT,last_failure_day TEXT);
INSERT INTO school_coverage(school_id,last_success_day,last_failure_day)
 SELECT school_id,MAX(CASE WHEN outcome='success' THEN substr(diagnosed_at,1,10) END),MAX(CASE WHEN outcome='failure' THEN substr(diagnosed_at,1,10) END)
 FROM reports WHERE status='approved' GROUP BY school_id;
CREATE TRIGGER review_coverage AFTER UPDATE OF status ON reports WHEN NEW.status!=OLD.status BEGIN
 INSERT INTO school_coverage(school_id,last_success_day,last_failure_day)
 VALUES(NEW.school_id,
  (SELECT MAX(substr(diagnosed_at,1,10)) FROM reports WHERE school_id=NEW.school_id AND status='approved' AND outcome='success'),
  (SELECT MAX(substr(diagnosed_at,1,10)) FROM reports WHERE school_id=NEW.school_id AND status='approved' AND outcome='failure'))
 ON CONFLICT(school_id) DO UPDATE SET last_success_day=excluded.last_success_day,last_failure_day=excluded.last_failure_day;
 DELETE FROM school_coverage WHERE school_id=NEW.school_id AND last_success_day IS NULL AND last_failure_day IS NULL;
END;
