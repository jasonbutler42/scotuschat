'use strict';

var mongoose = require('mongoose'),
    Schema = mongoose.Schema;

var CaseFileSchema = new Schema({
  name: String,
  date: { type : Date, default: Date.now },
  parts: [{
  	timestarted: { type : Date, default: Date.now },
  	intro: String,
  	speakers: String, 
  }],
  active: Boolean
});

module.exports = mongoose.model('CaseFile', CaseFileSchema);