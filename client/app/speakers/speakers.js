'use strict';

angular.module('scotusChatApp')
  .config(function ($stateProvider) {
    $stateProvider
      .state('speakers', {
        url: '/speakers',
        templateUrl: 'app/speakers/speakers.html',
        controller: 'SpeakersCtrl'
      });
  });