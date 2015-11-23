'use strict';

angular.module('scotusChatApp')
  .controller('SpeakerCtrl', function (API, $scope, $rootScope, $stateParams, $http) {
    
    API.getSpeaker($stateParams.speakerId).then(function(data) {
      $scope.speaker = data;
    }); 



  });
