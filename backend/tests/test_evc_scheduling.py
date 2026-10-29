from datetime import datetime,timedelta,timezone
from unittest import TestCase
from backend.app.evc import common_availability,_aware
from fastapi import HTTPException
class EvcSchedulingIntersectionTests(TestCase):
 def setUp(self):
  self.now=datetime(2026,10,29,tzinfo=timezone.utc);self.start=self.now+timedelta(days=2);self.end=self.start+timedelta(hours=8)
 def row(self,start=None,end=None,status='available',confirmed=None):return {'start_at':start or self.start,'end_at':end or self.end,'availability_status':status,'last_confirmed_at':confirmed or self.now}
 def windows(self,p,earliest=None,latest=None):return common_availability(p,now=self.now,earliest=earliest or self.start,latest=latest or self.end,freshness_hours=72)
 def participants(self):return {k:[self.row()] for k in ['e1','e2','e3','e4','e5','institution']}
 def test_all_five_and_institution(self):self.assertEqual(self.windows(self.participants()),([(self.start,self.end)],[]))
 def test_fifth_expert_required(self):
  p=self.participants();p['e5']=[];self.assertEqual(self.windows(p),([],['e5']))
 def test_institution_required(self):
  p=self.participants();p['institution']=[];self.assertEqual(self.windows(p),([],['institution']))
 def test_stale_is_unknown(self):
  p=self.participants();p['e1']=[self.row(confirmed=self.now-timedelta(hours=73))];self.assertEqual(self.windows(p),([],['e1']))
 def test_future_confirmation_is_invalid(self):
  p=self.participants();p['e1']=[self.row(confirmed=self.now+timedelta(days=1))];self.assertEqual(self.windows(p),([],['e1']))
 def test_busy_splits_candidates(self):
  p=self.participants();p['e2'].append(self.row(self.start+timedelta(hours=3),self.start+timedelta(hours=5),'unavailable'));self.assertEqual(self.windows(p)[0],[(self.start,self.start+timedelta(hours=3)),(self.start+timedelta(hours=5),self.end)])
 def test_adjacent_windows_merge(self):
  p=self.participants();mid=self.start+timedelta(hours=4);p['e3']=[self.row(end=mid),self.row(start=mid)];self.assertEqual(self.windows(p)[0],[(self.start,self.end)])
 def test_deadline_bounds(self):
  a,b=self.start+timedelta(hours=1),self.end-timedelta(hours=1);self.assertEqual(self.windows(self.participants(),a,b)[0],[(a,b)])
 def test_no_overlap_no_slot(self):
  p=self.participants();p['e4']=[self.row(self.end+timedelta(hours=1),self.end+timedelta(hours=9))];self.assertEqual(self.windows(p)[0],[])
 def test_requires_timezone(self):
  with self.assertRaises(HTTPException):_aware('2026-11-01T10:00:00')
  self.assertEqual(_aware('2026-11-01T15:30:00+05:30'),datetime(2026,11,1,10,tzinfo=timezone.utc))
