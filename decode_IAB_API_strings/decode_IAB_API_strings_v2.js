import pkg from '@iabtcf/core';
const {TCString, TCModel} = pkg;

const myTCModel = TCString.decode(process.argv[2]);
console.log(JSON.stringify(myTCModel, null))
