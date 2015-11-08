'use strict';

var mongoose = require('mongoose'),
    Schema = mongoose.Schema;

var SpeakerSchema = new Schema({
  namefirst: String,
  namelast: String,
  title: String,
  abreviation: String,
  //date: { type : Date, default: Date.now },
  bench: Boolean,
  image: String,
  gender: String,
  birthdate: { type : Date},
  active: Boolean
});

module.exports = mongoose.model('Speaker', SpeakerSchema);