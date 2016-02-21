'use strict';

var _ = require('lodash');
var Chat = require('./chat.model');
var Speaker = require('../speaker/speaker.model');

// Get list of chats
exports.index = function(req, res) {
  Chat.find(function (err, chats) {
    if(err) { return handleError(res, err); }
    return res.status(200).json(chats);
  });
};

// Get a single chat
exports.show = function(req, res) {
  var resultObj = {};
  Chat.findById(req.params.id, function (err, chat) {
    if(err) { return handleError(res, err); }
    if(!chat) { return res.status(404).send('Not Found'); }    
    resultObj = chat;
  }).then(function(err, chat) {
    Speaker.find(function (err, speakers) {   
      resultObj.speakerList = speakers;     
      return res.json(resultObj);
    });
  });
};

// Creates a new chat in the DB.
exports.create = function(req, res) {
  Chat.create(req.body, function(err, chat) {
    if(err) { return handleError(res, err); }
    return res.status(201).json(chat);
  });
};

// Updates an existing chat in the DB.
exports.update = function(req, res) {
  if(req.body._id) { delete req.body._id; }
  Chat.findById(req.params.id, function (err, chat) {
    if (err) { return handleError(res, err); }
    if(!chat) { return res.status(404).send('Not Found'); }
    var updated = _.merge(chat, req.body);
    updated.save(function (err) {
      if (err) { return handleError(res, err); }
      return res.status(200).json(chat);
    });
  });
};

// Deletes a chat from the DB.
exports.destroy = function(req, res) {
  Chat.findById(req.params.id, function (err, chat) {
    if(err) { return handleError(res, err); }
    if(!chat) { return res.status(404).send('Not Found'); }
    chat.remove(function(err) {
      if(err) { return handleError(res, err); }
      return res.status(204).send('No Content');
    });
  });
};

function handleError(res, err) {
  return res.status(500).send(err);
}