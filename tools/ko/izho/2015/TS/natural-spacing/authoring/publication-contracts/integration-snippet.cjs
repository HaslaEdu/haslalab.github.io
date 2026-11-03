// Add the helper in the existing native-phase publication validator branch.
module.exports = (profile,witness,raw,page,item) => {
  if (profile.kind === 'source2015-complete-original-equation16-native-program-v1') {
    return require('./izho-2015-native-equation16.cjs')(profile,witness,raw,page,item);
  }
  throw new Error('This strict helper only handles the pinned original2015 equation16 witness.');
};
