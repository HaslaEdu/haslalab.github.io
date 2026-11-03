// Copy the helper and izho-2018-actual-negative-controls.json together.
module.exports=(profile,witness,raw,page,item)=>{if(profile.kind==='source2018-complete-original-native-program-v1')return require('./izho-2018-native-programs.cjs')(profile,witness,raw,page,item);throw new Error('Unexpected source-bound profile');};
// Also require(helper).validateLabels(exact frozen2018 stellar-label witness) for sourcepage10.
