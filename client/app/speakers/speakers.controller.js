'use strict';

angular.module('scotusChatApp')
  .controller('SpeakersCtrl', function ($scope, $http) {
    

  	$scope.speakers = [];
    $http.get('/api/speakers/').success(function(speakers) {
      $scope.speakers = speakers;
      //socket.syncUpdates('suspects', $scope.suspectList);
    });


});
