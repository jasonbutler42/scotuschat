/**
 * Populate DB with sample data on server start
 * to disable, edit config/environment/index.js, and set `seedDB: false`
 */

//'use strict';

//var Speaker = require('../api/speaker/speaker.model');
//var User = require('../api/user/user.model');
// var Chat = require('../api/chat/chat.model');

// Chat.find({}).remove(function() {
//   Chat.create({
//     namefirst : 'Ms.',
//     namelast:' Ginsberg'    
//   }, {
//     namefirst : 'Mr.',
//     namelast: 'Baner'
//   });
// });


// Speaker.find({}).remove(function() {
//   Speaker.create({
//     namefirst : 'Ms.',
//     namelast:' Ginsberg'    
//   }, {
//     namefirst : 'Mr.',
//     namelast: 'Baner'
//   });
// });


// User.find({}).remove(function() {
//   User.create({
//     provider: 'local',
//     name: 'Test User',
//     email: 'test@test.com',
//     password: 'test'
//   }, {
//     provider: 'local',
//     role: 'admin',
//     name: 'Admin',
//     email: 'admin@admin.com',
//     password: 'admin'
//   }, function() {
//       console.log('finished populating users');
//     }
//   );
// });