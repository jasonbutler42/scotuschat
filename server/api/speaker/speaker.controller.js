'use strict';

var _ = require('lodash');
var Speaker = require('./speaker.model');

// Get list of speakers
exports.index = function(req, res) {
  Speaker.find(function (err, speakers) {
    if(err) { return handleError(res, err); }
    return res.status(200).json(speakers);
  });
};

// Get a single speaker
exports.show = function(req, res) {
  Speaker.findById(req.params.id, function (err, speaker) {
    if(err) { return handleError(res, err); }
    if(!speaker) { return res.status(404).send('Not Found'); }
    return res.json(speaker);
  });
};

// Creates a new speaker in the DB.
exports.create = function(req, res) {
  Speaker.create(req.body, function(err, speaker) {
    if(err) { return handleError(res, err); }
    return res.status(201).json(speaker);
  });
};

// Updates an existing speaker in the DB.
exports.update = function(req, res) {
  if(req.body._id) { delete req.body._id; }
  Speaker.findById(req.params.id, function (err, speaker) {
    if (err) { return handleError(res, err); }
    if(!speaker) { return res.status(404).send('Not Found'); }
    var updated = _.merge(speaker, req.body);
    updated.save(function (err) {
      if (err) { return handleError(res, err); }
      return res.status(200).json(speaker);
    });
  });
};

// Deletes a speaker from the DB.
exports.destroy = function(req, res) {
  Speaker.findById(req.params.id, function (err, speaker) {
    if(err) { return handleError(res, err); }
    if(!speaker) { return res.status(404).send('Not Found'); }
    speaker.remove(function(err) {
      if(err) { return handleError(res, err); }
      return res.status(204).send('No Content');
    });
  });
};

function handleError(res, err) {
  return res.status(500).send(err);
}