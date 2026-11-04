import {Problem,requireValue} from './protocol';
export async function review(db:D1Database,id:string,action:'approve'|'reject'|'revoke',reason:string,actor:string) {
  requireValue(reason.trim().length>=3 && reason.length<=500 && actor.trim().length>0 && actor.length<100,'review_reason_and_actor_required');
  const status={approve:'approved',reject:'rejected',revoke:'revoked'}[action];
  requireValue(status,'invalid_review_action');
  const previous=await db.prepare('SELECT status FROM reports WHERE id=?').bind(id).first<{status:string}>();
  if(!previous) throw new Problem(404,'report_not_found');
  const allowed=action==='approve'?['pending','rejected']:action==='reject'?['pending']:['approved'];
  if(!allowed.includes(previous.status)) throw new Problem(409,'invalid_review_transition');
  await db.prepare('UPDATE reports SET status=?,review_reason=?,reviewed_by=? WHERE id=? AND status=?').bind(status,reason,actor,id,previous.status).run();
  return {id,status};
}
