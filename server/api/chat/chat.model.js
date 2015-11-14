'use strict';

var mongoose = require('mongoose'),
    Schema = mongoose.Schema;

var ChatSchema = new Schema({
  name: String,
  intro: String,
  speakers: [{
  	tag: String,
  	behalf: String
  }],
  parts: [{
  	number: String,
  	title: String,
  	arguments:[{
  		speakerTag: String,
  		speakerAlt: String,
  		message: String
  	}]
  }],
  active: Boolean
});

module.exports = mongoose.model('Chat', ChatSchema);