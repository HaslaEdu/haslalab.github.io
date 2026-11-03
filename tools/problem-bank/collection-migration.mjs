// Lossless, offline SQL planning for the two legacy collection CHECK constraints.
import {BANK_DISCIPLINES} from '../../community/src/problem-bank-catalogue.js';
export function collectionMigration({table,sql,columns,indexes=[]}){
 if(!['bank_question_facets','bank_source_presentations'].includes(table)||typeof sql!=='string'||!Array.isArray(columns)||!columns.length||columns.some(c=>!/^[a-z_][a-z0-9_]*$/.test(c)))throw Error('Invalid collection migration input');
 const old=/collection\s+IN\s*\(\s*'physics'\s*,\s*'astronomy'\s*\)/i;
 if(!old.test(sql)){if(BANK_DISCIPLINES.every(x=>sql.includes("'"+x+"'")))return {changed:false,sql:''};throw Error('Unrecognized collection constraint');}
 const temporary=table+'__collections_v2',name=new RegExp('^(CREATE\\s+TABLE\\s+(?:IF\\s+NOT\\s+EXISTS\\s+)?)["\\[]?'+table+'["\\]]?','i');
 if(!name.test(sql))throw Error('Unexpected collection table DDL');
 const create=sql.replace(name,'$1'+temporary).replace(old,"collection IN ("+BANK_DISCIPLINES.map(x=>"'"+x+"'").join(',')+")");
 if(indexes.some(x=>typeof x!=='string'||!new RegExp('^CREATE\\s+(?:UNIQUE\\s+)?INDEX\\s+[a-z_][a-z0-9_]*\\s+ON\\s+["\\[]?'+table+'["\\]]?\\s*\\(','i').test(x)))throw Error('Unexpected collection index');
 const list=columns.join(',');return {changed:true,sql:'-- Atomic D1 file import. Snapshot and compare every existing row before/after use.\n'+create.replace(/;?$/,';')+'\nINSERT INTO '+temporary+'('+list+') SELECT '+list+' FROM '+table+';\nDROP TABLE '+table+';\nALTER TABLE '+temporary+' RENAME TO '+table+';\n'+indexes.map(x=>x.replace(/;?$/,';')).join('\n')+'\n'};
}
