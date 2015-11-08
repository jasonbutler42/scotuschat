'use strict';

var _ = require('lodash');
var CaseFile = require('./caseFile.model');

// Get list of caseFiles
exports.index = function(req, res) {
  CaseFile.find(function (err, caseFiles) {
    if(err) { return handleError(res, err); }
    return res.status(200).json(caseFiles);
  });
};

// Get a single caseFile
exports.show = function(req, res) {
  CaseFile.findById(req.params.id, function (err, caseFile) {
    if(err) { return handleError(res, err); }
    if(!caseFile) { return res.status(404).send('Not Found'); }
    return res.json(caseFile);
  });
};

// Creates a new caseFile in the DB.
exports.create = function(req, res) {
  CaseFile.create(req.body, function(err, caseFile) {
    if(err) { return handleError(res, err); }
    return res.status(201).json(caseFile);
  });
};

// Updates an existing caseFile in the DB.
exports.update = function(req, res) {
  if(req.body._id) { delete req.body._id; }
  CaseFile.findById(req.params.id, function (err, caseFile) {
    if (err) { return handleError(res, err); }
    if(!caseFile) { return res.status(404).send('Not Found'); }
    var updated = _.merge(caseFile, req.body);
    updated.save(function (err) {
      if (err) { return handleError(res, err); }
      return res.status(200).json(caseFile);
    });
  });
};

// Deletes a caseFile from the DB.
exports.destroy = function(req, res) {
  CaseFile.findById(req.params.id, function (err, caseFile) {
    if(err) { return handleError(res, err); }
    if(!caseFile) { return res.status(404).send('Not Found'); }
    caseFile.remove(function(err) {
      if(err) { return handleError(res, err); }
      return res.status(204).send('No Content');
    });
  });
};

function handleError(res, err) {
  return res.status(500).send(err);
}