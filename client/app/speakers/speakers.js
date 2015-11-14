'use strict';

angular.module('scotusChatApp')
  .config(function ($stateProvider) {
    $stateProvider
      .state('speakers', {
        url: '/speakers',
        templateUrl: 'app/speakers/speakers.html',
        controller: 'SpeakersCtrl'
      })
      .state('speaker', {
        url: '/speaker/:speakerId',
        parent: 'speakers',
        templateUrl: 'app/speaker/speaker.html',
        controller: 'SpeakerCtrl'
      });
  });