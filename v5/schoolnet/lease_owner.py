"""Versioned ownership records. Existing DNS snapshot format is not rewritten."""
import json
from pathlib import Path

class Ownership:
    def __init__(self,path,owner):self.path=Path(path);self.owner=owner
    def read(self):
        if self.path.is_symlink():raise ValueError('Ownership path is a symlink')
        if not self.path.exists():return {'schema':1,'owner':self.owner,'generation':0,'unfinished':False}
        data=json.loads(self.path.read_text())
        if set(data)!={'schema','owner','generation','unfinished'} or data['schema']!=1 or data['owner']!=self.owner or type(data['generation']) is not int or data['generation']<0 or type(data['unfinished']) is not bool:raise ValueError('Ownership record invalid; recovery required')
        return data
    def save(self,state):
        previous=self.read()
        if state['generation']<previous['generation']:raise ValueError('Old owner generation')
        from .runtime import write_json
        write_json(self.path,{'schema':1,'owner':self.owner,**state})
