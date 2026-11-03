// Bind these functions to the actual publication ledger, not a copied fixture.
// The parent owns repository/ledger edits and the real-ledger public tests.
const validate=require('./izho-2019-native-source-programs.cjs');
module.exports={
 validateNativePhase(profile,witness,raw,page,item){
  if(profile.kind!==validate.kinds.PHASE)throw Error('Wrong source-bound2019 native-CID profile');
  return validate(profile,witness,raw,page,item);
 },
 validateSourceEdition(actualLedgerContract,item,readArtifact){
  // Resolve artifact IDs/hashes through the actual staged ledger. Local
  // source_path is historical provenance, not a trusted public filesystem path.
  return validate.validateEdition(actualLedgerContract,item,{readArtifact});
 },
 actualLedgerMutationCases:require('./izho-2019-native-source-mutations.cjs'),
};
